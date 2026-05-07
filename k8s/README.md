Kubernetes Helm chart for qc-app

Files:
- charts/qc-app: Helm chart skeleton for backend service.

Usage:
- Customize `values.yaml` (image, resources, secrets via external secrets manager)
- Deploy with Helm:
  - `helm install qc-app k8s/charts/qc-app -f k8s/charts/qc-app/values.yaml`

Notes:
- Set `ingress.enabled=true` and configure hosts for external access.
- Use external secrets (Vault/Secrets Manager) instead of embedding secrets in Helm.
