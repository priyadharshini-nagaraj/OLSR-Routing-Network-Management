"""Main Streamlit application"""

import streamlit as st
import pandas as pd
import time
from typing import Dict, Optional

from config import DEFAULT_CONFIG, NODE_COLORS
from simulation.network import NetworkSimulation
from simulation.core import run_simulation
from visualization.topology import create_network_visualization
from visualization.metrics import (
    create_pdr_chart, create_delay_chart, create_overhead_throughput_chart,
    create_message_distribution_chart, create_mpr_distribution_chart,
    create_node_message_chart
)
from analytics.statistics import (
    calculate_protocol_statistics, calculate_network_efficiency,
    calculate_performance_insights, calculate_connectivity_metrics
)
from analytics.export import (
    export_metrics_csv, export_node_statistics_csv,
    export_config_json, export_full_simulation_data
)

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

def initialize_session_state():
    """Initialize session state variables"""
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = None
    if 'simulation_config' not in st.session_state:
        st.session_state.simulation_config = {}
    if 'simulation_running' not in st.session_state:
        st.session_state.simulation_running = False

def create_sidebar_controls():
    """Create sidebar configuration controls"""
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

def display_network_topology_tab(sim):
    """Display network topology tab"""
    st.markdown("## Network Topology Visualization")
    
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
    
    # Display node details
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

def display_performance_metrics_tab(sim):
    """Display performance metrics tab"""
    st.markdown("## Performance Metrics Analysis")
    
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
        
        # Create and display charts
        st.plotly_chart(create_pdr_chart(metrics_df), use_container_width=True)
        st.plotly_chart(create_delay_chart(metrics_df), use_container_width=True)
        st.plotly_chart(create_overhead_throughput_chart(metrics_df), use_container_width=True)

def display_protocol_analysis_tab(sim):
    """Display protocol analysis tab"""
    st.markdown("## OLSR Protocol Analysis")
    
    # Calculate protocol statistics
    stats = calculate_protocol_statistics(sim)
    
    st.markdown("### MPR Distribution Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not stats['mpr_by_type'].empty:
            st.plotly_chart(create_mpr_distribution_chart(stats['mpr_by_type']), 
                          use_container_width=True)
    
    with col2:
        if not stats['node_stats'].empty:
            st.plotly_chart(
                create_node_message_chart(stats['node_stats']), 
                use_container_width=True
            )
    
    # Message statistics
    st.markdown("### Message Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if stats['message_stats']:
            st.plotly_chart(
                create_message_distribution_chart(stats['message_stats']), 
                use_container_width=True
            )
    
    with col2:
        # Protocol efficiency metrics
        efficiency = calculate_network_efficiency(sim, stats['message_stats'])
        
        st.markdown("#### Protocol Efficiency")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Control Messages", efficiency['control_messages'])
        with col_b:
            st.metric("Data Messages", efficiency['data_messages'])
        with col_c:
            st.metric("Control/Data Ratio", f"{efficiency['control_data_ratio']:.2f}")

def display_results_tab(sim, config: Dict):
    """Display results and export tab"""
    st.markdown("## Simulation Results & Export")
    
    # Summary statistics
    st.markdown("### Simulation Summary")
    
    stats = sim.get_network_statistics()
    avg_pdr = np.mean(sim.metrics['pdr']) if sim.metrics['pdr'] else 0
    avg_delay = np.mean(sim.metrics['delay']) if sim.metrics['delay'] else 0
    
    summary_cols = st.columns(2)
    
    with summary_cols[0]:
        st.markdown("**Network Configuration:**")
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
    metrics_df = pd.DataFrame(sim.metrics)
    insights = calculate_performance_insights(sim, metrics_df)
    
    st.markdown("### Performance Insights")
    for insight in insights:
        st.write(insight)
    
    # Export data section
    st.markdown("### Export Simulation Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Metrics CSV", use_container_width=True):
            csv = export_metrics_csv(sim)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="olsr_metrics.csv",
                mime="text/csv",
                key="metrics_csv"
            )
    
    with col2:
        if st.button("📋 Export Node Statistics", use_container_width=True):
            csv = export_node_statistics_csv(sim)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="node_statistics.csv",
                mime="text/csv",
                key="nodes_csv"
            )
    
    with col3:
        if st.button("⚙️ Export Configuration", use_container_width=True):
            config_json = export_config_json(config)
            st.download_button(
                label="Download JSON",
                data=config_json,
                file_name="simulation_config.json",
                mime="application/json",
                key="config_json"
            )

def main():
    """Main application entry point"""
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">OLSR Protocol Simulation Framework</h1>', 
                unsafe_allow_html=True)
    st.markdown("""
    ### **Hybrid NPN/PLMN Network Simulation**
    
    Discrete-event simulation of Optimized Link State Routing protocol in 5G hybrid networks
    with Non-Public Networks (NPN A & B) and Public Land Mobile Network (PLMN) analytics.
    """)
    
    # Sidebar controls
    create_sidebar_controls()
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📡 Network Topology",
        "📊 Performance Metrics", 
        "🔬 Protocol Analysis",
        "📈 Results & Export"
    ])
    
    # Display appropriate content based on simulation state
    if st.session_state.simulation_results:
        sim = st.session_state.simulation_results
        config = st.session_state.simulation_config
        
        with tab1:
            display_network_topology_tab(sim)
        
        with tab2:
            display_performance_metrics_tab(sim)
        
        with tab3:
            display_protocol_analysis_tab(sim)
        
        with tab4:
            display_results_tab(sim, config)
    
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