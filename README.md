# AIOps Module 3 — Infrastructure & Containerization

Athreya Ganesh, DA24B002
Video Link: https://drive.google.com/drive/folders/1ghhAs5R9_u41p9oep3RT2NdKPlFcvX57?usp=drive_link


Write-up: **`report.pdf`** (2 pages).

All four questions build on one application: a REST API that classifies a short
text message as spam or ham using a TF-IDF vectorizer and a Naive Bayes
classifier.

- `POST /predict` with `{"text": "..."}` returns `{"label": "spam"}` or `{"label": "ham"}`
- `GET /healthz` returns 200 once the model is loaded

Everything below is CPU-only.

---

## Question 1 — Single-Stage vs. Multi-Stage Docker

| Deliverable | Where |
|---|---|
| Naive single-stage Dockerfile | `Dockerfile.naive` |
| Multi-stage Dockerfile | `Dockerfile` |
| Image sizes reported | `report.pdf` §1, `evidence/q1_image_sizes.txt` |
| Percentage reduction | `report.pdf` §1, `evidence/q1_reduction.txt` |
| Container serves `/predict` and `/healthz` | `evidence/q1_endpoints.txt` |
| Explanation of what was left behind | `report.pdf` §1 |

Naive 2.34 GB → multi-stage 645 MB, a 72.4% reduction.

```bash
docker build -f Dockerfile.naive -t spam-api:naive .
docker build -f Dockerfile       -t spam-api:multi .
docker images spam-api
```

---

## Question 2 — Multi-Container Orchestration with Docker Compose

| Deliverable | Where |
|---|---|
| API checks/writes the Redis cache | `app/main.py` (`predict`, `cache_key`) |
| `docker-compose.yml` with `api` + `cache` | `docker-compose.yml` |
| Inter-service networking by service name | `evidence/q2_networking.txt` |
| Evidence of a measurable cache-hit speedup | `evidence/q2_bench.txt`, `bench.sh` |
| Correct predictions on both hit and miss | `evidence/q2_hit_miss.txt` |
| Cache keys and TTL in Redis | `evidence/q2_redis_keys.txt` |
| Compose vs. Kubernetes explanation | `report.pdf` §2 |

Cache miss 0.892 ms, cache hit 0.135 ms, so a hit is 6.61× faster (n=30 each).

```bash
docker compose up -d --build
./bench.sh
docker compose down -v
```

---

## Question 3 — Kubernetes Indexed Job: Parallel Data Validation

| Deliverable | Where |
|---|---|
| 8 generated CSV shards | `signup_data/`, built by `build_signup_shards.py` |
| Seeded ground-truth invalid counts | `shard_truth.json` |
| Parallelism choice and justification | `report.pdf` §3 |
| Full Indexed Job manifest | `k8s/job-signup-audit.yaml` |
| `kubectl get pods -o wide` proving parallelism reached | `evidence/q3_parallelism_evidence.txt`, `q3_pods_wide.txt` |
| Per-shard invalid-row counts, read via the K8s API | `evidence/q3_pod_logs.txt`, `q3_results.txt` |
| Counts checked against ground truth | `evidence/q3_verification.txt`, `verify_q3.py` |
| Why not a shared volume | `report.pdf` §3 |
| 6-CPU re-justification | `report.pdf` §3 |
| Node CPU allocatable / system-pod requests | `evidence/q3_cluster.txt` |

`completions: 8`, `parallelism: 4`, `completionMode: Indexed`,
`restartPolicy: Never`, CPU requests equal to limits at `500m`, and
`POD_NAME` / `NODE_NAME` via the Downward API.

Four pods ran concurrently (`.status.active = 4`); all 8 finished in 23 s across
two waves. 6464 rows audited, 333 invalid, all 8 shards matching ground truth.

```bash
minikube start --nodes=2 --cpus=2 --memory=1900 --driver=docker
python3 build_signup_shards.py
kubectl create configmap signup-parts --from-file=signup_data/
kubectl create configmap audit-code   --from-file=audit_part.py
kubectl apply -f k8s/job-signup-audit.yaml
./peak.sh                # parallelism evidence
./collect_results.sh     # per-shard counts via kubectl logs
python3 verify_q3.py     # check against shard_truth.json
```

---

## Question 4 — Kubernetes Deployments: Self-Healing & Rolling Updates

| Deliverable | Where |
|---|---|
| Deployment manifest (2 replicas, resources, readinessProbe) | `k8s/deployment-spam-api.yaml` |
| Service manifest | `k8s/service-spam-api.yaml` |
| Both applied, endpoints registered | `evidence/q4_context.txt` |
| Self-healing evidence after manual pod deletion | `evidence/q4_selfhealing.txt`, `selfheal.sh` |
| Which controller is responsible | `report.pdf` §4 |
| `rollout status` and `rollout history` output | `evidence/q4_rollout.txt`, `rollout_evidence.sh` |
| No-downtime measurement during the update | `evidence/q4_downtime_check.txt`, `q4_poll_raw.txt` |
| Job-vs-Deployment contrast | `report.pdf` §4 |

The visible change for the rolling update is a version string in the `/healthz`
response, baked into the image at build time so `v1` and `v2` are different
images.

```bash
docker build --build-arg APP_VERSION=1.0.0 -t spam-api:v1 .
docker build --build-arg APP_VERSION=2.0.0 -t spam-api:v2 .
minikube image load spam-api:v1 && minikube image load spam-api:v2
kubectl apply -f k8s/deployment-spam-api.yaml -f k8s/service-spam-api.yaml
./selfheal.sh
./poll_rollout.sh "$(minikube service spam-api --url)" 250 &
kubectl set image deployment/spam-api api=spam-api:v2
./rollout_evidence.sh
```

---

## Notes

The API treats Redis as optional. If it cannot connect it logs the failure and
serves uncached predictions, which is why the same image runs under Question 2
with a cache beside it and under Question 4 without one.

The Question 3 cluster was created with `--cpus=2`, but the minikube nodes report
4 allocatable CPUs each. The parallelism choice in `report.pdf` is sized to the
4-CPU budget the question specifies, not to what the cluster would have allowed.

During the Question 4 rolling update, 249 of 250 requests succeeded. The single
failure fell in the switchover window and is explained in `report.pdf` §4.
