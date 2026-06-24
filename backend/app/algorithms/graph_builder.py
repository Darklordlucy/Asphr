import os
import re
import math
import json
import time
import asyncio
import datetime
from typing import Dict, Tuple, List, Optional
import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, Point, Polygon
from geoalchemy2.shape import from_shape, to_shape
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db_models import RoadSegment, SegmentHazard, TrafficCondition, WeatherGrid, PopularPlace, IoTReading
from app.models.hazard_predictor import HazardPredictor
from app.models.traffic_forecaster import TrafficForecaster

# Set OSMnx settings
ox.settings.use_cache = True
ox.settings.log_console = False

# Mumbai Metropolitan Area Bounds (covers CSMT to Virar and Thane to Kalyan)
MUMBAI_BBOX = {
    "min_lat": 18.90,
    "max_lat": 19.50,
    "min_lon": 72.75,
    "max_lon": 73.20
}

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the bearing between two points in degrees."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    d_lon = lon2 - lon1
    y = math.sin(d_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
    bearing = math.atan2(y, x)
    return math.degrees(bearing) % 360

def parse_max_speed(val) -> Optional[int]:
    """Parse speed limits from OSM strings (e.g. '80 km/h', '50 mph') to km/h."""
    if not val:
        return None
    if isinstance(val, list):
        val = val[0]
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        match = re.search(r'\d+', val)
        if match:
            speed = int(match.group())
            if 'mph' in val.lower():
                speed = int(speed * 1.60934)
            return speed
    return None

def parse_lanes(val) -> Optional[int]:
    """Parse lanes count from OSM string/int."""
    if not val:
        return None
    if isinstance(val, list):
        val = val[0]
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        try:
            return int(val)
        except ValueError:
            return None
    return None

class GraphManager:
    _instance = None

    def __init__(self):
        self.graph: Optional[nx.MultiDiGraph] = None
        self.last_updated: Optional[datetime.datetime] = None
        self.cache_dir = os.path.join("data", "map_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_graph(self) -> nx.MultiDiGraph:
        if self.graph is None:
            # Try loading cached merged graph first
            mumbai_full_path = os.path.join(self.cache_dir, "mumbai_full.graphml")
            if os.path.exists(mumbai_full_path):
                print(f"Loading full Mumbai graph from local cache: {mumbai_full_path}")
                try:
                    self.graph = ox.load_graphml(mumbai_full_path)
                    self.last_updated = datetime.datetime.now()
                except Exception as e:
                    print(f"Failed to load cached full graph: {e}. Downloading instead.")

            if self.graph is None:
                # Download and build from tiles
                print("No cached full graph found. Starting tiled download...")
                self.graph = self.download_and_build_graph()
                self.last_updated = datetime.datetime.now()

        return self.graph

    # ------------------------------------------------------------------
    # Private helpers for resilient tile downloading
    # ------------------------------------------------------------------

    def _load_manifest(self) -> dict:
        """Load the tile download manifest from cache_dir (tracks ok/empty/failed)."""
        path = os.path.join(self.cache_dir, "download_manifest.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}

    def _save_manifest(self, manifest: dict):
        """Persist the manifest so downloads survive Colab/process restarts."""
        path = os.path.join(self.cache_dir, "download_manifest.json")
        with open(path, "w") as f:
            json.dump(manifest, f, indent=2)

    def _split_into_quadrants(self, bbox: Tuple) -> List[Tuple]:
        """Split a (min_lon, min_lat, max_lon, max_lat) bbox into 4 equal quadrants."""
        min_lon, min_lat, max_lon, max_lat = bbox
        mid_lon = (min_lon + max_lon) / 2
        mid_lat = (min_lat + max_lat) / 2
        return [
            (min_lon, min_lat, mid_lon, mid_lat),   # SW
            (mid_lon, min_lat, max_lon, mid_lat),   # SE
            (min_lon, mid_lat, mid_lon, max_lat),   # NW
            (mid_lon, mid_lat, max_lon, max_lat),   # NE
        ]

    def _is_connection_issue(self, e: Exception) -> bool:
        """True for network/connectivity failures (not data-volume timeouts).
        Splitting tiles doesn't fix these — only waiting + retrying does."""
        try:
            import requests as req_lib
            conn_types = (
                req_lib.exceptions.ConnectionError,
                req_lib.exceptions.Timeout,
            )
        except ImportError:
            conn_types = ()
        return isinstance(
            e, conn_types + (ConnectionError, ConnectionResetError, OSError, TimeoutError)
        )

    def _download_tile_recursive(
        self,
        bbox: Tuple,
        tile_id: str,
        manifest: dict,
        depth: int = 0,
        max_depth: int = 3,
        max_retries: int = 2,
        max_conn_retries: int = 5,
    ) -> Optional[nx.MultiDiGraph]:
        """
        Download one bbox tile. On connection errors: retry the SAME tile size
        with exponential backoff (splitting won't help if the server is down).
        On data-volume / timeout errors: retry twice then recursively split into
        4 quadrants (up to max_depth). Completed tiles are cached to disk and
        skipped on re-runs via the manifest.
        """
        status = manifest.get(tile_id, {}).get("status")

        # Already finished in a previous run — reload from disk cache
        if status == "ok":
            cache_path = os.path.join(self.cache_dir, f"tile_{tile_id}.graphml")
            if os.path.exists(cache_path):
                try:
                    g = ox.load_graphml(cache_path)
                    print(f"[{tile_id}] loaded from cache ({len(g.nodes)} nodes)")
                    return g
                except Exception:
                    pass  # corrupted cache — fall through to re-download
        elif status == "empty":
            return None

        cache_path = os.path.join(self.cache_dir, f"tile_{tile_id}.graphml")
        min_lon, min_lat, max_lon, max_lat = bbox
        conn_failures = 0
        data_failures = 0

        while True:
            try:
                g = ox.graph_from_bbox(
                    bbox=(min_lon, min_lat, max_lon, max_lat),
                    network_type="drive",
                    simplify=True,
                )
                ox.save_graphml(g, cache_path)
                manifest[tile_id] = {
                    "status": "ok",
                    "nodes": len(g.nodes),
                    "edges": len(g.edges),
                    "depth": depth,
                }
                self._save_manifest(manifest)
                print(
                    f"[{tile_id}] OK -- {len(g.nodes)} nodes, "
                    f"{len(g.edges)} edges (depth {depth})"
                )
                return g

            except Exception as e:
                msg = str(e).lower()

                # --- connectivity failure: wait longer, retry same tile ---
                if self._is_connection_issue(e):
                    conn_failures += 1
                    if conn_failures > max_conn_retries:
                        manifest[tile_id] = {
                            "status": "failed",
                            "depth": depth,
                            "reason": "connection",
                        }
                        self._save_manifest(manifest)
                        print(
                            f"[{tile_id}] giving up after {max_conn_retries} "
                            f"connection retries -- re-run cell to retry"
                        )
                        return None
                    wait = min(20 * conn_failures, 120)
                    print(
                        f"[{tile_id}] connection issue ({type(e).__name__}), "
                        f"retry {conn_failures}/{max_conn_retries} in {wait}s "
                        f"(NOT splitting -- same tile size)"
                    )
                    time.sleep(wait)
                    continue  # retry the exact same polygon

                # --- empty area (water / park / no roads) ---
                if (
                    "insufficient" in msg
                    or "found no graph" in msg
                    or "no data" in msg
                ):
                    manifest[tile_id] = {"status": "empty", "depth": depth}
                    self._save_manifest(manifest)
                    print(f"[{tile_id}] empty (no roads -- likely water/park)")
                    return None

                # --- data-volume / oversized response: limited retries then split ---
                data_failures += 1
                if data_failures >= max_retries:
                    break
                wait = 5 * data_failures
                print(
                    f"[{tile_id}] attempt {data_failures}/{max_retries} failed "
                    f"({type(e).__name__}); retrying in {wait}s"
                )
                time.sleep(wait)

        # Exhausted retries for data-volume reasons — split into quadrants
        if depth < max_depth:
            print(f"[{tile_id}] splitting into quadrants (depth {depth} -> {depth + 1})")
            sub_graphs = []
            for qi, q_bbox in enumerate(self._split_into_quadrants(bbox)):
                g = self._download_tile_recursive(
                    q_bbox,
                    f"{tile_id}_{qi}",
                    manifest,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_retries=max_retries,
                    max_conn_retries=max_conn_retries,
                )
                if g is not None:
                    sub_graphs.append(g)
            return nx.compose_all(sub_graphs) if sub_graphs else None
        else:
            manifest[tile_id] = {
                "status": "failed",
                "depth": depth,
                "reason": "data_volume",
            }
            self._save_manifest(manifest)
            print(f"[{tile_id}] FAILED at max recursion depth -- skipped")
            return None

    # ------------------------------------------------------------------
    # Public download entry-point (signature unchanged)
    # ------------------------------------------------------------------

    def download_and_build_graph(self, grid_rows: int = 4, grid_cols: int = 4) -> nx.MultiDiGraph:
        """Divide Mumbai bounding box into tiles, download drive network for each, and merge them."""
        min_lat = MUMBAI_BBOX["min_lat"]
        max_lat = MUMBAI_BBOX["max_lat"]
        min_lon = MUMBAI_BBOX["min_lon"]
        max_lon = MUMBAI_BBOX["max_lon"]

        lat_step = (max_lat - min_lat) / grid_rows
        lon_step = (max_lon - min_lon) / grid_cols

        manifest = self._load_manifest()
        graphs = []

        print(f"Downloading Mumbai road network in a {grid_rows}x{grid_cols} grid of tiles...")

        for r in range(grid_rows):
            for c in range(grid_cols):
                tile_min_lat = min_lat + r * lat_step
                tile_max_lat = tile_min_lat + lat_step
                tile_min_lon = min_lon + c * lon_step
                tile_max_lon = tile_min_lon + lon_step

                tile_id = f"t{r}_{c}"
                bbox = (tile_min_lon, tile_min_lat, tile_max_lon, tile_max_lat)

                g = self._download_tile_recursive(bbox, tile_id, manifest)
                if g is not None:
                    graphs.append(g)
                time.sleep(1)   # polite gap between Overpass requests

        failed = [k for k, v in manifest.items() if v.get("status") == "failed"]
        if failed:
            print(
                f"\nWarning: {len(failed)} tile(s) ultimately failed "
                f"-- re-run get_graph() / download_and_build_graph() to retry: {failed}"
            )

        if not graphs:
            raise Exception("No sub-graphs were successfully loaded or downloaded.")

        # Compose all sub-graphs
        print("Composing sub-graphs into a unified Mumbai graph...")
        mumbai_graph = nx.compose_all(graphs)

        # Precalculate static edge bearing and tortuosity
        print("Precalculating static edge bearing and tortuosity...")
        for u, v, k, data in mumbai_graph.edges(keys=True, data=True):
            node_u = mumbai_graph.nodes[u]
            node_v = mumbai_graph.nodes[v]

            # Calculate bearing
            bearing = calculate_bearing(node_u['y'], node_u['x'], node_v['y'], node_v['x'])
            data['bearing'] = bearing

            # Calculate tortuosity (windingness)
            length = data.get('length', 0.0)
            euclidean_dist = ox.distance.great_circle(node_u['y'], node_u['x'], node_v['y'], node_v['x'])
            data['tortuosity'] = max(1.0, length / euclidean_dist) if euclidean_dist > 0.1 else 1.0

        # Cache the final composed graph
        mumbai_full_path = os.path.join(self.cache_dir, "mumbai_full.graphml")
        ox.save_graphml(mumbai_graph, mumbai_full_path)
        print(f"Composed graph saved to local cache: {mumbai_full_path}")

        return mumbai_graph

    async def sync_graph_to_db(self, db: AsyncSession):
        """Synchronize the road network nodes and edges from the graph to the PostgreSQL database."""
        g = self.get_graph()
        print("Synchronizing graph segments to the database...")

        # Fetch existing segments to avoid duplicate inserts
        result = await db.execute(select(RoadSegment.source_node, RoadSegment.target_node))
        existing_segments = {(r[0], r[1]) for r in result.all()}

        new_segments = []
        batch_size = 500

        for u, v, k, data in g.edges(keys=True, data=True):
            if (u, v) in existing_segments:
                continue

            node_u = g.nodes[u]
            node_v = g.nodes[v]

            # Construct geometry
            if 'geometry' in data and isinstance(data['geometry'], LineString):
                geom = data['geometry']
            else:
                geom = LineString([(node_u['x'], node_u['y']), (node_v['x'], node_v['y'])])

            road_type = data.get('highway')
            if isinstance(road_type, list):
                road_type = road_type[0]

            max_speed = parse_max_speed(data.get('maxspeed'))
            lanes = parse_lanes(data.get('lanes'))

            segment = RoadSegment(
                osm_way_id=data.get('osmid') if isinstance(data.get('osmid'), int) else (data.get('osmid')[0] if isinstance(data.get('osmid'), list) else None),
                source_node=u,
                target_node=v,
                geometry=from_shape(geom, srid=4326),
                length_meters=float(data.get('length', 0.0)),
                road_type=road_type,
                max_speed=max_speed,
                lanes=lanes
            )
            new_segments.append(segment)

            if len(new_segments) >= batch_size:
                db.add_all(new_segments)
                await db.commit()
                print(f"Synced {len(new_segments)} new segments to db...")
                new_segments = []

        if new_segments:
            db.add_all(new_segments)
            await db.commit()
            print(f"Synced final {len(new_segments)} new segments to db.")

        print("Graph synchronization complete.")

    async def enrich_graph_weights(self, db: AsyncSession):
        """Fetch latest database metrics (hazards, traffic, weather, IoT) and compute routing edge weights."""
        g = self.get_graph()
        print("Enriching graph edge weights with real-time database data...")

        # 1. Fetch Segment Mappings (source_node, target_node) -> segment_id
        result = await db.execute(select(RoadSegment.id, RoadSegment.source_node, RoadSegment.target_node,
                                         RoadSegment.road_type, RoadSegment.lanes, RoadSegment.length_meters,
                                         RoadSegment.has_speed_bump, RoadSegment.is_toll))
        segment_rows = result.all()
        segment_map = {(r[1], r[2]): r[0] for r in segment_rows}
        segment_meta = {r[0]: {"road_type": r[3], "lanes": r[4] or 2,
                                "length_meters": r[5] or 100.0,
                                "has_speed_bump": 1 if r[6] else 0,
                                "is_toll": bool(r[7])} for r in segment_rows}

        # 2. Fetch Latest Hazards
        hazards_result = await db.execute(select(SegmentHazard.segment_id, SegmentHazard.hazard_score))
        hazards = {row[0]: row[1] for row in hazards_result.all() if row[0] is not None}

        # 3. Fetch Latest Traffic Conditions
        traffic_result = await db.execute(select(TrafficCondition.segment_id, TrafficCondition.speed_kmh,
                                                  TrafficCondition.congestion_level, TrafficCondition.traffic_volume))
        traffic_rows = traffic_result.all()
        traffic_speed = {row[0]: row[1] for row in traffic_rows if row[0] is not None}
        traffic_congestion = {row[0]: row[2] for row in traffic_rows if row[0] is not None}
        traffic_volume = {row[0]: row[3] for row in traffic_rows if row[0] is not None}

        # 4. Fetch Weather Grid cells
        weather_result = await db.execute(select(WeatherGrid.cell_geometry, WeatherGrid.precipitation_mm,
                                                  WeatherGrid.visibility_km, WeatherGrid.weather_condition))
        weather_cells = []
        for cell_geom, precip, vis, cond in weather_result.all():
            poly_shape = to_shape(cell_geom)
            minx, miny, maxx, maxy = poly_shape.bounds
            weather_cells.append((poly_shape, minx, miny, maxx, maxy, precip or 0.0, vis or 10.0, cond or "clear"))

        # 5. Fetch Popular Places for scenic routing
        places_result = await db.execute(select(PopularPlace.geometry, PopularPlace.popularity_score))
        popular_points = [(to_shape(geom), score or 0.0) for geom, score in places_result.all()]

        # 6. Fetch IoT vibration aggregates per segment for ML features
        from sqlalchemy import func as sa_func
        iot_result = await db.execute(
            select(
                IoTReading.segment_id,
                sa_func.avg(IoTReading.vibration_level),
                sa_func.stddev(IoTReading.vibration_level),
                sa_func.max(IoTReading.vibration_level),
                sa_func.count(IoTReading.id),
                sa_func.avg(sa_func.extract('hour', IoTReading.timestamp)),
            ).where(IoTReading.segment_id.isnot(None))
            .group_by(IoTReading.segment_id)
        )
        iot_agg = {}
        for row in iot_result.all():
            iot_agg[row[0]] = {
                "mean_vibration": float(row[1] or 0),
                "std_vibration": float(row[2] or 0),
                "max_vibration": float(row[3] or 0),
                "reading_count": int(row[4] or 0),
                "avg_hour": float(row[5] or 12),
            }

        default_speeds = {
            'motorway': 80,
            'trunk': 70,
            'primary': 60,
            'secondary': 50,
            'tertiary': 40,
            'residential': 30,
            'living_street': 15,
            'unclassified': 30
        }

        # Known categories for one-hot encoding (must match training)
        ROAD_TYPES_OH = [
            "motorway", "trunk", "primary", "secondary",
            "tertiary", "residential", "living_street", "unclassified",
        ]
        WEATHER_CONDITIONS_OH = ["clear", "cloudy", "mist", "fog", "rain", "heavy rain", "thunderstorm", "snow"]

        # 7. ML Hazard Prediction — build feature dicts for batch prediction
        predictor = HazardPredictor.get_instance()
        forecaster = TrafficForecaster.get_instance()
        
        edge_keys = []       # (u, v, k) for each edge
        feature_dicts = []   # feature dict per edge
        traffic_feature_dicts = []  # traffic feature dict per edge
        weather_cache = {}   # cache weather lookups by node

        # Temporal context for traffic forecaster
        current_time = datetime.datetime.now()
        current_hour = current_time.hour + current_time.minute / 60.0
        current_day = current_time.weekday()

        for u, v, k, data in g.edges(keys=True, data=True):
            segment_id = segment_map.get((u, v))

            # Default parameters
            length = data.get('length', 1.0)
            if isinstance(length, list):
                length = length[0]
            try:
                length = float(length)
            except (ValueError, TypeError):
                length = 1.0
            road_type = data.get('highway')
            if isinstance(road_type, list):
                road_type = road_type[0]

            # Determine speed limits
            osm_maxspeed = parse_max_speed(data.get('maxspeed'))
            base_speed = osm_maxspeed or default_speeds.get(road_type, 30)

            # --- 1. Compute Traffic / Speed ---
            current_speed = traffic_speed.get(segment_id, float(base_speed))
            # Fallback/Safety speed capping
            current_speed = max(5.0, min(current_speed, float(base_speed)))
            speed_mps = current_speed / 3.6

            # Fastest Weight (travel time in seconds)
            data['weight_fastest'] = length / (speed_mps + 1e-5)

            # --- 2. Compute DB Hazards ---
            db_hazard_score = hazards.get(segment_id, 0.0)

            # --- 3. Compute Weather Penalty ---
            weather_penalty = 0.0
            weather_precip = 0.0
            weather_vis = 10.0
            weather_cond = "clear"
            # Identify which grid cell contains the source node
            if u not in weather_cache:
                lon_u = g.nodes[u]['x']
                lat_u = g.nodes[u]['y']
                for poly, minx, miny, maxx, maxy, precip, vis, cond in weather_cells:
                    if minx <= lon_u <= maxx and miny <= lat_u <= maxy:
                        if poly.contains(Point(lon_u, lat_u)):
                            weather_cache[u] = (precip, vis, cond)
                            break
                else:
                    weather_cache[u] = (0.0, 10.0, "clear")
            weather_precip, weather_vis, weather_cond = weather_cache[u]

            if weather_precip > 2.0 or weather_cond.lower() in ["rain", "heavy rain", "thunderstorm", "snow"]:
                weather_penalty = 0.4
            elif weather_cond.lower() in ["fog", "mist"]:
                weather_penalty = 0.2

            # --- Build ML feature dict for this edge ---
            iot_data = iot_agg.get(segment_id, {})
            seg_meta = segment_meta.get(segment_id, {})
            cong_level = traffic_congestion.get(segment_id, 0)
            traf_vol = traffic_volume.get(segment_id, 50)
            avg_hour = iot_data.get("avg_hour", 12.0)

            feat = {
                # Vibration
                "mean_vibration": iot_data.get("mean_vibration", 0.0),
                "std_vibration": iot_data.get("std_vibration", 0.0),
                "max_vibration": iot_data.get("max_vibration", 0.0),
                "reading_count": iot_data.get("reading_count", 0),
                "vibration_normalized": min(1.0, iot_data.get("mean_vibration", 0.0) / 5.0),
                # Traffic
                "speed_kmh": current_speed,
                "congestion_level": cong_level,
                "traffic_volume": traf_vol,
                # Road metadata
                "lanes": seg_meta.get("lanes", 2),
                "length_meters": seg_meta.get("length_meters", length),
                "has_speed_bump": seg_meta.get("has_speed_bump", 0),
                # Weather numeric
                "precipitation_mm": weather_precip,
                "visibility_km": weather_vis,
                # Temporal
                "hour_of_day": avg_hour,
                "is_night": 1 if (avg_hour >= 20 or avg_hour <= 6) else 0,
            }
            # Road type one-hot
            rt_lower = (road_type or "").lower()
            for rt in ROAD_TYPES_OH:
                feat[f"road_{rt}"] = 1 if rt_lower == rt else 0
            # Weather condition one-hot
            wc_lower = weather_cond.lower().strip()
            for wc in WEATHER_CONDITIONS_OH:
                feat[f"weather_{wc.replace(' ', '_')}"] = 1 if wc_lower == wc else 0

            edge_keys.append((u, v, k))
            feature_dicts.append(feat)

            # Build ML traffic feature dict for this edge
            traffic_feat = {
                "speed_kmh": current_speed,
                "weather_condition": weather_cond,
                "hour_of_day": current_hour,
                "day_of_week": current_day
            }
            traffic_feature_dicts.append(traffic_feat)

            # Store intermediate values for non-ML weight computation
            data['_db_hazard'] = db_hazard_score
            data['_weather_penalty'] = weather_penalty
            data['_length'] = length
            data['_road_type'] = road_type
            data['_current_speed'] = current_speed
            data['_base_speed'] = base_speed
            
            # Save segment mapping, is_toll, and other metadata on the edge
            data['segment_id'] = segment_id
            data['is_toll'] = seg_meta.get("is_toll", False)
            data['congestion_level'] = cong_level

        # --- Run ML batch prediction ---
        ml_scores = None
        if predictor.is_ready and feature_dicts:
            ml_scores = predictor.predict_batch(feature_dicts)
            if ml_scores:
                print(f"  ML hazard predictions: {len(ml_scores)} edges scored")

        # --- Run Traffic ML batch prediction ---
        predicted_speeds = None
        if forecaster.is_ready and traffic_feature_dicts:
            predicted_speeds = forecaster.predict_batch(traffic_feature_dicts)
            if predicted_speeds:
                print(f"  ML traffic speed predictions: {len(predicted_speeds)} edges predicted")

        # --- Apply hazard scores and compute remaining weights ---
        for idx, (u, v, k) in enumerate(edge_keys):
            data = g[u][v][k]
            db_hazard = data.pop('_db_hazard', 0.0)
            weather_penalty = data.pop('_weather_penalty', 0.0)
            length = data.pop('_length', 1.0)
            road_type = data.pop('_road_type', None)
            current_speed = data.pop('_current_speed', 30.0)
            base_speed = data.pop('_base_speed', 30.0)

            # Blend ML prediction with DB hazard score
            if ml_scores is not None and idx < len(ml_scores):
                ml_score = ml_scores[idx]
                if db_hazard > 0.01:
                    # 70% ML + 30% DB when DB data exists
                    hazard_score = 0.7 * ml_score + 0.3 * db_hazard
                else:
                    # Pure ML prediction when no DB hazard data
                    hazard_score = ml_score
            else:
                hazard_score = db_hazard

            data['hazard_score'] = hazard_score

            # Safest Weight (distance scaled by hazards and weather)
            data['weight_safest'] = length * (1.0 + hazard_score) * (1.0 + weather_penalty)

            # --- Proactive Congestion Penalty ---
            predicted_speed = current_speed
            if predicted_speeds is not None and idx < len(predicted_speeds):
                predicted_speed = predicted_speeds[idx]
                # Cap predicted speed
                predicted_speed = max(5.0, min(predicted_speed, float(base_speed)))
            
            # Store predicted speed on edge
            data['predicted_speed'] = predicted_speed
            
            # Penalty ratio: if predicted speed 30m ahead is slower than base_speed, penalize
            penalty_factor = max(0.0, (base_speed - predicted_speed) / base_speed)
            
            # Update fastest weight (travel time in seconds, scaled by penalty factor)
            original_fastest_weight = length / ((current_speed / 3.6) + 1e-5)
            data['weight_fastest'] = original_fastest_weight * (1.0 + penalty_factor)

            # --- 4. Straightest Weight params (Windingness & Bearings) ---
            tortuosity = data.get('tortuosity', 1.0)
            if isinstance(tortuosity, list):
                tortuosity = tortuosity[0]
            try:
                tortuosity = float(tortuosity)
            except (ValueError, TypeError):
                tortuosity = 1.0
            data['weight_straightest'] = length * tortuosity

            # --- 5. Compute Popularity Weight ---
            nearby_popularity = 0.0
            lat_u = g.nodes[u]['y']
            lon_u = g.nodes[u]['x']
            for pt, score in popular_points:
                # 500 meters is roughly 0.005 degrees latitude/longitude.
                # Fast bounding box check to avoid expensive great_circle calculations.
                if abs(lat_u - pt.y) <= 0.005 and abs(lon_u - pt.x) <= 0.005:
                    dist = ox.distance.great_circle(lat_u, lon_u, pt.y, pt.x)
                    if dist <= 500:
                        nearby_popularity += score

            data['weight_popular'] = length / (1.0 + nearby_popularity)

        print("Enriched weights successfully.")

async def refresh_graph_periodically():
    """Background loop to recompute and enrich weights every 5 minutes."""
    await asyncio.sleep(300) # Wait for initial startup enrichment to complete
    while True:
        try:
            from app.config import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                manager = GraphManager.get_instance()
                # Ensure graph is loaded
                manager.get_graph()
                # Update weights with db conditions
                await manager.enrich_graph_weights(session)
                manager.last_updated = datetime.datetime.now()
            print("Successfully refreshed in-memory road network weights.")
        except Exception as e:
            print(f"Error refreshing graph weights: {e}")
        await asyncio.sleep(300) # Sleep for 5 minutes