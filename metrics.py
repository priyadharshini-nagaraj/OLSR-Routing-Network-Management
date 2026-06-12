"""Performance metrics visualization"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List

def create_pdr_chart(metrics_df: pd.DataFrame):
    """Create Packet Delivery Ratio chart"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=metrics_df['Time'],
        y=metrics_df['PDR'],
        mode='lines+markers',
        name='Packet Delivery Ratio',
        line=dict(color='green', width=2),
        marker=dict(size=6)
    ))
    fig.update_layout(
        title='Packet Delivery Ratio Over Time',
        xaxis_title='Simulation Time (s)',
        yaxis_title='PDR',
        hovermode='x unified',
        height=400,
        template='plotly_white'
    )
    return fig

def create_delay_chart(metrics_df: pd.DataFrame):
    """Create End-to-End Delay chart"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=metrics_df['Time'],
        y=metrics_df['Delay (ms)'],
        mode='lines+markers',
        name='End-to-End Delay',
        line=dict(color='red', width=2),
        marker=dict(size=6)
    ))
    fig.update_layout(
        title='End-to-End Delay Over Time',
        xaxis_title='Simulation Time (s)',
        yaxis_title='Delay (ms)',
        hovermode='x unified',
        height=400,
        template='plotly_white'
    )
    return fig

def create_overhead_throughput_chart(metrics_df: pd.DataFrame):
    """Create combined overhead and throughput chart"""
    fig = go.Figure()
    
    # Overhead Ratio
    fig.add_trace(go.Scatter(
        x=metrics_df['Time'],
        y=metrics_df['Overhead Ratio'],
        name='Routing Overhead',
        line=dict(color='blue', width=2)
    ))
    
    # Throughput
    fig.add_trace(go.Scatter(
        x=metrics_df['Time'],
        y=metrics_df['Throughput'],
        name='Throughput',
        yaxis='y2',
        line=dict(color='orange', width=2)
    ))
    
    fig.update_layout(
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
    return fig

def create_message_distribution_chart(message_stats: Dict):
    """Create message type distribution pie chart"""
    msg_types = list(message_stats.keys())
    msg_counts = list(message_stats.values())
    
    fig = px.pie(
        values=msg_counts,
        names=msg_types,
        title='Message Type Distribution',
        hole=0.4
    )
    fig.update_layout(height=350)
    return fig

def create_mpr_distribution_chart(mpr_data: pd.DataFrame):
    """Create MPR distribution bar chart"""
    fig = px.bar(
        mpr_data,
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
    return fig

def create_node_message_chart(node_data: pd.DataFrame):
    """Create node message statistics chart"""
    top_nodes = node_data.nlargest(8, 'Messages Sent')
    
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
    return fig