from setup import *
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
import csv

RESULTS_DIR = os.path.join("data", "results")
RESULTS_SPEED_BIN_PATH = os.path.join(RESULTS_DIR, "speed_bin.csv")
RESULTS_ABOVE_THRESH_PATH = os.path.join(RESULTS_DIR, "above_thresholds.txt")
RESULTS_ABOVE_SPEED_LIMIT = os.path.join(RESULTS_DIR, "above_speed_limit.txt")
RESULTS_PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")

if __name__ == "__main__":
    station_data = {}
    setup(station_data)
    thresholds = [65, 70, 75, 80, 85, 90]

    # plan:
    # for each freeway:
    #     for each station:
    #         get speeds across all timestamps
    #         get flow across all timestamps
    #         calculate VMT using flow
    #         bin speed for that station, add VMT to bin

    #     VMT distribution by 5-mph speed bin and time of day
    # {district : {#mph : vmt}}
    total_vmt = 0
    vmt_above = {threshold: 0 for threshold in thresholds}
    vmt_above_limit = 0
    vmt_above_limit_5 = 0
    vmt_above_limit_10 = 0

    count = 0
    print("Creating Speed Bins...")
    # {district: {freeway: {speed_bin: vmt}}}
    bins = defaultdict(
        lambda: defaultdict(lambda: defaultdict(float))
    )  # auto initialize bins to 0

    for station, data in station_data.items():
        # Error checks
        if "avg_speed" not in data:
            print(f"Missing avg_speed for station {station}")
            continue
        speed_limit = data.get("speed_limit")
        valid_speed_limit = (
            speed_limit is not None
            and speed_limit > 0
        )
        if not valid_speed_limit:
            print(f"Could not get speed limit for station {station}")
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
            count += 1
            if count % 10000 == 0:
                print(f"Calculated {count:,} VMTs...", end="\r")

    # write results
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

    # print fraction of VMT above threshold:
    print("\nVMT fractions:")
    with open(RESULTS_ABOVE_THRESH_PATH, "w", newline="") as f:
        for threshold in thresholds:
            fraction = vmt_above[threshold] / total_vmt if total_vmt else 0
            s = f"Above {threshold} mph: {fraction:.4%}\n"
            print(s)
            f.write(s)

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

    # Plot data
    # {freeway: {district: {speed: total_vmt}}}
    os.makedirs(RESULTS_PLOTS_DIR, exist_ok=True)
    freeway_data = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    for district, freeways in bins.items():
        for freeway, speeds in freeways.items():
            for speed, bin_vmt in speeds.items():
                freeway_data[freeway][district][speed] += bin_vmt

    # Plot one figure for each freeway
    for freeway, districts in freeway_data.items():
        all_speeds = sorted(
            {
                speed
                for district_speeds in districts.values()
                for speed in district_speeds
            }
        )
        district_names = sorted(districts.keys())
        x = np.arange(len(all_speeds))
        bar_width = 0.8 / len(district_names)
        plt.figure(figsize=(14, 8))
        for i, district in enumerate(district_names):
            y = [districts[district].get(speed, 0) for speed in all_speeds]
            offset = (i - (len(district_names) - 1) / 2) * bar_width
            plt.bar(x + offset, y, width=bar_width, label=f"District {district}")
        plt.xticks(x, all_speeds)
        plt.xlabel("Speed (mph)")
        plt.ylabel("VMT")
        plt.title(f"Freeway {freeway}")
        plt.legend(title="District")
        plot_path = os.path.join(
            RESULTS_PLOTS_DIR,
            f"freeway_{freeway}.png",
        )
        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        print(f"Saved {plot_path}")
        plt.show()
        plt.close()
