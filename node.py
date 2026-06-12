"""OLSRNode implementation"""

import simpy
import random
from typing import Dict, Set
from protocols.message import OLSRMessage, MessageType
from protocols.olsr import OLSRProtocol

class OLSRNode:
    """OLSR protocol implementation for a single node"""
    
    def __init__(self, env, node_id, node_type, position, network):
        self.env = env
        self.node_id = node_id
        self.node_type = node_type
        self.position = position
        self.network = network
        
        # OLSR state
        self.neighbors: Set[str] = set()
        self.two_hop_neighbors: Set[str] = set()
        self.mpr_set: Set[str] = set()
        self.mpr_selectors: Set[str] = set()
        self.routing_table: Dict[str, list] = {}
        self.topology_set: Set[tuple] = set()
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'data_packets_sent': 0,
            'data_packets_received': 0,
            'mpr_changes': 0,
            'hello_intervals': 0
        }
        
        # Message queues
        self.message_queue = simpy.Store(env, capacity=100)
        
        # Start processes
        self.hello_process = env.process(self.hello_generator())
        self.tc_process = env.process(self.tc_generator())
        self.routing_process = env.process(self.routing_updater())
        self.message_process = env.process(self.message_handler())
    
    def hello_generator(self):
        """Periodic HELLO message generation"""
        HELLO_INTERVAL = 2.0
        
        while True:
            try:
                # Update neighbor list
                self.update_neighbors()
                
                # Select MPRs
                self.select_mpr()
                
                # Create HELLO message
                hello_msg = OLSRMessage(
                    msg_id=f"HELLO_{self.node_id}_{self.env.now:.2f}",
                    msg_type=MessageType.HELLO,
                    source=self.node_id,
                    timestamp=self.env.now,
                    payload={
                        'neighbors': list(self.neighbors),
                        'mpr_set': list(self.mpr_set),
                        'position': self.position
                    }
                )
                
                # Broadcast HELLO
                self.network.broadcast_message(hello_msg)
                
                self.stats['hello_intervals'] += 1
                yield self.env.timeout(HELLO_INTERVAL)
                
            except simpy.Interrupt:
                break
    
    def tc_generator(self):
        """Periodic TC message generation (only by MPRs)"""
        TC_INTERVAL = 5.0
        
        while True:
            try:
                if self.mpr_set:  # Only MPRs send TC messages
                    tc_msg = OLSRMessage(
                        msg_id=f"TC_{self.node_id}_{self.env.now:.2f}",
                        msg_type=MessageType.TC,
                        source=self.node_id,
                        timestamp=self.env.now,
                        payload={
                            'mpr_set': list(self.mpr_set),
                            'advertised_neighbors': list(self.neighbors)
                        }
                    )
                    
                    # Flood TC message through MPRs
                    self.network.flood_message(tc_msg, self.mpr_set)
                
                yield self.env.timeout(TC_INTERVAL)
                
            except simpy.Interrupt:
                break
    
    def routing_updater(self):
        """Update routing table periodically"""
        UPDATE_INTERVAL = 1.0
        
        while True:
            try:
                self.update_routing_table()
                yield self.env.timeout(UPDATE_INTERVAL)
            except simpy.Interrupt:
                break
    
    def message_handler(self):
        """Handle incoming messages"""
        while True:
            try:
                msg = yield self.message_queue.get()
                self.process_message(msg)
            except simpy.Interrupt:
                break
    
    def update_neighbors(self):
        """Update neighbor list based on network topology"""
        new_neighbors = set()
        for node_id, node in self.network.nodes.items():
            if node_id != self.node_id:
                # Simple distance-based neighbor detection
                dist = self.calculate_distance(node.position)
                if dist <= self.network.transmission_range:
                    new_neighbors.add(node_id)
        
        if new_neighbors != self.neighbors:
            self.neighbors = new_neighbors
            self.update_two_hop_neighbors()
    
    def calculate_distance(self, other_position):
        """Calculate Euclidean distance to another position"""
        import numpy as np
        return np.sqrt(
            (self.position[0] - other_position[0])**2 + 
            (self.position[1] - other_position[1])**2
        )
    
    def update_two_hop_neighbors(self):
        """Update two-hop neighbor set"""
        self.two_hop_neighbors = OLSRProtocol.update_two_hop_neighbors(
            self.neighbors, self.network.nodes
        )
        self.two_hop_neighbors.discard(self.node_id)
    
    def select_mpr(self):
        """MPR selection algorithm"""
        old_mpr_set = set(self.mpr_set)
        
        self.mpr_set = OLSRProtocol.select_mpr(
            self.neighbors, self.two_hop_neighbors, self.network.nodes
        )
        
        # Update statistics if MPR set changed
        if old_mpr_set != self.mpr_set:
            self.stats['mpr_changes'] += 1
    
    def update_routing_table(self):
        """Update routing table based on topology information"""
        self.routing_table = OLSRProtocol.calculate_routing_table(
            self.node_id, self.neighbors, self.topology_set, 
            set(self.network.nodes.keys())
        )
    
    def process_message(self, msg):
        """Process received message"""
        self.stats['messages_received'] += 1
        
        if msg.msg_type == MessageType.HELLO:
            self.process_hello_message(msg)
        elif msg.msg_type == MessageType.TC:
            self.process_tc_message(msg)
        elif msg.msg_type == MessageType.DATA:
            self.process_data_message(msg)
    
    def process_hello_message(self, msg):
        """Process HELLO message"""
        # Update MPR selector set
        if 'mpr_set' in msg.payload and self.node_id in msg.payload['mpr_set']:
            self.mpr_selectors.add(msg.source)
        
        # Update topology information
        if 'neighbors' in msg.payload:
            for neighbor in msg.payload['neighbors']:
                if neighbor != self.node_id:
                    self.topology_set.add((msg.source, neighbor))
    
    def process_tc_message(self, msg):
        """Process TC message"""
        if 'advertised_neighbors' in msg.payload:
            for neighbor in msg.payload['advertised_neighbors']:
                if neighbor != self.node_id:
                    self.topology_set.add((msg.source, neighbor))
    
    def process_data_message(self, msg):
        """Process DATA message"""
        self.stats['data_packets_received'] += 1
        
        if msg.destination == self.node_id:
            # Packet arrived at destination
            self.network.log_packet_delivery(msg)
        else:
            # Forward packet
            self.forward_packet(msg)
    
    def forward_packet(self, msg):
        """Forward data packet to next hop"""
        if msg.destination in self.routing_table:
            path = self.routing_table[msg.destination]
            if len(path) > 1:
                next_hop = path[1]
                
                # Create new message for forwarding
                fwd_msg = OLSRMessage(
                    msg_id=f"{msg.msg_id}_FWD",
                    msg_type=MessageType.DATA,
                    source=msg.source,
                    destination=msg.destination,
                    timestamp=self.env.now,
                    payload=msg.payload
                )
                
                # Send to next hop
                self.network.send_direct_message(fwd_msg, next_hop)
    
    def send_data(self, dest, payload):
        """Send data packet to destination"""
        data_msg = OLSRMessage(
            msg_id=f"DATA_{self.node_id}_{dest}_{self.env.now:.2f}",
            msg_type=MessageType.DATA,
            source=self.node_id,
            destination=dest,
            timestamp=self.env.now,
            payload=payload
        )
        
        self.stats['data_packets_sent'] += 1
        self.forward_packet(data_msg)