from setup import *
from vmt_processing import *
from plots import *
import time

USE_MAINLINE = True
THRESHOLDS = [65, 70, 75, 80, 85, 90]

if __name__ == "__main__":
    start_time = time.time()
    station_data = {}
    lane_type = MAINLINE if USE_MAINLINE else OFF_RAMP
    setup(station_data, lane_type)

    # Process data
    (
        bins,
        vmt_hourly,
        total_vmt,
        vmt_above,
        vmt_above_limit,
        vmt_above_limit_5,
        vmt_above_limit_10,
        total_vmt_valid_speed_limit,
    ) = calculate_vmt(station_data, THRESHOLDS)

    # Save data
    save_speed_bins(bins)
    save_vmt_hourly(vmt_hourly)
    save_above_speeds(
        THRESHOLDS,
        vmt_above,
        total_vmt,
        vmt_above_limit,
        vmt_above_limit_5,
        vmt_above_limit_10,
        total_vmt_valid_speed_limit,
    )

    # Plot data
    plot_speed_bins(bins, lane_type)
    plot_vmt_hourly(vmt_hourly, lane_type)
    plot_california_speed_map(station_data)
    
    time_elapsed = time.time() - start_time
    print(f"Finished in {time_elapsed} seconds.")
