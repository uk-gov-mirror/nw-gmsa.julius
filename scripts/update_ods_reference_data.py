#!/usr/bin/env python3
"""
Refreshes the bundled NHS ODS reference data the stats screens use to work
out an organisation's ICS and NHS region — so the running app needs no
outbound internet access for it (FhirClient.ods_trusts()/icb_name() read
these files first, and only fall back to downloading if they're missing).

Writes, under data/ods/:
  - etr.csv         — ODS's "NHS Trusts" export, as downloaded
                      (FhirClient.ODS_TRUSTS_REPORT_URL)
  - icb_names.json  — {ICB ODS code: name} for every ICB code in etr.csv,
                      from the NHS ODS lookup API

Re-run when ICBs or trusts change (mergers, new trusts), then commit the
two files.

Usage:
    python3 scripts/update_ods_reference_data.py
"""
import argparse
import csv
import io
import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fhir_client import FhirClient  # noqa: E402


def main():
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()

    os.makedirs(FhirClient.ODS_REFERENCE_DATA_DIR, exist_ok=True)

    resp = requests.get(FhirClient.ODS_TRUSTS_REPORT_URL, timeout=60)
    resp.raise_for_status()
    rows = [r for r in csv.reader(io.StringIO(resp.text)) if len(r) >= 12 and r[0]]
    if not rows:
        print("Error: the ODS trust export came back empty — nothing written.", file=sys.stderr)
        return 1
    with open(FhirClient.ODS_TRUSTS_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(resp.text)
    print(f"Wrote {len(rows)} trusts to {FhirClient.ODS_TRUSTS_FILE}")

    icb_codes = sorted({r[3] for r in rows if r[3]})
    names, missing = {}, []
    for code in icb_codes:
        name, _ = FhirClient.ods_lookup(code)
        if name:
            names[code] = FhirClient._ods_name_case(name)
        else:
            missing.append(code)
    with open(FhirClient.ODS_ICB_NAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(names, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"Wrote {len(names)} ICB names to {FhirClient.ODS_ICB_NAMES_FILE}")
    if missing:
        print(f"Couldn't name {len(missing)} ICB code(s): {', '.join(missing)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
