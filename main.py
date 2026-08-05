from read_data import *
from osm_get_speed_limits import get_speed_limits

if __name__ == "__main__":
  station_data = {}
  print("Reading station hourly data...")
  read_data(station_data)
  print("Reading station metadata...")
  read_metadata(station_data)
  print("Reading OSM data...")
  get_speed_limits(station_data)
  print("Finished reading data...")

  # where people are speeding over 65..80mph
  speeding_data = {}

  # get speed limit data

  # loop thru station data
#   num_speeders = 0
#   thresholds = [80, 75, 70, 65, 60]
#   for key, value in station_data.items():
#       for threshold in thresholds:
#           if value["avg_speed"] > threshold:
#               # filters out speeding data
#               speeding_data[threshold] = {
#                   "latitude": value["latitude"],
#                   "longitude": value["longitude"],
#               }
#               thresholds += 1
#               break

  # get percent ppl that speed

  
  # display on map
  
  # color code by speed

