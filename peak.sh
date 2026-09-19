#!/usr/bin/env bash
echo "=== snapshots where 4 pods were active at once ==="
grep -A6 'active=4' evidence/q3_pods_wide.txt | head -40

echo
echo "=== max Running pods seen in any single snapshot ==="
awk '/^=====/{if(n>max)max=n; n=0} /Running/{n++} END{if(n>max)max=n; print max}' \
    evidence/q3_pods_wide.txt

echo
echo "=== final placement: which pod ran on which node ==="
kubectl get pods -l job-name=signup-audit -o wide
