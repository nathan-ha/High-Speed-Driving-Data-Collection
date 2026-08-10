from setup import *

RESULTS_DIR = os.path.join("data", "results")
RESULTS_SPEED_BIN_PATH = os.path.join(RESULTS_DIR, "speed_bin.csv")

if __name__ == "__main__":
    station_data = {}
    setup(station_data)

#     VMT distribution by 5-mph speed bin and time of day


# VMT fraction above 65, 70, 75, 80, 85, and 90 mph
# Fraction of VMT above posted speed limit, speed limit +5 mph, and speed limit +10 mph
