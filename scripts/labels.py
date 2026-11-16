"""Import delayed labels locally; no label mutation endpoint is exposed publicly."""

import argparse
import csv
import os

from fraudline.pipeline import ROOT
from fraudline.store import Store

parser = argparse.ArgumentParser()
parser.add_argument("csv", help="CSV columns: prediction_id,is_fraud")
args = parser.parse_args()
store = Store(os.environ.get("DATABASE_URL", f"sqlite:///{ROOT / 'runtime/events.db'}"))
with open(args.csv, newline="") as stream:
    rows = list(csv.DictReader(stream))
for row in rows:
    store.add_label(row["prediction_id"], int(row["is_fraud"]))
print(f"Imported {len(rows)} delayed labels. Duplicate or unknown IDs are rejected.")
