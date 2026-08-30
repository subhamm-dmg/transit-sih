"""
backend/app/services/gtfs_loader.py — GTFS Ingestion & Fast In-Memory Graph Index.

Loads processed Delhi DTC Bus and Delhi Metro GTFS datasets, indexing stops,
routes, stop sequences, and transfer points for high-performance multi-modal routing.
"""

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Optional
import pandas as pd


@dataclass
class Stop:
    stop_id: str
    stop_name: str
    lat: float
    lon: float
    mode: str  # "BUS" or "METRO"
    stop_code: str = ""


@dataclass
class TransitRoute:
    route_id: str
    route_short_name: str
    route_long_name: str
    mode: str  # "BUS" or "METRO"
    color: str
    stops_sequence: list[str] = field(default_factory=list)  # list of stop_ids in order


class GTFSNetwork:
    """In-memory multi-modal GTFS network graph."""

    _instance: Optional["GTFSNetwork"] = None

    def __init__(self, data_root: Optional[Path] = None):
        if data_root is None:
            data_root = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"

        self.data_root = data_root
        self.stops: dict[str, Stop] = {}
        self.routes: dict[str, TransitRoute] = {}
        self.stop_to_routes: dict[str, set[str]] = {}
        self.name_to_stop_ids: dict[str, list[str]] = {}
        self.all_stop_names: list[str] = []
        self.is_loaded = False
        self.load_network()

    @classmethod
    def get_instance(cls) -> "GTFSNetwork":
        if cls._instance is None:
            cls._instance = GTFSNetwork()
        return cls._instance

    def load_network(self):
        try:
            dtc_path = self.data_root / "dtc_gtfs"
            metro_path = self.data_root / "gtfs_metro"

            # 1. Load Metro
            if metro_path.exists():
                self._load_metro(metro_path)

            # 2. Load DTC Bus
            if dtc_path.exists():
                self._load_dtc(dtc_path)

            # Build stop search list
            unique_names = set()
            for stop in self.stops.values():
                unique_names.add(stop.stop_name)
            self.all_stop_names = sorted(list(unique_names))

            self.is_loaded = True
            print(f"[GTFSNetwork] Loaded {len(self.stops)} stops, {len(self.routes)} routes.")
        except Exception as err:
            print(f"[GTFSNetwork] Warning during GTFS load: {err}. Network will use mock stops.")
            self._load_mock_fallback()

    def _load_metro(self, path: Path):
        stops_file = path / "stops.txt"
        routes_file = path / "routes.txt"
        trips_file = path / "trips.txt"
        st_file = path / "stop_times.txt"

        if not (stops_file.exists() and routes_file.exists()):
            return

        df_stops = pd.read_csv(stops_file)
        for _, row in df_stops.iterrows():
            sid = f"metro_{row['stop_id']}"
            name = str(row["stop_name"]).strip()
            lat = float(row["stop_lat"])
            lon = float(row["stop_lon"])
            self.stops[sid] = Stop(stop_id=sid, stop_name=name, lat=lat, lon=lon, mode="METRO")
            norm_name = name.lower()
            self.name_to_stop_ids.setdefault(norm_name, []).append(sid)

        df_routes = pd.read_csv(routes_file)
        route_colors = {
            "RED": "#E53935",
            "YELLOW": "#FBC02D",
            "BLUE": "#1E88E5",
            "GREEN": "#43A047",
            "VIOLET": "#8E24AA",
            "PINK": "#D81B60",
            "MAGENTA": "#C2185B",
            "GRAY": "#757575",
            "AQUA": "#00ACC1",
            "RAPID": "#FB8C00",
        }
        for _, row in df_routes.iterrows():
            rid = f"metro_{row['route_id']}"
            short_name = str(row.get("route_short_name", "")).strip()
            long_name = str(row.get("route_long_name", "")).strip()
            color = "#1E88E5"
            for c_name, c_hex in route_colors.items():
                if c_name in long_name.upper() or c_name in short_name.upper():
                    color = c_hex
                    break
            self.routes[rid] = TransitRoute(
                route_id=rid,
                route_short_name=short_name or "Metro",
                route_long_name=long_name or f"Metro Line {rid}",
                mode="METRO",
                color=color,
            )

        # Build stop sequences from stop_times
        if st_file.exists() and trips_file.exists():
            # Sample first trip per route for sequence
            df_trips = pd.read_csv(trips_file).drop_duplicates(subset=["route_id"])
            trip_to_route = {str(r["trip_id"]): f"metro_{r['route_id']}" for _, r in df_trips.iterrows()}
            
            df_st = pd.read_csv(st_file)
            df_st["trip_id_str"] = df_st["trip_id"].astype(str)
            sample_st = df_st[df_st["trip_id_str"].isin(trip_to_route.keys())]
            sample_st = sample_st.sort_values(by=["trip_id", "stop_sequence"])

            for trip_id_str, group in sample_st.groupby("trip_id_str"):
                rid = trip_to_route.get(trip_id_str)
                if rid and rid in self.routes:
                    seq = [f"metro_{s}" for s in group["stop_id"].tolist()]
                    self.routes[rid].stops_sequence = seq
                    for s in seq:
                        self.stop_to_routes.setdefault(s, set()).add(rid)

    def _load_dtc(self, path: Path):
        stops_file = path / "stops.txt"
        routes_file = path / "routes.txt"
        trips_file = path / "trips.txt"
        st_file = path / "stop_times.txt"

        if not (stops_file.exists() and routes_file.exists()):
            return

        df_stops = pd.read_csv(stops_file)
        for _, row in df_stops.iterrows():
            sid = f"bus_{row['stop_id']}"
            name = str(row["stop_name"]).strip()
            lat = float(row["stop_lat"])
            lon = float(row["stop_lon"])
            code = str(row.get("stop_code", ""))
            self.stops[sid] = Stop(stop_id=sid, stop_name=name, lat=lat, lon=lon, mode="BUS", stop_code=code)
            norm_name = name.lower()
            self.name_to_stop_ids.setdefault(norm_name, []).append(sid)

        df_routes = pd.read_csv(routes_file)
        for _, row in df_routes.iterrows():
            rid = f"bus_{row['route_id']}"
            long_name = str(row.get("route_long_name", "")).strip()
            short_name = str(row.get("route_short_name", "")).strip()
            if not short_name and long_name:
                short_name = long_name.split("DOWN")[0].split("UP")[0].strip()
            self.routes[rid] = TransitRoute(
                route_id=rid,
                route_short_name=short_name or f"Bus {rid}",
                route_long_name=long_name or f"Bus Route {rid}",
                mode="BUS",
                color="#FFB020",
            )

        if st_file.exists() and trips_file.exists():
            df_trips = pd.read_csv(trips_file).drop_duplicates(subset=["route_id"])
            trip_to_route = {str(r["trip_id"]): f"bus_{r['route_id']}" for _, r in df_trips.iterrows()}

            df_st = pd.read_csv(st_file)
            df_st["trip_id_str"] = df_st["trip_id"].astype(str)
            sample_st = df_st[df_st["trip_id_str"].isin(trip_to_route.keys())]
            sample_st = sample_st.sort_values(by=["trip_id", "stop_sequence"])

            for trip_id_str, group in sample_st.groupby("trip_id_str"):
                rid = trip_to_route.get(trip_id_str)
                if rid and rid in self.routes:
                    seq = [f"bus_{s}" for s in group["stop_id"].tolist()]
                    self.routes[rid].stops_sequence = seq
                    for s in seq:
                        self.stop_to_routes.setdefault(s, set()).add(rid)

    def _load_mock_fallback(self):
        fallback_stops = [
            ("Kashmere Gate", 28.6678, 77.2280, "METRO"),
            ("Rajiv Chowk", 28.6328, 77.2195, "METRO"),
            ("Connaught Place", 28.6315, 77.2167, "BUS"),
            ("Central Secretariat", 28.6145, 77.2119, "METRO"),
            ("Hauz Khas", 28.5432, 77.2064, "METRO"),
            ("Noida Sector 18", 28.5708, 77.3260, "METRO"),
            ("Inderlok", 28.6734, 77.1702, "METRO"),
            ("GB Road", 28.6480, 77.2240, "BUS"),
            ("Shradhanand Marg", 28.6480, 77.2240, "BUS"),
            ("New Delhi Railway Station", 28.6429, 77.2191, "BUS"),
            ("AIIMS", 28.5672, 77.2100, "METRO"),
            ("Saket", 28.5204, 77.2014, "METRO"),
            ("Karol Bagh", 28.6514, 77.1907, "METRO"),
            ("India Gate", 28.6129, 77.2295, "BUS"),
            ("Majestic Terminal", 12.9767, 77.5713, "BUS"),
            ("Indiranagar", 12.9784, 77.6408, "BUS"),
            ("Koramangala", 12.9352, 77.6245, "BUS"),
            ("Whitefield", 12.9698, 77.7500, "BUS"),
            ("Hampankatta", 12.8688, 74.8430, "BUS"),
            ("NITK Campus", 13.0108, 74.7943, "BUS"),
            ("Mangaluru Central", 12.8624, 74.8441, "BUS"),
        ]
        for i, (name, lat, lon, mode) in enumerate(fallback_stops):
            sid = f"mock_{i}"
            self.stops[sid] = Stop(stop_id=sid, stop_name=name, lat=lat, lon=lon, mode=mode)
            self.name_to_stop_ids.setdefault(name.lower(), []).append(sid)
        self.all_stop_names = [s[0] for s in fallback_stops]

        # Mock routes connecting key Delhi stops
        mock_routes_def = [
            ("DTC-410", "410", "Kashmere Gate - Connaught Place", "BUS", "#FFB020", ["Kashmere Gate", "GB Road", "New Delhi Railway Station", "Connaught Place"]),
            ("DTC-6", "6", "Old Delhi - AIIMS via GB Road", "BUS", "#FFB020", ["Kashmere Gate", "GB Road", "Shradhanand Marg", "New Delhi Railway Station", "AIIMS"]),
            ("DTC-14", "14", "Kashmere Gate - New Delhi RS - Rajiv Chowk", "BUS", "#FFB020", ["Kashmere Gate", "GB Road", "New Delhi Railway Station", "Rajiv Chowk"]),
            ("METRO-YL", "Yellow Line", "Samaypur Badli - Huda City Centre", "METRO", "#FBC02D", ["Kashmere Gate", "Rajiv Chowk", "Central Secretariat", "AIIMS", "Hauz Khas", "Saket"]),
        ]

        for rid, short_name, long_name, mode, color, stop_names in mock_routes_def:
            seq = []
            for sname in stop_names:
                matching_sids = self.name_to_stop_ids.get(sname.lower(), [])
                if matching_sids:
                    seq.append(matching_sids[0])
            self.routes[rid] = TransitRoute(
                route_id=rid,
                route_short_name=short_name,
                route_long_name=long_name,
                mode=mode,
                color=color,
                stops_sequence=seq,
            )
            for sid in seq:
                self.stop_to_routes.setdefault(sid, set()).add(rid)

        print(f"[GTFSNetwork] GTFS mock fallback loaded: {len(self.stops)} stops, {len(self.routes)} routes.")
        self.is_loaded = True

    def find_stops_by_query(self, query: str, limit: int = 8) -> list[dict]:
        """Fuzzy and prefix match stop names for autocomplete."""
        q = query.strip().lower()
        if not q:
            return [{"name": name} for name in self.all_stop_names[:limit]]

        exact_prefix = []
        substring_match = []
        for name in self.all_stop_names:
            n_lower = name.lower()
            if n_lower.startswith(q):
                exact_prefix.append({"name": name})
            elif q in n_lower:
                substring_match.append({"name": name})
            if len(exact_prefix) >= limit:
                break

        results = exact_prefix + substring_match
        return results[:limit]

    def find_nearest_stop(self, name_or_query: str) -> Optional[Stop]:
        """Find best matching Stop object by exact name, substring, or word match."""
        q = name_or_query.strip().lower()
        if not q:
            return None

        # 1. Exact match in index
        if q in self.name_to_stop_ids:
            return self.stops[self.name_to_stop_ids[q][0]]

        # 2. Substring match
        for stop_name, sids in self.name_to_stop_ids.items():
            if q in stop_name or stop_name in q:
                return self.stops[sids[0]]

        # 3. Word-level fallback for composite names (e.g., 'GB Road', 'Kashmere Gate Metro')
        words = [w for w in q.replace(".", " ").replace("-", " ").split() if len(w) >= 2]
        for word in words:
            if word in ("gate", "road", "marg", "chowk", "station", "stop", "terminal"):
                continue  # skip generic words for primary matching
            for stop_name, sids in self.name_to_stop_ids.items():
                if word in stop_name:
                    return self.stops[sids[0]]

        # 4. Final word fallback if still unmatched
        for word in words:
            if len(word) >= 3:
                for stop_name, sids in self.name_to_stop_ids.items():
                    if word in stop_name:
                        return self.stops[sids[0]]

        return None


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)
