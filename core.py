"""Core simulation runner"""

import simpy
from simulation.network import NetworkSimulation

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