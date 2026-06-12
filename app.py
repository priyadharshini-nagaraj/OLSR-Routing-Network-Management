import simpy
import networkx as nx
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from collections import defaultdict, deque
import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
import json
from enum import Enum
import streamlit as st

# Streamlit page config
st.set_page_config(
    page_title="OLSR Protocol Simulation",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        background: linear-gradient(90deg, #1E3A8A, #3B82F6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        padding: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .protocol-box {
        background: #f8f9fa;
        border-left: 4px solid #3B82F6;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .simulation-controls {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Constants
class MessageType(Enum):
    HELLO = "HELLO"
    TC = "TOPOLOGY_CONTROL"
    DATA = "DATA"

@dataclass
class OLSRMessage:
    """OLSR protocol message"""
    msg_id: str
    msg_type: MessageType
    source: str
    destination: str = None
    timestamp: float = 0.0
    ttl: int = 32
    payload: Dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            'id': self.msg_id,
            'type': self.msg_type.value,
            'source': self.source,
            'destination': self.destination,
            'timestamp': self.timestamp,
            'ttl': self.ttl
        }

class OLSRNode:
    """OLSR protocol implementation for a single node"""
    
    def __init__(self, env, node_id, node_type, position, network):
        self.env = env
        self.node_id = node_id
        self.node_type = node_type
        self.position = position
        self.network = network
        
        # OLSR state
        self.neighbors = set()
        self.two_hop_neighbors = set()
        self.mpr_set = set()
        self.mpr_selectors = set()
        self.routing_table = {}
        self.topology_set = set()
        
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
                
                # Update neighbor list
                self.update_neighbors()
                
                # Select MPRs
                self.select_mpr()
                
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
                # Wait for message
                msg = yield self.message_queue.get()
                
                # Process message
                self.process_message(msg)
                
            except simpy.Interrupt:
                break
    
    def update_neighbors(self):
        """Update neighbor list based on network topology"""
        new_neighbors = set()
        for node_id, node in self.network.nodes.items():
            if node_id != self.node_id:
                # Simple distance-based neighbor detection
                dist = np.sqrt(
                    (self.position[0] - node.position[0])**2 + 
                    (self.position[1] - node.position[1])**2
                )
                if dist <= self.network.transmission_range:
                    new_neighbors.add(node_id)
        
        if new_neighbors != self.neighbors:
            self.neighbors = new_neighbors
            self.update_two_hop_neighbors()
    
    def update_two_hop_neighbors(self):
        """Update two-hop neighbor set"""
        self.two_hop_neighbors = set()
        for neighbor in self.neighbors:
            if neighbor in self.network.nodes:
                neighbor_node = self.network.nodes[neighbor]
                self.two_hop_neighbors.update(neighbor_node.neighbors)
        
        self.two_hop_neighbors -= self.neighbors
        self.two_hop_neighbors.discard(self.node_id)
    
    def select_mpr(self):
        """MPR selection algorithm"""
        old_mpr_set = set(self.mpr_set)
        
        # Reset MPR set
        self.mpr_set = set()
        
        # If no two-hop neighbors, no MPR needed
        if not self.two_hop_neighbors:
            if old_mpr_set:
                self.stats['mpr_changes'] += 1
            return
        
        # MPR selection algorithm (simplified)
        uncovered = set(self.two_hop_neighbors)
        
        # Phase 1: Select nodes that are the only way to reach some two-hop neighbors
        for n in self.two_hop_neighbors:
            # Find all one-hop neighbors that can reach this two-hop neighbor
            reachable_by = set()
            for neighbor in self.neighbors:
                if neighbor in self.network.nodes:
                    neighbor_node = self.network.nodes[neighbor]
                    if n in neighbor_node.neighbors:
                        reachable_by.add(neighbor)
            
            if len(reachable_by) == 1:
                only_neighbor = next(iter(reachable_by))
                if only_neighbor not in self.mpr_set:
                    self.mpr_set.add(only_neighbor)
                    # Update uncovered set
                    neighbor_node = self.network.nodes[only_neighbor]
                    uncovered -= set(neighbor_node.neighbors)
        
        # Phase 2: Greedy selection
        while uncovered:
            best_neighbor = None
            best_coverage = 0
            
            for neighbor in self.neighbors - self.mpr_set:
                if neighbor in self.network.nodes:
                    neighbor_node = self.network.nodes[neighbor]
                    coverage = len(uncovered.intersection(neighbor_node.neighbors))
                    if coverage > best_coverage:
                        best_coverage = coverage
                        best_neighbor = neighbor
            
            if best_neighbor:
                self.mpr_set.add(best_neighbor)
                neighbor_node = self.network.nodes[best_neighbor]
                uncovered -= set(neighbor_node.neighbors)
            else:
                break
        
        # Update statistics if MPR set changed
        if old_mpr_set != self.mpr_set:
            self.stats['mpr_changes'] += 1
    
    def update_routing_table(self):
        """Update routing table based on topology information"""
        # Build network graph
        G = nx.Graph()
        
        # Add all known nodes
        for node_id in self.network.nodes:
            G.add_node(node_id)
        
        # Add edges from topology information
        for link in self.topology_set:
            if isinstance(link, tuple) and len(link) == 2:
                G.add_edge(link[0], link[1], weight=1)
        
        # Add direct neighbor edges
        for neighbor in self.neighbors:
            G.add_edge(self.node_id, neighbor, weight=1)
        
        # Calculate shortest paths
        if nx.is_connected(G):
            try:
                paths = nx.single_source_shortest_path(G, self.node_id)
                self.routing_table = paths
            except:
                pass
    
    def process_message(self, msg):
        """Process received message"""
        self.stats['messages_received'] += 1
        
        if msg.msg_type == MessageType.HELLO:
            # Update MPR selector set
            if 'mpr_set' in msg.payload and self.node_id in msg.payload['mpr_set']:
                self.mpr_selectors.add(msg.source)
            
            # Update topology information
            if 'neighbors' in msg.payload:
                for neighbor in msg.payload['neighbors']:
                    if neighbor != self.node_id:
                        self.topology_set.add((msg.source, neighbor))
        
        elif msg.msg_type == MessageType.TC:
            # Update topology set from TC message
            if 'advertised_neighbors' in msg.payload:
                for neighbor in msg.payload['advertised_neighbors']:
                    if neighbor != self.node_id:
                        self.topology_set.add((msg.source, neighbor))
        
        elif msg.msg_type == MessageType.DATA:
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

class NetworkSimulation:
    """Main network simulation using SimPy"""
    
    def __init__(self, env, config):
        self.env = env
        self.config = config
        self.nodes = {}
        self.links = {}
        
        # Metrics tracking
        self.metrics = {
            'time': [],
            'pdr': [],
            'delay': [],
            'overhead': [],
            'throughput': [],
            'active_nodes': []
        }
        
        self.packet_log = []
        self.message_log = []
        self.sent_packets = 0
        self.delivered_packets = 0
        
        # Network parameters
        self.transmission_range = config.get('transmission_range', 50.0)
        self.link_reliability = config.get('link_reliability', 0.98)
        
        # Initialize network
        self.initialize_network()
        
        # Start monitoring
        self.monitor_process = env.process(self.monitor_performance())
    
    def initialize_network(self):
        """Initialize hybrid NPN/PLMN network"""
        # Clear existing network
        self.nodes = {}
        self.links = {}
        
        # Create NPN A nodes
        for i in range(1, self.config.get('npn_a_nodes', 5) + 1):
            pos = (random.uniform(0, 40), random.uniform(60, 100))
            node_id = f"NPN_A_{i}"
            self.nodes[node_id] = OLSRNode(
                self.env, node_id, 'npn_a', pos, self
            )
        
        # Create NPN B nodes
        for i in range(1, self.config.get('npn_b_nodes', 5) + 1):
            pos = (random.uniform(60, 100), random.uniform(60, 100))
            node_id = f"NPN_B_{i}"
            self.nodes[node_id] = OLSRNode(
                self.env, node_id, 'npn_b', pos, self
            )
        
        # Create PLMN nodes
        for i in range(1, self.config.get('plmn_nodes', 3) + 1):
            pos = (random.uniform(40, 60), random.uniform(10, 40))
            node_id = f"PLMN_{i}"
            self.nodes[node_id] = OLSRNode(
                self.env, node_id, 'plmn', pos, self
            )
        
        # Create Gateway nodes
        for i in range(1, 3):
            pos = (random.uniform(40, 60), random.uniform(50, 60))
            node_id = f"GW_{i}"
            self.nodes[node_id] = OLSRNode(
                self.env, node_id, 'gateway', pos, self
            )
        
        # Create network links
        self.create_network_links()
    
    def create_network_links(self):
        """Create network links with realistic parameters"""
        # Clear existing links
        self.links = {}
        
        # NPN internal links (low latency)
        for i in range(1, self.config.get('npn_a_nodes', 5) + 1):
            for j in range(i + 1, self.config.get('npn_a_nodes', 5) + 1):
                if random.random() > 0.5:
                    latency = random.uniform(5, 15)
                    self.add_link(f"NPN_A_{i}", f"NPN_A_{j}", latency)
        
        for i in range(1, self.config.get('npn_b_nodes', 5) + 1):
            for j in range(i + 1, self.config.get('npn_b_nodes', 5) + 1):
                if random.random() > 0.5:
                    latency = random.uniform(5, 15)
                    self.add_link(f"NPN_B_{i}", f"NPN_B_{j}", latency)
        
        # NPN to Gateway links
        for i in range(1, self.config.get('npn_a_nodes', 5) + 1):
            if random.random() > 0.3:
                latency = random.uniform(10, 25)
                self.add_link(f"NPN_A_{i}", "GW_1", latency)
        
        for i in range(1, self.config.get('npn_b_nodes', 5) + 1):
            if random.random() > 0.3:
                latency = random.uniform(10, 25)
                self.add_link(f"NPN_B_{i}", "GW_2", latency)
        
        # Gateway to PLMN links
        self.add_link("GW_1", "PLMN_1", 5)
        self.add_link("GW_2", "PLMN_1", 5)
        self.add_link("GW_1", "GW_2", 20)
        
        # PLMN internal links
        for i in range(1, self.config.get('plmn_nodes', 3)):
            self.add_link(f"PLMN_{i}", f"PLMN_{i+1}", 2)
    
    def add_link(self, node1, node2, latency):
        """Add bidirectional link between nodes"""
        key = tuple(sorted([node1, node2]))
        self.links[key] = {
            'latency': latency,
            'reliability': self.link_reliability,
            'bandwidth': 1000  # kbps
        }
    
    def broadcast_message(self, msg):
        """Broadcast message to all neighbors within range"""
        if msg.source not in self.nodes:
            return
        
        source_node = self.nodes[msg.source]
        
        for node_id, node in self.nodes.items():
            if node_id != msg.source:
                # Check if within transmission range
                dist = np.sqrt(
                    (source_node.position[0] - node.position[0])**2 +
                    (source_node.position[1] - node.position[1])**2
                )
                
                if dist <= self.transmission_range:
                    # Simulate propagation delay
                    propagation_delay = dist * 0.001  # 1ms per unit distance
                    total_delay = propagation_delay + random.uniform(0, 0.005)
                    
                    # Schedule message delivery with reliability
                    if random.random() < self.link_reliability:
                        self.env.process(self.deliver_message_with_delay(msg, node_id, total_delay))
        
        # Log message
        self.message_log.append({
            'time': self.env.now,
            'type': msg.msg_type.value,
            'source': msg.source,
            'action': 'broadcast',
            'msg_id': msg.msg_id
        })
    
    def flood_message(self, msg, mpr_set):
        """Flood message through MPRs"""
        for mpr in mpr_set:
            if mpr != msg.source and mpr in self.nodes:
                # Send directly to each MPR
                self.send_direct_message(msg, mpr)
    
    def send_direct_message(self, msg, destination):
        """Send message directly to specific destination"""
        if msg.source not in self.nodes or destination not in self.nodes:
            return
        
        # Get link parameters
        key = tuple(sorted([msg.source, destination]))
        if key in self.links:
            link = self.links[key]
            total_delay = link['latency'] / 1000.0  # Convert ms to seconds
        else:
            # Estimate delay based on distance
            src_node = self.nodes[msg.source]
            dst_node = self.nodes[destination]
            dist = np.sqrt(
                (src_node.position[0] - dst_node.position[0])**2 +
                (src_node.position[1] - dst_node.position[1])**2
            )
            total_delay = dist * 0.002  # 2ms per unit distance
        
        # Add small random jitter
        total_delay += random.uniform(0, 0.001)
        
        # Schedule delivery with reliability
        if random.random() < self.link_reliability:
            self.env.process(self.deliver_message_with_delay(msg, destination, total_delay))
        
        # Log message
        self.message_log.append({
            'time': self.env.now,
            'type': msg.msg_type.value,
            'source': msg.source,
            'destination': destination,
            'action': 'send',
            'msg_id': msg.msg_id
        })
    
    def deliver_message_with_delay(self, msg, destination, delay):
        """Deliver message after delay"""
        yield self.env.timeout(delay)
        
        if destination in self.nodes:
            node = self.nodes[destination]
            
            # Create a copy of the message with updated timestamp
            delivered_msg = OLSRMessage(
                msg_id=msg.msg_id,
                msg_type=msg.msg_type,
                source=msg.source,
                destination=msg.destination,
                timestamp=self.env.now,
                ttl=msg.ttl - 1,
                payload=msg.payload.copy() if msg.payload else {}
            )
            
            # Put message in node's queue
            yield node.message_queue.put(delivered_msg)
    
    def log_packet_delivery(self, msg):
        """Log successful packet delivery"""
        if msg.msg_type == MessageType.DATA:
            self.delivered_packets += 1
            
            packet_info = {
                'packet_id': msg.msg_id,
                'source': msg.source,
                'destination': msg.destination,
                'delivery_time': self.env.now,
                'size': len(str(msg.payload)) if msg.payload else 0,
                'delay': self.env.now - msg.timestamp
            }
            
            self.packet_log.append(packet_info)
    
    def monitor_performance(self):
        """Monitor network performance metrics"""
        MONITOR_INTERVAL = 5.0
        
        while True:
            try:
                current_time = self.env.now
                
                # Calculate packet delivery ratio
                if self.sent_packets > 0:
                    pdr = self.delivered_packets / max(1, self.sent_packets)
                else:
                    pdr = 0.0
                
                # Calculate average delay
                if self.packet_log:
                    recent_packets = [
                        p for p in self.packet_log 
                        if p['delivery_time'] > current_time - MONITOR_INTERVAL
                    ]
                    if recent_packets:
                        avg_delay = np.mean([p['delay'] for p in recent_packets])
                    else:
                        avg_delay = 0.0
                else:
                    avg_delay = 0.0
                
                # Calculate routing overhead
                control_msgs = [
                    m for m in self.message_log
                    if m['type'] in ['HELLO', 'TOPOLOGY_CONTROL']
                    and m['time'] > current_time - MONITOR_INTERVAL
                ]
                
                data_msgs = [
                    m for m in self.message_log
                    if m['type'] == 'DATA'
                    and m['time'] > current_time - MONITOR_INTERVAL
                ]
                
                overhead_ratio = len(control_msgs) / max(1, len(data_msgs))
                
                # Calculate throughput (packets per second)
                throughput = len(data_msgs) / MONITOR_INTERVAL
                
                # Store metrics
                self.metrics['time'].append(current_time)
                self.metrics['pdr'].append(pdr)
                self.metrics['delay'].append(avg_delay)
                self.metrics['overhead'].append(overhead_ratio)
                self.metrics['throughput'].append(throughput)
                self.metrics['active_nodes'].append(len(self.nodes))
                
                yield self.env.timeout(MONITOR_INTERVAL)
                
            except simpy.Interrupt:
                break
    
    def generate_traffic(self):
        """Generate analytics traffic between NPN and PLMN"""
        TRAFFIC_INTERVAL = 2.0
        
        while True:
            try:
                # Generate traffic from NPN A to PLMN
                npn_a_nodes = [n for n in self.nodes.keys() if n.startswith('NPN_A')]
                plmn_nodes = [n for n in self.nodes.keys() if n.startswith('PLMN')]
                
                if npn_a_nodes and plmn_nodes:
                    for _ in range(min(3, len(npn_a_nodes))):  # Up to 3 packets per interval
                        source = random.choice(npn_a_nodes)
                        destination = random.choice(plmn_nodes)
                        
                        if source in self.nodes and destination in self.nodes:
                            payload = {
                                'analytics_data': {
                                    'timestamp': self.env.now,
                                    'node_id': source,
                                    'metrics': {
                                        'cpu_usage': random.random() * 100,
                                        'memory_usage': random.random() * 100,
                                        'connected_devices': random.randint(1, 50)
                                    }
                                }
                            }
                            
                            self.nodes[source].send_data(destination, payload)
                            self.sent_packets += 1
                
                # Generate traffic from NPN B to PLMN
                npn_b_nodes = [n for n in self.nodes.keys() if n.startswith('NPN_B')]
                
                if npn_b_nodes and plmn_nodes:
                    for _ in range(min(3, len(npn_b_nodes))):
                        source = random.choice(npn_b_nodes)
                        destination = random.choice(plmn_nodes)
                        
                        if source in self.nodes and destination in self.nodes:
                            payload = {
                                'analytics_data': {
                                    'timestamp': self.env.now,
                                    'node_id': source,
                                    'metrics': {
                                        'cpu_usage': random.random() * 100,
                                        'throughput': random.randint(100, 1000),
                                        'latency': random.randint(5, 50)
                                    }
                                }
                            }
                            
                            self.nodes[source].send_data(destination, payload)
                            self.sent_packets += 1
                
                yield self.env.timeout(TRAFFIC_INTERVAL)
                
            except simpy.Interrupt:
                break
    
    def get_network_statistics(self):
        """Get current network statistics"""
        total_mprs = sum(len(node.mpr_set) for node in self.nodes.values())
        node_types = defaultdict(int)
        
        for node in self.nodes.values():
            node_types[node.node_type] += 1
        
        return {
            'total_nodes': len(self.nodes),
            'total_links': len(self.links),
            'active_mprs': total_mprs,
            'total_messages': len(self.message_log),
            'total_packets': len(self.packet_log),
            'sent_packets': self.sent_packets,
            'delivered_packets': self.delivered_packets,
            'node_types': dict(node_types)
        }

def run_simulation(config):
    """Run the complete simulation"""
    env = simpy.Environment()
    
    # Create network simulation
    network_sim = NetworkSimulation(env, config)
    
    # Start traffic generation
    traffic_process = env.process(network_sim.generate_traffic())
    
    # Run simulation
    simulation_time = config.get('simulation_time', 120)
    env.run(until=simulation_time)
    
    # Interrupt processes
    traffic_process.interrupt()
    network_sim.monitor_process.interrupt()
    
    # Interrupt all node processes
    for node in network_sim.nodes.values():
        node.hello_process.interrupt()
        node.tc_process.interrupt()
        node.routing_process.interrupt()
        node.message_process.interrupt()
    
    return network_sim

def create_network_visualization(sim):
    """Create network topology visualization"""
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Color mapping for node types
    color_map = {
        'npn_a': '#3B82F6',  # Blue
        'npn_b': '#10B981',  # Green
        'plmn': '#EF4444',   # Red
        'gateway': '#F59E0B' # Orange
    }
    
    # Draw nodes
    for node_id, node in sim.nodes.items():
        pos = node.position
        node_color = color_map.get(node.node_type, 'gray')
        
        # Draw node
        ax.scatter(pos[0], pos[1], s=300, c=node_color, alpha=0.8, 
                  edgecolors='black', linewidth=2, zorder=3)
        
        # Add node label
        ax.text(pos[0], pos[1] + 3, node_id, 
                fontsize=9, ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", 
                         alpha=0.8, edgecolor='gray'),
                zorder=4)
        
        # Highlight MPR nodes
        if node.mpr_set:
            circle = plt.Circle(pos, 6, color='yellow', alpha=0.3, 
                              fill=True, linewidth=1, zorder=2)
            ax.add_patch(circle)
            ax.text(pos[0], pos[1] - 5, 'MPR', 
                   fontsize=7, ha='center', va='center', color='darkgoldenrod',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor="yellow", 
                            alpha=0.5))
    
    # Draw edges
    for (node1, node2), link_data in sim.links.items():
        if node1 in sim.nodes and node2 in sim.nodes:
            pos1 = sim.nodes[node1].position
            pos2 = sim.nodes[node2].position
            
            # Draw link
            ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], 
                   color='gray', linestyle='-', alpha=0.5, linewidth=1.5, zorder=1)
            
            # Add latency label
            mid_x = (pos1[0] + pos2[0]) / 2
            mid_y = (pos1[1] + pos2[1]) / 2
            ax.text(mid_x, mid_y - 2, f"{link_data['latency']:.0f}ms", 
                   fontsize=7, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7))
    
    ax.set_xlim(-10, 110)
    ax.set_ylim(-10, 110)
    ax.set_title("Hybrid NPN/PLMN Network Topology with OLSR Routing", 
                fontsize=14, pad=20, fontweight='bold')
    ax.grid(True, alpha=0.2)
    ax.set_aspect('equal')
    
    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#3B82F6', 
                  markersize=10, label='NPN A', markeredgecolor='black'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#10B981', 
                  markersize=10, label='NPN B', markeredgecolor='black'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#EF4444', 
                  markersize=10, label='PLMN', markeredgecolor='black'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#F59E0B', 
                  markersize=10, label='Gateway', markeredgecolor='black'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='yellow', 
                  markersize=10, label='MPR Node', alpha=0.5, markeredgecolor='darkgoldenrod')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10, 
             framealpha=0.9, fancybox=True, shadow=True)
    
    return fig

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">OLSR Protocol Simulation Framework</h1>', unsafe_allow_html=True)
    st.markdown("""
    ### **Hybrid NPN/PLMN Network Simulation**
    
    Discrete-event simulation of Optimized Link State Routing protocol in 5G hybrid networks
    with Non-Public Networks (NPN A & B) and Public Land Mobile Network (PLMN) analytics.
    """)
    
    # Initialize session state
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = None
    if 'simulation_config' not in st.session_state:
        st.session_state.simulation_config = {}
    if 'simulation_running' not in st.session_state:
        st.session_state.simulation_running = False
    
    # Sidebar controls
    with st.sidebar:
        st.markdown("## ⚙️ Simulation Configuration")
        
        with st.form("simulation_config_form"):
            # Network parameters
            st.markdown("### Network Parameters")
            npn_a_nodes = st.slider("NPN A Nodes", 3, 10, 5)
            npn_b_nodes = st.slider("NPN B Nodes", 3, 10, 5)
            plmn_nodes = st.slider("PLMN Nodes", 2, 5, 3)
            
            # OLSR parameters
            st.markdown("### OLSR Protocol Parameters")
            hello_interval = st.slider("Hello Interval (s)", 1.0, 5.0, 2.0, 0.5)
            tc_interval = st.slider("TC Interval (s)", 3.0, 10.0, 5.0, 0.5)
            transmission_range = st.slider("Transmission Range", 30.0, 100.0, 50.0, 5.0)
            
            # Traffic parameters
            st.markdown("### Traffic Parameters")
            traffic_rate = st.slider("Traffic Rate (pkts/interval)", 1, 10, 3)
            simulation_time = st.slider("Simulation Time (s)", 30, 300, 120)
            
            # Submit button
            submitted = st.form_submit_button("🚀 Run Simulation", type="primary", use_container_width=True)
            
            if submitted:
                config = {
                    'npn_a_nodes': npn_a_nodes,
                    'npn_b_nodes': npn_b_nodes,
                    'plmn_nodes': plmn_nodes,
                    'hello_interval': hello_interval,
                    'tc_interval': tc_interval,
                    'transmission_range': transmission_range,
                    'traffic_rate': traffic_rate,
                    'simulation_time': simulation_time
                }
                
                st.session_state.simulation_config = config
                st.session_state.simulation_running = True
                
                with st.spinner("Running simulation..."):
                    try:
                        results = run_simulation(config)
                        st.session_state.simulation_results = results
                        st.session_state.simulation_running = False
                        st.success("Simulation completed successfully!")
                    except Exception as e:
                        st.error(f"Simulation error: {str(e)}")
                        st.session_state.simulation_running = False
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📡 Network Topology",
        "📊 Performance Metrics", 
        "🔬 Protocol Analysis",
        "📈 Results & Export"
    ])
    
    with tab1:
        st.markdown("## Network Topology Visualization")
        
        if st.session_state.simulation_results:
            sim = st.session_state.simulation_results
            
            # Create and display network visualization
            fig = create_network_visualization(sim)
            st.pyplot(fig)
            
            # Network statistics
            stats = sim.get_network_statistics()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Nodes", stats['total_nodes'])
                st.metric("NPN A Nodes", stats['node_types'].get('npn_a', 0))
            with col2:
                st.metric("Active MPRs", stats['active_mprs'])
                st.metric("NPN B Nodes", stats['node_types'].get('npn_b', 0))
            with col3:
                st.metric("Total Links", stats['total_links'])
                st.metric("PLMN Nodes", stats['node_types'].get('plmn', 0))
            with col4:
                st.metric("Gateway Nodes", stats['node_types'].get('gateway', 0))
                st.metric("Total Packets", stats['total_packets'])
            
            # Display node details in expandable sections
            with st.expander("📋 Node Details"):
                node_data = []
                for node_id, node in sim.nodes.items():
                    node_data.append({
                        'Node ID': node_id,
                        'Type': node.node_type,
                        'Neighbors': len(node.neighbors),
                        'MPRs': len(node.mpr_set),
                        'Routing Entries': len(node.routing_table)
                    })
                
                if node_data:
                    df = pd.DataFrame(node_data)
                    st.dataframe(df, use_container_width=True)
    
    with tab2:
        st.markdown("## Performance Metrics Analysis")
        
        if st.session_state.simulation_results:
            sim = st.session_state.simulation_results
            
            # Create metrics dataframe
            metrics_df = pd.DataFrame({
                'Time': sim.metrics['time'],
                'PDR': sim.metrics['pdr'],
                'Delay (ms)': sim.metrics['delay'],
                'Overhead Ratio': sim.metrics['overhead'],
                'Throughput': sim.metrics['throughput']
            })
            
            if not metrics_df.empty:
                # Display key metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    avg_pdr = metrics_df['PDR'].mean()
                    st.metric("Average PDR", f"{avg_pdr:.2%}")
                with col2:
                    avg_delay = metrics_df['Delay (ms)'].mean()
                    st.metric("Avg Delay", f"{avg_delay:.2f} ms")
                with col3:
                    avg_overhead = metrics_df['Overhead Ratio'].mean()
                    st.metric("Routing Overhead", f"{avg_overhead:.2f}")
                with col4:
                    avg_throughput = metrics_df['Throughput'].mean()
                    st.metric("Throughput", f"{avg_throughput:.2f} pkts/s")
                
                # Create plots
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(
                    x=metrics_df['Time'],
                    y=metrics_df['PDR'],
                    mode='lines+markers',
                    name='Packet Delivery Ratio',
                    line=dict(color='green', width=2),
                    marker=dict(size=6)
                ))
                fig1.update_layout(
                    title='Packet Delivery Ratio Over Time',
                    xaxis_title='Simulation Time (s)',
                    yaxis_title='PDR',
                    hovermode='x unified',
                    height=400,
                    template='plotly_white'
                )
                st.plotly_chart(fig1, use_container_width=True)
                
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=metrics_df['Time'],
                    y=metrics_df['Delay (ms)'],
                    mode='lines+markers',
                    name='End-to-End Delay',
                    line=dict(color='red', width=2),
                    marker=dict(size=6)
                ))
                fig2.update_layout(
                    title='End-to-End Delay Over Time',
                    xaxis_title='Simulation Time (s)',
                    yaxis_title='Delay (ms)',
                    hovermode='x unified',
                    height=400,
                    template='plotly_white'
                )
                st.plotly_chart(fig2, use_container_width=True)
                
                # Combined metrics plot
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=metrics_df['Time'],
                    y=metrics_df['Overhead Ratio'],
                    name='Routing Overhead',
                    line=dict(color='blue', width=2)
                ))
                fig3.add_trace(go.Scatter(
                    x=metrics_df['Time'],
                    y=metrics_df['Throughput'],
                    name='Throughput',
                    yaxis='y2',
                    line=dict(color='orange', width=2)
                ))
                fig3.update_layout(
                    title='Routing Overhead and Throughput',
                    xaxis_title='Simulation Time (s)',
                    yaxis_title='Overhead Ratio',
                    yaxis2=dict(
                        title='Throughput (pkts/s)',
                        overlaying='y',
                        side='right'
                    ),
                    hovermode='x unified',
                    height=400,
                    template='plotly_white',
                    legend=dict(x=0.02, y=0.98)
                )
                st.plotly_chart(fig3, use_container_width=True)
    
    with tab3:
        st.markdown("## OLSR Protocol Analysis")
        
        if st.session_state.simulation_results:
            sim = st.session_state.simulation_results
            
            # Collect protocol statistics
            mpr_data = []
            message_stats = defaultdict(int)
            node_type_stats = defaultdict(lambda: defaultdict(int))
            
            for node_id, node in sim.nodes.items():
                mpr_data.append({
                    'Node': node_id,
                    'Type': node.node_type,
                    'Neighbors': len(node.neighbors),
                    'MPRs': len(node.mpr_set),
                    'MPR Selectors': len(node.mpr_selectors),
                    'Messages Sent': node.stats['messages_sent'],
                    'Data Packets': node.stats['data_packets_sent']
                })
                
                node_type_stats[node.node_type]['nodes'] += 1
                node_type_stats[node.node_type]['mprs'] += len(node.mpr_set)
                node_type_stats[node.node_type]['neighbors'] += len(node.neighbors)
            
            # Message type distribution
            for msg in sim.message_log:
                message_stats[msg['type']] += 1
            
            # Display MPR statistics
            st.markdown("### MPR Distribution Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # MPR by node type
                mpr_by_type = []
                for node_type, stats in node_type_stats.items():
                    avg_mprs = stats['mprs'] / max(1, stats['nodes'])
                    mpr_by_type.append({
                        'Node Type': node_type.upper(),
                        'Avg MPRs per Node': avg_mprs,
                        'Total Nodes': stats['nodes']
                    })
                
                if mpr_by_type:
                    df_mpr_type = pd.DataFrame(mpr_by_type)
                    fig = px.bar(
                        df_mpr_type,
                        x='Node Type',
                        y='Avg MPRs per Node',
                        color='Node Type',
                        title='Average MPRs by Node Type',
                        color_discrete_map={
                            'NPN_A': '#3B82F6',
                            'NPN_B': '#10B981',
                            'PLMN': '#EF4444',
                            'GATEWAY': '#F59E0B'
                        }
                    )
                    fig.update_layout(height=300, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Neighbors vs MPRs scatter plot
                if mpr_data:
                    df_mpr = pd.DataFrame(mpr_data)
                    fig = px.scatter(
                        df_mpr,
                        x='Neighbors',
                        y='MPRs',
                        color='Type',
                        size='Messages Sent',
                        hover_name='Node',
                        title='Neighbors vs MPRs Relationship',
                        color_discrete_map={
                            'npn_a': '#3B82F6',
                            'npn_b': '#10B981',
                            'plmn': '#EF4444',
                            'gateway': '#F59E0B'
                        }
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
            
            # Message statistics
            st.markdown("### Message Statistics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Message type distribution
                if message_stats:
                    msg_types = list(message_stats.keys())
                    msg_counts = list(message_stats.values())
                    
                    fig = px.pie(
                        values=msg_counts,
                        names=msg_types,
                        title='Message Type Distribution',
                        hole=0.4
                    )
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Node message statistics
                if mpr_data:
                    df_nodes = pd.DataFrame(mpr_data)
                    top_nodes = df_nodes.nlargest(8, 'Messages Sent')
                    
                    fig = px.bar(
                        top_nodes,
                        x='Node',
                        y='Messages Sent',
                        color='Type',
                        title='Top Message Senders',
                        color_discrete_map={
                            'npn_a': '#3B82F6',
                            'npn_b': '#10B981',
                            'plmn': '#EF4444',
                            'gateway': '#F59E0B'
                        }
                    )
                    fig.update_layout(height=350, xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
            
            # Protocol efficiency metrics
            st.markdown("### Protocol Efficiency")
            
            stats = sim.get_network_statistics()
            control_msgs = sum(count for msg_type, count in message_stats.items() 
                             if msg_type in ['HELLO', 'TOPOLOGY_CONTROL'])
            data_msgs = message_stats.get('DATA', 0)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Control Messages", control_msgs)
            with col2:
                st.metric("Data Messages", data_msgs)
            with col3:
                if data_msgs > 0:
                    efficiency = control_msgs / data_msgs
                    st.metric("Control/Data Ratio", f"{efficiency:.2f}")
                else:
                    st.metric("Control/Data Ratio", "N/A")
    
    with tab4:
        st.markdown("## Simulation Results & Export")
        
        if st.session_state.simulation_results:
            sim = st.session_state.simulation_results
            
            # Summary statistics
            st.markdown("### Simulation Summary")
            
            stats = sim.get_network_statistics()
            avg_pdr = np.mean(sim.metrics['pdr']) if sim.metrics['pdr'] else 0
            avg_delay = np.mean(sim.metrics['delay']) if sim.metrics['delay'] else 0
            
            summary_cols = st.columns(2)
            
            with summary_cols[0]:
                st.markdown("**Network Configuration:**")
                config = st.session_state.simulation_config
                st.write(f"- NPN A Nodes: {config.get('npn_a_nodes', 5)}")
                st.write(f"- NPN B Nodes: {config.get('npn_b_nodes', 5)}")
                st.write(f"- PLMN Nodes: {config.get('plmn_nodes', 3)}")
                st.write(f"- Simulation Time: {config.get('simulation_time', 120)}s")
                st.write(f"- Transmission Range: {config.get('transmission_range', 50)} units")
            
            with summary_cols[1]:
                st.markdown("**Performance Results:**")
                st.write(f"- Average PDR: {avg_pdr:.2%}")
                st.write(f"- Average Delay: {avg_delay:.2f} ms")
                st.write(f"- Total Packets Sent: {stats['sent_packets']}")
                st.write(f"- Total Packets Delivered: {stats['delivered_packets']}")
                st.write(f"- Active MPR Nodes: {stats['active_mprs']}")
            
            # Performance insights
            st.markdown("### Performance Insights")
            
            insights = []
            
            if avg_pdr > 0.95:
                insights.append("✅ **Excellent Reliability**: OLSR provides high packet delivery suitable for critical management data")
            elif avg_pdr > 0.90:
                insights.append("⚠️ **Good Reliability**: Acceptable for most analytics traffic, consider optimizing MPR selection")
            else:
                insights.append("❌ **Reliability Concern**: Investigate network connectivity and routing convergence")
            
            if avg_delay < 50:
                insights.append("✅ **Low Latency**: Suitable for real-time analytics and time-sensitive operations")
            elif avg_delay < 100:
                insights.append("⚠️ **Moderate Latency**: Acceptable for periodic analytics data collection")
            else:
                insights.append("❌ **High Latency**: May impact time-sensitive management operations")
            
            # Check convergence
            if len(sim.metrics['pdr']) > 5:
                early_pdr = np.mean(sim.metrics['pdr'][:3])
                late_pdr = np.mean(sim.metrics['pdr'][-3:])
                
                if late_pdr > early_pdr * 1.15:
                    insights.append("📈 **Good Convergence**: Network performance improves as routes stabilize")
                elif late_pdr < early_pdr * 0.85:
                    insights.append("📉 **Performance Degradation**: Network may be overloaded or experiencing instability")
            
            # MPR efficiency
            mpr_efficiency = stats['active_mprs'] / max(1, stats['total_nodes'])
            if mpr_efficiency < 0.3:
                insights.append("⚡ **Efficient MPR Selection**: Minimal MPRs selected, reducing control overhead")
            elif mpr_efficiency > 0.5:
                insights.append("⚠️ **High MPR Count**: Consider optimizing MPR selection criteria")
            
            for insight in insights:
                st.write(insight)
            
            # Export data section
            st.markdown("### Export Simulation Data")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Export metrics
                if st.button("📊 Export Metrics CSV", use_container_width=True):
                    metrics_df = pd.DataFrame({
                        'Time': sim.metrics['time'],
                        'PDR': sim.metrics['pdr'],
                        'Delay_ms': sim.metrics['delay'],
                        'Overhead_Ratio': sim.metrics['overhead'],
                        'Throughput': sim.metrics['throughput']
                    })
                    csv = metrics_df.to_csv(index=False)
                    
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="olsr_metrics.csv",
                        mime="text/csv",
                        key="metrics_csv"
                    )
            
            with col2:
                # Export node data
                if st.button("📋 Export Node Statistics", use_container_width=True):
                    node_data = []
                    for node_id, node in sim.nodes.items():
                        node_data.append({
                            'node_id': node_id,
                            'type': node.node_type,
                            'neighbors': len(node.neighbors),
                            'mprs': len(node.mpr_set),
                            'mpr_selectors': len(node.mpr_selectors),
                            'routing_entries': len(node.routing_table),
                            'messages_sent': node.stats['messages_sent'],
                            'data_packets_sent': node.stats['data_packets_sent']
                        })
                    
                    df = pd.DataFrame(node_data)
                    csv = df.to_csv(index=False)
                    
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="node_statistics.csv",
                        mime="text/csv",
                        key="nodes_csv"
                    )
            
            with col3:
                # Export configuration
                if st.button("⚙️ Export Configuration", use_container_width=True):
                    config_json = json.dumps(st.session_state.simulation_config, indent=2)
                    
                    st.download_button(
                        label="Download JSON",
                        data=config_json,
                        file_name="simulation_config.json",
                        mime="application/json",
                        key="config_json"
                    )
            
            # Advanced analysis
            with st.expander("🔍 Advanced Analysis"):
                st.markdown("#### Network Connectivity Analysis")
                
                # Build connectivity matrix
                node_ids = list(sim.nodes.keys())
                connectivity = np.zeros((len(node_ids), len(node_ids)))
                
                for i, node1 in enumerate(node_ids):
                    for j, node2 in enumerate(node_ids):
                        if i != j:
                            key = tuple(sorted([node1, node2]))
                            if key in sim.links:
                                connectivity[i, j] = 1
                
                # Calculate connectivity metrics
                total_possible_links = len(node_ids) * (len(node_ids) - 1) / 2
                actual_links = len(sim.links)
                connectivity_ratio = actual_links / total_possible_links if total_possible_links > 0 else 0
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Network Connectivity", f"{connectivity_ratio:.2%}")
                with col2:
                    st.metric("Average Node Degree", f"{2 * actual_links / len(node_ids):.2f}")
                
                # Display connectivity heatmap
                fig = px.imshow(
                    connectivity,
                    x=node_ids,
                    y=node_ids,
                    title="Network Connectivity Matrix",
                    color_continuous_scale='Blues'
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
        
        elif st.session_state.simulation_running:
            st.info("⏳ Simulation is running... Please wait.")
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.1)
                progress_bar.progress(i + 1)
        else:
            st.info("👈 Configure and run a simulation from the sidebar to see results.")

if __name__ == "__main__":
    main()