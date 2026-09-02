import os
import pickle
from csv import reader
from pathlib import Path

DATA_PATH = os.path.join(
    "data", "station_hourly"
)  # Input: directory containing hourly station data
METADATA_PATH = os.path.join(
    "data", "station_metadata"
)  # Input: directory containing station metadata files
STATION_COORDS = os.path.join(
    "data", "station_coordinates.csv"
)  # Output: consolidated station coordinates CSV


# puts data from station hourly file into a dictionary
def read_data(station_data, LANE_TYPE = "ML"):
    count = 0
    pathlist = Path(DATA_PATH).rglob("*.txt")
    for path in pathlist:
        with open(str(path)) as csv_file:
            district = int(os.path.basename(str(path))[1:3]) # get district from file name
            csv_reader = reader(csv_file)
            for row in csv_reader:
                timestamp = row[0]
                station = row[1]
                route = row[3]
                # use this line to filter highways out
                # if int(route) != 10:
                #     continue 
                travel_direction = row[4]
                lane_type = row[5]
                if lane_type != LANE_TYPE:
                    continue
                station_length = row[6]
                num_samples = row[7]
                percent_observed = row[8]
                total_flow = row[9]
                avg_occupancy = row[10]
                avg_speed = row[11]

                # filter out incomplete data points
                if not station_length or not total_flow or not avg_speed:
                    continue


                if station not in station_data:
                    station_data[station] = {
                        "district": int(district),
                        "route": int(route),
                        "travel_direction": travel_direction,
                        "lane_type": lane_type,
                        "station_length": float(station_length),
                        "num_samples": {},
                        "percent_observed": {},
                        "total_flow": {},
                        "avg_occupancy": {},
                        "avg_speed": {},
                    }

                station_data[station]["num_samples"][timestamp] = int(num_samples)
                station_data[station]["percent_observed"][timestamp] = float(percent_observed)
                station_data[station]["total_flow"][timestamp] = float(total_flow)
                station_data[station]["avg_occupancy"][timestamp] = float(avg_occupancy)
                station_data[station]["avg_speed"][timestamp] = float(avg_speed)
                count += 1
                if count % 10000 == 0:
                    print(f"Read {count:,} data rows...", end="\r")
    print(f"Read {count:,} data rows...")
    print(f"Found {len(station_data)} stations")


# puts data from station metadata into a dictionary
def read_metadata(station_data):
    count = 0
    pathlist = Path(METADATA_PATH).rglob("*.txt")

    # save station location data for openstreetmaps to use later
    with open(STATION_COORDS, "w", newline="") as f:
        f.write("Station_ID,Latitude,Longitude\n")

    with open(STATION_COORDS, "a", newline="") as f:
        for path in pathlist:
            with open(path) as csv_file:
                csv_reader = reader(csv_file, delimiter="\t")
                next(csv_reader, None)  # skip header row

                for row in csv_reader:
                    station = row[0]
                    # metadata-only stations are not useful
                    if station not in station_data:
                        continue

                    highway_number = row[1]
                    highway_direction = row[2]
                    district = row[3]
                    county = row[4]
                    city = row[5]
                    state_postmile = row[6]
                    absolute_postmile = row[7]
                    latitude = row[8]
                    longitude = row[9]
                    length = row[10]
                    station_type = row[11]
                    lanes = row[12]
                    name = row[13]

                    station_data[station].update(
                        {
                            "highway_number": highway_number,
                            "highway_direction": highway_direction,
                            "county": county,
                            "city": city,
                            "state_postmile": state_postmile,
                            "absolute_postmile": absolute_postmile,
                            "latitude": latitude,
                            "longitude": longitude,
                            "length": length,
                            "type": station_type,
                            "num_lanes": lanes,
                            "name": name,
                        }
                    )

                    f.write(f"{station},{latitude},{longitude}\n")

                    count += 1
                    if count % 10000 == 0:
                        print(f"Read {count:,} metadata rows...", end="\r")
        print(f"Read {count:,} metadata rows...")
        print(f"Found {len(station_data)} stations")
