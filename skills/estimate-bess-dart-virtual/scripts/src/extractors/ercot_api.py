"""
ERCOT API Extractor
===================
Fetches BESS (ESR) data from NP3-966-ER (60-Day DAM Disclosure Reports)
via the ERCOT Public API archive endpoint.

Flow:
  1. Download archive ZIP for the target posting date
  2. Extract ESR_Data CSV → find BESS settlement point names + HSL
  3. Extract EnergyOnlyOfferAwards CSV → filter by BESS nodes (Short)
  4. Extract EnergyBidAwards CSV → filter by BESS nodes (Long)

Authentication: OAuth2 B2C ROPC flow → Bearer token + Subscription key
"""

import os
import io
import time
import zipfile
from datetime import datetime, timedelta
from typing import Optional, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.utils.logger import setup_logger

logger = setup_logger("ercot_api")


class ErcotAPIClient:
    """Client for ERCOT Public API (api.ercot.com)."""

    TOKEN_URL = (
        "https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/"
        "B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token"
    )
    BASE_URL = "https://api.ercot.com/api/public-reports"
    CLIENT_ID = "fec253ea-0d06-4272-a5e6-b478baeecd70"
    TOKEN_EXPIRY_SECONDS = 3500  # Refresh slightly before 1hr expiry

    # CSV file keywords within the NP3-966-ER archive ZIP
    ESR_DATA_KEYWORD = "ESR_Data"
    GEN_RES_DATA_KEYWORD = "Gen_Resource_Data"
    OFFER_AWARDS_KEYWORD = "EnergyOnlyOfferAwards"
    BID_AWARDS_KEYWORD = "EnergyBidAwards"

    # Resource types that identify BESS/ESS in Gen_Resource_Data (older archives)
    BESS_RESOURCE_TYPES = {"PWRSTR", "ESR", "BESS"}

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        subscription_key: Optional[str] = None,
    ):
        load_dotenv()
        self.username = username or os.getenv("ERCOT_USERNAME")
        self.password = password or os.getenv("ERCOT_PASSWORD")
        self.subscription_key = subscription_key or os.getenv("ERCOT_SUBSCRIPTION_KEY")

        if not all([self.username, self.password, self.subscription_key]):
            missing = []
            if not self.username:
                missing.append("ERCOT_USERNAME")
            if not self.password:
                missing.append("ERCOT_PASSWORD")
            if not self.subscription_key:
                missing.append("ERCOT_SUBSCRIPTION_KEY")
            raise ValueError(
                f"ERCOT credentials required. Missing: {', '.join(missing)}. "
                "Copy .env.template to .env and fill in your credentials:\n"
                "  cp .env.template .env"
            )

        self._token: Optional[str] = None
        self._token_time: Optional[datetime] = None
        self.session = requests.Session()
        # Cache: {posting_date_str: {file_keyword: DataFrame}}
        self._archive_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        # Cache: {delivery_date_str: posting_date_str or None}
        self._posting_date_cache: Dict[str, Optional[str]] = {}
        # Rate limiting
        self._last_request_time: Optional[float] = None
        self._min_request_interval: float = 1.5  # seconds between API calls

    # ------------------------------------------------------------------ auth
    def _authenticate(self) -> str:
        """Obtain an OAuth2 access token via ROPC flow."""
        logger.info("Authenticating with ERCOT B2C...")
        payload = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
            "scope": f"openid {self.CLIENT_ID} offline_access",
            "client_id": self.CLIENT_ID,
            "response_type": "id_token",
        }
        resp = requests.post(self.TOKEN_URL, data=payload, timeout=30)
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not token:
            raise RuntimeError(f"No access_token in response: {resp.json()}")
        self._token = token
        self._token_time = datetime.now()
        logger.info("ERCOT authentication successful.")
        return token

    @property
    def token(self) -> str:
        if (
            self._token is None
            or self._token_time is None
            or (datetime.now() - self._token_time).seconds > self.TOKEN_EXPIRY_SECONDS
        ):
            return self._authenticate()
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
        }

    def _api_get(self, url: str, params: dict = None, timeout: int = 60, max_retries: int = 5) -> requests.Response:
        """Rate-limited GET with exponential backoff retry on 429."""
        for attempt in range(max_retries):
            # Rate limiting: wait between requests
            if self._last_request_time is not None:
                elapsed = time.time() - self._last_request_time
                if elapsed < self._min_request_interval:
                    time.sleep(self._min_request_interval - elapsed)

            self._last_request_time = time.time()
            resp = self.session.get(url, headers=self._headers(), params=params, timeout=timeout)

            if resp.status_code == 429:
                wait = min(2 ** attempt * 3, 60)  # 3, 6, 12, 24, 48 seconds
                logger.warning(f"429 Too Many Requests — retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            return resp

        # Final attempt failed
        resp.raise_for_status()
        return resp

    # ------------------------------------------------- archive ZIP download
    def _download_archive_csvs(
        self,
        posting_date: str,
        keywords: List[str],
    ) -> Dict[str, pd.DataFrame]:
        """
        Download NP3-966-ER archive ZIP and extract CSVs matching keywords.

        Args:
            posting_date: Date the report was posted (YYYY-MM-DD).
            keywords: List of file keywords to extract (e.g. ["ESR_Data", "EnergyOnlyOfferAwards"]).

        Returns:
            Dict mapping keyword → DataFrame for each matched CSV.
        """
        # Check cache first
        if posting_date in self._archive_cache:
            cached = self._archive_cache[posting_date]
            if all(k in cached for k in keywords):
                logger.info(f"Using cached archive data for {posting_date}")
                return {k: cached[k] for k in keywords}

        url = f"{self.BASE_URL}/archive/np3-966-er"
        params = {
            "postDatetimeFrom": f"{posting_date}T00:00:00",
            "postDatetimeTo": f"{posting_date}T23:59:59",
        }
        logger.info(f"Fetching archive listing for posting date {posting_date}...")
        resp = self._api_get(url, params=params, timeout=60)
        archives = resp.json().get("archives", resp.json().get("data", []))

        if not archives:
            logger.warning(f"No archives found for posting date {posting_date}")
            return {k: pd.DataFrame() for k in keywords}

        result: Dict[str, pd.DataFrame] = {}
        remaining_keywords = set(keywords)

        for archive in archives:
            if not remaining_keywords:
                break
            doc_id = archive.get("docId", archive.get("documentId", ""))
            download_url = f"{url}?download={doc_id}"
            logger.info(f"Downloading archive {doc_id}...")
            try:
                dl_resp = self._api_get(download_url, timeout=120)

                with zipfile.ZipFile(io.BytesIO(dl_resp.content)) as zf:
                    for fname in zf.namelist():
                        for keyword in list(remaining_keywords):
                            if keyword in fname and fname.endswith(".csv"):
                                logger.info(f"  Extracting {fname}")
                                with zf.open(fname) as f:
                                    df = pd.read_csv(f)
                                result[keyword] = df
                                remaining_keywords.discard(keyword)
                                break
            except Exception as e:
                logger.error(f"Failed to download/extract archive {doc_id}: {e}")
                continue

        # Fill missing keywords with empty DataFrames
        for k in keywords:
            if k not in result:
                result[k] = pd.DataFrame()

        # Update cache
        if posting_date not in self._archive_cache:
            self._archive_cache[posting_date] = {}
        self._archive_cache[posting_date].update(result)

        return result

    def _find_posting_date(self, delivery_date: str) -> Optional[str]:
        """
        Find the archive posting date for a given delivery date.

        The NP3-966-ER report is posted ~60 days after the delivery date.
        We calculate the expected posting date and search around it.
        For recent delivery dates (within ~60 days of today), we also
        search backwards from today as a fallback.

        Results are cached to avoid redundant API calls during backfill.
        """
        # Check cache first
        if delivery_date in self._posting_date_cache:
            cached = self._posting_date_cache[delivery_date]
            logger.info(f"Using cached posting date for {delivery_date}: {cached}")
            return cached

        delivery_dt = datetime.strptime(delivery_date, "%Y-%m-%d")
        today = datetime.now()

        # Strategy 1: Calculate expected posting date (delivery + 60 days)
        # and search around it (±14 days)
        expected_posting = delivery_dt + timedelta(days=60)

        # Don't search future dates
        if expected_posting > today:
            expected_posting = today

        search_dates = []
        # Search from expected posting date, then expand outward
        search_dates.append(expected_posting.strftime("%Y-%m-%d"))
        for offset in range(1, 15):
            for direction in [-1, 1]:
                candidate = expected_posting + timedelta(days=direction * offset)
                candidate_str = candidate.strftime("%Y-%m-%d")
                if candidate <= today and candidate_str not in search_dates:
                    search_dates.append(candidate_str)

        # Strategy 2: For recent dates, also try today backwards (original logic)
        for days_back in range(0, 10):
            candidate = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
            if candidate not in search_dates:
                search_dates.append(candidate)

        url = f"{self.BASE_URL}/archive/np3-966-er"
        for posting_date in search_dates:
            params = {
                "postDatetimeFrom": f"{posting_date}T00:00:00",
                "postDatetimeTo": f"{posting_date}T23:59:59",
            }
            try:
                resp = self._api_get(url, params=params, timeout=60)
                archives = resp.json().get("archives", resp.json().get("data", []))
                if archives:
                    logger.info(f"Found archive posted on {posting_date} for delivery date {delivery_date}")
                    self._posting_date_cache[delivery_date] = posting_date
                    return posting_date
            except Exception as e:
                logger.warning(f"Error checking posting date {posting_date}: {e}")
                continue

        logger.warning(f"No archive found for delivery date {delivery_date} (searched {len(search_dates)} posting dates)")
        self._posting_date_cache[delivery_date] = None
        return None

    # ------------------------------------------------------ public methods
    def get_esr_data(
        self, posting_date: str
    ) -> pd.DataFrame:
        """
        Get ESR (Energy Storage Resource) data from archive.
        This identifies BESS nodes and their HSL values.

        Tries ESR_Data first (modern archives), falls back to
        Gen_Resource_Data (legacy archives) if not found.

        Returns:
            DataFrame with ESR/BESS resource data.
        """
        csvs = self._download_archive_csvs(
            posting_date, [self.ESR_DATA_KEYWORD, self.GEN_RES_DATA_KEYWORD]
        )
        df = csvs[self.ESR_DATA_KEYWORD]

        if df.empty:
            df = csvs[self.GEN_RES_DATA_KEYWORD]
            if not df.empty:
                logger.info(f"Using Gen_Resource_Data fallback: {len(df)} rows")
            else:
                logger.warning("Neither ESR_Data nor Gen_Resource_Data found in archive.")
                return df

        sp_col = None
        for candidate in ["Settlement Point Name", "SettlementPointName", "Settlement Point"]:
            if candidate in df.columns:
                sp_col = candidate
                break

        if sp_col:
            logger.info(f"Resource data: {len(df)} rows, {df[sp_col].nunique()} unique settlement points")
        else:
            logger.info(f"Resource data: {len(df)} rows")
        return df

    def get_esr_nodes_and_hsl(
        self, posting_date: str, esr_df: Optional[pd.DataFrame] = None
    ) -> tuple:
        """
        Extract BESS settlement point names and HSL from ESR data.

        Handles both formats:
          - Modern: ESR_Data CSV (dedicated ESR file, all rows are BESS)
          - Legacy: Gen_Resource_Data CSV (mixed resource types, needs filtering)

        When the DataFrame contains a 'Resource Type' column, filters by
        BESS_RESOURCE_TYPES (PWRSTR, ESR, BESS) to exclude non-storage resources.

        Returns:
            Tuple of (node_list: List[str], hsl_df: DataFrame with columns [node, hsl])
        """
        df = esr_df if esr_df is not None else self.get_esr_data(posting_date)
        if df.empty:
            return [], pd.DataFrame(columns=["node", "hsl"])

        # --- Resource Type filtering (needed for Gen_Resource_Data fallback) ---
        rt_col = None
        for candidate in ["Resource Type", "ResourceType", "resource_type"]:
            if candidate in df.columns:
                rt_col = candidate
                break

        if rt_col:
            unique_types = df[rt_col].dropna().unique().tolist()
            logger.info(f"Resource types in data: {unique_types}")
            bess_mask = df[rt_col].str.upper().str.strip().isin(
                {rt.upper() for rt in self.BESS_RESOURCE_TYPES}
            )
            filtered = df[bess_mask]
            if filtered.empty:
                logger.warning(
                    f"No BESS resource types ({self.BESS_RESOURCE_TYPES}) found "
                    f"in '{rt_col}' column. Available types: {unique_types}"
                )
                return [], pd.DataFrame(columns=["node", "hsl"])
            logger.info(f"Filtered to BESS resources: {len(filtered)} rows (from {len(df)})")
            df = filtered

        # --- Find settlement point column ---
        sp_col = None
        for candidate in ["Settlement Point Name", "SettlementPointName",
                          "Settlement Point", "SettlementPoint"]:
            if candidate in df.columns:
                sp_col = candidate
                break
        if not sp_col:
            logger.error(f"No settlement point column found. Available: {list(df.columns)}")
            return [], pd.DataFrame(columns=["node", "hsl"])

        # --- Find HSL column ---
        hsl_col = None
        for candidate in ["HSL", "Hsl", "hsl"]:
            if candidate in df.columns:
                hsl_col = candidate
                break

        nodes = sorted(df[sp_col].dropna().unique().tolist())
        logger.info(f"BESS nodes: {len(nodes)} unique settlement points")

        # HSL: max across all hours per node
        if hsl_col:
            hsl_data = (
                df.groupby(sp_col)[hsl_col]
                .max()
                .reset_index()
                .rename(columns={sp_col: "node", hsl_col: "hsl"})
            )
            hsl_data["hsl"] = pd.to_numeric(hsl_data["hsl"], errors="coerce").fillna(0)
        else:
            logger.warning("No HSL column found — setting HSL to 0")
            hsl_data = pd.DataFrame({"node": nodes, "hsl": 0.0})

        hsl_data["node"] = hsl_data["node"].astype(str).str.strip()

        logger.info(f"HSL data: {len(hsl_data)} nodes")
        for _, row in hsl_data.iterrows():
            logger.debug(f"  {row['node']}: {row['hsl']:.1f} MW")

        return nodes, hsl_data

    def get_energy_only_offer_awards(
        self,
        posting_date: str,
        bess_nodes: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Get EnergyOnlyOfferAwards (Virtual Short) from archive.
        Optionally filter by BESS settlement point names.
        """
        csvs = self._download_archive_csvs(posting_date, [self.OFFER_AWARDS_KEYWORD])
        df = csvs[self.OFFER_AWARDS_KEYWORD]

        if df.empty:
            logger.warning("No EnergyOnlyOfferAwards found in archive.")
            return df

        logger.info(f"EnergyOnlyOfferAwards raw: {len(df)} rows")

        if bess_nodes:
            sp_col = next(
                (c for c in ["Settlement Point", "Settlement Point Name",
                             "SettlementPoint", "SettlementPointName"]
                 if c in df.columns),
                None,
            )
            if sp_col:
                df = df[df[sp_col].isin(bess_nodes)].copy()
                logger.info(f"EnergyOnlyOfferAwards after BESS filter: {len(df)} rows, {df[sp_col].nunique()} nodes")
            else:
                logger.warning(f"No settlement point column found in OfferAwards. Columns: {list(df.columns)}")

        return df

    def get_energy_bid_awards(
        self,
        posting_date: str,
        bess_nodes: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Get EnergyBidAwards (Virtual Long) from archive.
        Optionally filter by BESS settlement point names.
        """
        csvs = self._download_archive_csvs(posting_date, [self.BID_AWARDS_KEYWORD])
        df = csvs[self.BID_AWARDS_KEYWORD]

        if df.empty:
            logger.warning("No EnergyBidAwards found in archive.")
            return df

        logger.info(f"EnergyBidAwards raw: {len(df)} rows")

        if bess_nodes:
            sp_col = next(
                (c for c in ["Settlement Point", "Settlement Point Name",
                             "SettlementPoint", "SettlementPointName"]
                 if c in df.columns),
                None,
            )
            if sp_col:
                df = df[df[sp_col].isin(bess_nodes)].copy()
                logger.info(f"EnergyBidAwards after BESS filter: {len(df)} rows, {df[sp_col].nunique()} nodes")
            else:
                logger.warning(f"No settlement point column found in BidAwards. Columns: {list(df.columns)}")

        return df

    def fetch_all_bess_data(
        self, delivery_date: str
    ) -> dict:
        """
        Convenience method: fetch all BESS data for a delivery date.

        Steps:
          1. Find archive posting date for the delivery date
          2. Download ZIP and extract ESR_Data, EnergyOnlyOfferAwards, EnergyBidAwards
          3. Get BESS nodes from ESR_Data
          4. Filter offer/bid awards by BESS nodes

        Returns:
            Dict with keys: 'esr_data', 'nodes', 'hsl', 'offer_awards', 'bid_awards', 'posting_date'
        """
        posting_date = self._find_posting_date(delivery_date)
        if not posting_date:
            logger.error(f"Cannot find archive for delivery date {delivery_date}")
            return {
                "esr_data": pd.DataFrame(),
                "nodes": [],
                "hsl": pd.DataFrame(columns=["node", "hsl"]),
                "offer_awards": pd.DataFrame(),
                "bid_awards": pd.DataFrame(),
                "posting_date": None,
            }

        # Download all CSVs at once (single ZIP download)
        # Request both ESR_Data and Gen_Resource_Data to handle old + new archive formats
        all_keywords = [
            self.ESR_DATA_KEYWORD, self.GEN_RES_DATA_KEYWORD,
            self.OFFER_AWARDS_KEYWORD, self.BID_AWARDS_KEYWORD,
        ]
        csvs = self._download_archive_csvs(posting_date, all_keywords)

        # Try ESR_Data first (modern format), fall back to Gen_Resource_Data (legacy)
        esr_df = csvs[self.ESR_DATA_KEYWORD]
        if esr_df.empty:
            gen_df = csvs[self.GEN_RES_DATA_KEYWORD]
            if not gen_df.empty:
                logger.info(
                    "ESR_Data not found in archive — using Gen_Resource_Data fallback "
                    f"({len(gen_df)} rows, will filter by Resource Type)"
                )
                esr_df = gen_df
            else:
                logger.warning("Neither ESR_Data nor Gen_Resource_Data found in archive.")

        nodes, hsl_data = self.get_esr_nodes_and_hsl(posting_date, esr_df)

        if not nodes:
            logger.warning("No BESS nodes found in archive.")

        offer_awards = csvs[self.OFFER_AWARDS_KEYWORD]
        bid_awards = csvs[self.BID_AWARDS_KEYWORD]

        # Filter awards by BESS nodes (with fuzzy column matching)
        sp_candidates = [
            "Settlement Point", "Settlement Point Name",
            "SettlementPoint", "SettlementPointName",
        ]
        if nodes and not offer_awards.empty:
            sp_col = next((c for c in sp_candidates if c in offer_awards.columns), None)
            if sp_col:
                offer_awards = offer_awards[offer_awards[sp_col].isin(nodes)].copy()
                logger.info(f"EnergyOnlyOfferAwards after BESS filter: {len(offer_awards)} rows")
            else:
                logger.warning(f"No settlement point column found in OfferAwards. Columns: {list(offer_awards.columns)}")

        if nodes and not bid_awards.empty:
            sp_col = next((c for c in sp_candidates if c in bid_awards.columns), None)
            if sp_col:
                bid_awards = bid_awards[bid_awards[sp_col].isin(nodes)].copy()
                logger.info(f"EnergyBidAwards after BESS filter: {len(bid_awards)} rows")
            else:
                logger.warning(f"No settlement point column found in BidAwards. Columns: {list(bid_awards.columns)}")

        return {
            "esr_data": esr_df,
            "nodes": nodes,
            "hsl": hsl_data,
            "offer_awards": offer_awards,
            "bid_awards": bid_awards,
            "posting_date": posting_date,
        }


if __name__ == "__main__":
    # Quick test
    client = ErcotAPIClient()
    target = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    print(f"\nTarget delivery date: {target}")

    result = client.fetch_all_bess_data(target)
    print(f"\nPosting date: {result['posting_date']}")
    print(f"ESR nodes: {len(result['nodes'])}")
    print(f"HSL data: {result['hsl'].shape}")
    print(f"Offer Awards: {result['offer_awards'].shape}")
    print(f"Bid Awards: {result['bid_awards'].shape}")
