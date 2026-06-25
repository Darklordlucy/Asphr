import math
from typing import Dict, List, Tuple, Any, Optional
import networkx as nx
import osmnx as ox
from shapely.geometry import LineString

from app.algorithms.graph_builder import GraphManager, calculate_bearing

class RouteOptimizer:
    def __init__(self):
        self.manager = GraphManager.get_instance()

    def get_vehicle_filtered_graph(self, G: nx.MultiDiGraph, vehicle_type: str, avoid_tolls: bool = False) -> nx.MultiDiGraph:
        """Create a filtered view of the graph based on vehicle constraints."""
        vehicle_type = vehicle_type.lower()
        
        def filter_edge(u, v, k) -> bool:
            data = G[u][v][k]
            
            # Avoid tolls if requested
            if avoid_tolls and data.get("is_toll", False):
                return False
                
            # 1. Supercars avoid speed bumps
            if vehicle_type == "supercar":
                # Check graph attribute or database override
                if data.get("has_speed_bump", False):
                    return False
                # Supercars also avoid extremely rough roads or living streets
                if data.get("highway") in ["living_street", "unclassified", "track"]:
                    return False

            # 2. Bikes avoid motorways and prefer bike-friendly or smaller roads
            elif vehicle_type == "bike":
                if data.get("highway") in ["motorway", "motorway_link", "trunk", "trunk_link"]:
                    return False

            # 3. Trucks avoid narrow paths and living streets
            elif vehicle_type == "truck":
                if data.get("highway") in ["living_street", "service", "pedestrian", "path"]:
                    return False
                # If width/height attributes exist, we could filter here
                if float(data.get("width", 99.0)) < 3.0:
                    return False
            
            return True

        return nx.subgraph_view(G, filter_edge=filter_edge)

    def compute_route(
        self, 
        start_lat: float, 
        start_lon: float, 
        end_lat: float, 
        end_lon: float, 
        route_type: str, 
        vehicle_type: str,
        avoid_tolls: bool = False
    ) -> Dict[str, Any]:
        """Snaps input coordinates, filters by vehicle, selects weight, and computes path."""
        G = self.manager.get_graph()
        route_type = route_type.lower()
        
        # 1. Snap coordinates to nearest nodes
        start_node = ox.nearest_nodes(G, X=start_lon, Y=start_lat)
        end_node = ox.nearest_nodes(G, X=end_lon, Y=end_lat)

        if start_node == end_node:
            raise ValueError("Start and end locations are too close to each other.")

        # 2. Filter graph by vehicle constraints
        filtered_G = self.get_vehicle_filtered_graph(G, vehicle_type, avoid_tolls=avoid_tolls)
        
        # If the start or end node is disconnected due to filtering, fall back to full graph
        if start_node not in filtered_G:
            filtered_G = G
            print(f"Warning: Start node {start_node} not in filtered graph. Falling back to full graph.")
        if end_node not in filtered_G:
            filtered_G = G
            print(f"Warning: End node {end_node} not in filtered graph. Falling back to full graph.")

        # 3. Pathfinding and Weight Selection
        import time
        start_time = time.perf_counter()
        
        path = []
        weight_attribute = ""
        active_graph = filtered_G
        algo_used = "Dijkstra"
        
        try:
            if route_type == "fastest":
                weight_attribute = "weight_fastest"
                path = nx.shortest_path(active_graph, source=start_node, target=end_node, weight=weight_attribute)
            
            elif route_type == "safest":
                weight_attribute = "weight_safest"
                path = nx.shortest_path(active_graph, source=start_node, target=end_node, weight=weight_attribute)
            
            elif route_type == "popular":
                weight_attribute = "weight_popular"
                path = nx.shortest_path(active_graph, source=start_node, target=end_node, weight=weight_attribute)
            
            elif route_type == "straightest":
                algo_used = "A* Search"
                # Implement A* with dynamic angular turn cost and great-circle heuristic
                target_lat = G.nodes[end_node]['y']
                target_lon = G.nodes[end_node]['x']
                
                # Heuristic: great-circle distance to target
                def heuristic(u, target):
                    u_lat = G.nodes[u]['y']
                    u_lon = G.nodes[u]['x']
                    return ox.distance.great_circle(u_lat, u_lon, target_lat, target_lon)

                # Weight: combines edge cost (straightest parameter) + turn bearing deviation
                def straightest_cost(u, v, edge_data):
                    length = edge_data.get('length', 1.0)
                    tortuosity = edge_data.get('tortuosity', 1.0)
                    edge_bearing = edge_data.get('bearing', 0.0)
                    
                    # Calculate direction bearing from u to destination
                    u_lat = G.nodes[u]['y']
                    u_lon = G.nodes[u]['x']
                    dest_bearing = calculate_bearing(u_lat, u_lon, target_lat, target_lon)
                    
                    # Compute angle deviation
                    diff = abs(edge_bearing - dest_bearing)
                    diff = min(diff, 360 - diff)
                    angular_deviation = diff / 180.0 # 0.0 (directly towards) to 1.0 (directly away)
                    
                    # Return composite straightness penalty (straight edges going towards destination cost less)
                    return length * tortuosity * (1.0 + angular_deviation * 2.5)

                path = nx.astar_path(active_graph, source=start_node, target=end_node, heuristic=heuristic, weight=straightest_cost)
            
            else:
                # Default fallback
                weight_attribute = "length"
                path = nx.shortest_path(active_graph, source=start_node, target=end_node, weight=weight_attribute)

        except nx.NetworkXNoPath:
            # Fall back to standard Dijkstra on full graph if no path is found
            print(f"No path found on filtered graph for {vehicle_type}. Falling back to full graph.")
            active_graph = G
            algo_used = "Dijkstra (Fallback)"
            try:
                weight_attribute = "length"
                path = nx.shortest_path(active_graph, source=start_node, target=end_node, weight="length")
            except nx.NetworkXNoPath:
                raise ValueError("No routing path exists between selected locations.")

        # 4. Resolve Route Details and Coordinates
        route_coords = []
        total_distance = 0.0
        total_duration = 0.0
        segments = []

        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            
            # Find the best edge between u and v
            edge_data = None
            min_weight = float('inf')
            
            # Iterate through parallel edges and select the one with the smallest weight
            for k, data in active_graph[u][v].items():
                w = data.get(weight_attribute, data.get('length', 0.0)) if weight_attribute else data.get('length', 0.0)
                if w < min_weight:
                    min_weight = w
                    edge_data = data
            
            if edge_data is None:
                continue

            length = float(edge_data.get('length', 0.0))
            total_distance += length
            
            # Duration estimation (in minutes) based on fastest weight or default speed limits
            # weight_fastest is in seconds, so divide by 60
            duration_sec = edge_data.get('weight_fastest', length / (30.0 / 3.6)) 
            total_duration += duration_sec / 60.0

            # Gather segment coordinates
            node_u = G.nodes[u]
            if 'geometry' in edge_data and isinstance(edge_data['geometry'], LineString):
                # Add all coordinates of the linestring (excluding the last one to avoid duplication)
                coords = list(edge_data['geometry'].coords)[:-1]
                route_coords.extend(coords)
            else:
                route_coords.append((node_u['x'], node_u['y']))
                
            # Map congestion level to traffic text
            cong_lvl = edge_data.get("congestion_level", 0)
            traffic_map = {
                0: "free-flow",
                1: "light",
                2: "moderate",
                3: "heavy",
                4: "standstill"
            }
            traffic_str = traffic_map.get(cong_lvl, "free-flow")

            segments.append({
                "id": edge_data.get("segment_id"),
                "hazard": edge_data.get("hazard_score", 0.0),
                "traffic": traffic_str,
                "hazard_score": edge_data.get("hazard_score", 0.0) # Keep for compatibility
            })

        # Append final destination node coordinate
        dest_node = G.nodes[end_node]
        route_coords.append((dest_node['x'], dest_node['y']))

        # Convert coordinates into [longitude, latitude] sequence (standard GeoJSON)
        geojson_coords = [[lon, lat] for lon, lat in route_coords]

        # Calculate average hazard score for path
        hazard_sum = 0.0
        for segment in segments:
            hazard_sum += segment.get("hazard_score", 0.0)
        avg_hazard = hazard_sum / len(segments) if segments else 0.0

        # Strip internal temporary field
        for seg in segments:
            seg.pop("hazard_score", None)

        end_time = time.perf_counter()
        search_time_ms = round((end_time - start_time) * 1000.0, 2)

        # Count nodes in the bounding box between start and end coordinates
        min_x = min(G.nodes[start_node]['x'], G.nodes[end_node]['x'])
        max_x = max(G.nodes[start_node]['x'], G.nodes[end_node]['x'])
        min_y = min(G.nodes[start_node]['y'], G.nodes[end_node]['y'])
        max_y = max(G.nodes[start_node]['y'], G.nodes[end_node]['y'])

        # Add 0.015 degrees padding (~1.5km buffer) to represent the local search corridor
        pad_x = 0.015
        pad_y = 0.015
        bbox_nodes_count = sum(
            1 for n, data in G.nodes(data=True)
            if (min_x - pad_x) <= data['x'] <= (max_x + pad_x) and (min_y - pad_y) <= data['y'] <= (max_y + pad_y)
        )

        return {
            "origin_node": start_node,
            "destination_node": end_node,
            "coordinates": geojson_coords,
            "distance_km": round(total_distance / 1000.0, 2),
            "duration_min": int(round(total_duration)),
            "hazard_score_avg": round(avg_hazard, 2),
            "segments_count": len(segments),
            "segments": segments,
            "search_stats": {
                "total_nodes_in_search_area": bbox_nodes_count,
                "nodes_selected": len(path),
                "search_time_ms": search_time_ms,
                "algorithm": algo_used,
                "graph_total_nodes": len(G.nodes)
            }
        }
