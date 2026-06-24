import sys
sys.path.insert(0, 'd:/Asphr/backend')
import networkx as nx
import osmnx as ox
import os

cache_path = 'd:/Asphr/backend/data/map_cache/mumbai_full.graphml'
print(f'Cache size: {os.path.getsize(cache_path)} bytes')
G = ox.load_graphml(cache_path)
print(f'Nodes: {len(G.nodes)}, Edges: {len(G.edges)}')

# Check connectivity
comps = list(nx.weakly_connected_components(G))
print(f'Weakly connected components: {len(comps)}')
sizes = sorted([len(c) for c in comps], reverse=True)[:5]
print(f'Top 5 component sizes: {sizes}')

# Check if weight_fastest exists on edges (sample)
has_weight = 0
no_weight = 0
for u, v, k, d in list(G.edges(keys=True, data=True))[:1000]:
    if 'weight_fastest' in d:
        has_weight += 1
    else:
        no_weight += 1
print(f'Edges WITH weight_fastest: {has_weight}, WITHOUT: {no_weight}')

# Try to find path between Kharghar and Panvel
kharghar_lat, kharghar_lon = 19.0421, 73.0689
panvel_lat, panvel_lon = 18.9894, 73.1011

start_node = ox.nearest_nodes(G, X=kharghar_lon, Y=kharghar_lat)
end_node   = ox.nearest_nodes(G, X=panvel_lon, Y=panvel_lat)
print(f'Start node: {start_node}, End node: {end_node}')
print(f'Start in G: {start_node in G}, End in G: {end_node in G}')

# Check if they're in the same component
same_comp = False
for comp in comps:
    if start_node in comp and end_node in comp:
        same_comp = True
        break
print(f'Same weakly connected component: {same_comp}')

try:
    path = nx.shortest_path(G, source=start_node, target=end_node, weight='length')
    print(f'Path found via length! Nodes: {len(path)}')
except nx.NetworkXNoPath:
    print('NO PATH via length!')
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
