from setup import *
from vmt_processing import *
from plots import *


USE_MAINLINE = True

if __name__ == "__main__":
    station_data = {}
    lane_type = MAINLINE if USE_MAINLINE else OFF_RAMP
    setup(station_data, lane_type)
    thresholds = [65, 70, 75, 80, 85, 90]

    (
        bins,
        vmt_hourly,
        total_vmt,
        vmt_above,
        vmt_above_limit,
        vmt_above_limit_5,
        vmt_above_limit_10,
    ) = calculate_vmt(station_data, thresholds)

    save_speed_bins(bins)
    save_vmt_hourly(vmt_hourly)
    save_above_thresholds(
        thresholds,
        vmt_above,
        total_vmt,
    )

    save_above_speed_limit(
        vmt_above_limit,
        vmt_above_limit_5,
        vmt_above_limit_10,
        total_vmt,
    )

    plot_speed_bins(bins, lane_type)
    plot_vmt_hourly(vmt_hourly, lane_type)
    plot_california_speed_map(station_data)
