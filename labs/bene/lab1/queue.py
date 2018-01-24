"""
Python Code for Experimenting with Queuing Delay
Author: Braden Hitchcock
Class:  CS 460 - Computer Communications and Networking

The below python script code collects data on network speeds and queuing delays, writes the data to a file, and
plots the data.
"""
from src.packet import Packet
from src.sim import Sim
from networks.network import Network
import pandas as pd
import random

class Generator(object):
    def __init__(self, node, destination, load, duration):
        self.node = node
        self.load = load
        self.destination = destination
        self.duration = duration
        self.start = 0
        self.ident = 1

    def handle(self, event):
        # quit if done
        now = Sim.scheduler.current_time()
        if (now - self.start) > self.duration:
            return

        # generate a packet
        self.ident += 1
        p = Packet(destination_address=self.destination, ident=self.ident, protocol='delay', length=1000)
        Sim.scheduler.add(delay=0, event=p, handler=self.node.send_packet)
        # schedule the next time we should generate a packet
        Sim.scheduler.add(delay=random.expovariate(self.load), event='generate', handler=self.handle)

class DataWrangler(object):
    def __init__(self, utilization):
        self.packet_info = []
        self.utilization = utilization

    def receive_packet(self, packet):
        # Formatted as Packet ID, Utilization, Create Time, Receive Time
        received_time = Sim.scheduler.current_time() - packet.created
        data = "{0},{1},{2},{3}".format(packet.ident, self.utilization, packet.created, received_time)
        self.packet_info.append(data)

    def write_to_file(self, file):
        with open(file, "w") as output_file:
            output_file.write("Packet ID, Utilization, Create Time, Receive Time\n")
            for d in self.packet_info:
                output_file.write(d + "\n")
            output_file.close()

def plot(csv_file):
    return None


def run_simulation(network_file, output_file, utilization=1):
    Sim.scheduler.reset()

    network = Network(network_file)

    # setup routes
    n1 = network.get_node('n1')
    n2 = network.get_node('n2')
    n1.add_forwarding_entry(address=n2.get_address('n1'), link=n1.links[0])
    n2.add_forwarding_entry(address=n1.get_address('n2'), link=n2.links[0])

    # setup app
    d = DataWrangler(utilization)
    network.nodes['n2'].add_protocol(protocol="delay", handler=d)

    # setup packet generator
    destination = n2.get_address('n1')
    max_rate = 1000000 // (1000 * 8)
    load = utilization * max_rate
    g = Generator(node=n1, destination=destination, load=load, duration=10)
    Sim.scheduler.add(delay=0, event='generate', handler=g.handle)

    # run the simulation
    Sim.scheduler.run()

    d.write_to_file(output_file)


def main():
    run_simulation(network_file="./twonode1.txt", output_file="./output.txt", utilization=0.8)


if __name__ == "__main__":
    main()