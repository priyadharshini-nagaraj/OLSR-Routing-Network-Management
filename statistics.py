"""Statistical analysis functions"""

import pandas as pd
import numpy as np
from typing import Dict, List
from collections import defaultdict

def calculate_protocol_statistics(sim):
    """Calculate comprehensive protocol statistics"""
    # Collect node statistics
    node_stats = []
    message_stats = defaultdict(int)
    node_type_stats = defaultdict(lambda: defaultdict(int))
    
    for node_id, node in sim.nodes.items():
        node_stats.append({
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
    
    # Calculate MPR statistics by node type
    mpr_by_type = []
    for node_type, stats in node_type_stats.items():
        avg_mprs = stats['mprs'] / max(1, stats['nodes'])
        mpr_by_type.append({
            'Node Type': node_type.upper(),
            'Avg MPRs per Node': avg_mprs,
            'Total Nodes': stats['nodes']
        })
    
    return {
        'node_stats': pd.DataFrame(node_stats),
        'message_stats': dict(message_stats),
        'mpr_by_type': pd.DataFrame(mpr_by_type),
        'node_type_stats': dict(node_type_stats)
    }

def calculate_network_efficiency(sim, message_stats: Dict):
    """Calculate network efficiency metrics"""
    stats = sim.get_network_statistics()
    
    # Control vs Data messages
    control_msgs = sum(count for msg_type, count in message_stats.items() 
                      if msg_type in ['HELLO', 'TOPOLOGY_CONTROL'])
    data_msgs = message_stats.get('DATA', 0)
    
    # Protocol efficiency
    efficiency_metrics = {
        'control_messages': control_msgs,
        'data_messages': data_msgs,
        'control_data_ratio': control_msgs / max(1, data_msgs),
        'mpr_efficiency': stats['active_mprs'] / max(1, stats['total_nodes']),
        'link_utilization': stats['total_links'] / (stats['total_nodes'] * (stats['total_nodes'] - 1) / 2)
    }
    
    return efficiency_metrics

def calculate_performance_insights(sim, metrics_df: pd.DataFrame):
    """Calculate performance insights and recommendations"""
    insights = []
    
    avg_pdr = metrics_df['PDR'].mean() if not metrics_df.empty else 0
    avg_delay = metrics_df['Delay (ms)'].mean() if not metrics_df.empty else 0
    
    # PDR insights
    if avg_pdr > 0.95:
        insights.append("✅ **Excellent Reliability**: OLSR provides high packet delivery suitable for critical management data")
    elif avg_pdr > 0.90:
        insights.append("⚠️ **Good Reliability**: Acceptable for most analytics traffic, consider optimizing MPR selection")
    else:
        insights.append("❌ **Reliability Concern**: Investigate network connectivity and routing convergence")
    
    # Delay insights
    if avg_delay < 50:
        insights.append("✅ **Low Latency**: Suitable for real-time analytics and time-sensitive operations")
    elif avg_delay < 100:
        insights.append("⚠️ **Moderate Latency**: Acceptable for periodic analytics data collection")
    else:
        insights.append("❌ **High Latency**: May impact time-sensitive management operations")
    
    # Convergence analysis
    if len(metrics_df) > 5:
        early_pdr = metrics_df['PDR'].iloc[:3].mean()
        late_pdr = metrics_df['PDR'].iloc[-3:].mean()
        
        if late_pdr > early_pdr * 1.15:
            insights.append("📈 **Good Convergence**: Network performance improves as routes stabilize")
        elif late_pdr < early_pdr * 0.85:
            insights.append("📉 **Performance Degradation**: Network may be overloaded or experiencing instability")
    
    # MPR efficiency
    stats = sim.get_network_statistics()
    mpr_efficiency = stats['active_mprs'] / max(1, stats['total_nodes'])
    if mpr_efficiency < 0.3:
        insights.append("⚡ **Efficient MPR Selection**: Minimal MPRs selected, reducing control overhead")
    elif mpr_efficiency > 0.5:
        insights.append("⚠️ **High MPR Count**: Consider optimizing MPR selection criteria")
    
    return insights

def calculate_connectivity_metrics(sim):
    """Calculate network connectivity metrics"""
    node_ids = list(sim.nodes.keys())
    n = len(node_ids)
    
    if n == 0:
        return {
            'connectivity_ratio': 0,
            'avg_node_degree': 0,
            'network_density': 0
        }
    
    total_possible_links = n * (n - 1) / 2
    actual_links = len(sim.links)
    
    return {
        'connectivity_ratio': actual_links / total_possible_links if total_possible_links > 0 else 0,
        'avg_node_degree': 2 * actual_links / n,
        'network_density': actual_links / total_possible_links if total_possible_links > 0 else 0
    }