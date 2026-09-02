from setup import *
from collections import defaultdict
import csv
from setup import RESULTS_DIR, ERRORS_FILE

RESULTS_SPEED_BIN_PATH = os.path.join(RESULTS_DIR, "speed_bin.csv")
RESULTS_VMT_HOURLY_PATH = os.path.join(RESULTS_DIR, "vmt_hourly_distribution.csv")
SPEED_MIN = 55

def calculate_vmt(station_data, thresholds):
    # {district : {#mph : vmt}}
    total_vmt = defaultdict(float)
    vmt_above = defaultdict(lambda: {threshold: 0 for threshold in thresholds})
    vmt_above_limit = defaultdict(float)
    vmt_above_limit_5 = defaultdict(float)
    vmt_above_limit_10 = defaultdict(float)
    total_vmt_valid_speed_limit = defaultdict(float)
    count = 0
    print("Creating Speed Bins...")
    error_count_speed_limit = 0
    error_count_avg_speed = 0
    error_count_total_flow = 0
    error_count_invalid_speed = 0
    error_lines = []
    # {district: {highway: {speed_bin: vmt}}}
    bins = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    vmt_hourly = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    for station, data in station_data.items():
        # Error checks
        if "avg_speed" not in data:
            error_lines.append(f"Missing avg_speed for station {station}")
            error_count_avg_speed += 1
            continue

        speed_limit = data.get("speed_limit")
        valid_speed_limit = speed_limit is not None and speed_limit >= SPEED_MIN

        if not valid_speed_limit:
            error_lines.append(f"Could not get speed limit for station {station}")
            error_count_speed_limit += 1

        # Read all timestamps for each station
        for timestamp, avg_speed in data["avg_speed"].items():
            if timestamp not in data["total_flow"]:
                error_lines.append(
                    f"Missing total_flow for station {station}, "
                    f"timestamp {timestamp}"
                )
                error_count_total_flow += 1
                continue

            if avg_speed is None or avg_speed < 0:
                error_lines.append(
                    f"Invalid average speed for station {station}, "
                    f"timestamp {timestamp}: {avg_speed}"
                )
                error_count_invalid_speed += 1
                continue

            highway = data["route"]
            district = data["district"]

            # VMT calculation
            flow = data["total_flow"][timestamp]
            vmt = flow * data["station_length"]
            total_vmt[highway] += vmt


            # VMT above each threshold
            for threshold in thresholds:
                if avg_speed > threshold:
                    vmt_above[highway][threshold] += vmt

            # VMT above posted speed limit
            if valid_speed_limit:
                total_vmt_valid_speed_limit[highway] += vmt

                if avg_speed > speed_limit:
                    vmt_above_limit[highway] += vmt

                if avg_speed > speed_limit + 5:
                    vmt_above_limit_5[highway] += vmt

                if avg_speed > speed_limit + 10:
                    vmt_above_limit_10[highway] += vmt

            # Add VMT to speed bin
            speed_bin = int(avg_speed / 5 + 0.5) * 5
            bins[district][highway][speed_bin] += vmt

            hour = int(timestamp.split(" ")[1].split(":")[0])
            vmt_hourly[district][highway][hour] += vmt

            count += 1

            if count % 10000 == 0:
                print(f"Calculated {count:,} VMTs...", end="\r")

    summary = [
        f"\n\nSUMMARY:",
        f"Total number of stations: {len(station_data)}",
        f"Could not get speed limit for {error_count_speed_limit} stations",
        f"Could not get average speed for {error_count_avg_speed} stations",
        f"Missing total_flow for {error_count_total_flow} station/timestamp pairs",
        f"Invalid average speed for {error_count_invalid_speed} station/timestamp pairs",
        "\n\n",
    ]

    error = "\n".join(error_lines + summary)

    print("\n".join(summary))
    print(f"Detailed errors written to {ERRORS_FILE}")

    with open(ERRORS_FILE, "w") as f:
        f.write(error)

    return (
        bins,
        vmt_hourly,
        total_vmt,
        vmt_above,
        vmt_above_limit,
        vmt_above_limit_5,
        vmt_above_limit_10,
        total_vmt_valid_speed_limit,
    )


def save_speed_bins(bins):
    # write speed bin results
    print("Saving speed bin results...")

    with open(RESULTS_SPEED_BIN_PATH, "w", newline="") as f:
        fieldnames = ["district", "highway", "speed", "total_vmt"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for district, highways in bins.items():
            for highway, speeds in highways.items():
                for speed, bin_vmt in speeds.items():
                    if speed == 0:
                        continue

                    writer.writerow(
                        {
                            "district": district,
                            "highway": highway,
                            "speed": speed,
                            "total_vmt": bin_vmt,
                        }
                    )


def save_vmt_hourly(vmt_hourly):
    # write vmt hourly distribution results
    print("Saving vmt hourly distribution results...")

    with open(RESULTS_VMT_HOURLY_PATH, "w", newline="") as f:
        fieldnames = ["district", "highway", "hour", "total_vmt"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for district, highways in vmt_hourly.items():
            for highway, hours in highways.items():
                for hour, vmt in hours.items():
                    writer.writerow(
                        {
                            "district": district,
                            "highway": highway,
                            "hour": hour,
                            "total_vmt": vmt,
                        }
                    )


def save_above_thresholds(thresholds, vmt_above, total_vmt):
    # print fraction of VMT above threshold:
    print("\nVMT fractions:")

    for highway, threshold_vmt in vmt_above.items():
        highway_plots_dir = os.path.join(
            RESULTS_DIR,
            f"highway_{highway}",
        )
        os.makedirs(highway_plots_dir, exist_ok=True)
        path = os.path.join(highway_plots_dir, f"highway_{highway}_above_speeds.txt")
        with open(path, "w", newline="") as f:
            f.write("VMT Fractions:\n")
            for threshold in thresholds:
                fraction = threshold_vmt[threshold] / total_vmt[highway] if total_vmt[highway] else 0
                s = f"Above {threshold} mph: {fraction:.4%}\n"
                print(s, end="")
                f.write(s)


def save_above_speed_limit(
    vmt_above_limit,
    vmt_above_limit_5,
    vmt_above_limit_10,
    total_vmt_valid_speed_limit,
):
    # print fraction of VMT above speed limit:
    for highway in vmt_above_limit:
        highway_plots_dir = os.path.join(
            RESULTS_DIR,
            f"highway_{highway}",
        )
        os.makedirs(highway_plots_dir, exist_ok=True)
        path = os.path.join(highway_plots_dir, f"highway_{highway}_above_speeds.txt")
        with open(path, "a", newline="") as f:
            s = (
                "\nVMT fractions relative to the posted speed limit:\n"
                f"Above the speed limit: "
                f"{vmt_above_limit[highway] / total_vmt_valid_speed_limit[highway]:.4%}\n"
                f"Above the speed limit +5 mph: "
                f"{vmt_above_limit_5[highway] / total_vmt_valid_speed_limit[highway]:.4%}\n"
                f"Above the speed limit +10 mph: "
                f"{vmt_above_limit_10[highway] / total_vmt_valid_speed_limit[highway]:.4%}"
            )
            print(s)
            f.write(s + "\n")


def save_above_speeds(
    thresholds,
    vmt_above,
    total_vmt,
    vmt_above_limit,
    vmt_above_limit_5,
    vmt_above_limit_10,
    total_vmt_valid_speed_limit,
):
    
    save_above_thresholds(
        thresholds,
        vmt_above,
        total_vmt,
    )
    save_above_speed_limit(
        vmt_above_limit,
        vmt_above_limit_5,
        vmt_above_limit_10,
        total_vmt_valid_speed_limit,
    )
