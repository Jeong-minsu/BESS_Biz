"""
Smoke test: list_objects_v2 on prefix 'ercot/' returns expected top-level categories.
Requires live S3 credentials in .env.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "ingestion"))
from _datalake_client import get_s3_client, BUCKET

EXPECTED_PREFIXES = {
    "ercot/ace/",
    "ercot/ancillary/",
    "ercot/flow/",
    "ercot/ftr/",
    "ercot/gen/",
    "ercot/load/",
    "ercot/metadata/",
    "ercot/prices/",
    "ercot/transmission/",
    "ercot/vintage/",
    "ercot/weather/",
}


def test_list_ercot_prefixes():
    client = get_s3_client()
    resp = client.list_objects_v2(
        Bucket=BUCKET, Prefix="ercot/", Delimiter="/", MaxKeys=50
    )
    found = {p["Prefix"] for p in resp.get("CommonPrefixes", [])}
    missing = EXPECTED_PREFIXES - found
    assert not missing, f"Expected prefixes not found: {missing}\nFound: {found}"
    print(f"PASS: found {len(found)} top-level prefixes under ercot/")
    print("Prefixes:", sorted(found))


if __name__ == "__main__":
    test_list_ercot_prefixes()
    print("All smoke tests passed.")
