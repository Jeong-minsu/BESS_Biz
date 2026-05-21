"""
DART Revenue Calculator
=======================
Merges ERCOT Award data with Yes Energy LMP data to compute
DART Revenue for BESS (PWRSTR) nodes.

Formulas:
  EnergyOnlyOffer Revenue (Virtual Short) = (DA_LMP - RT_LMP) × Offer_Award_MW
  EnergyBid Revenue (Virtual Long)        = (RT_LMP - DA_LMP) × Bid_Award_MW
  Net DART Revenue = Offer Revenue + Bid Revenue
"""

import os
import sys
from typing import Optional, Tuple

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.utils.logger import setup_logger

logger = setup_logger("dart_calc")


class DARTCalculator:
    """Calculate DART Revenue from Award + LMP data."""

    # Column name mappings to handle various formats from APIs
    NODE_COL_CANDIDATES = [
        "Settlement Point Name", "SettlementPoint", "Settlement Point",
        "SettlementPointName", "settlementPointName",
        "settlement_point", "settlementPoint",
        "Resource Name", "Load Resource Name", "ResourceName",
        "resourceName", "loadResourceName", "resource_name", "node",
    ]
    HOUR_COL_CANDIDATES = [
        "HourEnding", "hourEnding", "Hour Ending", "hour_ending", "hour",
        "HE", "Hour", "DeliveryHour", "Delivery Hour",
    ]
    # Interval columns that contain datetime strings (need special parsing)
    INTERVAL_COL_CANDIDATES = [
        "Interval End", "IntervalEnd", "Interval Start", "IntervalStart",
    ]
    OFFER_MW_COL_CANDIDATES = [
        "Energy Only Offer Award in MW",
        "Awarded Quantity", "awardedQuantity", "EnergyOnlyOfferAwardMW",
        "EnergyOnlyOffer Award MW", "EnergyOnlyOfferAward",
        "AwardedMW", "Awarded MW", "TotalAwardedMW", "award_mw", "AwardMW",
    ]
    BID_MW_COL_CANDIDATES = [
        "Energy Only Bid Award in MW",
        "Awarded Quantity", "EnergyBidAwardMW", "EnergyBid Award MW",
        "EnergyBidAward", "AwardedMW", "Awarded MW",
        "TotalAwardedMW", "award_mw", "AwardMW",
    ]
    DATE_COL_CANDIDATES = [
        "Delivery Date", "DeliveryDate", "deliveryDate", "delivery_date",
        "Date", "date", "TradeDate",
    ]

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: list) -> Optional[str]:
        """Find the first matching column name from candidates."""
        for col in candidates:
            if col in df.columns:
                return col
        return None

    def prepare_award_data(
        self,
        df: pd.DataFrame,
        award_type: str = "offer",
    ) -> pd.DataFrame:
        """
        Normalize ERCOT award data to standard column names.

        Returns DataFrame with: [node, date, hour, award_mw]
        """
        if df.empty:
            return pd.DataFrame(columns=["node", "date", "hour", "award_mw"])

        result = pd.DataFrame()

        # Find node column
        node_col = self._find_col(df, self.NODE_COL_CANDIDATES)
        if node_col:
            result["node"] = df[node_col].astype(str).str.strip()
        else:
            logger.error(f"No node column found. Available: {list(df.columns)}")
            return pd.DataFrame(columns=["node", "date", "hour", "award_mw"])

        # Find date column
        date_col = self._find_col(df, self.DATE_COL_CANDIDATES)
        if date_col:
            result["date"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")

        # Find hour column
        hour_col = self._find_col(df, self.HOUR_COL_CANDIDATES)
        if hour_col:
            result["hour"] = pd.to_numeric(df[hour_col], errors="coerce").astype("Int64")
        else:
            # Try interval datetime columns (ERCOT API returns Interval Start/End)
            interval_col = self._find_col(df, self.INTERVAL_COL_CANDIDATES)
            if interval_col:
                interval_dt = pd.to_datetime(df[interval_col], errors="coerce")
                if "End" in interval_col:
                    result["hour"] = interval_dt.dt.hour
                    result["hour"] = result["hour"].replace(0, 24).astype("Int64")
                else:
                    result["hour"] = (interval_dt.dt.hour + 1)
                    result["hour"] = result["hour"].replace(25, 1).astype("Int64")
                # Also extract date from interval if not already found
                if "date" not in result.columns:
                    if "End" in interval_col:
                        # For hour ending 24 (midnight), date is the previous day
                        result["date"] = interval_dt.dt.strftime("%Y-%m-%d")
                        mask_midnight = result["hour"] == 24
                        if mask_midnight.any():
                            result.loc[mask_midnight, "date"] = (
                                interval_dt[mask_midnight] - pd.Timedelta(days=1)
                            ).dt.strftime("%Y-%m-%d")
                    else:
                        result["date"] = interval_dt.dt.strftime("%Y-%m-%d")
                logger.info(f"Extracted hour from '{interval_col}' column")

        # Find award MW column
        mw_candidates = (
            self.OFFER_MW_COL_CANDIDATES
            if award_type == "offer"
            else self.BID_MW_COL_CANDIDATES
        )
        mw_col = self._find_col(df, mw_candidates)
        if mw_col:
            result["award_mw"] = pd.to_numeric(df[mw_col], errors="coerce").fillna(0)
        else:
            logger.error(f"No MW column found for {award_type}. Available: {list(df.columns)}")
            result["award_mw"] = 0

        # Group by node+hour in case of multiple entries
        if not result.empty and "hour" in result.columns:
            group_cols = ["node"]
            if "date" in result.columns:
                group_cols.append("date")
            group_cols.append("hour")
            result = result.groupby(group_cols, as_index=False)["award_mw"].sum()

        logger.info(
            f"Prepared {award_type} awards: {len(result)} rows, "
            f"{result['node'].nunique()} unique nodes"
        )
        return result

    def prepare_lmp_data(self, df: pd.DataFrame, lmp_type: str = "da") -> pd.DataFrame:
        """
        Normalize Yes Energy LMP data to standard column names.

        Returns DataFrame with: [node, date, hour, {da|rt}_lmp]
        """
        if df.empty:
            col_name = f"{lmp_type}_lmp"
            return pd.DataFrame(columns=["node", "date", "hour", col_name])

        result = pd.DataFrame()

        # Node
        if "node" in df.columns:
            result["node"] = df["node"].astype(str).str.strip()
        else:
            node_col = self._find_col(df, self.NODE_COL_CANDIDATES)
            if node_col:
                result["node"] = df[node_col].astype(str).str.strip()

        # Date and Hour from datetime
        if "datetime" in df.columns:
            dt = pd.to_datetime(df["datetime"])
            result["date"] = dt.dt.strftime("%Y-%m-%d")
            result["hour"] = dt.dt.hour + 1  # Convert to hour ending (1-24)
        else:
            if "date" in df.columns:
                result["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            if "hour" in df.columns:
                result["hour"] = pd.to_numeric(df["hour"], errors="coerce").astype("Int64")

        # LMP value
        col_name = f"{lmp_type}_lmp"
        if "lmp" in df.columns:
            result[col_name] = pd.to_numeric(df["lmp"], errors="coerce")
        elif col_name in df.columns:
            result[col_name] = pd.to_numeric(df[col_name], errors="coerce")
        elif f"{lmp_type.upper()}LMP" in df.columns:
            result[col_name] = pd.to_numeric(df[f"{lmp_type.upper()}LMP"], errors="coerce")

        return result

    def calculate_dart_revenue(
        self,
        offer_awards: pd.DataFrame,
        bid_awards: pd.DataFrame,
        da_lmp: pd.DataFrame,
        rt_lmp: pd.DataFrame,
        target_date: str,
        hsl_data: Optional[pd.DataFrame] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calculate DART Revenue for all PWRSTR nodes.

        Args:
            offer_awards: Raw EnergyOnlyOffer Award data from ERCOT
            bid_awards: Raw EnergyBid Award data from ERCOT
            da_lmp: Raw DA LMP data from Yes Energy
            rt_lmp: Raw RT LMP data from Yes Energy
            target_date: Date string (YYYY-MM-DD)
            hsl_data: Optional DataFrame with [node, hsl] for capacity info

        Returns:
            Tuple of (hourly_detail, daily_summary) DataFrames
        """
        logger.info(f"Calculating DART Revenue for {target_date}...")

        # Normalize all data
        offers = self.prepare_award_data(offer_awards, "offer")
        bids = self.prepare_award_data(bid_awards, "bid")
        da = self.prepare_lmp_data(da_lmp, "da")
        rt = self.prepare_lmp_data(rt_lmp, "rt")

        # Merge keys
        merge_keys = ["node", "hour"]
        if "date" in offers.columns:
            merge_keys = ["node", "date", "hour"]

        # --- EnergyOnlyOffer DART Revenue ---
        offer_merged = pd.DataFrame()
        if not offers.empty and not da.empty and not rt.empty:
            offer_lmp = pd.merge(da, rt, on=merge_keys, how="inner")
            offer_merged = pd.merge(
                offers.rename(columns={"award_mw": "offer_mw"}),
                offer_lmp,
                on=merge_keys,
                how="left",
            )
            # Virtual Short: (DA - RT) × MW
            offer_merged["offer_revenue"] = (
                (offer_merged["da_lmp"] - offer_merged["rt_lmp"])
                * offer_merged["offer_mw"]
            )
            logger.info(f"Offer revenue calculated: {len(offer_merged)} rows")

        # --- EnergyBid DART Revenue ---
        bid_merged = pd.DataFrame()
        if not bids.empty and not da.empty and not rt.empty:
            bid_lmp = pd.merge(da, rt, on=merge_keys, how="inner")
            bid_merged = pd.merge(
                bids.rename(columns={"award_mw": "bid_mw"}),
                bid_lmp,
                on=merge_keys,
                how="left",
            )
            # Virtual Long: (RT - DA) × MW
            bid_merged["bid_revenue"] = (
                (bid_merged["rt_lmp"] - bid_merged["da_lmp"])
                * bid_merged["bid_mw"]
            )
            logger.info(f"Bid revenue calculated: {len(bid_merged)} rows")

        # --- Combine into hourly detail ---
        if not offer_merged.empty and not bid_merged.empty:
            hourly = pd.merge(
                offer_merged,
                bid_merged[merge_keys + ["bid_mw", "bid_revenue"]],
                on=merge_keys,
                how="outer",
            )
        elif not offer_merged.empty:
            hourly = offer_merged.copy()
            hourly["bid_mw"] = 0
            hourly["bid_revenue"] = 0
        elif not bid_merged.empty:
            hourly = bid_merged.copy()
            hourly["offer_mw"] = 0
            hourly["offer_revenue"] = 0
        else:
            logger.warning("No data to calculate revenue.")
            return pd.DataFrame(), pd.DataFrame()

        # Fill NaN
        for col in ["offer_mw", "bid_mw", "offer_revenue", "bid_revenue", "da_lmp", "rt_lmp"]:
            if col in hourly.columns:
                hourly[col] = hourly[col].fillna(0)

        # Net revenue
        hourly["net_revenue"] = hourly["offer_revenue"] + hourly["bid_revenue"]
        hourly["dart_spread"] = hourly.get("da_lmp", 0) - hourly.get("rt_lmp", 0)

        # Ensure date column
        if "date" not in hourly.columns:
            hourly["date"] = target_date

        # --- Daily summary by node ---
        daily = (
            hourly.groupby(["node", "date"])
            .agg(
                total_offer_mw=("offer_mw", "sum"),
                total_bid_mw=("bid_mw", "sum"),
                offer_revenue=("offer_revenue", "sum"),
                bid_revenue=("bid_revenue", "sum"),
                net_revenue=("net_revenue", "sum"),
                avg_da_lmp=("da_lmp", "mean"),
                avg_rt_lmp=("rt_lmp", "mean"),
                avg_dart_spread=("dart_spread", "mean"),
                hours_positive=("net_revenue", lambda x: (x > 0).sum()),
                hours_negative=("net_revenue", lambda x: (x < 0).sum()),
                hours_participated=("net_revenue", lambda x: ((x != 0)).sum()),
                positive_revenue=("net_revenue", lambda x: x[x > 0].sum()),
                negative_revenue=("net_revenue", lambda x: x[x < 0].sum()),
            )
            .reset_index()
        )

        # --- Win Rate ---
        # = hours with positive revenue / total hours participated (where award > 0)
        daily["win_rate"] = daily.apply(
            lambda r: (
                round(r["hours_positive"] / r["hours_participated"] * 100, 1)
                if r["hours_participated"] > 0
                else 0.0
            ),
            axis=1,
        )

        # --- Profit/Loss Ratio (손익비) ---
        # = (avg revenue per winning hour) / |avg revenue per losing hour|
        daily["profit_loss_ratio"] = daily.apply(
            lambda r: (
                round(
                    (r["positive_revenue"] / r["hours_positive"])
                    / (abs(r["negative_revenue"]) / r["hours_negative"]),
                    2,
                )
                if r["hours_positive"] > 0 and r["hours_negative"] > 0
                else (99.99 if r["hours_positive"] > 0 else 0.0)
            ),
            axis=1,
        )

        # --- HSL & Participation Rate ---
        if hsl_data is not None and not hsl_data.empty:
            daily = daily.merge(hsl_data[["node", "hsl"]], on="node", how="left")
            daily["hsl"] = daily["hsl"].fillna(0)

            # Participation Rate = total awarded MW / (HSL × 24) × 100
            # total awarded = offer_mw + |bid_mw| (bid_mw is negative)
            daily["total_awarded_mw"] = daily["total_offer_mw"] + daily["total_bid_mw"].abs()
            daily["max_possible_mw"] = daily["hsl"] * 24
            daily["participation_rate"] = daily.apply(
                lambda r: (
                    round(r["total_awarded_mw"] / r["max_possible_mw"] * 100, 1)
                    if r["max_possible_mw"] > 0
                    else 0.0
                ),
                axis=1,
            )
        else:
            daily["hsl"] = 0
            daily["total_awarded_mw"] = daily["total_offer_mw"] + daily["total_bid_mw"].abs()
            daily["max_possible_mw"] = 0
            daily["participation_rate"] = 0.0
            logger.warning("No HSL data provided — participation rate set to 0")

        logger.info(
            f"Daily summary: {len(daily)} nodes, "
            f"Total Net Revenue: ${daily['net_revenue'].sum():,.2f}"
        )
        for _, row in daily.iterrows():
            logger.info(
                f"  {row['node']:<30s} Net: ${row['net_revenue']:>10,.2f}  "
                f"HSL: {row['hsl']:>6.0f}MW  "
                f"WinRate: {row['win_rate']:>5.1f}%  "
                f"Participation: {row['participation_rate']:>5.1f}%  "
                f"P/L Ratio: {row['profit_loss_ratio']:>5.2f}"
            )

        return hourly, daily
