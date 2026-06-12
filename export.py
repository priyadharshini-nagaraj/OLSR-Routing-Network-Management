"""Data export functions"""

import pandas as pd
import json
from typing import Dict, List

def export_metrics_csv(sim):
    """Export performance metrics to CSV"""
    metrics_df = pd.DataFrame({
        'Time': sim.metrics['time'],
        'PDR': sim.metrics['pdr'],
        'Delay_ms': sim.metrics['delay'],
        'Overhead_Ratio': sim.metrics['overhead'],
        'Throughput': sim.metrics['throughput']
    })
    return metrics_df.to_csv(index=False)

def export_node_statistics_csv(sim):
    """Export node statistics to CSV"""
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
    return df.to_csv(index=False)

def export_packet_log_csv(sim):
    """Export packet log to CSV"""
    if not sim.packet_log:
        return ""
    
    df = pd.DataFrame(sim.packet_log)
    return df.to_csv(index=False)

def export_message_log_csv(sim):
    """Export message log to CSV"""
    if not sim.message_log:
        return ""
    
    df = pd.DataFrame(sim.message_log)
    return df.to_csv(index=False)

def export_config_json(config: Dict):
    """Export simulation configuration to JSON"""
    return json.dumps(config, indent=2)

def export_full_simulation_data(sim, config: Dict):
    """Export complete simulation data as JSON"""
    data = {
        'configuration': config,
        'network_statistics': sim.get_network_statistics(),
        'metrics_summary': {
            'average_pdr': np.mean(sim.metrics['pdr']) if sim.metrics['pdr'] else 0,
            'average_delay': np.mean(sim.metrics['delay']) if sim.metrics['delay'] else 0,
            'average_overhead': np.mean(sim.metrics['overhead']) if sim.metrics['overhead'] else 0,
            'average_throughput': np.mean(sim.metrics['throughput']) if sim.metrics['throughput'] else 0
        },
        'node_count': len(sim.nodes),
        'simulation_time': sim.env.now if hasattr(sim, 'env') else 0
    }
    
    return json.dumps(data, indent=2, default=str)