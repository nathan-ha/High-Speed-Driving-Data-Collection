import geopandas as gpd
import contextily as ctx
import os
import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np
import pandas as pd
from setup import RESULTS_DIR
from setup import ERRORS_FILE

RESULTS_PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")


def plot_california_speed_map(station_data):
    stations = []
    error_lines = []
    error_count_missing_fields = 0
    for station, data in station_data.items():
        if (
            ("latitude" not in data)
            or ("longitude" not in data)
            or ("avg_speed" not in data)
            or ("route" not in data)
        ):
            error_lines.append(f"Could not map station {station}")
            error_count_missing_fields += 1
            continue
        speeds = [
            speed
            for speed in data["avg_speed"].values()
            if speed is not None and speed >= 0
        ]
        if not speeds:
            continue
        latitude = pd.to_numeric(data["latitude"], errors="coerce")
        longitude = pd.to_numeric(data["longitude"], errors="coerce")
        if pd.isna(latitude) or pd.isna(longitude):
            error_lines.append(
                f"Could not map station {station}: invalid latitude/longitude"
            )
            error_count_missing_fields += 1
            continue
        average_speed = sum(speeds) / len(speeds)
        stations.append(
            {
                "station": station,
                "freeway": data["route"],
                "latitude": latitude,
                "longitude": longitude,
                "average_speed": average_speed,
            }
        )
    summary = [
        f"\n\nSUMMARY:",
        f"Total number of stations: {len(station_data)}",
        f"Could not map {error_count_missing_fields} stations (missing lat/lon/avg_speed/freeway)",
        "\n\n",
    ]
    error = "\n".join(error_lines + summary)
    print("\n".join(summary))
    print(f"Detailed errors written to {ERRORS_FILE}")
    with open(ERRORS_FILE, "a") as f:
        f.write(error)
    if not stations:
        print("No valid stations to plot.")
        return

    # Convert station data into a GeoDataFrame
    gdf = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(
            [station["longitude"] for station in stations],
            [station["latitude"] for station in stations],
        ),
        crs="EPSG:4326",
    )

    # Contextily requires Web Mercator coordinates
    gdf = gdf.to_crs(epsg=3857)

    # Plot one map for each freeway
    for freeway in sorted(gdf["freeway"].unique()):
        freeway_gdf = gdf[gdf["freeway"] == freeway]

        # Create freeway directory
        freeway_plots_dir = os.path.join(
            RESULTS_PLOTS_DIR,
            f"freeway_{freeway}",
        )
        os.makedirs(freeway_plots_dir, exist_ok=True)

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 16))

        # Plot stations
        freeway_gdf.plot(
            ax=ax,
            column="average_speed",
            cmap="RdYlGn",
            markersize=8,
            legend=True,
            legend_kwds={
                "label": "Average Speed (mph)",
                "shrink": 0.1,
            },
        )

        # Add real map underneath
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)

        ax.set_axis_off()
        plt.title(f"Freeway {freeway} Average Speeds", fontsize=16)
        plt.tight_layout()

        plot_path = os.path.join(freeway_plots_dir, f"freeway_{freeway}_speed_map.png")

        plt.savefig(plot_path, dpi=300, bbox_inches="tight")

        print(f"Saved {plot_path}")
        plt.close()


def plot_speed_bins(bins, lane_type):
    # Plot data
    # {freeway: {district: {speed: total_vmt}}}
    print("Plotting speed bins...")
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

        # Create freeway directory
        freeway_plots_dir = os.path.join(
            RESULTS_PLOTS_DIR,
            f"freeway_{freeway}",
        )
        os.makedirs(freeway_plots_dir, exist_ok=True)

        plt.figure(figsize=(14, 8))

        for i, district in enumerate(district_names):
            # Get raw VMT values
            y = np.array(
                [districts[district].get(speed, 0) for speed in all_speeds], dtype=float
            )

            # High-low (min-max) normalization
            min_value = np.min(y)
            max_value = np.max(y)

            if max_value != min_value:
                normalized = (y - min_value) / (max_value - min_value)
            else:
                normalized = np.zeros_like(y)

            offset = (i - (len(district_names) - 1) / 2) * bar_width

            plt.bar(
                x + offset,
                normalized,
                width=bar_width,
                label=f"District {district}",
            )

        plt.xticks(x, all_speeds)
        plt.xlabel("Speed (mph)")
        plt.ylabel("Normalized VMT")
        plt.title(f"Freeway {freeway}")
        plt.legend(title="District")

        plot_path = os.path.join(
            freeway_plots_dir,
            f"freeway_{freeway}_{lane_type}.png",
        )

        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        print(f"Saved {plot_path}")
        plt.close()


def plot_vmt_hourly(vmt_hourly, lane_type):
    print("Plotting speed hourly VMT distribution...")

    freeway_data = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    for district, freeways in vmt_hourly.items():
        for freeway, hours in freeways.items():
            for hour, vmt in hours.items():
                freeway_data[freeway][district][hour] += vmt

    for freeway, districts in freeway_data.items():
        # Plot one figure for each freeway
        all_hours = sorted(
            {hour for district_hours in districts.values() for hour in district_hours}
        )

        district_names = sorted(districts.keys())
        x = np.arange(len(all_hours))
        bar_width = 0.8 / len(district_names)

        # Create freeway directory
        freeway_plots_dir = os.path.join(
            RESULTS_PLOTS_DIR,
            f"freeway_{freeway}",
        )
        os.makedirs(freeway_plots_dir, exist_ok=True)

        plt.figure(figsize=(14, 8))

        for i, district in enumerate(district_names):
            y = np.array(
                [districts[district].get(hour, 0) for hour in all_hours], dtype=float
            )

            # High-low (min-max) normalization
            min_value = np.min(y)
            max_value = np.max(y)

            if max_value != min_value:
                normalized = (y - min_value) / (max_value - min_value)
            else:
                normalized = np.zeros_like(y)

            offset = (i - (len(district_names) - 1) / 2) * bar_width

            plt.bar(
                x + offset,
                normalized,
                width=bar_width,
                label=f"District {district}",
            )

        plt.xticks(x, all_hours)
        plt.xlabel("Hour")
        plt.ylabel("Normalized VMT")
        plt.title(f"Freeway {freeway} Hourly VMT Distribution")
        plt.legend(title="District")

        plot_path = os.path.join(
            freeway_plots_dir,
            f"freeway_{freeway}_hourly_{lane_type}.png",
        )

        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        print(f"Saved {plot_path}")
        plt.close()
