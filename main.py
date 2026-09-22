from setup import *
from vmt_processing import *
from plots import *
import time

USE_MAINLINE = True
THRESHOLDS = [55, 65, 70, 75, 80, 85, 90]

if __name__ == "__main__":
    start_time = time.time()
    station_data = {}
    lane_type = MAINLINE if USE_MAINLINE else OFF_RAMP
    setup(station_data, lane_type)

    # Process data
    (
        speed_bins,
        vmt_hourly, # used for generating time-of-day vmt bins
        vmt_above_hourly,
        total_vmt,
        vmt_above, # vmt above thresholds (65, 70, 75mph, etc.)
        vmt_above_limit,
        vmt_above_limit_5,
        vmt_above_limit_10,
        total_vmt_valid_speed_limit, # filtered out station vmt with no valid speed limits
        speed_limit_coverage,
        vmt_speed_limit,
    ) = calculate_vmt(station_data, THRESHOLDS)

    # Save data
    # save_speed_bins(speed_bins)
    # save_vmt_hourly(vmt_hourly)
    # save_above_speeds(
    #     THRESHOLDS,
    #     vmt_above,
    #     total_vmt,
    #     vmt_above_limit,
    #     vmt_above_limit_5,
    #     vmt_above_limit_10,
    #     total_vmt_valid_speed_limit,
    #     speed_limit_coverage,
    # )

    # save_vmt_above_thresholds_hourly(
    #     vmt_hourly,
    #     vmt_above_hourly,
    #     THRESHOLDS,
    # )

    # Plot data
    # plot_speed_bins(vmt_speed_limit, lane_type)
    # plot_vmt_hourly(vmt_hourly, lane_type)
    # plot_speed_limit_coverage(station_data)
    plot_california_speed_map(station_data)
    
    time_elapsed = time.time() - start_time
    print(f"Finished in {time_elapsed} seconds.")
