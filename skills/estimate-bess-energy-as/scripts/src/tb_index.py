"""
TB Index Calculator -- Theoretical Best revenue index for BESS nodes.
TB{n} = Top n consecutive hour RT LMP prices - Bottom n consecutive hour RT LMP prices
Constraint: charging (bottom hours) must occur before discharging (top hours).
One day, one cycle assumption.

Supports fractional duration via linear interpolation:
    TB(d) = TB_floor * (1 - frac) + TB_ceil * frac
    e.g. TB(1.5h) = TB1 * 0.5 + TB2 * 0.5
"""
import math
import pandas as pd
import numpy as np


def _best_consecutive_sum(prices: np.ndarray, n: int, mode: str) -> tuple[float, int]:
    """
    Find the best n consecutive hours for charging or discharging.
    mode: 'max' for discharge (top prices), 'min' for charge (bottom prices)
    Returns (sum_of_prices, start_index)
    """
    if len(prices) < n:
        return (0.0, 0)

    best_sum = None
    best_idx = 0

    for i in range(len(prices) - n + 1):
        window_sum = prices[i : i + n].sum()
        if best_sum is None:
            best_sum = window_sum
            best_idx = i
        elif mode == "max" and window_sum > best_sum:
            best_sum = window_sum
            best_idx = i
        elif mode == "min" and window_sum < best_sum:
            best_sum = window_sum
            best_idx = i

    return (best_sum, best_idx)


def calculate_tb_index_single_day(hourly_rt_lmp: np.ndarray, n_hours: int) -> float:
    """
    Calculate TB index for a single day (integer hours).
    hourly_rt_lmp: array of 24 hourly RT LMP values
    n_hours: battery duration in integer hours (1, 2, 3, ...)

    Returns TB index in $/MWh for that day.
    Constraint: charge (bottom) hours must come before discharge (top) hours.
    """
    prices = np.array(hourly_rt_lmp, dtype=float)
    if n_hours <= 0 or len(prices) < 2 * n_hours:
        return 0.0

    best_tb = 0.0

    # Enumerate all possible charge windows, then find best discharge after
    for charge_start in range(len(prices) - 2 * n_hours + 1):
        charge_end = charge_start + n_hours
        charge_cost = prices[charge_start:charge_end].sum()

        # Discharge must start after charge ends
        discharge_prices = prices[charge_end:]
        if len(discharge_prices) < n_hours:
            continue

        discharge_sum, _ = _best_consecutive_sum(discharge_prices, n_hours, "max")
        tb = discharge_sum - charge_cost

        if tb > best_tb:
            best_tb = tb

    return best_tb


def calculate_tb_index_fractional(
    hourly_rt_lmp: np.ndarray,
    duration_hours: float,
) -> float:
    """
    Calculate TB index for fractional battery duration using linear interpolation.

    TB(d) = TB_floor * (1 - frac) + TB_ceil * frac

    Examples:
        TB(1.0) = TB1
        TB(1.5) = TB1 * 0.5 + TB2 * 0.5
        TB(2.3) = TB2 * 0.7 + TB3 * 0.3
        TB(0.35) = TB0 * 0.65 + TB1 * 0.35 = 0 + TB1 * 0.35

    For duration < 1h, TB0 = 0 (can't do a 0-hour cycle), so:
        TB(0.5) = TB1 * 0.5
    """
    if duration_hours <= 0:
        return 0.0

    prices = np.array(hourly_rt_lmp, dtype=float)

    n_floor = math.floor(duration_hours)
    n_ceil = math.ceil(duration_hours)
    frac = duration_hours - n_floor

    # Exact integer duration
    if frac < 1e-9:
        return calculate_tb_index_single_day(prices, n_floor)

    # TB for floor and ceil
    tb_floor = calculate_tb_index_single_day(prices, n_floor) if n_floor > 0 else 0.0
    tb_ceil = calculate_tb_index_single_day(prices, n_ceil)

    return tb_floor * (1 - frac) + tb_ceil * frac


def calculate_tb_index(
    rt_lmp_hourly: pd.DataFrame,
    n_hours: int,
    date_col: str = "date",
    price_col: str = "rt_lmp",
    hour_col: str = "hour",
) -> pd.DataFrame:
    """
    Calculate daily TB index for a set of dates.

    rt_lmp_hourly: DataFrame with [date, hour (0-23), rt_lmp]
    n_hours: battery duration (1, 2, or 3)

    Returns DataFrame with [date, tb_index]
    """
    results = []

    for d, group in rt_lmp_hourly.groupby(date_col):
        group = group.sort_values(hour_col)
        prices = group[price_col].values
        tb = calculate_tb_index_single_day(prices, n_hours)
        results.append({"date": d, f"tb{n_hours}_index": tb})

    return pd.DataFrame(results)


def calculate_tb_index_for_node(
    rt_lmp_hourly: pd.DataFrame,
    battery_hours: int,
) -> pd.DataFrame:
    """
    Convenience function: calculate TB index for a node's RT LMP data.

    rt_lmp_hourly should have columns: [date, hour, rt_lmp]
    battery_hours: 1, 2, or 3

    Returns DataFrame with [date, tb{n}_index]
    """
    return calculate_tb_index(
        rt_lmp_hourly,
        n_hours=battery_hours,
        date_col="date",
        price_col="rt_lmp",
        hour_col="hour",
    )


def calculate_optimization_rate(
    actual_revenue_per_mw: float,
    tb_index_per_mw: float,
) -> float:
    """
    Calculate optimization rate.
    optimization_rate = actual_revenue / tb_index * 100

    Both values should be in the same unit ($/MW/period).
    """
    if tb_index_per_mw <= 0:
        return 0.0
    return (actual_revenue_per_mw / tb_index_per_mw) * 100.0
