#!/usr/bin/env bash
# Reads every pod's stdout through the API server. No shared volume involved.
PODS=$(kubectl get pods -l job-name=signup-audit \
         -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)

echo "=== raw logs, all 8 pods, read via the API server ==="
for p in $PODS; do kubectl logs "$p"; done

echo
echo "part   node             rows    invalid"
for p in $PODS; do
  kubectl logs "$p" | grep '^AUDIT'
done | sed 's/AUDIT //' | sort -t= -k2 -n \
     | awk '{for(i=1;i<=NF;i++){split($i,a,"=");v[a[1]]=a[2]}
             printf "%-6s %-16s %-7s %s\n", v["part"], v["node"], v["rows"], v["invalid"]}'
