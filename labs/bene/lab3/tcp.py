from src.buffer import SendBuffer, ReceiveBuffer
from src.connection import Connection
from src.sim import Sim
from src.tcppacket import TCPPacket


class TCP(Connection):
    """ A TCP connection between two hosts."""

    def __init__(self, transport, source_address, source_port,
                 destination_address, destination_port, app=None, window=1000,drop=[]):
        Connection.__init__(self, transport, source_address, source_port,
                            destination_address, destination_port, app)

        # -- Sender functionality

        # send window; represents the total number of bytes that may
        # be outstanding at one time
        self.window = window
        # send buffer
        self.send_buffer = SendBuffer()
        # maximum segment size, in bytes
        self.mss = 1000
        # largest sequence number that has been ACKed so far; represents
        # the next sequence number the client expects to receive
        self.sequence = 0
        # plot sequence numbers
        self.plot_sequence_header()
        # plot congestion window headers
        self.plot_window_header()
        # packets to drop
        self.drop = drop
        self.dropped = []
        # retransmission timer
        self.timer = None
        # timeout duration in seconds
        self.timeout = 1
        # RTO calculation variables
        self.rto = 1
        self.srtt = 0
        self.rttvar = 0
        # Variables for handling fast retransmit
        self.fast_enable = False
        self.last_ack = 0
        self.same_ack_count = 0
        self.fast_retransmitted = False
        # Congestion control
        self.threshold = 100000
        self.increment = 0

        # -- Receiver functionality

        # receive buffer
        self.receive_buffer = ReceiveBuffer()
        # ack number to send; represents the largest in-order sequence
        # number not yet received
        self.ack = 0

    def trace(self, message):
        """ Print debugging messages. """
        Sim.trace("TCP", message)

    def plot_sequence_header(self):
        if self.node.hostname =='n1':
            Sim.plot('sequence.csv','Time,Sequence Number,Event\n')

    def plot_sequence(self,sequence,event):
        if self.node.hostname =='n1':
            Sim.plot('sequence.csv','%s,%s,%s\n' % (Sim.scheduler.current_time(),sequence,event))

    def plot_window_header(self):
        if self.node.hostname == 'n1':
            Sim.plot('cwnd.csv','Time,Congestion Window,Threshold,Event\n')

    def plot_window(self, event):
        if self.node.hostname == 'n1':
            Sim.plot('cwnd.csv', '%s,%s,%s,%s\n' % (Sim.scheduler.current_time(), self.window, self.threshold, event))

    def receive_packet(self, packet):
        """ Receive a packet from the network layer. """
        if packet.ack_number > 0:
            # handle ACK
            self.handle_ack(packet)
        if packet.length > 0:
            # handle networks
            self.handle_data(packet)

    def set_fast_retransmit_enabled(self, val):
        self.fast_enable = val

    ''' Sender '''

    def send(self, data):
        """ Send networks on the connection. Called by the application. This code puts the
        networks to send in a send buffer that handles when the networks will be sent."""
        # Put the networks in the send buffer
        self.send_buffer.put(data)
        # Check for available bytes to send
        while self.send_buffer.available() != 0 and self.send_buffer.outstanding() < self.window:
            # Only send as many bytes as the window allows
            send_data, sequence = self.send_buffer.get(self.mss)
            self.send_packet(send_data, sequence)
            # set a timer
            if self.timer is None:
                self.timer = Sim.scheduler.add(delay=self.timeout, event='retransmit', handler=self.retransmit)

    def send_packet(self, data, sequence):
        packet = TCPPacket(source_address=self.source_address,
                           source_port=self.source_port,
                           destination_address=self.destination_address,
                           destination_port=self.destination_port,
                           body=data,
                           sequence=sequence, ack_number=self.ack)

        if sequence in self.drop and not sequence in self.dropped:
            self.dropped.append(sequence)
            self.plot_sequence(sequence,'drop')
            self.trace("%s (%d) dropping TCP segment to %d for %d" % (
                self.node.hostname, self.source_address, self.destination_address, packet.sequence))
            return

        # send the packet
        self.plot_sequence(sequence,'send')
        self.trace("%s (%d) sending TCP segment to %d for %d" % (
            self.node.hostname, self.source_address, self.destination_address, packet.sequence))
        self.transport.send_packet(packet)

        # set a timer
        if self.timer is None:
            self.timer = Sim.scheduler.add(delay=self.timeout, event='retransmit', handler=self.retransmit)

    def handle_ack(self, packet):
        """ Handle an incoming ACK. """
        self.plot_sequence(packet.ack_number - 1000,'ack')
        self.trace("%s (%d) received ACK from %d for %d" % (
            self.node.hostname, packet.destination_address, packet.source_address, packet.ack_number))

        # Handle fast retransmit
        if self.fast_enable:
            if packet.ack_number == self.last_ack:
                self.same_ack_count += 1
                if self.same_ack_count == 3 and not self.fast_retransmitted:
                    self.fast_retransmit(packet)
                    return
            else:
                # Reset fast retransmit variables
                self.same_ack_count = 0
                self.last_ack = packet.ack_number
                self.fast_retransmitted = False

        # Congestion control
        if self.window >= self.threshold:
            self.additive_increase(packet.ack_number - self.sequence)
        else:
            self.slow_start(packet.ack_number - self.sequence)


        # Update the send buffer
        self.sequence = packet.ack_number
        self.send_buffer.slide(packet.ack_number)
        # Send additional bytes from the send buffer if there are any
        while self.send_buffer.available() != 0 and self.send_buffer.outstanding() < self.window:
            # Only send as many bytes as the window allows
            send_data, sequence = self.send_buffer.get(self.mss)
            self.send_packet(send_data, sequence)

        # Calculate the SRTT and RTTVAR
        if self.srtt == 0:
            # First estimate
            self.srtt = Sim.scheduler.current_time() - packet.created
            self.rttvar = self.srtt / 2.0
        else:
            r = Sim.scheduler.current_time() - packet.created
            alpha = 0.125
            beta = 0.25
            self.rttvar = (1 - beta) * self.rttvar + beta * abs(self.srtt - r)
            self.srtt = (1 - alpha) * self.srtt + alpha * r
        # Update the RTO
        rto = self.srtt + 4 * self.rttvar
        self.rto = rto if rto >= 1.0 else 1.0

        self.cancel_timer()
        if self.send_buffer.outstanding() != 0:
            self.timer = Sim.scheduler.add(delay=self.timeout, event='retransmit', handler=self.retransmit)

    def fast_retransmit(self, packet):
        """ Retransmit networks. """
        self.trace("%s (%d) sending fast retransmit to %d for %d" % (
            self.node.hostname, packet.destination_address, packet.source_address, packet.ack_number))
        self.cancel_timer()
        self.threshold = max(self.window // 2, self.mss)
        self.threshold = self.threshold - (self.threshold % self.mss)
        self.window = self.mss
        self.increment = 0
        self.plot_window('fast retransmit')
        data, sequence = self.send_buffer.resend(self.window)
        if len(data) == 0:
            return
        self.send_packet(data, sequence)
        if self.timer is None:
            self.timer = Sim.scheduler.add(delay=self.timeout, event='retransmit', handler=self.retransmit)
        self.fast_retransmitted = True

    def retransmit(self, event):
        """ Retransmit networks. """
        self.trace("%s (%d) retransmission timer fired" % (self.node.hostname, self.source_address))
        self.threshold = max(self.window // 2, self.mss)
        self.threshold = self.threshold - (self.threshold % self.mss)
        self.window = self.mss
        self.increment = 0
        self.plot_window('retransmission')
        data, sequence = self.send_buffer.resend(self.window)
        # Handle the case when we get a misfire on retransmission and their isn't any data left
        # in the send buffer
        if len(data) == 0:
            self.cancel_timer()
            return
        self.send_packet(data, sequence)
        self.timer = Sim.scheduler.add(delay=self.rto, event='retransmit', handler=self.retransmit)

    def slow_start(self, bytes):
        self.trace("%s (%d) incrementing slow start" % (self.node.hostname, self.source_address))
        self.window = self.window + (bytes if bytes <= self.mss else self.mss)
        self.plot_window('slow start')

    def additive_increase(self, bytes):
        self.increment = self.increment +  bytes * self.mss / self.window
        if self.increment >= self.mss:
            self.trace("%s (%d) incrementing additive increase" % (self.node.hostname, self.source_address))
            self.window = self.window + self.mss
            self.increment = self.increment - self.mss
            self.plot_window('additive increase')


    def cancel_timer(self):
        """ Cancel the timer. """
        if self.timer is None:
            return
        Sim.scheduler.cancel(self.timer)
        self.timer = None

    ''' Receiver '''

    def handle_data(self, packet):
        """ Handle incoming networks. This code currently gives all networks to
            the application, regardless of whether it is in order, and sends
            an ACK."""
        self.trace("%s (%d) received TCP segment from %d for %d" % (
            self.node.hostname, packet.destination_address, packet.source_address, packet.sequence))
        self.receive_buffer.put(packet.body, packet.sequence)
        data, start_sequence = self.receive_buffer.get()
        self.app.receive_data(data)
        self.ack = start_sequence + len(data)
        self.send_ack()

    def send_ack(self):
        """ Send an ack. """
        packet = TCPPacket(source_address=self.source_address,
                           source_port=self.source_port,
                           destination_address=self.destination_address,
                           destination_port=self.destination_port,
                           sequence=self.sequence, ack_number=self.ack)
        # send the packet
        self.trace("%s (%d) sending TCP ACK to %d for %d" % (
            self.node.hostname, self.source_address, self.destination_address, packet.ack_number))
        self.transport.send_packet(packet)
