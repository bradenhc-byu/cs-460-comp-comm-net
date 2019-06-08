from __future__ import print_function

import sys

sys.path.append('..')

from src.sim import Sim
from src.packet import Packet

from networks.network import Network


class BroadcastApp(object):
    def __init__(self, node):
        self.node = node

    def receive_packet(self, packet):
        change = self.node.update_distance_vector(packet.body["hostname"], packet.body["dv"])

        # If we haven't heard from a neighbor link in 40 seconds, drop the link and update the distance vector
        for host in self.node.distance_vectors:
            if host != self.node.hostname and Sim.scheduler.current_time() - self.node.get_distance_vector_time(host) > 6:
                change = True
                self.node.remove_distance_vector(host)
                break

        # If new values were detected and the forwarding entries were changed, broadcast new values
        delay = 2
        if change:
            print("Change!", self.node.hostname, self.node.distance_vectors[self.node.hostname]["dv"])
            delay = 1

        # Setup new event to rebroadcast
        pbody = {
            "hostname": self.node.hostname,
            "dv": self.node.get_distance_vector()
        }
        p = Packet(
            destination_address=0,
            ident=0, ttl=1, protocol='broadcast', body=pbody)
        Sim.scheduler.add(delay=delay, event=p, handler=self.node.send_packet)


class FileWriter(object):
    """
    Simple wrapper class for writing strings to a file. Provides a quick and dirty portable implementation of
    a file writer
    """
    def __init__(self, filename):
        """
        Constructs a new File writer
        :param filename: The path to the file where the strings should be writen
        """
        self.filename = filename
        self.writer = open(filename, "w+")

    def write(self, line):
        """
        Writes to the file specified in the constructor without appending a newline at the end
        :param line: The string to append to the file
        """
        self.writer.write(line)

    def writeline(self, line):
        """
        Writes to the file specified in the constructor and appends as newline '\n' to the end of the string
        :param line: The string to append to the file
        """
        self.writer.write(line + "\n")

    def close(self):
        """
        Closes the file for writing. Once closed, the file writer cannot be used
        :return:
        """
        self.writer.close()


class PacketHandler(object):
    """
    A simple class that provides a callback method to the Bene simulator. When a packet is received by a node in
    the simulator, it will trigger the 'receive_packet()' method in this class
    """
    def __init__(self, name=None):
        """
        Constructor for the class
        :param filename: The path of the file where the packet information should be stored
        :param name: The name of the handler. If specified, the name will be prepended to the packet information
        """
        #self.writer = FileWriter(filename)
        self.name = name

    #def __del__(self):
        #self.writer.close()

    def receive_packet(self, packet):
        """
        Callback function for the Bene simulator
        :param packet: The packet received by the node in the simulator when this function is called
        """
        prefix = "node: " + self.name + " " if self.name is not None else ""
        msg = prefix + "ident: {0} created: {1} received: {2} delay: {3}".format(packet.ident, packet.created,
                                                                        Sim.scheduler.current_time(),
                                                                        Sim.scheduler.current_time() - packet.created)
        #self.writer.writeline(msg)
        print(msg)

def main():
    # parameters
    Sim.scheduler.reset()

    # setup network
    #net = Network('./networks/five-nodes-line.txt')
    #net = Network('./networks/five-nodes-ring.txt')
    net = Network('./networks/fifteen-nodes.txt')

    # Setup broadcast protocol for all nodes in the network
    packet_count = 1
    for k, n in net.nodes.iteritems():
        b = BroadcastApp(n)
        ph = PacketHandler(k)
        n.add_protocol(protocol="broadcast", handler=b)
        n.add_protocol(protocol="transmit", handler=ph)
        n.init_routing()
        pbody = {
            "hostname": n.hostname,
            "dv": n.get_distance_vector()
        }
        p = Packet(
            destination_address=0,
            ident=packet_count, ttl=1, protocol='broadcast', body=pbody)
        Sim.scheduler.add(delay=0, event=p, handler=n.send_packet)
        packet_count = packet_count + 1

    # Send a packet after everything has been setup
    n1 = net.get_node('n1')
    n4 = net.get_node('n4')
    n5 = net.get_node('n5')
    daddr = 5
    p = Packet(destination_address=daddr, ident=2, protocol='transmit', length=1000)
    Sim.scheduler.add(delay=5, event=p, handler=n1.send_packet)

    if True:
        # Take a link down (between n5 and n1)
        Sim.scheduler.add(delay=10, event=None, handler=net.get_link(daddr-1).down)
        Sim.scheduler.add(delay=10, event=None, handler=net.get_link(daddr-1).down)

        # Send a packet
        p = Packet(destination_address=daddr, ident=3, protocol='transmit', length=1000)
        Sim.scheduler.add(delay=20, event=p, handler=n1.send_packet)

        # Bring the link back up
        Sim.scheduler.add(delay=30, event=None, handler=net.get_link(daddr-1).up)
        Sim.scheduler.add(delay=30, event=None, handler=net.get_link(daddr-1).up)

        # Send a packet
        p = Packet(destination_address=daddr, ident=2, protocol='transmit', length=1000)
        Sim.scheduler.add(delay=40, event=p, handler=n1.send_packet)


    # run the simulation
    Sim.scheduler.run()

if __name__ == '__main__':
    main()
