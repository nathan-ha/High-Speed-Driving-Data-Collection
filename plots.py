import geopandas as gpd
import contextily as ctx
import os
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
from collections import defaultdict
import numpy as np
import pandas as pd
from setup import RESULTS_DIR
from setup import ERRORS_FILE
from dotenv import load_dotenv

load_dotenv()


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
        CARTO_KEY = os.getenv("CARTO_KEY")
        if not CARTO_KEY:
            print("No CARTO key detected. Could not generate California Map.")
            return
        basemap_source = f"https://basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}.png?key={CARTO_KEY}"
        ctx.add_basemap(ax, source=basemap_source)

        ax.set_axis_off()
        plt.title(f"highway {highway} Average Speeds", fontsize=16)
        plt.tight_layout()

        plot_path = os.path.join(
            highway_plots_dir,
            f"highway_{highway}_speed_map.png",
        )

        plt.savefig(
            plot_path,
            dpi=300,
            bbox_inches="tight",
        )

        print(f"Saved {plot_path}")
        plt.close()


def plot_speed_bins(vmt_speed_limit, lane_type):
    # {highway: {district: {speed_limit: {speed: total_vmt}}}}

    # Build one global speed-limit to color mapping so colors are
    # consistent across all districts and all highway plots
    global_speed_limits = sorted(
        {
            speed_limit
            for districts in vmt_speed_limit.values()
            for district_data in districts.values()
            for speed_limit in district_data
        }
    )
    speed_limit_colors = {
        speed_limit: color
        for speed_limit, color in zip(
            global_speed_limits,
            [
                "#1F77B4",  # Blue
                "#FF7F0E",  # Orange
                "#2CA02C",  # Green
                "#D62728",  # Red
                "#9467BD",  # Purple
                "#8C564B",  # Brown
                "#17BECF",  # Cyan
            ],
        )
    }

    for highway, districts in vmt_speed_limit.items():
        all_districts = sorted(districts.keys())
        all_speed_limits = sorted(
            {
                speed_limit
                for district_data in districts.values()
                for speed_limit in district_data
            }
        )
        all_speeds = sorted(
            {
                speed
                for district_data in districts.values()
                for speed_limit_data in district_data.values()
                for speed in speed_limit_data
            }
        )

        if not all_speeds:
            continue

        # Calculate total VMT for this highway
        total_district_vmt = {}
        hatches = [
            "///",
            "\\\\",
            "xxx",
            "...",
            "---",
            "+++",
        ]

        district_hatches = {
            district: hatches[i % len(hatches)]
            for i, district in enumerate(all_districts)
        }

        district_legend_handles = [
            Patch(
                facecolor="white",
                edgecolor="0.35",
                hatch=district_hatches[district],
                label=f"District {district}",
            )
            for district in all_districts
        ]

        for district in all_districts:
            total_district_vmt[district] = sum(
                vmt
                for speed_limit_data in districts[district].values()
                for vmt in speed_limit_data.values()
            )

        # Make the graph wider when there are more speed bins or districts
        fig_width = max(16, len(all_districts) * 3)
        fig, ax = plt.subplots(figsize=(fig_width, 8))

        x = np.arange(len(all_speeds))
        width = 0.8 / len(all_districts)

        for district_index, district in enumerate(all_districts):
            hatch = district_hatches[district]
            x_offset = (district_index - (len(all_districts) - 1) / 2) * width
            x_positions = x + x_offset

            bottom = np.zeros(len(all_speeds))

            for speed_limit in all_speed_limits:
                values = []

                for speed in all_speeds:
                    vmt = districts[district].get(speed_limit, {}).get(speed, 0)

                    # Calculate the VMT percentage relative to
                    # total VMT for this highway
                    percentage = (
                        vmt / total_district_vmt[district] * 100
                        if total_district_vmt[district]
                        else 0
                    )

                    values.append(percentage)

                values = np.array(values)

                ax.bar(
                    x_positions,
                    values,
                    width,
                    bottom=bottom,
                    color=speed_limit_colors[speed_limit],
                    hatch=hatch,
                    edgecolor="0.35",
                    linewidth=0.4,
                    label=f"{speed_limit} mph" if district_index == 0 else None,
                )

                # Put the posted speed limit inside the stack
                # for i, value in enumerate(values):
                #     if value > 1:
                #         ax.text(
                #             x_positions[i],
                #             bottom[i] + value / 2,
                #             f"{speed_limit}",
                #             ha="center",
                #             va="center",
                #             fontsize=6,
                #         )

                bottom += values

            # Total % of VMT on top of each bar
            # for i, x_pos in enumerate(x_positions):
            #     if bottom[i] > 0:
            #         ax.text(
            #             x_pos,
            #             bottom[i] + 0.5,
            #             f"{bottom[i]:.1f}%",
            #             ha="center",
            #             va="bottom",
            #             fontsize=2,
            #         )

        ax.set_xticks(x)
        ax.set_xticklabels(all_speeds)
        ax.set_xlabel("Observed Speed (mph)")
        ax.set_ylabel("% of VMT")
        ax.set_title(
            f"Highway {highway} VMT Distribution by Observed Speed "
            f"and Posted Speed Limit"
        )

        # A little space above the bars so the top labels aren't clipped
        ax.set_ylim(0, ax.get_ylim()[1] * 1.08)

        # Legend for posted speed limits
        speed_limit_legend = ax.legend(
            title="Posted Speed Limit",
            loc="upper left",
            bbox_to_anchor=(1.02, 1.0),
        )

        # Add district hatch legend
        district_legend = ax.legend(
            handles=district_legend_handles,
            title="District",
            loc="upper left",
            bbox_to_anchor=(1.02, 0.55),
        )

        # Keep both legends
        ax.add_artist(speed_limit_legend)

        ax.grid(axis="y", alpha=0.3)

        plot_dir = os.path.join(RESULTS_DIR, f"highway_{highway}")
        os.makedirs(plot_dir, exist_ok=True)

        plot_path = os.path.join(
            plot_dir, f"highway_{highway}_{lane_type}_speed_bins.png"
        )

        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close(fig)


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
    speed_lengths = defaultdict(lambda: defaultdict(float))
    error_lines = []

    for station, data in station_data.items():
        highway = data["route"]
        speed_limit = data.get("speed_limit")

        if speed_limit is None:
            error_lines.append(f"Could not plot speed coverage for station {station}")
            continue

        speed_lengths[highway][speed_limit] += data["station_length"]

    # pie chart
    for highway, lengths in speed_lengths.items():
        speed_limits = sorted(lengths.keys())
        lengths = [lengths[speed_limit] for speed_limit in speed_limits]
        labels = [
            f"{limit} mph ({lengths[i]:.1f} mi)" for i, limit in enumerate(speed_limits)
        ]
        fig, ax = plt.subplots()
        ax.pie(lengths, labels=labels, autopct="%1.1f%%")
        ax.set_title(f"Highway {highway} Speed Limit Coverage")
        highway_plots_dir = os.path.join(RESULTS_DIR, f"highway_{highway}")
        os.makedirs(highway_plots_dir, exist_ok=True)

        plot_path = os.path.join(
            highway_plots_dir, f"highway_{highway}_speed_limit_coverage.png"
        )
        fig.savefig(plot_path, dpi=300, bbox_inches="tight")
        print(f"Saved {plot_path}")
        plt.close()


def plot_vmt_speed_bin_hourly(vmt_speed_bin_hourly, total_vmt):
    for highway, districts in vmt_speed_bin_hourly.items():
        highway_dir = os.path.join(
            RESULTS_DIR,
            f"highway_{highway}",
        )
        os.makedirs(highway_dir, exist_ok=True)
        for district, hours in districts.items():
            # Get all speed bins that occur for this highway/district
            speed_bins = sorted(
                {speed_bin for hour_data in hours.values() for speed_bin in hour_data}
            )

            # Remove invalid/zero speed bins
            speed_bins = [speed_bin for speed_bin in speed_bins if speed_bin > 0]
            if not speed_bins:
                continue
            # Create table data
            table_data = []
            for hour in range(24):
                row = []
                for speed_bin in speed_bins:
                    raw_vmt = hours[hour][speed_bin]
                    # Percentage of total VMT for this
                    # highway/district
                    fraction = (
                        raw_vmt / total_vmt[highway][district]
                        if total_vmt[highway][district]
                        else 0
                    )
                    row.append(fraction * 100)
                table_data.append(row)
            # Calculate total percentage for each speed bin
            total_row = []

            for speed_bin in speed_bins:
                speed_bin_vmt = sum(hours[hour][speed_bin] for hour in range(24))
                fraction = (
                    speed_bin_vmt / total_vmt[highway][district]
                    if total_vmt[highway][district]
                    else 0
                )
                total_row.append(fraction * 100)

            # Add total row
            table_data.append(total_row)
            # Find maximum percentage for color scaling
            max_value = max(max(row) for row in table_data)
            if max_value == 0:
                max_value = 1
            # Green -> yellow -> red
            cmap = plt.cm.RdYlGn_r
            norm = mcolors.Normalize(
                vmin=0,
                vmax=max_value,
            )
            # Create figure
            fig_width = max(10, len(speed_bins) * 0.8)
            fig, ax = plt.subplots(figsize=(fig_width, 9))
            ax.axis("off")

            # Create row labels
            row_labels = [f"{hour}:00" for hour in range(24)]
            row_labels.append("Total %VMT")

            # Create column labels
            column_labels = [f"{speed_bin} mph" for speed_bin in speed_bins]

            # Create table
            table = ax.table(
                cellText=[[f"{value:.2f}%" for value in row] for row in table_data],
                rowLabels=row_labels,
                colLabels=column_labels,
                cellLoc="center",
                rowLoc="center",
                loc="center",
            )

            # Font size
            table.auto_set_font_size(False)
            table.set_fontsize(9)

            # Scale table
            table.scale(
                1,
                1.5,
            )

            # Color data cells
            for row in range(len(table_data)):
                for col in range(len(speed_bins)):
                    value = table_data[row][col]
                    cell = table.get_celld()[(row + 1, col)]
                    cell.set_facecolor(cmap(norm(value)))
                    # Use white text for high values
                    if value > max_value * 0.6:
                        cell.get_text().set_color("white")
                    else:
                        cell.get_text().set_color("black")

            # Make the total row slightly more prominent
            total_row_index = len(table_data)

            for col in range(len(speed_bins)):
                cell = table.get_celld()[(total_row_index, col)]
                cell.set_text_props(weight="bold")

            # Make the row labels readable
            for row in range(len(table_data)):
                cell = table.get_celld()[(row + 1, -1)]
                cell.set_text_props(weight="bold")

            # Make column headers bold
            for col in range(len(speed_bins)):
                cell = table.get_celld()[(0, col)]
                cell.set_text_props(weight="bold")

            # Title
            ax.set_title(
                f"highway {highway} - District {district}\n" f"Hourly VMT by Speed Bin",
                fontsize=14,
                pad=20,
            )

            # Add colorbar
            sm = plt.cm.ScalarMappable(
                cmap=cmap,
                norm=norm,
            )

            sm.set_array([])

            cbar = fig.colorbar(
                sm,
                ax=ax,
                fraction=0.025,
                pad=0.02,
            )

            cbar.set_label(
                "% of Total VMT",
                rotation=270,
                labelpad=15,
            )

            # Save
            output_path = os.path.join(
                highway_dir,
                f"CA{highway}_D_{district}_VMT_table.png",
            )

            plt.savefig(
                output_path,
                dpi=300,
                bbox_inches="tight",
            )

            plt.close(fig)
