#!/usr/bin/env bash
echo "=== rollout status ==="
kubectl rollout status deployment/spam-api

echo
echo "=== rollout history ==="
kubectl rollout history deployment/spam-api

echo
echo "=== revision 1 ==="
kubectl rollout history deployment/spam-api --revision=1 | grep -E 'Image|change-cause'

echo
echo "=== revision 2 ==="
kubectl rollout history deployment/spam-api --revision=2 | grep -E 'Image|change-cause'

echo
echo "=== both ReplicaSets: old scaled to 0, new to 2 ==="
kubectl get rs -l app=spam-api

echo
echo "=== live version now served ==="
kubectl get deployment spam-api -o jsonpath='{.spec.template.spec.containers[0].image}'
echo
