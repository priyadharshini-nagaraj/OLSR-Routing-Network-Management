"""Configuration constants and enums"""

from enum import Enum

class MessageType(Enum):
    HELLO = "HELLO"
    TC = "TOPOLOGY_CONTROL"
    DATA = "DATA"

# Simulation defaults
DEFAULT_CONFIG = {
    'npn_a_nodes': 5,
    'npn_b_nodes': 5,
    'plmn_nodes': 3,
    'hello_interval': 2.0,
    'tc_interval': 5.0,
    'transmission_range': 50.0,
    'traffic_rate': 3,
    'simulation_time': 120,
    'link_reliability': 0.98
}

# Color mapping for node types
NODE_COLORS = {
    'npn_a': '#3B82F6',  # Blue
    'npn_b': '#10B981',  # Green
    'plmn': '#EF4444',   # Red
    'gateway': '#F59E0B' # Orange
}

# Network parameters
MAX_NODES = 30
MAX_X = 100
MAX_Y = 100
MONITOR_INTERVAL = 5.0