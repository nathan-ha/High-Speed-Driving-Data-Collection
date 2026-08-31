from setup import *
from collections import defaultdict
import csv
from setup import RESULTS_DIR, ERRORS_FILE

RESULTS_SPEED_BIN_PATH = os.path.join(RESULTS_DIR, "speed_bin.csv")
RESULTS_VMT_HOURLY_PATH = os.path.join(RESULTS_DIR, "vmt_hourly_distribution.csv")
RESULTS_ABOVE_THRESH_PATH = os.path.join(RESULTS_DIR, "above_thresholds.txt")
RESULTS_ABOVE_SPEED_LIMIT = os.path.join(RESULTS_DIR, "above_speed_limit.txt")


def calculate_vmt(station_data, thresholds):
    # {district : {#mph : vmt}}
    total_vmt = 0
    vmt_above = defaultdict(lambda: {threshold: 0 for threshold in thresholds})
    vmt_above_limit = defaultdict(float)
    vmt_above_limit_5 = defaultdict(float)
    vmt_above_limit_10 = defaultdict(float)
    count = 0
    print("Creating Speed Bins...")
    error_count_speed_limit = 0
    error_count_avg_speed = 0
    error_count_total_flow = 0
    error_count_invalid_speed = 0
    error_lines = []
    # {district: {freeway: {speed_bin: vmt}}}
    bins = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    vmt_hourly = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    for station, data in station_data.items():
        # Error checks
        if "avg_speed" not in data:
            error_lines.append(f"Missing avg_speed for station {station}")
            error_count_avg_speed += 1
            continue

        speed_limit = data.get("speed_limit")
        valid_speed_limit = speed_limit is not None and speed_limit > 0

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

            # VMT calculation
            flow = data["total_flow"][timestamp]
            vmt = flow * data["station_length"]
            total_vmt += vmt

            freeway = data["route"]
            district = data["district"]

            # VMT above each threshold
            for threshold in thresholds:
                if avg_speed > threshold:
                    vmt_above[freeway][threshold] += vmt

            # VMT above posted speed limit
            if valid_speed_limit:
                if avg_speed > speed_limit:
                    vmt_above_limit[freeway] += vmt

                if avg_speed > speed_limit + 5:
                    vmt_above_limit_5[freeway] += vmt

                if avg_speed > speed_limit + 10:
                    vmt_above_limit_10[freeway] += vmt

            # Add VMT to speed bin
            speed_bin = int(avg_speed / 5 + 0.5) * 5
            bins[district][freeway][speed_bin] += vmt

            hour = int(timestamp.split(" ")[1].split(":")[0])
            vmt_hourly[district][freeway][hour] += vmt

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
        for freeway, threshold_vmt in vmt_above.items():
            s = f"\nFreeway {freeway}:\n"
            print(s, end="")
            f.write(s)

            for threshold in thresholds:
                fraction = threshold_vmt[threshold] / total_vmt if total_vmt else 0

                s = f"Above {threshold} mph: {fraction:.4%}\n"
                print(s, end="")
                f.write(s)


def save_above_speed_limit(
    vmt_above_limit,
    vmt_above_limit_5,
    vmt_above_limit_10,
    total_vmt,
):
    # print fraction of VMT above speed limit:
    with open(RESULTS_ABOVE_SPEED_LIMIT, "w", newline="") as f:
        for freeway in vmt_above_limit:
            s = (
                f"\nFreeway {freeway}:"
                "\nVMT fractions relative to the posted speed limit:\n"
                f"Above the speed limit: "
                f"{vmt_above_limit[freeway] / total_vmt:.4%}\n"
                f"Above the speed limit +5 mph: "
                f"{vmt_above_limit_5[freeway] / total_vmt:.4%}\n"
                f"Above the speed limit +10 mph: "
                f"{vmt_above_limit_10[freeway] / total_vmt:.4%}"
            )

            print(s)
            f.write(s + "\n")
