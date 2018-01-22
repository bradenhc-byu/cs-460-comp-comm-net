from src.packet import Packet
from src.sim import Sim
from networks.network import Network


class SimpleDelayHandler(object):
    @staticmethod
    def receive_packet(packet):
        print "ident:", packet.ident,\
            "created:", packet.created,\
            "received:", Sim.scheduler.current_time() - packet.created


class DelayHandler(object):
    def __init__(self, name):
        self.name = name

    def receive_packet(self, packet):
        print "node:", self.name, \
            "ident:", packet.ident, \
            "created:", packet.created, \
            "received:", Sim.scheduler.current_time() - packet.created


def two_node_network():
    print "TWO NODE NETWORK"
    # initialize the simulator
    Sim.scheduler.reset()

    # set up the first network network
    network1 = Network(config="./twonode1.txt")

    # get the nodes in the network and set up the routes
    n1 = network1.get_node("n1")
    n2 = network1.get_node("n2")
    n1.add_forwarding_entry(address=n2.get_address("n1"), link=n1.links[0])
    n2.add_forwarding_entry(address=n1.get_address("n2"), link=n2.links[0])

    # configure a handler that is called when the simulate receives a packet
    sdh = SimpleDelayHandler()
    n2.add_protocol(protocol="delay", handler=sdh)

    # Send a packet
    p = Packet(destination_address=n2.get_address('n1'), ident=1, protocol="delay", length=8000)
    Sim.scheduler.add(delay=0, event=p, handler=n1.send_packet)

    # set up the second network
    network2 = Network(config="./twonode2.txt")

    # get the nodes in the network and set up the routes
    n1 = network2.get_node("n1")
    n2 = network2.get_node("n2")
    n1.add_forwarding_entry(address=n2.get_address("n1"), link=n1.links[0])
    n2.add_forwarding_entry(address=n1.get_address("n2"), link=n2.links[0])

    # configure a handler that is called when the simulate receives a packet
    n2.add_protocol(protocol="delay", handler=sdh)

    # Send a packet
    p = Packet(destination_address=n2.get_address('n1'), ident=2, protocol="delay", length=8000)
    Sim.scheduler.add(delay=0, event=p, handler=n1.send_packet)

    # set up the third network
    network3 = Network(config="./twonode3.txt")

    # get the nodes in the network and set up the routes
    n1 = network3.get_node("n1")
    n2 = network3.get_node("n2")
    n1.add_forwarding_entry(address=n2.get_address("n1"), link=n1.links[0])
    n2.add_forwarding_entry(address=n1.get_address("n2"), link=n2.links[0])

    # configure a handler that is called when the simulator receives a packet
    n2.add_protocol(protocol="delay", handler=sdh)

    # add the packets to send when the simulator is run
    p1 = Packet(destination_address=n2.get_address('n1'), ident=3, protocol="delay", length=8000)
    p2 = Packet(destination_address=n2.get_address('n1'), ident=4, protocol="delay", length=8000)
    p3 = Packet(destination_address=n2.get_address('n1'), ident=5, protocol="delay", length=8000)
    p4 = Packet(destination_address=n2.get_address('n1'), ident=6, protocol="delay", length=8000)
    Sim.scheduler.add(delay=0, event=p1, handler=n1.send_packet)
    Sim.scheduler.add(delay=0, event=p2, handler=n1.send_packet)
    Sim.scheduler.add(delay=0, event=p3, handler=n1.send_packet)
    Sim.scheduler.add(delay=2, event=p4, handler=n1.send_packet)

    # run the scheduler
    Sim.scheduler.run()


def three_node_network():
    print "THREE NODE NETWORK"
    # reset the simulator
    Sim.scheduler.reset()

    # setup the network connection
    network1 = Network("./threenode1.txt")

    # initialize the routes in the network
    n1 = network1.get_node("n1")
    n2 = network1.get_node("n2")
    n3 = network1.get_node("n3")
    n1.add_forwarding_entry(address=n2.get_address("n1"), link=n1.links[0])
    n2.add_forwarding_entry(address=n1.get_address("n2"), link=n2.links[0])
    n2.add_forwarding_entry(address=n3.get_address("n2"), link=n2.links[1])
    n3.add_forwarding_entry(address=n2.get_address("n3"), link=n3.links[0])

    # configure a packet handler
    phn2 = DelayHandler("n2")
    phn3 = DelayHandler("n3")
    n2.add_protocol(protocol="delay", handler=phn2)
    n3.add_protocol(protocol="delay", handler=phn3)

    # Create the packets to be sent
    packet_size = 8000
    transmission_delay = packet_size / n1.links[0].bandwidth
    for x in xrange(1000):
        p1 = Packet(destination_address=n3.get_address('n2'), ident=x, protocol="delay", length=packet_size)
        Sim.scheduler.add(delay=x*transmission_delay, event=p1, handler=n1.send_packet)

    # run the simulation
    Sim.scheduler.run()


def main():
    two_node_network()
    three_node_network()


if __name__ == "__main__":
    main()
