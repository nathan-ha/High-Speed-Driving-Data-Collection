from setup import *
from collections import defaultdict
import csv

RESULTS_DIR = os.path.join("data", "results")
RESULTS_SPEED_BIN_PATH = os.path.join(RESULTS_DIR, "speed_bin.csv")


if __name__ == "__main__":
    station_data = {}
    setup(station_data)


    # plan:
    # for each freeway:
    #     for each station:
    #         get average speeds across all timestamps
    #         get average flow across all timestamps
    #         calculate average VMT using flow
    #         bin average speed for that station, add VMT to bin

    #     VMT distribution by 5-mph speed bin and time of day
    # {district : {#mph : occurrences}}
    print("Creating Speed Bins...")
    bins = defaultdict(lambda: defaultdict(int))  # auto initialize bins to 0
    for station, data in station_data.items():
        # filter invalid speeds
        speeds = [
            float(speed)
            for speed in station_data[station]["avg_speed"].values()
            if speed != "" and float(speed) >= 0
        ]
        if not speeds:
            print(f"No valid speeds for station {station}")
            continue
        # take avg speed over all timestamps
        average_speed = sum(speeds) / len(speeds) if speeds else 0
        speed_bin = int(average_speed / 5 + 0.5) * 5
        bins[data["district"]][speed_bin] += 1

    # write results
    print("Saving speed bin results...")
    with open(RESULTS_SPEED_BIN_PATH, "w", newline="") as f:
        fieldnames = ["district", "speed", "count"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for district, speeds in bins.items():
            for speed, count in speeds.items():
                if speed == 0:
                    continue
                writer.writerow({"district": district, "speed": speed, "count": count})

    # VMT fraction above 65, 70, 75, 80, 85, and 90 mph
    # Fraction of VMT above posted speed limit, speed limit +5 mph, and speed limit +10 mph

    print("Done")