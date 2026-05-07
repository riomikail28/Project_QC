#!/bin/sh
# Simple chaos script: randomly delete one pod for a given label in a namespace
# USAGE: ./scripts/run_chaos.sh <namespace> <labelSelector>
set -eu

NAMESPACE=${1:-default}
LABEL=${2:-app.kubernetes.io/name=qc-app}

if [ -z "$KUBECONFIG" ]; then
  echo "KUBECONFIG must be set to run chaos scripts" >&2
  exit 2
fi

PODS=$(kubectl get pods -n "$NAMESPACE" -l "$LABEL" -o jsonpath='{.items[*].metadata.name}')
if [ -z "$PODS" ]; then
  echo "No pods found for selector $LABEL in namespace $NAMESPACE" >&2
  exit 1
fi

ARR=($PODS)
SIZE=${#ARR[@]}
RAND=$((RANDOM % SIZE))
TARGET=${ARR[$RAND]}

echo "Deleting pod: $TARGET in namespace $NAMESPACE"
kubectl delete pod "$TARGET" -n "$NAMESPACE" --grace-period=5 --wait=false

echo "Chaos: pod deleted (cluster will reschedule if deployment/statefulset)."