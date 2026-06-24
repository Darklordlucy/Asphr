"""
rebuild_graph.py — One-time repair script for the disconnected Mumbai road graph.

ROOT CAUSE: The original tiles were downloaded with simplify=True and hard bbox cuts.
OSMnx creates different simplified boundary nodes for each tile, so nx.compose_all()
produces 16 disconnected islands.

FIX: Re-download tiles with a 10% geographic overlap so adjacent tiles share boundary
nodes (same OSM IDs), making nx.compose_all() produce a properly connected graph.

Usage:
    python scripts/rebuild_graph.py

Takes roughly 10–20 minutes depending on Overpass API speed.
Restart the backend after this finishes.
"""

import sys
import os
import time
import math
import json

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import networkx as nx
import osmnx as ox

ox.settings.use_cache = True
ox.settings.log_console = False

# ─── Config ──────────────────────────────────────────────────────────────────
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'map_cache')
OUTPUT_PATH = os.path.join(CACHE_DIR, 'mumbai_full.graphml')

# Mumbai full bounding box
MIN_LAT, MAX_LAT = 18.90, 19.50
MIN_LON, MAX_LON = 72.75, 73.20

GRID_ROWS, GRID_COLS = 4, 4

# Overlap fraction — 10% of tile size so boundary nodes are shared
OVERLAP_FRAC = 0.10

# ─── Helpers ─────────────────────────────────────────────────────────────────

def calculate_bearing(lat1, lon1, lat2, lon2):
    import math
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    d_lon = lon2 - lon1
    y = math.sin(d_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
    return math.degrees(math.atan2(y, x)) % 360


def download_tile(min_lon, min_lat, max_lon, max_lat, tile_id, retries=3):
    """Download a single tile with retries, using OSMnx cache when available."""
    tile_cache = os.path.join(CACHE_DIR, f'overlap_tile_{tile_id}.graphml')
    if os.path.exists(tile_cache):
        try:
            g = ox.load_graphml(tile_cache)
            print(f'  [{tile_id}] loaded from overlap cache ({len(g.nodes)} nodes)')
            return g
        except Exception:
            pass

    for attempt in range(retries):
        try:
            g = ox.graph_from_bbox(
                bbox=(min_lon, min_lat, max_lon, max_lat),
                network_type='drive',
                simplify=True,
            )
            ox.save_graphml(g, tile_cache)
            print(f'  [{tile_id}] downloaded ({len(g.nodes)} nodes, {len(g.edges)} edges)')
            return g
        except Exception as e:
            msg = str(e).lower()
            if 'insufficient' in msg or 'found no graph' in msg or 'no data' in msg:
                print(f'  [{tile_id}] empty area (no roads) — skipping')
                return None
            wait = 10 * (attempt + 1)
            print(f'  [{tile_id}] attempt {attempt+1}/{retries} failed: {e}. Retrying in {wait}s...')
            time.sleep(wait)

    print(f'  [{tile_id}] FAILED after {retries} attempts — skipping')
    return None


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(CACHE_DIR, exist_ok=True)

    lat_step = (MAX_LAT - MIN_LAT) / GRID_ROWS
    lon_step = (MAX_LON - MIN_LON) / GRID_COLS
    lat_overlap = lat_step * OVERLAP_FRAC
    lon_overlap = lon_step * OVERLAP_FRAC

    print('=' * 60)
    print('ASPHR Graph Rebuild — Overlapping Tile Download')
    print(f'Grid: {GRID_ROWS}x{GRID_COLS}, Overlap: {OVERLAP_FRAC*100:.0f}%')
    print(f'Tile size: {lat_step:.4f}° lat × {lon_step:.4f}° lon')
    print(f'Overlap:   {lat_overlap:.4f}° lat × {lon_overlap:.4f}° lon')
    print('=' * 60)

    graphs = []
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            tile_id = f'ov_{r}_{c}'

            # Base tile bounds
            tile_min_lat = MIN_LAT + r * lat_step
            tile_max_lat = tile_min_lat + lat_step
            tile_min_lon = MIN_LON + c * lon_step
            tile_max_lon = tile_min_lon + lon_step

            # Expand by overlap on every side (clamp to outer bbox)
            exp_min_lat = max(MIN_LAT, tile_min_lat - lat_overlap)
            exp_max_lat = min(MAX_LAT, tile_max_lat + lat_overlap)
            exp_min_lon = max(MIN_LON, tile_min_lon - lon_overlap)
            exp_max_lon = min(MAX_LON, tile_max_lon + lon_overlap)

            print(f'\nTile [{r},{c}] ({tile_id}): '
                  f'lat {exp_min_lat:.4f}–{exp_max_lat:.4f}, '
                  f'lon {exp_min_lon:.4f}–{exp_max_lon:.4f}')

            g = download_tile(exp_min_lon, exp_min_lat, exp_max_lon, exp_max_lat, tile_id)
            if g is not None:
                graphs.append(g)

            time.sleep(2)  # polite gap for Overpass

    if not graphs:
        print('\nERROR: No tiles downloaded successfully. Check your network connection.')
        sys.exit(1)

    print(f'\n{"="*60}')
    print(f'Composing {len(graphs)} tile graphs...')
    G = nx.compose_all(graphs)
    print(f'Composed graph: {len(G.nodes)} nodes, {len(G.edges)} edges')

    # ── Connectivity check ───────────────────────────────────────────────────
    comps = list(nx.weakly_connected_components(G))
    print(f'Weakly connected components: {len(comps)}')
    sizes = sorted([len(c) for c in comps], reverse=True)[:5]
    print(f'Top 5 component sizes: {sizes}')

    if len(comps) > 1:
        print(f'Extracting largest connected component ({sizes[0]} nodes)...')
        largest = max(comps, key=len)
        G = G.subgraph(largest).copy()
        print(f'Pruned graph: {len(G.nodes)} nodes, {len(G.edges)} edges')

    # ── Pre-compute static edge attributes ──────────────────────────────────
    print('Pre-computing edge bearing and tortuosity...')
    for u, v, k, data in G.edges(keys=True, data=True):
        node_u = G.nodes[u]
        node_v = G.nodes[v]

        bearing = calculate_bearing(node_u['y'], node_u['x'], node_v['y'], node_v['x'])
        data['bearing'] = bearing

        length = data.get('length', 0.0)
        try:
            euclidean_dist = ox.distance.great_circle(
                node_u['y'], node_u['x'], node_v['y'], node_v['x']
            )
            data['tortuosity'] = max(1.0, length / euclidean_dist) if euclidean_dist > 0.1 else 1.0
        except Exception:
            data['tortuosity'] = 1.0

    # ── Save ────────────────────────────────────────────────────────────────
    print(f'\nSaving repaired graph to:\n  {OUTPUT_PATH}')
    ox.save_graphml(G, OUTPUT_PATH)
    print('\n✅ Graph rebuild complete!')
    print('   Restart the backend server to load the new graph.')

    # ── Quick validation ─────────────────────────────────────────────────────
    print('\nValidating: Kharghar → Panvel route...')
    try:
        start = ox.nearest_nodes(G, X=73.0689, Y=19.0421)
        end   = ox.nearest_nodes(G, X=73.1011, Y=18.9894)
        path  = nx.shortest_path(G, source=start, target=end, weight='length')
        print(f'  ✅ Path found! {len(path)} nodes.')
    except nx.NetworkXNoPath:
        print('  ⚠️  Still no path between Kharghar and Panvel.')
        print('     Check if these locations fall within tile boundaries.')
    except Exception as e:
        print(f'  ⚠️  Validation error: {e}')


if __name__ == '__main__':
    main()
