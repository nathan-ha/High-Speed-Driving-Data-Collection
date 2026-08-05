import os
import csv
import pickle
import time
import numpy as np
import osmium
from scipy.spatial import cKDTree

from read_data import STATION_COORDS

# Paths
PBF_PATH = os.path.join(
    "data", "osm", "california-260728.osm.pbf"
)  # Input: OpenStreetMap PBF extract
STATIONS_PATH = STATION_COORDS  # Input: station coordinate CSV
CACHE_PATH = os.path.join(
    "data", "osm", "california_roads.pkl"
)  # Cache: extracted road network
OUTPUT_PATH = os.path.join(
    "data", "osm", "station_speed_limits.csv"
)  # Output: station speed limits


HIGHWAY_TYPES = {"motorway", "trunk", "primary", "secondary", "tertiary"}

EARTH_RADIUS = 6371000  # meters


# ---------------------------------------------------------
# Extract roads from OSM
# ---------------------------------------------------------


class RoadHandler(osmium.SimpleHandler):

    def __init__(self):
        super().__init__()
        self.roads = []
        self.count = 0


def load_roads():
    if os.path.exists(CACHE_PATH):
        print("Loading road cache...")
        start = time.time()
        with open(CACHE_PATH, "rb") as f:
            roads = pickle.load(f)
        print(
            f"Loaded {len(roads):,} cached roads " f"in {time.time()-start:.2f}s",
            end="\r",
        )
        return roads
    print("No cache found. Extracting OSM roads...")
    print(f"Reading: {PBF_PATH}")
    start = time.time()
    handler = RoadHandler()
    handler.apply_file(PBF_PATH, locations=True)
    roads = handler.roads
    print(f"Extracted {len(roads):,} roads " f"in {time.time()-start:.2f}s", end="\r")
    print("Saving road cache...")
    with open(CACHE_PATH, "wb") as f:
        pickle.dump(roads, f)
    print(f"Saved cache: {CACHE_PATH}")
    return roads


# ---------------------------------------------------------
# Convert lat/lon to XYZ
# ---------------------------------------------------------


def to_xyz(lat, lon):
    lat = np.radians(lat)
    lon = np.radians(lon)
    x = EARTH_RADIUS * np.cos(lat) * np.cos(lon)
    y = EARTH_RADIUS * np.cos(lat) * np.sin(lon)
    z = EARTH_RADIUS * np.sin(lat)
    return np.column_stack((x, y, z))


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------


def get_speed_limits(station_data):
    print("\n===== STARTING SPEED LIMIT EXTRACTION =====\n")
    roads = load_roads()
    print(f"Preparing {len(roads):,} roads for KD-tree...", end="\r")

    # Build road vertex index
    road_points = []
    road_speed = []
    start = time.time()
    for i, road in enumerate(roads):
        for point in road["coords"]:
            # save every road coordinate and their corresponding speed limit 
            road_points.append(point)
            road_speed.append(road["maxspeed"])
        if i % 50000 == 0 and i > 0:
            print(f"  Processed {i:,} / {len(roads):,} roads", end="\r")
    print(
        f"Created {len(road_points):,} road vertices " f"in {time.time()-start:.2f}s",
        end="\r",
    )

    # conversion to xyz makes distance calculations easier
    print("Building XYZ coordinates...")
    road_lat = np.array([p[0] for p in road_points])
    road_lon = np.array([p[1] for p in road_points])
    road_xyz = to_xyz(road_lat, road_lon)
    print("Building KD-tree...")
    start = time.time()
    tree = cKDTree(road_xyz)
    print(f"KD-tree built in {time.time()-start:.2f}s")

    # Load stations
    print("\nLoading stations...")
    with open(STATIONS_PATH, newline="") as f:
        reader = csv.DictReader(f)
        stations = [row for row in reader if row["Latitude"] and row["Longitude"]]
    print(f"Loaded {len(stations):,} valid stations", end="\r")
    lat = np.array([float(x["Latitude"]) for x in stations])
    lon = np.array([float(x["Longitude"]) for x in stations])
    station_xyz = to_xyz(lat, lon)

    # Query stations
    print("\nFinding nearest roads...")
    start = time.time()
    _, indexes = tree.query(station_xyz)
    print(
        f"Matched {len(indexes):,} stations " f"in {time.time()-start:.2f}s", end="\r"
    )

    # Output
    print("\nWriting output CSV...")
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Station_ID", "speed_limit"])
        for i, (station, idx) in enumerate(zip(stations, indexes), start=1):
            speed = road_speed[idx]
            digits = "".join(c for c in speed if c.isdigit())
            writer.writerow([station["Station_ID"], digits])
            if i % 10000 == 0:
                print(f"  Wrote {i:,} stations...", end="\r")

    # Store speed limits into existing station dictionary
    for i, (station, idx) in enumerate(zip(stations, indexes), start=1):
        speed = road_speed[idx]
        # Extract numeric speed value from OSM maxspeed tag
        # Example: "65 mph" -> 65
        digits = "".join(c for c in speed if c.isdigit())
        station_id = station["Station_ID"]
        # Update existing station dictionary
        if station_id in station_data:
            station_data[station_id]["speed_limit"] = int(digits) if digits else None
        if i % 10000 == 0:
            print(f"  Updated {i:,} stations...", end="\r")
    print("Speed limits added to station dictionary.")
    print("\n===== GET SPEED LIMIT COMPLETE =====")
    print(f"Speed Limit Output: {OUTPUT_PATH}")
