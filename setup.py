import os
import pickle
from read_data import *
from osm_get_speed_limits import get_speed_limits

USE_CACHE = False
DATA_CACHE = os.path.join("data", "cache", "station.cache")


def is_dir_empty(path):
    with os.scandir(path) as it:
        return not any(it)


def setup(station_data):
    print("Starting...")

    # create data directories if they don't already exist
    base_dir = "data"
    subdirs = ["cache", "osm", "station_hourly", "station_metadata"]
    for sub in subdirs:
        curr_dir = os.path.join(base_dir, sub)
        os.makedirs(curr_dir, exist_ok=True)
        if is_dir_empty(curr_dir) and curr_dir != os.path.join("data", "cache"):
            print(f"Warning: {curr_dir} is empty")

    # load cache data
    if USE_CACHE and os.path.isfile(DATA_CACHE):
        print("Loading cache data...")
        with open(DATA_CACHE, "rb") as f:
            station_data = pickle.load(f)
        print("Using cached station data")

    # read csv data
    else:
        print("Reading station hourly data...")
        read_data(station_data)
        print("Reading station metadata...")
        read_metadata(station_data)
        if USE_CACHE:
            print("Saving data to cache...")
            with open(DATA_CACHE, "wb") as f:
                pickle.dump(station_data, f)

    print("Reading OSM data...")
    get_speed_limits(station_data)
    print("Finished reading data...")
