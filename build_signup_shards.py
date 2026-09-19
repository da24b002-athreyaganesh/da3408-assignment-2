"""Build 8 partitioned signup CSVs with a seeded, known number of bad rows.

Schema:
    ref            SGN-<partition>-<6 digits>     required
    contact_email  address                        required
    enrolled_on    DD-MM-YYYY                     required
    plan_tier      starter | growth | scale       optional
    referral_code  8-char code, often blank       optional
    opt_in         yes | no                       optional

A row is invalid if a required column is blank or contact_email is malformed.
Counts per partition are written to shard_truth.json so the Job's answers can
be checked against ground truth instead of taken on trust.
"""
import csv
import json
import random
import string

random.seed(7717)

N_PARTS = 8
COLUMNS = ["ref", "contact_email", "enrolled_on", "plan_tier",
           "referral_code", "opt_in"]

CONSONANTS = "bcdfgklmnprstvz"
VOWELS = "aeiou"
DOMAINS = ["arcline.io", "brightmail.dev", "corvus.org",
           "delta-post.net", "eastwind.co"]
TIERS = ["starter", "growth", "scale"]


def handle():
    """Build a pronounceable local-part from syllables."""
    syllables = "".join(
        random.choice(CONSONANTS) + random.choice(VOWELS) for _ in range(3)
    )
    return f"{syllables}{random.randint(10, 99)}"


def referral():
    if random.random() < 0.45:
        return ""            # legitimately blank optional column
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def clean_row(part, seq):
    return {
        "ref": f"SGN-{part}-{seq:06d}",
        "contact_email": f"{handle()}@{random.choice(DOMAINS)}",
        "enrolled_on": (f"{random.randint(1,28):02d}-"
                        f"{random.randint(1,12):02d}-"
                        f"{random.choice([2024, 2025])}"),
        "plan_tier": random.choice(TIERS),
        "referral_code": referral(),
        "opt_in": random.choice(["yes", "no"]),
    }


def break_row(row):
    """Apply exactly one defect so the invalid count stays exact."""
    defect = random.choice([
        "double_at", "no_local_part", "space_inside",
        "no_tld", "blank_ref", "blank_date",
    ])
    addr = row["contact_email"]
    local, _, domain = addr.partition("@")

    if defect == "double_at":
        row["contact_email"] = f"{local}@@{domain}"
    elif defect == "no_local_part":
        row["contact_email"] = f"@{domain}"
    elif defect == "space_inside":
        row["contact_email"] = f"{local[:3]} {local[3:]}@{domain}"
    elif defect == "no_tld":
        row["contact_email"] = f"{local}@intranet"
    elif defect == "blank_ref":
        row["ref"] = ""
    elif defect == "blank_date":
        row["enrolled_on"] = ""
    return row


truth = {}
for part in range(N_PARTS):
    n_rows = random.randint(620, 880)          # uneven partitions
    n_bad = random.randint(18, 64)             # seeded, so reproducible
    bad_rows = set(random.sample(range(n_rows), n_bad))

    path = f"signup_data/signups_part_{part}.csv"
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        for seq in range(n_rows):
            row = clean_row(part, seq)
            if seq in bad_rows:
                row = break_row(row)
            writer.writerow(row)

    truth[part] = {"rows": n_rows, "invalid": n_bad}
    print(f"{path}: {n_rows} rows, {n_bad} invalid")

with open("shard_truth.json", "w") as fh:
    json.dump(truth, fh, indent=2)

print("\nGround truth -> shard_truth.json")
print("total rows   :", sum(v["rows"] for v in truth.values()))
print("total invalid:", sum(v["invalid"] for v in truth.values()))
