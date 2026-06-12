"""OLSR protocol logic and MPR selection algorithms"""

from typing import Set, Dict, List
import networkx as nx

class OLSRProtocol:
    """OLSR protocol logic implementation"""
    
    @staticmethod
    def select_mpr(neighbors: Set[str], two_hop_neighbors: Set[str], 
                  network_nodes: Dict) -> Set[str]:
        """
        MPR selection algorithm (RFC 3626)
        
        Args:
            neighbors: Set of one-hop neighbors
            two_hop_neighbors: Set of two-hop neighbors
            network_nodes: Dictionary of all network nodes
            
        Returns:
            Set of selected MPR nodes
        """
        mpr_set = set()
        
        # If no two-hop neighbors, no MPR needed
        if not two_hop_neighbors:
            return mpr_set
        
        uncovered = set(two_hop_neighbors)
        
        # Phase 1: Select nodes that are the only way to reach some two-hop neighbors
        for n2 in two_hop_neighbors:
            reachable_by = set()
            for neighbor in neighbors:
                if neighbor in network_nodes:
                    neighbor_node = network_nodes[neighbor]
                    if n2 in neighbor_node.neighbors:
                        reachable_by.add(neighbor)
            
            # If only one neighbor can reach this two-hop neighbor
            if len(reachable_by) == 1:
                only_neighbor = next(iter(reachable_by))
                if only_neighbor not in mpr_set:
                    mpr_set.add(only_neighbor)
                    # Update uncovered set
                    neighbor_node = network_nodes[only_neighbor]
                    uncovered -= set(neighbor_node.neighbors)
        
        # Phase 2: Greedy selection
        while uncovered:
            best_neighbor = None
            best_coverage = 0
            
            for neighbor in neighbors - mpr_set:
                if neighbor in network_nodes:
                    neighbor_node = network_nodes[neighbor]
                    coverage = len(uncovered.intersection(neighbor_node.neighbors))
                    if coverage > best_coverage:
                        best_coverage = coverage
                        best_neighbor = neighbor
            
            if best_neighbor:
                mpr_set.add(best_neighbor)
                neighbor_node = network_nodes[best_neighbor]
                uncovered -= set(neighbor_node.neighbors)
            else:
                break
        
        return mpr_set
    
    @staticmethod
    def calculate_routing_table(node_id: str, neighbors: Set[str],
                               topology_set: Set[tuple], 
                               all_nodes: Set[str]) -> Dict[str, List[str]]:
        """
        Calculate routing table using shortest path algorithm
        
        Args:
            node_id: Current node ID
            neighbors: Set of one-hop neighbors
            topology_set: Set of known links (tuples)
            all_nodes: Set of all node IDs in network
            
        Returns:
            Routing table dictionary {destination: path_list}
        """
        routing_table = {}
        
        # Build network graph
        G = nx.Graph()
        
        # Add all nodes
        for node in all_nodes:
            G.add_node(node)
        
        # Add edges from topology information
        for link in topology_set:
            if isinstance(link, tuple) and len(link) == 2:
                G.add_edge(link[0], link[1], weight=1)
        
        # Add direct neighbor edges
        for neighbor in neighbors:
            G.add_edge(node_id, neighbor, weight=1)
        
        # Calculate shortest paths if graph is connected
        if nx.is_connected(G):
            try:
                paths = nx.single_source_shortest_path(G, node_id)
                routing_table = paths
            except nx.NetworkXError:
                # If no path exists, create empty routing table
                pass
        
        return routing_table
    
    @staticmethod
    def update_two_hop_neighbors(neighbors: Set[str], 
                                network_nodes: Dict) -> Set[str]:
        """
        Calculate two-hop neighbor set
        
        Args:
            neighbors: Set of one-hop neighbors
            network_nodes: Dictionary of all network nodes
            
        Returns:
            Set of two-hop neighbors
        """
        two_hop = set()
        
        for neighbor in neighbors:
            if neighbor in network_nodes:
                neighbor_node = network_nodes[neighbor]
                two_hop.update(neighbor_node.neighbors)
        
        # Remove one-hop neighbors and self
        two_hop -= neighbors
        
        return two_hop