"""
Yes Energy API Extractor
========================
Fetches DA LMP and RT LMP hourly data from Yes Energy's DataSignals API.

Authentication: HTTP Basic Auth (username:password)

Uses the /timeseries/multiple.csv bulk endpoint to fetch up to 75 nodes
per request, dramatically reducing API calls compared to per-node fetching.
"""

import os
import time
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Optional

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.utils.logger import setup_logger

logger = setup_logger("yes_energy")

# Maximum items per bulk request (Yes Energy limit)
BATCH_SIZE = 75


class YesEnergyClient:
    """Client for Yes Energy DataSignals REST API."""

    BASE_URL = "https://services.yesenergy.com/PS/rest"

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        load_dotenv()
        self.username = username or os.getenv("YES_ENERGY_USERNAME")
        self.password = password or os.getenv("YES_ENERGY_PASSWORD")

        if not all([self.username, self.password]):
            missing = []
            if not self.username:
                missing.append("YES_ENERGY_USERNAME")
            if not self.password:
                missing.append("YES_ENERGY_PASSWORD")
            raise ValueError(
                f"Yes Energy credentials required. Missing: {', '.join(missing)}. "
                "Copy .env.template to .env and fill in your credentials:\n"
                "  cp .env.template .env"
            )

        self.auth = HTTPBasicAuth(self.username, self.password)
        self.session = requests.Session()
        self.session.auth = self.auth

    # --------------------------------------------------------- internal
    def _request(self, url: str, params: Optional[dict] = None) -> requests.Response:
        """Make an authenticated GET request with retry logic."""
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=120)
                resp.raise_for_status()
                return resp
            except requests.exceptions.HTTPError as e:
                if resp.status_code == 429:  # Rate limit
                    wait = min(30, 5 * attempt)
                    logger.warning(f"Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                elif resp.status_code == 401:
                    raise RuntimeError(
                        "Yes Energy authentication failed. Check credentials."
                    )
                else:
                    logger.error(f"HTTP {resp.status_code} for {url}")
                    if attempt == max_retries:
                        raise
                    time.sleep(2 * attempt)
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error (attempt {attempt}): {e}")
                if attempt == max_retries:
                    raise
                time.sleep(5 * attempt)

    # ----------------------------------------------------------------
    # BULK FETCH: /timeseries/multiple.csv (up to 75 items per call)
    # ----------------------------------------------------------------
    def _fetch_bulk_lmp(
        self,
        nodes: List[str],
        start_date: str,
        end_date: str,
        data_type: str = "DALMP",
    ) -> pd.DataFrame:
        """
        Fetch hourly LMP for multiple nodes using the bulk CSV endpoint.

        Args:
            nodes: List of settlement point names (max 75 per call).
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            data_type: "DALMP" or "RTLMP"

        Returns:
            DataFrame with columns: [node, datetime, date, hour, lmp]
        """
        items = ",".join([f"{data_type}:{n}" for n in nodes])
        url = f"{self.BASE_URL}/timeseries/multiple.csv"
        params = {
            "items": items,
            "startdate": start_date,
            "enddate": end_date,
            "agglevel": "hour",
        }

        resp = self._request(url, params)
        df = pd.read_csv(StringIO(resp.text))

        # Check for error response
        if "error" in df.columns:
            logger.error(f"Yes Energy bulk API error: {df['error'].iloc[0]}")
            return pd.DataFrame()

        if df.empty:
            return pd.DataFrame()

        # Identify metadata vs value columns
        meta_cols = {"DATETIME", "HOURENDING", "MARKETDAY", "PEAKTYPE", "MONTH", "YEAR"}
        value_cols = [c for c in df.columns if c not in meta_cols]

        if not value_cols:
            return pd.DataFrame()

        # Melt wide format → long format: one row per (node, hour)
        id_cols = [c for c in ["DATETIME", "HOURENDING"] if c in df.columns]
        melted = df.melt(
            id_vars=id_cols,
            value_vars=value_cols,
            var_name="node_raw",
            value_name="lmp",
        )

        # Parse node name: "ADL_RN (DALMP)" → "ADL_RN"
        melted["node"] = melted["node_raw"].str.replace(r"\s*\(.*\)", "", regex=True)
        melted["lmp"] = pd.to_numeric(melted["lmp"], errors="coerce")

        if "DATETIME" in melted.columns:
            melted["datetime"] = pd.to_datetime(melted["DATETIME"])
            melted["date"] = melted["datetime"].dt.strftime("%Y-%m-%d")
        if "HOURENDING" in melted.columns:
            melted["hour"] = pd.to_numeric(melted["HOURENDING"], errors="coerce").astype("Int64")

        # Drop helper columns
        melted = melted.drop(columns=["node_raw", "DATETIME", "HOURENDING"], errors="ignore")
        # Drop rows with NaN LMP (node not found in Yes Energy)
        melted = melted.dropna(subset=["lmp"])

        return melted

    def get_lmp_data(
        self,
        nodes: List[str],
        start_date: str,
        end_date: str,
        data_type: str = "DALMP",
    ) -> pd.DataFrame:
        """
        Fetch hourly LMP data for multiple nodes in batches of 75.

        Args:
            nodes: List of settlement point names
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            data_type: "DALMP" or "RTLMP"

        Returns:
            DataFrame with columns: [node, datetime, date, hour, lmp]
        """
        all_dfs = []
        total_batches = (len(nodes) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, len(nodes), BATCH_SIZE):
            batch = nodes[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            logger.info(
                f"Fetching {data_type} batch {batch_num}/{total_batches} "
                f"({len(batch)} nodes)..."
            )

            try:
                df = self._fetch_bulk_lmp(batch, start_date, end_date, data_type)
                if not df.empty:
                    all_dfs.append(df)
                    logger.info(f"  Got {len(df)} rows for {df['node'].nunique()} nodes")
                else:
                    logger.warning(f"  Batch {batch_num} returned empty")
            except Exception as e:
                logger.error(f"  Batch {batch_num} failed: {e}")
                # Fallback: try nodes individually for this batch
                logger.info("  Falling back to per-node fetching...")
                for node in batch:
                    try:
                        single_df = self._fetch_bulk_lmp([node], start_date, end_date, data_type)
                        if not single_df.empty:
                            all_dfs.append(single_df)
                    except Exception:
                        logger.warning(f"  Skipping node {node}")
                    time.sleep(0.5)

            if batch_num < total_batches:
                time.sleep(1)  # Rate limit between batches

        if not all_dfs:
            logger.warning(f"No {data_type} data fetched for any node.")
            return pd.DataFrame()

        result = pd.concat(all_dfs, ignore_index=True)
        logger.info(
            f"Total {data_type}: {len(result)} records across {result['node'].nunique()} nodes"
        )
        return result

    # ----------------------------------------------------------------
    # Convenience methods
    # ----------------------------------------------------------------
    def get_da_lmp(
        self,
        nodes: List[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Fetch Day-Ahead LMP hourly data for nodes."""
        return self.get_lmp_data(nodes, start_date, end_date, data_type="DALMP")

    def get_rt_lmp(
        self,
        nodes: List[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Fetch Real-Time LMP hourly data for nodes."""
        return self.get_lmp_data(nodes, start_date, end_date, data_type="RTLMP")


if __name__ == "__main__":
    client = YesEnergyClient()
    target = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    print(f"Target date: {target}")

    test_nodes = ["ADL_RN", "AE_RN", "ALVIN_RN"]
    da = client.get_da_lmp(test_nodes, target, target)
    print(f"\nDA LMP shape: {da.shape}")
    if not da.empty:
        print(da.head())
