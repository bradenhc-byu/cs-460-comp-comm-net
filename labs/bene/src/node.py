import copy

from .sim import Sim


class Node(object):
    def __init__(self, hostname):
        self.hostname = hostname
        self.links = []
        self.protocols = {}
        self.forwarding_table = {}
        # Added for the routing lab
        self.distance_vectors = {}

    @staticmethod
    def trace(message):
        Sim.trace("Node", message)

    # -- Links --

    def add_link(self, link):
        self.links.append(link)

    def delete_link(self, link):
        if link not in self.links:
            return
        self.links.remove(link)

    def get_link(self, name):
        for link in self.links:
            if link.endpoint.hostname == name:
                return link
        return None

    def get_address(self, name):
        for link in self.links:
            if link.endpoint.hostname == name:
                return link.address
        return 0

    # -- Protocols --

    def add_protocol(self, protocol, handler):
        self.protocols[protocol] = handler

    def delete_protocol(self, protocol):
        if protocol not in self.protocols:
            return
        del self.protocols[protocol]

    # -- Forwarding table --

    def add_forwarding_entry(self, address, link):
        self.forwarding_table[address] = link

    def delete_forwarding_entry(self, address):
        if address not in self.forwarding_table:
            return
        del self.forwarding_table[address]

    # -- Distance Vectors --

    def init_routing(self):
        # Initialize the forwarding table and distance vector for the node
        self.forwarding_table = {}
        self.distance_vectors = {}
        distance_vector = {}
        for l in self.links:
            if l.running:
                link_address = self.get_address(l.endpoint.hostname)
                self.add_forwarding_entry(link_address, l)
                distance_vector[link_address] = 1
        self.distance_vectors[self.hostname] = {
            "timestamp": Sim.scheduler.current_time(),
            "dv": distance_vector
        }

    def get_distance_vector(self, hostname=None):
        if hostname is None and self.hostname in self.distance_vectors:
            return self.distance_vectors[self.hostname]["dv"]
        elif hostname in self.distance_vectors:
            return self.distance_vectors[hostname]["dv"]
        else:
            return None

    def get_distance_vector_time(self, hostname=None):
        if hostname is None and self.hostname in self.distance_vectors:
            return self.distance_vectors[self.hostname]["timestamp"]
        elif hostname in self.distance_vectors:
            return self.distance_vectors[hostname]["timestamp"]
        else:
            return None

    def update_distance_vector(self, hostname, vector):
        changed = self.vector_changed(hostname, vector)
        self.distance_vectors[hostname] = {
            "timestamp": Sim.scheduler.current_time(),
            "dv": vector
        }
        if changed:
            self.build_forwarding_table()
            return True
        else:
            return False

    def build_forwarding_table(self):
        my_vector = self.distance_vectors[self.hostname]["dv"]
        for host in self.distance_vectors:
            if host != self.hostname:
                vector = self.distance_vectors[host]["dv"]
                for k, v in vector.iteritems():
                    found = False
                    for l in self.links:
                        if k == l.address:
                            found = True
                            break
                    if found:
                        continue
                    if k in my_vector.keys():
                        if v + 1 < my_vector[k]:
                            my_vector[k] = v + 1
                            self.add_forwarding_entry(k, self.get_link(host))
                    else:
                        my_vector[k] = v + 1
                        self.add_forwarding_entry(k, self.get_link(host))

        self.distance_vectors[self.hostname]["timestamp"] = Sim.scheduler.current_time()

    def remove_distance_vector(self, hostname):
        if hostname in self.distance_vectors:
            del self.distance_vectors[hostname]
            self.init_routing()
            self.build_forwarding_table()
            return True
        return False

    def vector_changed(self, hostname, new_vector):
        if hostname in self.distance_vectors:
            old_vector = self.distance_vectors[hostname]["dv"]
            if len(old_vector) != len(new_vector):
                return True
            else:
                for k in old_vector:
                    if k not in new_vector or old_vector[k] != new_vector[k]:
                        return True
                return False
        else:
            return True

    # -- Handling packets --

    def send_packet(self, packet):
        # if this is the first time we have seen this packet, set its
        # creation timestamp
        if packet.created is None:
            packet.created = Sim.scheduler.current_time()

        # forward the packet
        self.forward_packet(packet)

    def receive_packet(self, packet):
        # handle broadcast packets
        if packet.destination_address == 0:
            self.trace("%s received packet" % self.hostname)
            self.deliver_packet(packet)
        else:
            # check if unicast packet is for me
            for link in self.links:
                if link.address == packet.destination_address:
                    self.trace("%s received packet" % self.hostname)
                    self.deliver_packet(packet)
                    return

        # decrement the TTL and drop if it has reached the last hop
        packet.ttl -= 1
        if packet.ttl <= 0:
            self.trace("%s dropping packet due to TTL expired" % self.hostname)
            return

        # forward the packet
        self.forward_packet(packet)

    def deliver_packet(self, packet):
        if packet.protocol not in self.protocols:
            return
        self.protocols[packet.protocol].receive_packet(packet)

    def forward_packet(self, packet):
        if packet.destination_address == 0:
            # broadcast the packet
            self.forward_broadcast_packet(packet)
        else:
            # forward the packet
            self.forward_unicast_packet(packet)

    def forward_unicast_packet(self, packet):
        if packet.destination_address not in self.forwarding_table:
            self.trace("%s no routing entry for %d" % (self.hostname, packet.destination_address))
            return
        link = self.forwarding_table[packet.destination_address]
        self.trace("%s forwarding packet to %d" % (self.hostname, packet.destination_address))
        link.send_packet(packet)

    def forward_broadcast_packet(self, packet):
        for link in self.links:
            self.trace("%s forwarding broadcast packet to %s" % (self.hostname, link.endpoint.hostname))
            packet_copy = copy.deepcopy(packet)
            link.send_packet(packet_copy)
