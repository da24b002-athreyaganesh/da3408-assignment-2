"""Audit exactly ONE partition, chosen by this pod's Job completion index.

Kubernetes sets JOB_COMPLETION_INDEX automatically in an Indexed Job. The pod
and node names arrive via the Downward API. Results go to stdout, which is the
only channel the collector in Step 7 reads.
"""
import csv
import os
import re
import time

PART = int(os.environ["JOB_COMPLETION_INDEX"])
POD = os.environ.get("POD_NAME", "?")
NODE = os.environ.get("NODE_NAME", "?")
HOLD = float(os.environ.get("AUDIT_HOLD_SECONDS", "0"))

ADDRESS = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
REQUIRED = ("ref", "contact_email", "enrolled_on")

source = f"/data/signups_part_{PART}.csv"
print(f"[part {PART}] pod={POD} node={NODE} source={source}", flush=True)

rows = blank_required = bad_address = 0
with open(source, newline="") as fh:
    for record in csv.DictReader(fh):
        rows += 1
        if any(not (record.get(col) or "").strip() for col in REQUIRED):
            blank_required += 1
        elif not ADDRESS.match(record["contact_email"]):
            bad_address += 1

invalid = blank_required + bad_address

# Auditing a few hundred rows takes milliseconds. This pause keeps the pod
# alive long enough for the snapshot loop in Step 6 to observe it. It runs
# after every figure above is final and changes none of them.
if HOLD:
    time.sleep(HOLD)

print(f"[part {PART}] rows={rows} blank_required={blank_required} "
      f"bad_address={bad_address}", flush=True)
print(f"AUDIT part={PART} node={NODE} rows={rows} invalid={invalid}", flush=True)
