"""
normalize_graph.py — Fix list-typed edge attributes in mumbai_full.graphml.

Some OSMnx edges store numeric fields (length, width, etc.) as lists instead of
scalars, e.g. length=[100.0] instead of length=100.0. The route_optimizer calls
float(edge_data.get('length')) which crashes with "float() argument must be a
string or a real number, not 'list'".

This script loads the graph, flattens every list-typed numeric attribute to its
first element, and saves the file back in-place. No backend code changes needed.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import osmnx as ox

CACHE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'map_cache', 'mumbai_full.graphml')

# Attributes that must be scalar numbers
NUMERIC_ATTRS = [
    'length', 'width', 'lanes', 'maxspeed', 'bearing', 'tortuosity',
    'weight_fastest', 'weight_safest', 'weight_popular', 'weight_straightest',
    'speed_kph', 'travel_time', 'grade', 'grade_abs',
]

def flatten(val):
    """Return first element if val is a list, otherwise val unchanged."""
    if isinstance(val, list):
        return val[0] if val else None
    return val

print('Loading graph from %s ...' % CACHE_PATH)
G = ox.load_graphml(CACHE_PATH)
print('Nodes: %d  Edges: %d' % (len(G.nodes), len(G.edges)))

fixed_edges = 0
fixed_fields = 0

for u, v, k, data in G.edges(keys=True, data=True):
    changed = False
    for attr in NUMERIC_ATTRS:
        if attr in data and isinstance(data[attr], list):
            data[attr] = flatten(data[attr])
            fixed_fields += 1
            changed = True
    # Also fix any OTHER attribute that is a list of a single number
    for attr, val in list(data.items()):
        if attr not in NUMERIC_ATTRS and isinstance(val, list):
            if len(val) == 1:
                data[attr] = val[0]
                fixed_fields += 1
                changed = True
    if changed:
        fixed_edges += 1

print('Fixed %d list attributes across %d edges.' % (fixed_fields, fixed_edges))

# Also normalize node attributes
fixed_nodes = 0
for n, data in G.nodes(data=True):
    for attr in ['x', 'y', 'lon', 'lat', 'elevation']:
        if attr in data and isinstance(data[attr], list):
            data[attr] = flatten(data[attr])
            fixed_nodes += 1

print('Fixed %d node list attributes.' % fixed_nodes)

print('Saving normalized graph...')
ox.save_graphml(G, CACHE_PATH)
print('Saved to %s' % CACHE_PATH)
print('Done. Restart the backend.')
