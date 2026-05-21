"""
ERCOT API Fetcher – Download 60-day disclosure ESR data from ERCOT Public API.
Post-RTC+B (2025-12-05+), ESR data is in separate files within the disclosure ZIPs.

Requires:
    ERCOT_API_USERNAME, ERCOT_API_PASSWORD, ERCOT_API_SUBSCRIPTION_KEY in .env
"""
import os
import io
import hashlib
import logging
import time
from datetime import date, timedelta
from zipfile import ZipFile

import pandas as pd
import requests
from config import DATA_CACHE_DIR

logger = logging.getLogger(__name__)

# ── Rate Limiting & Retry Configuration ──
REQUEST_DELAY_SEC = 3.0       # Delay between API requests (throttle)
MAX_RETRIES = 5               # Max retries for 429/500 errors
INITIAL_BACKOFF_SEC = 30      # Initial backoff for exponential retry (quota resets slowly)
MAX_BACKOFF_SEC = 300         # Max backoff cap (5 min)

# ── ERCOT API Configuration ──
ERCOT_API_BASE = "https://api.ercot.com/api/public-reports"
ERCOT_AUTH_URL = "https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token"

# 60-Day Disclosure product IDs & endpoints
SCED_DISCLOSURE_ENDPOINT = "/np3-965-er/60_sced_smne_gen_res"  # any NP3-965-ER endpoint triggers ZIP
DAM_DISCLOSURE_ENDPOINT = "/np3-966-er/60_dam_gen_res_as_offers"  # any NP3-966-ER endpoint triggers ZIP

# ESR file name patterns in disclosure ZIPs (case-insensitive matching)
# Verified against actual ZIP contents downloaded 2026-03-13
ESR_FILE_PATTERNS = {
    # SCED disclosure (NP3-965-ER)
    "sced_esr": "60d_ESR_Data_in_SCED",                     # 198 cols, 5-min ESR base point/output/SOC/AS
    "sced_resource_as_offers": "60d_SCED_Resource_AS_OFFERS", # RT AS offer curves
    "sced_gen_resource": "60d_SCED_Gen_Resource_Data",        # 207 cols, general gen (no ESR post-RTC+B)
    "sced_smne": "60d_SCED_SMNE_GEN_RES",                    # telemetered net output
    # DAM disclosure (NP3-966-ER)
    "dam_esr": "60d_DAM_ESR_Data",                            # 48 cols, DA ESR awards/HSL/AS
    "dam_esr_as_offers": "60d_DAM_ESR_ASOffers",              # 61 cols, DA ESR AS offer curves
    "dam_energy_only_awards": "60d_DAM_EnergyOnlyOfferAwards", # 7 cols, DA energy awards all resources
    "dam_energy_only_offers": "60d_DAM_EnergyOnlyOffers",     # DA energy offer curves
    "dam_gen_resource": "60d_DAM_Gen_Resource_Data",          # general gen (no ESR post-RTC+B)
    "dam_gen_as_offers": "60d_DAM_Generation_Resource_ASOffers",
}


def _deduplicate_sced_frames(frames: list) -> list:
    """
    Remove duplicate SCED frames that contain identical data for different operating dates.

    ERCOT occasionally publishes the same SCED ZIP for two consecutive API dates,
    producing identical SCED data assigned to two different _operating_date values.
    _operating_date is now the delivery date (API param + 1 day), and SCED timestamps
    should match the _operating_date directly.

    Strategy: compute a content fingerprint (hash of first few rows) per frame.
    When duplicates are found, keep the frame whose _operating_date matches
    the actual SCED timestamp date.
    """
    import hashlib as _hl
    from datetime import timedelta as _td

    if len(frames) < 2:
        return frames

    # Group frames by content fingerprint
    fingerprints = {}
    for i, frame in enumerate(frames):
        # Use a sample of data to compute fingerprint (fast for large frames)
        ts_col = None
        for c in frame.columns:
            if "time" in c.lower() or "stamp" in c.lower():
                ts_col = c
                break
        # Hash based on shape + first/last few values of timestamp + numeric cols
        sample = frame.head(20).to_csv(index=False, columns=[c for c in frame.columns if c != "_operating_date"])
        fp = _hl.md5(sample.encode()).hexdigest()

        if fp not in fingerprints:
            fingerprints[fp] = []
        fingerprints[fp].append(i)

    # For each group of duplicates, pick the best frame
    keep_indices = set()
    for fp, indices in fingerprints.items():
        if len(indices) == 1:
            keep_indices.add(indices[0])
            continue

        # Multiple frames with same content — pick the one whose _operating_date
        # matches the SCED timestamp date (since _operating_date = delivery date)
        best = None
        for idx in indices:
            frame = frames[idx]
            opd_str = frame["_operating_date"].iloc[0]
            opd = date.fromisoformat(opd_str)

            # Check if SCED timestamps match _operating_date (delivery date)
            ts_col = None
            for c in frame.columns:
                if "time" in c.lower() or "stamp" in c.lower():
                    ts_col = c
                    break
            if ts_col:
                try:
                    ts_dates = pd.to_datetime(frame[ts_col]).dt.date.unique()
                    if opd in ts_dates:
                        best = idx
                        break
                except Exception:
                    pass

        if best is not None:
            keep_indices.add(best)
            logger.info(
                f"SCED dedup: kept op_date={frames[best]['_operating_date'].iloc[0]}, "
                f"dropped {[frames[i]['_operating_date'].iloc[0] for i in indices if i != best]}"
            )
        else:
            # Can't determine — keep the first one
            keep_indices.add(indices[0])
            logger.warning(
                f"SCED dedup: no delivery-date match, keeping first op_date="
                f"{frames[indices[0]]['_operating_date'].iloc[0]}"
            )

    return [frames[i] for i in sorted(keep_indices)]


class ErcotApiFetcher:
    """Fetches ESR data from ERCOT's public API."""

    def __init__(
        self,
        username: str = None,
        password: str = None,
        subscription_key: str = None,
    ):
        self.username = username or os.getenv("ERCOT_USERNAME")
        self.password = password or os.getenv("ERCOT_PASSWORD")
        self.subscription_key = subscription_key or os.getenv("ERCOT_SUBSCRIPTION_KEY")
        self._token = None

        if not all([self.username, self.password, self.subscription_key]):
            raise ValueError(
                "ERCOT API credentials required. Set ERCOT_API_USERNAME, "
                "ERCOT_API_PASSWORD, ERCOT_API_SUBSCRIPTION_KEY in .env"
            )

    def _authenticate(self) -> str:
        """Get Bearer token from ERCOT B2C authentication."""
        if self._token:
            return self._token

        payload = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "response_type": "id_token",
            "scope": "openid fec253ea-0d06-4272-a5e6-b478baeecd70 offline_access",
            "client_id": "fec253ea-0d06-4272-a5e6-b478baeecd70",  # ERCOT public client ID
        }

        resp = requests.post(ERCOT_AUTH_URL, data=payload)
        resp.raise_for_status()
        self._token = resp.json()["id_token"]
        return self._token

    def _get_headers(self) -> dict:
        token = self._authenticate()
        return {
            "Authorization": f"Bearer {token}",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
        }

    def _cache_path(self, key: str) -> str:
        os.makedirs(DATA_CACHE_DIR, exist_ok=True)
        h = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(DATA_CACHE_DIR, f"ercot_api_{h}.parquet")

    def _request_with_retry(
        self,
        method: str,
        url: str,
        description: str,
        **kwargs,
    ) -> requests.Response | None:
        """
        HTTP request with exponential backoff retry on 429/500/502/503/504.
        Adds throttle delay between requests to stay within quota.
        """
        backoff = INITIAL_BACKOFF_SEC
        last_error = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                # Throttle: wait between requests
                if attempt == 0:
                    time.sleep(REQUEST_DELAY_SEC)
                else:
                    logger.info(
                        f"Retry {attempt}/{MAX_RETRIES} for {description}, "
                        f"waiting {backoff:.0f}s..."
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF_SEC)
                    # Re-authenticate in case token expired
                    self._token = None
                    kwargs["headers"] = self._get_headers()

                resp = requests.request(method, url, **kwargs)

                if resp.status_code in (429, 500, 502, 503, 504):
                    last_error = f"{resp.status_code} {resp.reason}"
                    # Check Retry-After header
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        try:
                            backoff = max(float(retry_after), backoff)
                        except ValueError:
                            pass
                    logger.warning(
                        f"{description}: {last_error} (attempt {attempt + 1})"
                    )
                    continue

                resp.raise_for_status()
                return resp

            except requests.exceptions.RequestException as e:
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"{description}: {last_error} (attempt {attempt + 1})"
                    )
                    continue
                break

        logger.warning(f"All retries exhausted for {description}: {last_error}")
        return None

    def _download_disclosure_zip(
        self,
        product_id: str,
        operating_date: date,
    ) -> bytes | None:
        """
        Download a disclosure ZIP from ERCOT for a specific operating date.
        The 60-day disclosure becomes available 60 days after the operating date.
        Uses exponential backoff retry on rate limit / server errors.
        """
        report_date = operating_date + timedelta(days=60)
        headers = self._get_headers()

        # Step 1: List available archives
        url = f"{ERCOT_API_BASE}/archive/{product_id}"
        params = {
            "postDatetimeFrom": (report_date - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00"),
            "postDatetimeTo": (report_date + timedelta(days=1)).strftime("%Y-%m-%dT23:59:59"),
        }

        resp = self._request_with_retry(
            "GET", url,
            description=f"list {product_id} for {operating_date}",
            headers=headers, params=params, timeout=30,
        )
        if resp is None:
            return None

        try:
            data = resp.json()
        except Exception:
            logger.warning(f"Invalid JSON from {product_id} list for {operating_date}")
            return None

        # Step 2: Find and download the ZIP
        archives = data.get("archives", [])
        if not archives:
            logger.warning(f"No archives found for {product_id} on {report_date}")
            return None

        for archive in archives:
            doc_id = archive.get("docId")
            if doc_id:
                download_url = f"{ERCOT_API_BASE}/archive/{product_id}"
                resp = self._request_with_retry(
                    "GET", download_url,
                    description=f"download {product_id}/{doc_id}",
                    headers=headers,
                    params={"download": str(doc_id)},
                    timeout=300,
                )
                if resp is not None:
                    return resp.content

        return None

    def _download_via_endpoint(
        self,
        product_id: str,
        operating_date: date,
    ) -> bytes | None:
        """Alternative: use direct data endpoint to get CSV data."""
        headers = self._get_headers()

        if "np3-965" in product_id:
            endpoint = SCED_DISCLOSURE_ENDPOINT
        elif "np3-966" in product_id:
            endpoint = DAM_DISCLOSURE_ENDPOINT
        else:
            return None

        url = f"{ERCOT_API_BASE}{endpoint}"
        params = {
            "deliveryDateFrom": operating_date.strftime("%Y-%m-%d"),
            "deliveryDateTo": operating_date.strftime("%Y-%m-%d"),
        }

        resp = self._request_with_retry(
            "GET", url,
            description=f"endpoint {endpoint} for {operating_date}",
            headers=headers, params=params, timeout=120,
        )
        return resp.content if resp is not None else None

    def _extract_files_from_zip(
        self,
        zip_bytes: bytes,
        file_patterns: dict,
    ) -> dict[str, pd.DataFrame]:
        """Extract and parse CSVs from a disclosure ZIP matching given patterns."""
        result = {}
        try:
            zf = ZipFile(io.BytesIO(zip_bytes))
        except Exception:
            return result

        for key, pattern in file_patterns.items():
            pattern_lower = pattern.lower().replace(" ", "_")
            for fname in zf.namelist():
                fname_clean = fname.lower().replace(" ", "_")
                if pattern_lower in fname_clean:
                    try:
                        df = pd.read_csv(zf.open(fname))
                        result[key] = df
                        logger.info(f"Extracted {key}: {fname} ({len(df)} rows)")
                    except Exception as e:
                        logger.warning(f"Failed to parse {fname}: {e}")
                    break

        return result

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def fetch_sced_disclosure(
        self,
        operating_date: date,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch 60-day SCED disclosure for a specific operating date.
        Extracts ESR-specific and general SCED files.

        Returns dict with possible keys:
            'sced_esr', 'sced_as_offers', 'sced_gen_resource', 'sced_smne'
        """
        cache_key = f"sced_disclosure_{operating_date}"
        cache_file = self._cache_path(cache_key)

        # Check cache
        if os.path.exists(cache_file):
            cached = pd.read_parquet(cache_file)
            if not cached.empty:
                return {"sced_esr": cached}

        zip_bytes = self._download_disclosure_zip("NP3-965-ER", operating_date)
        if not zip_bytes:
            return {}

        # Only extract ESR-specific file (skip massive gen resource / AS offers files)
        sced_patterns = {"sced_esr": ESR_FILE_PATTERNS["sced_esr"]}
        result = self._extract_files_from_zip(zip_bytes, sced_patterns)

        # Cache the ESR data
        if "sced_esr" in result:
            result["sced_esr"].to_parquet(cache_file, index=False)

        return result

    def fetch_dam_disclosure(
        self,
        operating_date: date,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch 60-day DAM disclosure for a specific operating date.
        Extracts ESR-specific DAM files.

        Returns dict with possible keys:
            'dam_esr', 'dam_esr_as_offers', 'dam_gen_resource', etc.
        """
        cache_key = f"dam_disclosure_{operating_date}"
        cache_file = self._cache_path(cache_key)

        if os.path.exists(cache_file):
            cached = pd.read_parquet(cache_file)
            if not cached.empty:
                return {"dam_esr": cached}

        zip_bytes = self._download_disclosure_zip("NP3-966-ER", operating_date)
        if not zip_bytes:
            return {}

        # Only extract ESR-specific and energy awards files
        dam_patterns = {
            "dam_esr": ESR_FILE_PATTERNS["dam_esr"],
            "dam_esr_as_offers": ESR_FILE_PATTERNS["dam_esr_as_offers"],
            "dam_energy_only_awards": ESR_FILE_PATTERNS["dam_energy_only_awards"],
        }
        result = self._extract_files_from_zip(zip_bytes, dam_patterns)

        if "dam_esr" in result:
            result["dam_esr"].to_parquet(cache_file, index=False)

        return result

    def fetch_esr_disclosure(
        self,
        start: date,
        end: date,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch all ESR disclosure data for a date range.
        Downloads both DAM and SCED disclosures and concatenates.

        Returns dict:
            'dam_esr':       DAM ESR data
            'dam_esr_as':    DAM ESR AS offers
            'sced_esr':      SCED ESR data (base point, output, SOC, etc.)
            'sced_as_offers': SCED AS offers
        """
        dam_frames = {"dam_esr": [], "dam_esr_as_offers": []}
        sced_frames = {"sced_esr": [], "sced_as_offers": []}

        total_days = (end - start).days + 1
        d = start
        day_num = 0
        while d <= end:
            day_num += 1
            # ERCOT disclosure API param `d` returns data for delivery date d+1.
            # e.g., API date=2026-01-01 → DAM Delivery Date=01/02/2026.
            # Use delivery date as _operating_date (the actual day energy flows).
            delivery_date = d + timedelta(days=1)
            logger.info(f"[{day_num}/{total_days}] Fetching ERCOT disclosure for {d} (delivery {delivery_date})...")

            # DAM
            try:
                dam = self.fetch_dam_disclosure(d)
                for key in dam_frames:
                    if key in dam and not dam[key].empty:
                        frame = dam[key].copy()
                        frame["_operating_date"] = delivery_date.isoformat()
                        dam_frames[key].append(frame)
            except Exception as e:
                logger.warning(f"DAM fetch failed for {d}: {e}")

            # SCED
            try:
                sced = self.fetch_sced_disclosure(d)
                for key in sced_frames:
                    if key in sced and not sced[key].empty:
                        frame = sced[key].copy()
                        frame["_operating_date"] = delivery_date.isoformat()
                        sced_frames[key].append(frame)
            except Exception as e:
                logger.warning(f"SCED fetch failed for {d}: {e}")

            d += timedelta(days=1)

        # Deduplicate SCED frames: ERCOT sometimes publishes identical SCED ZIPs
        # for consecutive operating dates (e.g., Jan 3 and Jan 4 both contain Jan 4
        # timestamped data). When this happens, assign to the operating date that
        # matches the normal convention (SCED timestamp date = operating_date + 1).
        for key in list(sced_frames.keys()):
            frames = sced_frames[key]
            if len(frames) < 2:
                continue
            deduped = _deduplicate_sced_frames(frames)
            sced_frames[key] = deduped

        result = {}
        for key, frames in {**dam_frames, **sced_frames}.items():
            if frames:
                result[key] = pd.concat(frames, ignore_index=True)
            else:
                result[key] = pd.DataFrame()

        return result
