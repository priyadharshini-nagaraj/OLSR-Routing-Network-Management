"""Network topology visualization"""

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from typing import Dict
from config import NODE_COLORS

def create_network_visualization(sim):
    """Create network topology visualization"""
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Draw nodes
    for node_id, node in sim.nodes.items():
        pos = node.position
        node_color = NODE_COLORS.get(node.node_type, 'gray')
        
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
    create_topology_legend(ax)
    
    return fig

def create_topology_legend(ax):
    """Create topology visualization legend"""
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=NODE_COLORS['npn_a'], 
                  markersize=10, label='NPN A', markeredgecolor='black'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=NODE_COLORS['npn_b'], 
                  markersize=10, label='NPN B', markeredgecolor='black'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=NODE_COLORS['plmn'], 
                  markersize=10, label='PLMN', markeredgecolor='black'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=NODE_COLORS['gateway'], 
                  markersize=10, label='Gateway', markeredgecolor='black'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='yellow', 
                  markersize=10, label='MPR Node', alpha=0.5, markeredgecolor='darkgoldenrod')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10, 
             framealpha=0.9, fancybox=True, shadow=True)

def create_connectivity_matrix(sim):
    """Create network connectivity matrix visualization"""
    import plotly.graph_objects as go
    
    node_ids = list(sim.nodes.keys())
    connectivity = np.zeros((len(node_ids), len(node_ids)))
    
    for i, node1 in enumerate(node_ids):
        for j, node2 in enumerate(node_ids):
            if i != j:
                key = tuple(sorted([node1, node2]))
                if key in sim.links:
                    connectivity[i, j] = 1
    
    fig = go.Figure(data=go.Heatmap(
        z=connectivity,
        x=node_ids,
        y=node_ids,
        colorscale='Blues',
        showscale=True
    ))
    
    fig.update_layout(
        title="Network Connectivity Matrix",
        xaxis_title="Node ID",
        yaxis_title="Node ID",
        height=500,
        template='plotly_white'
    )
    
    return fig