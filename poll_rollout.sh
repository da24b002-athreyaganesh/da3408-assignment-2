#!/usr/bin/env bash
# Hammers /healthz during a rollout and reports failures + versions observed.
URL="$1"
N="${2:-250}"
LOG=evidence/q4_poll_raw.txt
: > "$LOG"

ok=0; bad=0
for i in $(seq 1 "$N"); do
  body=$(curl -s --max-time 2 -w '\n%{http_code}' "$URL/healthz")
  code=$(echo "$body" | tail -1)
  ver=$(echo "$body" | head -1 | sed -n 's/.*"version":"\([^"]*\)".*/\1/p')
  if [ "$code" = "200" ]; then ok=$((ok+1)); else bad=$((bad+1)); fi
  echo "$(date +%T) code=${code:-none} version=${ver:-none}" >> "$LOG"
  sleep 0.2
done

echo "requests=$N  ok=$ok  failed=$bad"
echo
echo "versions observed:"
awk '{print $3}' "$LOG" | sort | uniq -c
echo
echo "first sighting of each version:"
awk '!seen[$3]++ {print $1, $3}' "$LOG"
