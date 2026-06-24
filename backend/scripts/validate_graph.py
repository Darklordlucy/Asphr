import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import networkx as nx
import osmnx as ox

cache_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'map_cache', 'mumbai_full.graphml')
print('File size: %.1f MB' % (os.path.getsize(cache_path) / 1024 / 1024))

print('Loading graph...')
G = ox.load_graphml(cache_path)
print('Nodes: %d, Edges: %d' % (len(G.nodes), len(G.edges)))

comps = list(nx.weakly_connected_components(G))
print('Weakly connected components: %d' % len(comps))

# Validate: Kharghar to Panvel
print('\nValidating Kharghar -> Panvel...')
start = ox.nearest_nodes(G, X=73.0689, Y=19.0421)
end   = ox.nearest_nodes(G, X=73.1011, Y=18.9894)
same = any(start in c and end in c for c in comps)
print('Same component: %s' % same)

try:
    path = nx.shortest_path(G, source=start, target=end, weight='length')
    print('PATH FOUND! %d nodes' % len(path))
except nx.NetworkXNoPath:
    print('NO PATH FOUND')

# Validate: Bandra to Nariman Point
print('\nValidating Bandra -> Nariman Point...')
start2 = ox.nearest_nodes(G, X=72.8361, Y=19.0543)
end2   = ox.nearest_nodes(G, X=72.8210, Y=18.9256)
try:
    path2 = nx.shortest_path(G, source=start2, target=end2, weight='length')
    print('PATH FOUND! %d nodes' % len(path2))
except nx.NetworkXNoPath:
    print('NO PATH FOUND')

print('\nDone.')
