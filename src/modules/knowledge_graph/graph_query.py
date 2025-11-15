"""
Graph Query Service
Provides graph-based query and analysis capabilities
"""
import logging
from typing import List, Dict, Set, Optional
from collections import defaultdict

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

from src.core.models import Entity, Relationship

logger = logging.getLogger(__name__)


class GraphQueryService:
    """Graph query and analysis service"""

    def __init__(self):
        """Initialize graph query service"""
        if not NETWORKX_AVAILABLE:
            logger.warning("NetworkX not installed, graph queries will be limited")

        self.graph: Optional['nx.DiGraph'] = None

    def build_graph(
        self,
        entities: List[Entity],
        relationships: List[Relationship]
    ) -> Optional['nx.DiGraph']:
        """Build NetworkX graph from entities and relationships"""
        if not NETWORKX_AVAILABLE:
            logger.warning("NetworkX not available")
            return None

        G = nx.DiGraph()

        # Add nodes (entities)
        for entity in entities:
            G.add_node(
                entity.id,
                type=entity.entity_type,
                name=entity.entity_name,
                importance=entity.importance_score,
                properties=entity.properties
            )

        # Add edges (relationships)
        for rel in relationships:
            G.add_edge(
                rel.source_entity_id,
                rel.target_entity_id,
                type=rel.relationship_type,
                weight=rel.weight,
                confidence=rel.confidence
            )

        self.graph = G
        logger.info(f"Built graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        return G

    def find_connected_concepts(
        self,
        concept_id: str,
        max_depth: int = 2
    ) -> List[Dict]:
        """Find concepts connected to a given concept"""
        if not self.graph or not NETWORKX_AVAILABLE:
            return []

        if concept_id not in self.graph:
            logger.warning(f"Concept {concept_id} not found in graph")
            return []

        try:
            # BFS to find connected nodes
            connected = nx.single_source_shortest_path_length(
                self.graph,
                concept_id,
                cutoff=max_depth
            )

            results = []
            for node_id, distance in connected.items():
                if node_id != concept_id:
                    node_data = self.graph.nodes[node_id]
                    results.append({
                        "id": node_id,
                        "name": node_data.get("name", ""),
                        "type": node_data.get("type", ""),
                        "distance": distance,
                        "importance": node_data.get("importance", 0.0)
                    })

            # Sort by distance and importance
            results.sort(key=lambda x: (x["distance"], -x["importance"]))
            return results

        except Exception as e:
            logger.error(f"Failed to find connected concepts: {e}")
            return []

    def find_shortest_path(
        self,
        source_id: str,
        target_id: str
    ) -> Optional[List[str]]:
        """Find shortest path between two entities"""
        if not self.graph or not NETWORKX_AVAILABLE:
            return None

        try:
            path = nx.shortest_path(self.graph, source_id, target_id)
            return path
        except nx.NetworkXNoPath:
            logger.info(f"No path found between {source_id} and {target_id}")
            return None
        except Exception as e:
            logger.error(f"Path finding failed: {e}")
            return None

    def compute_centrality(self) -> Dict[str, float]:
        """Compute centrality scores (importance) for all nodes"""
        if not self.graph or not NETWORKX_AVAILABLE:
            return {}

        try:
            # PageRank centrality
            centrality = nx.pagerank(self.graph, weight='weight')
            logger.info(f"Computed centrality for {len(centrality)} nodes")
            return centrality
        except Exception as e:
            logger.error(f"Centrality computation failed: {e}")
            return {}

    def detect_communities(self) -> List[Set[str]]:
        """Detect communities (research clusters) in the graph"""
        if not self.graph or not NETWORKX_AVAILABLE:
            return []

        try:
            # Convert to undirected for community detection
            G_undirected = self.graph.to_undirected()

            # Use Louvain algorithm if available
            try:
                import community as community_louvain
                partition = community_louvain.best_partition(G_undirected)

                # Group by community
                communities = defaultdict(set)
                for node, comm_id in partition.items():
                    communities[comm_id].add(node)

                result = list(communities.values())
                logger.info(f"Detected {len(result)} communities")
                return result

            except ImportError:
                # Fallback to connected components
                communities = list(nx.connected_components(G_undirected))
                logger.info(f"Found {len(communities)} connected components")
                return communities

        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return []

    def get_node_neighbors(
        self,
        node_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict]:
        """Get neighbors of a node"""
        if not self.graph:
            return []

        if node_id not in self.graph:
            return []

        neighbors = []
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.edges[node_id, neighbor]

            # Filter by relationship type if specified
            if relationship_type and edge_data.get("type") != relationship_type:
                continue

            node_data = self.graph.nodes[neighbor]
            neighbors.append({
                "id": neighbor,
                "name": node_data.get("name", ""),
                "type": node_data.get("type", ""),
                "relationship": edge_data.get("type", ""),
                "weight": edge_data.get("weight", 1.0)
            })

        return neighbors

    def get_subgraph(
        self,
        node_ids: List[str],
        include_edges: bool = True
    ) -> Optional['nx.DiGraph']:
        """Extract a subgraph containing specified nodes"""
        if not self.graph or not NETWORKX_AVAILABLE:
            return None

        try:
            # Filter to nodes that exist
            valid_nodes = [n for n in node_ids if n in self.graph]

            if not valid_nodes:
                return None

            subgraph = self.graph.subgraph(valid_nodes).copy()
            logger.info(f"Created subgraph with {subgraph.number_of_nodes()} nodes")
            return subgraph

        except Exception as e:
            logger.error(f"Subgraph extraction failed: {e}")
            return None

    def export_graph(self, format: str = "gexf") -> Optional[str]:
        """Export graph to file"""
        if not self.graph or not NETWORKX_AVAILABLE:
            return None

        try:
            output_path = f"graph_export.{format}"

            if format == "gexf":
                nx.write_gexf(self.graph, output_path)
            elif format == "graphml":
                nx.write_graphml(self.graph, output_path)
            elif format == "json":
                import json
                from networkx.readwrite import json_graph
                data = json_graph.node_link_data(self.graph)
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
            else:
                logger.error(f"Unsupported format: {format}")
                return None

            logger.info(f"Exported graph to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Graph export failed: {e}")
            return None
