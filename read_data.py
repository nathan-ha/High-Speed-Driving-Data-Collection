import os
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
def read_data(station_data):
    count = 0
    pathlist = Path(DATA_PATH).rglob("*.txt")
    for path in pathlist:
        with open(str(path)) as csv_file:
            csv_reader = reader(csv_file)
            for row in csv_reader:
                timestamp = row[0]
                station = row[1]
                district = row[2]
                route = row[3]
                travel_direction = row[4]
                lane_type = row[5]
                station_length = row[6]
                num_samples = row[7]
                percent_observed = row[8]
                total_flow = row[9]
                avg_occupancy = row[10]
                avg_speed = row[11]
                delay_35 = row[12]
                delay_40 = row[13]
                delay_45 = row[14]
                delay_50 = row[15]
                delay_55 = row[16]
                delay_60 = row[17]
                    
                if station not in station_data:
                    station_data[station] = {
                        "route": route,
                        "travel_direction": travel_direction,
                        "lane_type": lane_type,
                        "station_length": station_length,
                        "num_samples": {},
                        "percent_observed": {},
                        "total_flow": {},
                        "avg_occupancy": {},
                        "avg_speed": {},
                    }

                station_data[station]["num_samples"][timestamp] = num_samples
                station_data[station]["percent_observed"][timestamp] = percent_observed
                station_data[station]["total_flow"][timestamp] = total_flow
                station_data[station]["avg_occupancy"][timestamp] = avg_occupancy
                station_data[station]["avg_speed"][timestamp] = avg_speed
                count += 1
                if count % 10000 == 0:
                    print(f"Read {count:,} data rows...", end="\r")
    print(f"Read {count:,} data rows...")
    


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
                    if station not in station_data:
                        station_data[station] = {}

                    freeway_number = row[1]
                    freeway_direction = row[2]
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
                    user_id_1 = row[14]
                    user_id_2 = row[15]
                    user_id_3 = row[16]
                    user_id_4 = row[17]

                    station_data[station].update({
                        "freeway_number": freeway_number,
                        "freeway_direction": freeway_direction,
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
                    })

                    f.write(f"{station},{latitude},{longitude}\n")

                    count += 1
                    if count % 10000 == 0:
                        print(f"Read {count:,} metadata rows...", end="\r")
        print(f"Read {count:,} metadata rows...")
