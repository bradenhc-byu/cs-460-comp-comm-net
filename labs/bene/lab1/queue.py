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
import matplotlib.pyplot as plt
import numpy as np
import random


class Generator(object):
    """
    Class that generates packet events exponentially to model queuing delay
    """
    def __init__(self, node, destination, load, duration):
        self.node = node
        self.load = load
        self.destination = destination
        self.duration = duration
        self.start = 0
        self.ident = 1

    def handle(self, event):
        """
        The callback function for a 'generate' event in the Bene network simulator. This function generates a new
        packet and places it on the queue with a delay simulating network delay in relation to the percent utilization
        of the network.
        :param event: Not used, needed to use this method as the hook for handling an event in the simulator
        """
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
    """
    The handler object used by packets when they are received by a node in the simulator
    """
    def __init__(self, utilization):
        self.packet_info = pd.DataFrame(columns=['packet_id','util','create_time','receive_time'])
        self.utilization = utilization

    def receive_packet(self, packet):
        """
        For events in the simulator using the 'delay' protocol, this function will be implemented and will take the
        packet information and append it to a Pandas DataFrame object. This object can later be written to a CSV file
        to be used for graphing.
        :param packet: The packet received by the node in the simulator
        """
        # Formatted as Packet ID, Utilization, Create Time, Receive Time
        received_time = Sim.scheduler.current_time() - packet.created
        self.packet_info.loc[self.packet_info.size] = [packet.ident, self.utilization, packet.created,
                                                       received_time]

    def write_to_file(self, file):
        """
        Takes the information from the internal Pandas DataFrame and writes the contents to a CSV file to be used
        for graphing
        :param file: The name of the file to write the DataFrame to
        """
        self.packet_info.to_csv(path_or_buf=file, index=False)


def average_data(save_file, utils):
    """
    After different utilizations have been calculated, this takes the results and averages them so that they can be
    plotted against the theoretical queuing delay
    :param save_file: The name of the file to save the averaged CSV networks to
    :param utils: A list of the different percentages used in generating queue delay networks for various utilization levels
    """
    adf = pd.DataFrame(columns=['Utilization','Actual Delay'])
    for u in utils:
        df = pd.read_csv("./networks/output_{0}.csv".format(u))
        average = df['receive_time'].mean()
        adf.loc[adf.size] = [u, average]
    adf.to_csv(save_file, index=False)


def calculate_theoretical(save_file, bandwidth=1000000.0, packet_size=8000.0):
    """
    Uses the M/D/1 queuing delay theory to calculate the wait time given thousands of utilization levels. The
    results are written to a CSV file to later be used in plotting against the experimental results.
    :param save_file: The name of the file to save the CSV networks to
    :param bandwidth: The bandwidth of the network connection. Defaults to 1Mbps
    :param packet_size: The size of the packet to transfer. Defaults to 1kB
    """
    u = bandwidth / packet_size
    l = lambda x : u * x
    p = lambda x : l(x) / u
    formula = lambda x : (1.0 / (2.0 * u)) * (p(x) / (1.0 - p(x)))
    r = np.arange(0.001, 0.98, 0.001)
    df = pd.DataFrame(columns=['Utilization','Theoretical Delay'])
    for u in r:
        df.loc[df.size] = [u, formula(u)]
    df.to_csv(save_file, index=False)


def plot(avg_csv_file, t_csv_file):
    """
    Takes networks from the experimental CSV file and the theoretical CSV file for queuing delay and plots the two
    against each other.
    :param avg_csv_file: The path to the file containing averaged experimental networks
    :param t_csv_file: The path to the file containing theoretical queue delay networks
    """
    data = pd.read_csv(avg_csv_file)
    data2 = pd.read_csv(t_csv_file)
    plt.figure()
    ax = data.plot(x='Utilization', y='Actual Delay')
    data2.plot(ax=ax, x='Utilization', y='Theoretical Delay')
    ax.set_xlabel("Utilization")
    ax.set_ylabel("Queueing Delay")
    figure = ax.get_figure()
    plot_file = "./networks/queuing-delay.png"
    figure.savefig(plot_file)

#l = (bandwidth / packet_size) * 0.6
#u = 0.100
#formula = lambda y : (1 / (2 * l)) * (y / (1.0 - y)) + 0.1

def run_simulation(network_file, output_file, utilization=1.0):
    """
    Abstracted method to run a simulation of queuing delay at a specified utilization for the network. Using a network
    configuration file, it creates a network and then writes the results of the simulation to the provided output
    file.
    :param network_file: The path to the network configuration file
    :param output_file: The path to the file to write the result networks to
    :param utilization: A floating point number that specifies at what percentage of the maximum transfer rate the
                        simulation should run the network
    """
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
    packet_size = 1000
    max_rate = n1.links[0].bandwidth /  (packet_size * 8)
    load = utilization * max_rate
    g = Generator(node=n1, destination=destination, load=load, duration=10)
    Sim.scheduler.add(delay=0, event='generate', handler=g.handle)

    # run the simulation
    Sim.scheduler.run()

    d.write_to_file(output_file)


def main():
    """
    Function called when this script is run as the main target. Runs through several utilizations to help
    analyze the effects of queuing delay on a network
    :return:
    """
    # Setup variables
    utils = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.84, 0.88, 0.9, 0.92, 0.96, 0.98]
    network_file = "./networks/queue-config.txt"
    output_file_generator = lambda x : "./networks/output_{0}.csv".format(x)
    t_csv_file = "./networks/theory-queue.csv"
    a_csv_file = "./networks/average-queue.csv"
    # Begin calculations
    if False:
        for u in utils:
            output_file = output_file_generator(u)
            run_simulation(network_file=network_file, output_file=output_file, utilization=u)
    calculate_theoretical(t_csv_file)
    #average_data(a_csv_file, utils)
    plot(a_csv_file, t_csv_file)


# Run the main function when the script is the main target of execution
if __name__ == "__main__":
    main()