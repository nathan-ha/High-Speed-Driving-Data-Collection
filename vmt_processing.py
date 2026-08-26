from setup import *
from collections import defaultdict
import csv

RESULTS_DIR = os.path.join("data", "results")
RESULTS_SPEED_BIN_PATH = os.path.join(RESULTS_DIR, "speed_bin.csv")
RESULTS_VMT_HOURLY_PATH = os.path.join(RESULTS_DIR, "vmt_hourly_distribution.csv")
RESULTS_ABOVE_THRESH_PATH = os.path.join(RESULTS_DIR, "above_thresholds.txt")
RESULTS_ABOVE_SPEED_LIMIT = os.path.join(RESULTS_DIR, "above_speed_limit.txt")


def calculate_vmt(station_data, thresholds):
    # {district : {#mph : vmt}}
    total_vmt = 0
    vmt_above = {threshold: 0 for threshold in thresholds}
    vmt_above_limit = 0
    vmt_above_limit_5 = 0
    vmt_above_limit_10 = 0
    count = 0
    print("Creating Speed Bins...")
    # {district: {freeway: {speed_bin: vmt}}}
    bins = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    vmt_hourly = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    for station, data in station_data.items():
        # Error checks
        if "avg_speed" not in data:
            print(f"Missing avg_speed for station {station}")
            continue
        speed_limit = data.get("speed_limit")
        valid_speed_limit = speed_limit is not None and speed_limit > 0
        if not valid_speed_limit:
            print(f"Could not get speed limit for station {station}")
        # Read all timestamps for each station
        for timestamp, avg_speed in data["avg_speed"].items():
            if timestamp not in data["total_flow"]:
                print(
                    f"Missing total_flow for station {station}, "
                    f"timestamp {timestamp}"
                )
                continue
            if avg_speed is None or avg_speed < 0:
                print(
                    f"Invalid average speed for station {station}, "
                    f"timestamp {timestamp}: {avg_speed}"
                )
                continue

            # VMT calculation
            flow = data["total_flow"][timestamp]
            vmt = flow * data["station_length"]
            total_vmt += vmt
            # VMT above each threshold
            for threshold in thresholds:
                if avg_speed > threshold:
                    vmt_above[threshold] += vmt

            # VMT above posted speed limit
            if valid_speed_limit:
                if avg_speed > speed_limit:
                    vmt_above_limit += vmt
                if avg_speed > speed_limit + 5:
                    vmt_above_limit_5 += vmt
                if avg_speed > speed_limit + 10:
                    vmt_above_limit_10 += vmt

            # Add VMT to speed bin
            speed_bin = int(avg_speed / 5 + 0.5) * 5
            freeway = data["route"]
            district = data["district"]
            bins[district][freeway][speed_bin] += vmt
            hour = int(timestamp.split(" ")[1].split(":")[0])
            vmt_hourly[district][freeway][hour] += vmt
            count += 1
            if count % 10000 == 0:
                print(f"Calculated {count:,} VMTs...", end="\r")

    return (
        bins,
        vmt_hourly,
        total_vmt,
        vmt_above,
        vmt_above_limit,
        vmt_above_limit_5,
        vmt_above_limit_10,
    )


def save_speed_bins(bins):
    # write speed bin results
    print("Saving speed bin results...")
    with open(RESULTS_SPEED_BIN_PATH, "w", newline="") as f:
        fieldnames = ["district", "freeway", "speed", "total_vmt"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for district, freeways in bins.items():
            for freeway, speeds in freeways.items():
                for speed, bin_vmt in speeds.items():
                    if speed == 0:
                        continue
                    writer.writerow(
                        {
                            "district": district,
                            "freeway": freeway,
                            "speed": speed,
                            "total_vmt": bin_vmt,
                        }
                    )


def save_vmt_hourly(vmt_hourly):
    # write vmt hourly distribution results
    print("Saving vmt hourly distribution results...")
    with open(RESULTS_VMT_HOURLY_PATH, "w", newline="") as f:
        fieldnames = ["district", "freeway", "hour", "total_vmt"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for district, freeways in vmt_hourly.items():
            for freeway, hours in freeways.items():
                for hour, vmt in hours.items():
                    writer.writerow(
                        {
                            "district": district,
                            "freeway": freeway,
                            "hour": hour,
                            "total_vmt": vmt,
                        }
                    )


def save_above_thresholds(thresholds, vmt_above, total_vmt):
    # print fraction of VMT above threshold:
    print("\nVMT fractions:")
    with open(RESULTS_ABOVE_THRESH_PATH, "w", newline="") as f:
        for threshold in thresholds:
            fraction = vmt_above[threshold] / total_vmt if total_vmt else 0
            s = f"Above {threshold} mph: {fraction:.4%}\n"
            print(s)
            f.write(s)


def save_above_speed_limit(
    vmt_above_limit,
    vmt_above_limit_5,
    vmt_above_limit_10,
    total_vmt,
):
    # print fraction of VMT above speed limit:
    with open(RESULTS_ABOVE_SPEED_LIMIT, "w", newline="") as f:
        s = (
            "\nVMT fractions relative to the posted speed limit:\n"
            f"Above the speed limit: {vmt_above_limit / total_vmt:.4%}\n"
            f"Above the speed limit +5 mph: {vmt_above_limit_5 / total_vmt:.4%}\n"
            f"Above the speed limit +10 mph: {vmt_above_limit_10 / total_vmt:.4%}"
        )
        print(s)
        f.write(s)
