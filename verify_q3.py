"""Check the Job's reported counts against the generator's ground truth.

Reads every pod's log through the Kubernetes API (kubectl logs -> API server),
parses the AUDIT line, and compares row and invalid counts to shard_truth.json.
"""
import json
import re
import subprocess

truth = {int(k): v for k, v in json.load(open("shard_truth.json")).items()}

pods = subprocess.run(
    ["kubectl", "get", "pods", "-l", "job-name=signup-audit",
     "-o", "jsonpath={range .items[*]}{.metadata.name}{\"\\n\"}{end}"],
    capture_output=True, text=True).stdout.split()

got = {}
for pod in pods:
    log = subprocess.run(["kubectl", "logs", pod],
                         capture_output=True, text=True).stdout
    m = re.search(r"AUDIT part=(\d+) node=(\S+) rows=(\d+) invalid=(\d+)", log)
    if m:
        got[int(m.group(1))] = {
            "node": m.group(2),
            "rows": int(m.group(3)),
            "invalid": int(m.group(4)),
        }

header = f"{'part':<6}{'rows':<7}{'expected':<10}{'reported':<10}{'node':<17}{'ok'}"
print(header)
print("-" * len(header))

all_ok = True
for part in sorted(truth):
    exp = truth[part]
    rep = got.get(part)
    ok = (rep is not None
          and rep["invalid"] == exp["invalid"]
          and rep["rows"] == exp["rows"])
    all_ok &= ok
    print(f"{part:<6}{exp['rows']:<7}{exp['invalid']:<10}"
          f"{(rep['invalid'] if rep else '-'):<10}"
          f"{(rep['node'] if rep else '-'):<17}{'yes' if ok else 'NO'}")

print()
print("pods reporting:", len(got), "of", len(truth))
print("all partitions match ground truth:", all_ok)
print("total rows audited:", sum(r["rows"] for r in got.values()))
print("total invalid rows reported:", sum(r["invalid"] for r in got.values()))
