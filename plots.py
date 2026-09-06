import geopandas as gpd
import contextily as ctx
import os
import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np
import pandas as pd
from setup import RESULTS_DIR
from setup import ERRORS_FILE


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
                "highway": data["route"],
                "latitude": latitude,
                "longitude": longitude,
                "average_speed": average_speed,
            }
        )
    summary = [
        f"\n\nSUMMARY:",
        f"Total number of stations: {len(station_data)}",
        f"Could not map {error_count_missing_fields} stations (missing lat/lon/avg_speed/highway)",
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

    # Plot one map for each highway
    for highway in sorted(gdf["highway"].unique()):
        highway_gdf = gdf[gdf["highway"] == highway]

        # Create highway directory
        highway_plots_dir = os.path.join(
            RESULTS_DIR,
            f"highway_{highway}",
        )
        os.makedirs(highway_plots_dir, exist_ok=True)

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 16))

        # Plot stations
        highway_gdf.plot(
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
        plt.title(f"highway {highway} Average Speeds", fontsize=16)
        plt.tight_layout()

        plot_path = os.path.join(highway_plots_dir, f"highway_{highway}_speed_map.png")

        plt.savefig(plot_path, dpi=300, bbox_inches="tight")

        print(f"Saved {plot_path}")
        plt.close()


def plot_speed_bins(bins, lane_type):
    # Plot data
    # {highway: {district: {speed: total_vmt}}}
    print("Plotting speed bins...")
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Plot one figure for each highway
    for highway, districts in bins.items():
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

        # Create highway directory
        highway_plots_dir = os.path.join(
            RESULTS_DIR,
            f"highway_{highway}",
        )
        os.makedirs(highway_plots_dir, exist_ok=True)

        plt.figure(figsize=(14, 8))

        for i, district in enumerate(district_names):
            # Get raw VMT values
            highway_district_speed_bins = [districts[district][speed] for speed in all_speeds]
            y = np.array(highway_district_speed_bins)
            normalized = y / sum(highway_district_speed_bins) * 100

            offset = (i - (len(district_names) - 1) / 2) * bar_width

            plt.bar(
                x + offset,
                normalized,
                width=bar_width,
                label=f"District {district}",
            )

        plt.xticks(x, all_speeds)
        plt.xlabel("Speed (mph)")
        plt.ylabel("% of VMT")
        plt.title(f"highway {highway}")
        plt.legend(title="District")

        plot_path = os.path.join(
            highway_plots_dir,
            f"highway_{highway}_{lane_type}.png",
        )

        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        print(f"Saved {plot_path}")
        plt.close()


def plot_vmt_hourly(vmt_hourly, lane_type):
    print("Plotting speed hourly VMT distribution...")
    all_hours = range(24)

    for highway, districts in vmt_hourly.items():
        # Plot one figure for each highway

        district_names = sorted(districts.keys())
        x = np.arange(len(all_hours))
        bar_width = 0.8 / len(district_names)

        # Create highway directory
        highway_plots_dir = os.path.join(
            RESULTS_DIR,
            f"highway_{highway}",
        )
        os.makedirs(highway_plots_dir, exist_ok=True)

        plt.figure(figsize=(14, 8))

        for i, district in enumerate(district_names):
            highway_district_bins = [districts[district][hour] for hour in all_hours]
            y = np.array(highway_district_bins)
            normalized = y / sum(highway_district_bins) * 100
            offset = (i - (len(district_names) - 1) / 2) * bar_width

            plt.bar(
                x + offset,
                normalized,
                width=bar_width,
                label=f"District {district}",
            )

        plt.xticks(x, [f"{hour}-{hour+1}" for hour in all_hours])
        plt.xlabel("Hour")
        plt.ylabel("% of Total VMT")
        plt.title(f"highway {highway} Hourly VMT Distribution")
        plt.legend(title="District")

        plot_path = os.path.join(
            highway_plots_dir,
            f"highway_{highway}_hourly_{lane_type}.png",
        )

        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        print(f"Saved {plot_path}")
        plt.close()


def plot_speed_limit_coverage(station_data):
    speed_proportions = defaultdict(lambda: defaultdict(float))
    error_lines = []

    for station, data in station_data.items():
        highway = data["route"]
        speed_limit = data.get("speed_limit")

        if speed_limit is None:
            error_lines.append(
                f"Could not plot speed coverage for station {station}"
            )
            continue

        speed_proportions[highway][speed_limit] += data["station_length"]

    # pie chart
    for highway, proportions in speed_proportions.items():
        speed_limits = sorted(proportions.keys())
        lengths = [proportions[speed_limit] for speed_limit in speed_limits]
        labels = [f"{speed_limit} mph" for speed_limit in speed_limits]
        fig, ax = plt.subplots()
        ax.pie(
            lengths,
            labels=labels,
            autopct="%1.1f%%"
        )
        ax.set_title(f"Highway {highway} Speed Limit Coverage")
        highway_plots_dir = os.path.join(
            RESULTS_DIR,
            f"highway_{highway}"
        )
        os.makedirs(highway_plots_dir, exist_ok=True)

        plot_path = os.path.join(
            highway_plots_dir,
            f"highway_{highway}_speed_limit_coverage.png"
        )
        fig.savefig(plot_path, dpi=300, bbox_inches="tight")
        print(f"Saved {plot_path}")
        plt.close()