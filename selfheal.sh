#!/usr/bin/env bash
set -u
echo "=== ReplicaSet owning these pods ==="
kubectl get rs -l app=spam-api

echo
echo "=== pods BEFORE deletion ==="
kubectl get pods -l app=spam-api -o wide

VICTIM=$(kubectl get pods -l app=spam-api -o jsonpath='{.items[0].metadata.name}')
echo
echo "=== deleting pod: $VICTIM ==="
kubectl delete pod "$VICTIM"

echo
echo "=== pods immediately after deletion ==="
kubectl get pods -l app=spam-api -o wide

echo
echo "=== waiting for the replacement to become Ready ==="
kubectl wait --for=condition=ready pod -l app=spam-api --timeout=120s

echo
echo "=== pods AFTER self-healing ==="
kubectl get pods -l app=spam-api -o wide

echo
echo "=== the controller's own account of it ==="
kubectl describe rs -l app=spam-api | grep -A12 'Events:'
