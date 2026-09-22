from setup import *
from collections import defaultdict
import csv
from setup import RESULTS_DIR, ERRORS_FILE

RESULTS_SPEED_BIN_PATH = os.path.join(RESULTS_DIR, "speed_bin.csv")
RESULTS_VMT_HOURLY_PATH = os.path.join(RESULTS_DIR, "vmt_hourly_distribution.csv")
SPEED_MIN = 15


def calculate_vmt(station_data, thresholds):
    total_vmt = defaultdict(lambda: defaultdict(float))
    vmt_above = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    vmt_above_limit = defaultdict(lambda: defaultdict(float))
    vmt_above_limit_5 = defaultdict(lambda: defaultdict(float))
    vmt_above_limit_10 = defaultdict(lambda: defaultdict(float))
    total_vmt_valid_speed_limit = defaultdict(lambda: defaultdict(float))
    count = 0
    print("Creating Speed Bins...")
    error_count_speed_limit = 0
    error_count_avg_speed = 0
    error_count_total_flow = 0
    error_count_invalid_speed = 0
    error_lines = []
    bins = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    vmt_hourly = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    vmt_above_hourly = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    )
    speed_limit_coverage = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    vmt_speed_limit = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    )
    vmt_speed_bin_hourly = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(float)
            )
        )
    )

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

        highway = data["route"]
        district = data["district"]
        if valid_speed_limit:
            speed_limit_coverage[highway][district][speed_limit] += data[
                "station_length"
            ]

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
            total_vmt[highway][district] += vmt

            # VMT above each threshold
            hour = int(timestamp.split(" ")[1].split(":")[0])
            for threshold in thresholds:
                if avg_speed > threshold:
                    vmt_above[highway][district][threshold] += vmt
                    vmt_above_hourly[highway][district][hour][threshold] += vmt

            # VMT above posted speed limit
            if valid_speed_limit:
                total_vmt_valid_speed_limit[highway][district] += vmt
                if avg_speed > speed_limit:
                    vmt_above_limit[highway][district] += vmt
                if avg_speed > speed_limit + 5:
                    vmt_above_limit_5[highway][district] += vmt
                if avg_speed > speed_limit + 10:
                    vmt_above_limit_10[highway][district] += vmt

            # Add VMT to speed bin
            speed_bin = emfac_round(avg_speed)
            bins[highway][district][speed_bin] += vmt
            vmt_speed_bin_hourly[highway][district][hour][speed_bin] += vmt
            if valid_speed_limit:
                vmt_speed_limit[highway][district][speed_limit][speed_bin] += vmt
            vmt_hourly[highway][district][hour] += vmt
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
        vmt_above_hourly,
        vmt_speed_bin_hourly,
        total_vmt,
        vmt_above,
        vmt_above_limit,
        vmt_above_limit_5,
        vmt_above_limit_10,
        total_vmt_valid_speed_limit,
        speed_limit_coverage,
        vmt_speed_limit,
    )


def save_vmt_above_thresholds_hourly(vmt_hourly, vmt_above_hourly, thresholds):
    path = os.path.join(
        RESULTS_DIR,
        "vmt_above_thresholds_hourly.csv",
    )

    fieldnames = [
        "Highway",
        "District",
        "Hour",
    ]
    for threshold in thresholds:
        fieldnames.append(f"%VMT Above {threshold} mph")
    for threshold in thresholds:
        fieldnames.append(f"VMT Above {threshold} mph")
    fieldnames.append("Total VMT")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for highway, districts in vmt_hourly.items():
            for district, hours in districts.items():
                for hour, total_vmt in hours.items():
                    row = {
                        "Highway": highway,
                        "District": district,
                        "Hour": hour,
                        "Total VMT": total_vmt,
                    }
                    for threshold in thresholds:
                        raw_vmt = vmt_above_hourly[highway][district][hour][threshold]
                        fraction = raw_vmt / total_vmt if total_vmt else 0
                        row[f"%VMT Above {threshold} mph"] = f"{fraction:.4%}"
                        row[f"VMT Above {threshold} mph"] = raw_vmt
                    writer.writerow(row)


def save_speed_bins(bins):
    # write speed bin results
    print("Saving speed bin results...")
    with open(RESULTS_SPEED_BIN_PATH, "w", newline="") as f:
        fieldnames = ["district", "highway", "speed", "total_vmt"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for highway, districts in bins.items():
            for district, speeds in districts.items():
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
        for highway, districts in vmt_hourly.items():
            for district, hours in districts.items():
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
    path = os.path.join(RESULTS_DIR, "table_A_above_thresholds.csv")
    fieldnames = [
        "Highway",
        "District",
    ]
    for threshold in thresholds:
        fieldnames.append(f"%VMT Above {threshold} mph")
    for threshold in thresholds:
        fieldnames.append(f"VMT Above {threshold} mph")
    fieldnames.append("Total VMT")

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for highway, districts in vmt_above.items():
            for district, threshold_vmt in districts.items():
                row = {
                    "Highway": highway,
                    "District": district,
                }
                for threshold in thresholds:
                    raw_vmt = threshold_vmt[threshold]
                    fraction = (
                        raw_vmt / total_vmt[highway][district]
                        if total_vmt[highway][district]
                        else 0
                    )
                    row[f"%VMT Above {threshold} mph"] = f"{fraction:.4%}"
                    row[f"VMT Above {threshold} mph"] = raw_vmt

                row["Total VMT"] = total_vmt[highway][district]

                writer.writerow(row)


def save_above_speed_limit(
    vmt_above_limit,
    vmt_above_limit_5,
    vmt_above_limit_10,
    total_vmt_valid_speed_limit,
    speed_limit_coverage,
):
    speed_limits = set()

    for highway, districts in speed_limit_coverage.items():
        for district, limits in districts.items():
            for speed_limit in limits:
                speed_limits.add(speed_limit)

    speed_limits = sorted(speed_limits)

    # print fraction of VMT above speed limit:
    path = os.path.join(
        RESULTS_DIR,
        "table_B_above_limits.csv",
    )

    fieldnames = [
        "Highway",
        "District",
    ]

    for speed_limit in speed_limits:
        fieldnames.append(f"Speed limit coverage {speed_limit} mph")

    fieldnames += [
        "%VMT Above Speed Limit",
        "%VMT Above Speed Limit +5 mph",
        "%VMT Above Speed Limit +10 mph",
    ]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for highway, districts in total_vmt_valid_speed_limit.items():
            for district in districts:
                total = total_vmt_valid_speed_limit[highway][district]
                above_limit = vmt_above_limit[highway][district] / total if total else 0
                above_limit_5 = (
                    vmt_above_limit_5[highway][district] / total if total else 0
                )
                above_limit_10 = (
                    vmt_above_limit_10[highway][district] / total if total else 0
                )
                row = {
                    "Highway": highway,
                    "District": district,
                    "%VMT Above Speed Limit": f"{above_limit:.4%}",
                    "%VMT Above Speed Limit +5 mph": f"{above_limit_5:.4%}",
                    "%VMT Above Speed Limit +10 mph": f"{above_limit_10:.4%}",
                }

                for speed_limit in speed_limits:
                    coverage = speed_limit_coverage[highway][district][
                        speed_limit
                    ] / sum(speed_limit_coverage[highway][district].values())
                    row[f"Speed limit coverage {speed_limit} mph"] = f"{coverage:.4%}"

                writer.writerow(row)


def emfac_round(speed):
    if speed <= 5.0:
        return 5
    elif speed <= 10.0:
        return 10
    elif speed <= 15.0:
        return 15
    elif speed <= 20.0:
        return 20
    elif speed <= 25.0:
        return 25
    elif speed <= 30.0:
        return 30
    elif speed <= 35.0:
        return 35
    elif speed <= 40.0:
        return 40
    elif speed <= 45.0:
        return 45
    elif speed <= 50.0:
        return 50
    elif speed <= 55.0:
        return 55
    elif speed <= 60.0:
        return 60
    elif speed <= 65.0:
        return 65
    elif speed <= 70.0:
        return 70
    elif speed <= 75.0:
        return 75
    elif speed <= 80.0:
        return 80
    elif speed <= 85.0:
        return 85
    else:
        return 90


def save_above_speeds(
    thresholds,
    vmt_above,
    total_vmt,
    vmt_above_limit,
    vmt_above_limit_5,
    vmt_above_limit_10,
    total_vmt_valid_speed_limit,
    speed_limit_coverage,
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
        speed_limit_coverage,
    )

    sort_csv(
        os.path.join(RESULTS_DIR, "table_A_above_thresholds.csv"),
        ["Highway", "District"],
    )
    sort_csv(
        os.path.join(RESULTS_DIR, "table_B_above_limits.csv"), ["Highway", "District"]
    )


# sorts the csv by the specified keys
def sort_csv(path, keys):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    def sort_key(row):
        vals = []
        for k in keys:
            v = row[k]
            try:
                v = float(v)
            except ValueError:
                pass
            vals.append(v)
        return tuple(vals)

    rows.sort(key=sort_key)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
