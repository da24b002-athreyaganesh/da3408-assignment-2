#!/usr/bin/env bash
# Measures forced cache MISSes against cache HITs for the same input text.
set -euo pipefail

URL="${URL:-http://localhost:8000/predict}"
N="${N:-30}"
BODY='{"text":"WIN a FREE iPhone now! Click here: bit.ly/xyz123"}'

run_one() {
  curl -s -o /dev/null -D - -X POST "$URL" \
       -H 'Content-Type: application/json' -d "$BODY" \
  | tr -d '\r' \
  | awk -F': ' 'tolower($1)=="x-cache"{c=$2} tolower($1)=="x-elapsed-ms"{e=$2} END{print c, e}'
}

echo "=== $N forced MISSes (cache flushed before each call) ==="
: > /tmp/miss.txt
for _ in $(seq 1 "$N"); do
  docker compose exec -T cache redis-cli FLUSHALL >/dev/null
  run_one >> /tmp/miss.txt
done

echo "=== $N HITs (primed once, then repeated) ==="
run_one >/dev/null
: > /tmp/hit.txt
for _ in $(seq 1 "$N"); do run_one >> /tmp/hit.txt; done

echo
awk '{s+=$2; n++; if(n==1||$2<m)m=$2} END{printf "MISS  mean %.3f ms   min %.3f ms   n=%d\n", s/n, m, n}' /tmp/miss.txt
awk '{s+=$2; n++; if(n==1||$2<m)m=$2} END{printf "HIT   mean %.3f ms   min %.3f ms   n=%d\n", s/n, m, n}' /tmp/hit.txt
awk 'NR==FNR{a+=$2;an++;next}{b+=$2;bn++} END{printf "\nspeedup: %.2fx faster on a cache hit\n",(a/an)/(b/bn)}' /tmp/miss.txt /tmp/hit.txt

echo
echo "--- label correctness check ---"
echo -n "MISS path: "; head -1 /tmp/miss.txt
echo -n "HIT path:  "; head -1 /tmp/hit.txt
