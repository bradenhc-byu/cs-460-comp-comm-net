"""
Python code for experimenting with Node Networks
Author: Braden Hitchcock
Class: CS 460 - Computer Communications and Networking

This script file contains the Lab code for the first two parts of the Network Simulation Lab covering delay simulation
using the Bene Network Simulator.
"""
from src.packet import Packet
from src.sim import Sim
from networks.network import Network


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
    def __init__(self, filename, name=None):
        """
        Constructor for the class
        :param filename: The path of the file where the packet information should be stored
        :param name: The name of the handler. If specified, the name will be prepended to the packet information
        """
        self.writer = FileWriter(filename)
        self.name = name

    def __del__(self):
        self.writer.close()

    def receive_packet(self, packet):
        """
        Callback function for the Bene simulator
        :param packet: The packet received by the node in the simulator when this function is called
        """
        prefix = "node: " + self.name + " " if self.name is not None else ""
        msg = prefix + "ident: {0} created: {1} received: {2} delay: {3}".format(packet.ident, packet.created,
                                                                        Sim.scheduler.current_time(),
                                                                        Sim.scheduler.current_time() - packet.created)
        self.writer.writeline(msg)
        print msg


def two_node_network():
    """
    Runs through several different network scenarios using the Bene simulator and various types of networks. The
    results of the simulations are written to the file provided to the constructor of the PacketHanderl object
    in this function
    """
    print "TWO NODE NETWORK"
    # initialize the simulator
    Sim.scheduler.reset()

    # set up the first network network
    network1 = Network(config="./networks/twonode1.txt")

    # get the nodes in the network and set up the routes
    n1 = network1.get_node("n1")
    n2 = network1.get_node("n2")
    n1.add_forwarding_entry(address=n2.get_address("n1"), link=n1.links[0])
    n2.add_forwarding_entry(address=n1.get_address("n2"), link=n2.links[0])

    # configure a handler that is called when the simulate receives a packet
    sdh = PacketHandler(filename="./networks/network1.txt")
    n2.add_protocol(protocol="delay", handler=sdh)

    # Send a packet
    p = Packet(destination_address=n2.get_address('n1'), ident=1, protocol="delay", length=1000)
    Sim.scheduler.add(delay=0, event=p, handler=n1.send_packet)

    # set up the second network
    network2 = Network(config="./networks/twonode2.txt")

    # get the nodes in the network and set up the routes
    n1 = network2.get_node("n1")
    n2 = network2.get_node("n2")
    n1.add_forwarding_entry(address=n2.get_address("n1"), link=n1.links[0])
    n2.add_forwarding_entry(address=n1.get_address("n2"), link=n2.links[0])

    # configure a handler that is called when the simulate receives a packet
    n2.add_protocol(protocol="delay", handler=sdh)

    # Send a packet
    p = Packet(destination_address=n2.get_address('n1'), ident=2, protocol="delay", length=1000)
    Sim.scheduler.add(delay=0, event=p, handler=n1.send_packet)

    # set up the third network
    network3 = Network(config="./networks/twonode3.txt")

    # get the nodes in the network and set up the routes
    n1 = network3.get_node("n1")
    n2 = network3.get_node("n2")
    n1.add_forwarding_entry(address=n2.get_address("n1"), link=n1.links[0])
    n2.add_forwarding_entry(address=n1.get_address("n2"), link=n2.links[0])

    # configure a handler that is called when the simulator receives a packet
    n2.add_protocol(protocol="delay", handler=sdh)

    # add the packets to send when the simulator is run
    p1 = Packet(destination_address=n2.get_address('n1'), ident=3, protocol="delay", length=1000)
    p2 = Packet(destination_address=n2.get_address('n1'), ident=4, protocol="delay", length=1000)
    p3 = Packet(destination_address=n2.get_address('n1'), ident=5, protocol="delay", length=1000)
    p4 = Packet(destination_address=n2.get_address('n1'), ident=6, protocol="delay", length=1000)
    Sim.scheduler.add(delay=0, event=p1, handler=n1.send_packet)
    Sim.scheduler.add(delay=0, event=p2, handler=n1.send_packet)
    Sim.scheduler.add(delay=0, event=p3, handler=n1.send_packet)
    Sim.scheduler.add(delay=2, event=p4, handler=n1.send_packet)

    # run the scheduler
    Sim.scheduler.run()


def run_three_node_network_simulation(network_file):
    """
    Since the three node networks for this lab all require the same process (sending 1000 packets of size 1000 bytes),
    this function abstracts the process away so it can be easily applied to multiple networks
    :param network_file: The network configuration file that will be used to construct the network for the simulation
    """
    print "\nBeginning Network simulation with configuration file '{0}'".format(network_file)
    # reset the simulator
    Sim.scheduler.reset()

    # setup the network connection
    network = Network(network_file)

    # initialize the routes in the network
    n1 = network.get_node("n1")
    n2 = network.get_node("n2")
    n3 = network.get_node("n3")
    n1.add_forwarding_entry(address=n2.get_address("n1"), link=n1.links[0])
    n1.add_forwarding_entry(address=n3.get_address("n2"), link=n1.links[0])
    n2.add_forwarding_entry(address=n1.get_address("n2"), link=n2.links[0])
    n2.add_forwarding_entry(address=n3.get_address("n2"), link=n2.links[1])
    n3.add_forwarding_entry(address=n2.get_address("n3"), link=n3.links[0])

    # configure a packet handler
    phn2 = PacketHandler(filename="./networks/network2.txt", name="n2")
    phn3 = PacketHandler(filename="./networks/network3.txt", name="n3")
    n2.add_protocol(protocol="forward", handler=phn2)
    n3.add_protocol(protocol="forward", handler=phn3)

    # Create the packets to be sent
    packet_size = 1000
    transmission_delay = (packet_size * 8) / n1.links[0].bandwidth
    for x in xrange(1000):
        p = Packet(destination_address=n3.get_address('n2'), ident=x, protocol="forward", length=packet_size)
        Sim.scheduler.add(delay=x * transmission_delay, event=p, handler=n1.send_packet)

    # run the simulation
    Sim.scheduler.run()


def three_node_network():
    """
    Runs through the three different three-node network simulations required for this lab
    """
    print "THREE NODE NETWORK"
    # Run the two fast link
    run_three_node_network_simulation("./networks/threenode1.txt")
    # Run the two ultra-fast links
    run_three_node_network_simulation("./networks/threenode2.txt")
    # Run the varying links
    run_three_node_network_simulation("./networks/threenode3.txt")


def main():
    """
    Main function to be executed when this file is run as the main script
    :return:
    """
    two_node_network()
    three_node_network()


# Prevent the scrip from being run unless it is the main python executable
if __name__ == "__main__":
    main()
