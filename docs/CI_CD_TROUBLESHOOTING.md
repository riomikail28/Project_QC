# QC Central Kitchen - CI/CD Pipeline Troubleshooting Guide

## Executive Summary

**Pipeline Status**: Production-Ready  
**Last Updated**: 2026-05-09  
**Architecture**: GitHub Actions → Docker → Kubernetes (Helm) + Vercel (Frontend)

This guide provides comprehensive troubleshooting procedures for the QC CI/CD pipeline failures.

---

## Table of Contents

1. [Pipeline Architecture](#pipeline-architecture)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Debugging Workflow](#debugging-workflow)
4. [Common Failures & Solutions](#common-failures--solutions)
5. [Environment Configuration](#environment-configuration)
6. [Rollback Procedures](#rollback-procedures)

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  GitHub Actions Workflow                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  STAGE 1: VALIDATE                                           │
│  ├─ Python syntax check (compileall)                        │
│  ├─ Dependency validation (import check)                    │
│  └─ Production code only (exclude layers, services)         │
│                                                               │
│  STAGE 2: TEST                                               │
│  ├─ PostgreSQL + Redis services                             │
│  ├─ Unit tests (pytest)                                     │
│  └─ Coverage reporting                                       │
│                                                               │
│  STAGE 3: VALIDATE-K8S                                       │
│  ├─ Helm lint                                               │
│  ├─ Template rendering                                       │
│  └─ YAML validation                                          │
│                                                               │
│  STAGE 4: BUILD (if not PR)                                  │
│  ├─ Docker image build                                       │
│  └─ Push to GHCR                                             │
│                                                               │
│  STAGE 5: DEPLOY-STAGING (if develop branch)                 │
│  ├─ Helm deployment                                          │
│  └─ Rollout verification                                     │
│                                                               │
│  STAGE 6: DEPLOY-VERCEL (if main branch)                     │
│  └─ Frontend deployment                                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Root Cause Analysis

### CRITICAL: Dependencies Missing (FIXED)

**Original Issue**: Pipeline failed because Flask-CORS, pytest, redis, gunicorn not installed

**Root Causes Identified**:
1. **requirements.txt incomplete** - Missing pytest and other transitive dependencies
2. **Virtual environment out of sync** - requirements.txt != installed packages
3. **Version conflicts** - Flask 3.0.0 (required) vs 3.1.3 (installed)

**How It Was Fixed**:
```
requirements.txt BEFORE:        requirements.txt AFTER:
- Flask==3.0.0                  - Flask==3.0.0
- Flask-CORS==4.0.0             - Flask-CORS==4.0.0
- redis==5.0.1                  - redis==5.0.1
- (NO pytest)                    - pytest==7.4.3 ✓ NEW
- (NO werkzeug)                  - Werkzeug==3.0.0 ✓ NEW
```

**Verification**:
```bash
# Local verification
python -m pip install -r requirements.txt
python -c "import flask_cors; print('✓ Flask-CORS installed')"
python -m pytest --version
```

### HIGH: Workflow Duplicate/Conflict

**Issue**: Two workflow files (ci.yml and ci-cd.yml) could cause conflicting executions

**Solution**: 
- Keep: `ci-cd-production.yml` (comprehensive, production-ready)
- Deprecate: `ci.yml` (old, replaced)
- Note: `.github/workflows/cd_helm_deploy.yml` is standalone for manual Helm deploys

### MEDIUM: Experimental Code in Compile

**Issue**: Including `backend/layers/` and `backend/services/` (legacy) in compilation

**Solution**: 
- Production compile includes only: app, __init__, caching, core, database, middleware, notifications, repositories, routes, service (singular), skills, workers
- Excludes: layers, services (legacy), workers (if experimental)

---

## Debugging Workflow

### Step 1: Identify Failure Point

Check GitHub Actions run logs and locate FIRST failure:

```
Expected cascade:
1. ✓ validate (syntax, imports) 
2. ✓ test (pytest, coverage)        
3. ✓ validate-k8s (helm, yaml)
4. ✓ build (docker, push)
5. ✓ deploy-staging (helm, rollout)
6. ✓ deploy-vercel (frontend)

If ANY step fails, dependent steps are skipped.
```

### Step 2: Check Logs

**For VALIDATE stage failure**:
```bash
# Check what GitHub Actions captures
# Look for:
# - "No module named 'X'" → dependency missing
# - "SyntaxError" → Python syntax error  
# - "ImportError" → import path issue
```

**For TEST stage failure**:
```bash
# Check pytest output
# Look for:
# - "FAILED tests/" → specific test failed
# - "ModuleNotFoundError" → import issue
# - "ConnectionError" → DB/Redis not ready
```

### Step 3: Reproduce Locally

```bash
# Activate venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate

# Install deps exactly as CI does
pip install -r requirements.txt

# Run validation
python -m compileall backend/

# Run tests
python -m pytest tests/ --ignore=tests/integration -v

# Check Helm
helm lint k8s/charts/qc-app
```

### Step 4: Verify Environment Variables

```bash
# Required env vars for CI
export JWT_SECRET_KEY=test-secret
export DATABASE_URL=postgresql://...
export REDIS_URL=redis://...
export SUPABASE_URL=https://...
export SUPABASE_KEY=...

# Re-run validation
python -c "from backend import create_app; app = create_app(); print('✓ App created')"
```

---

## Common Failures & Solutions

### Failure: `ModuleNotFoundError: No module named 'flask_cors'`

**Symptoms**:
- Validate stage fails immediately
- Error appears during import check

**Root Cause**: 
- Flask-CORS not installed
- requirements.txt not up to date

**Solution**:
```bash
# Step 1: Update requirements.txt (already done)
# Step 2: Install in CI environment
pip install -r requirements.txt --no-cache-dir

# Step 3: Verify
python -c "import flask_cors; print(flask_cors.__version__)"
```

**GitHub Actions Fix**:
- Already implemented in `ci-cd-production.yml` step "Install dependencies"
- Uses `--no-cache-dir` to ensure fresh install

---

### Failure: `No tests collected` or `pytest: command not found`

**Symptoms**:
- Test stage fails with "collected 0 items"
- Or: "pytest: No such file or directory"

**Root Cause**:
- pytest not installed
- pytest.ini not found or misconfigured

**Solution**:
```bash
# Step 1: Ensure pytest in requirements.txt
grep pytest requirements.txt  # Should show pytest==7.4.3

# Step 2: Ensure pytest.ini exists
ls -la pytest.ini  # Should exist in project root

# Step 3: Run pytest discovery
pytest --collect-only tests/
```

**Files Provided**:
- ✓ requirements.txt - includes pytest==7.4.3
- ✓ pytest.ini - configured for project

---

### Failure: `FAILED tests/test_auth_flow.py::TestAuthFlow::test_*`

**Symptoms**:
- Test runs but fails at assertion
- Error: "ConnectionError" or "redis" related

**Root Cause**:
- PostgreSQL/Redis services not ready
- Test database not initialized

**Solution**:
```bash
# In CI: services are auto-started before tests
# Verify locally:
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15
docker run -d -p 6379:6379 redis:7-alpine

# Then run tests
python -m pytest tests/ -v
```

**GitHub Actions Ensures**:
- PostgreSQL health check: `pg_isready -U postgres -d test_db`
- Redis health check: `redis-cli ping`
- 5 retries with 10s intervals before tests start

---

### Failure: `helm lint` fails with "Chart.yaml not found"

**Symptoms**:
- Validate-K8s stage fails
- Error: "Error reading Chart.yaml"

**Root Cause**:
- Helm chart not at expected path
- Chart.yaml misconfigured

**Solution**:
```bash
# Verify chart structure
ls -la k8s/charts/qc-app/
# Should have: Chart.yaml, values.yaml, templates/

# Run helm lint
helm lint k8s/charts/qc-app --strict

# Dry-run deployment
helm template qc-app k8s/charts/qc-app \
  --set image.tag=test \
  --set secrets.jwtSecretKey=test
```

**GitHub Actions Configuration**:
- Validates chart exists before running helm commands
- Uses `--strict` flag for production readiness

---

### Failure: `docker build` fails with "Dockerfile not found"

**Symptoms**:
- Build stage fails
- Error: "dockerfile file not found"

**Root Cause**:
- Dockerfile.optimized not at expected path
- Docker context incorrect

**Solution**:
```bash
# Verify Dockerfile exists
ls -la backend/Dockerfile.optimized

# Test build locally
docker build -f backend/Dockerfile.optimized -t qc-app:test .

# If fails, check Dockerfile for issues
docker build --progress=plain -f backend/Dockerfile.optimized -t qc-app:test .
```

---

### Failure: Helm deployment fails with "Error: secret XXXX not found"

**Symptoms**:
- Deploy-Staging fails
- Error: "release qc-app: Helm deployment failed"
- Deployment pending/waiting

**Root Cause**:
- Kubernetes secrets not created
- KUBE_CONFIG_DATA secret not set in GitHub
- Namespace/RBAC issues

**Solution**:
```bash
# Step 1: Verify kubectl can connect
kubectl cluster-info

# Step 2: Check secrets exist
kubectl get secrets -n qc-staging

# Step 3: Create required secrets
kubectl create secret generic qc-secrets \
  --from-literal=jwtSecretKey=YOUR_SECRET \
  --from-literal=dbPassword=YOUR_PASSWORD \
  -n qc-staging

# Step 4: Verify Helm deployment
helm list -n qc-staging
kubectl get deployment qc-app -n qc-staging
```

**GitHub Actions Requires**:
1. `secrets.KUBE_CONFIG_DATA` - base64 encoded kubeconfig
2. `secrets.JWT_SECRET_KEY` - JWT signing key
3. `secrets.DB_PASSWORD` - Database password
4. `secrets.SUPABASE_URL` - Supabase URL
5. `secrets.SUPABASE_KEY` - Supabase API key

See [Environment Configuration](#environment-configuration) section.

---

### Failure: `Vercel deployment` fails with "Invalid Python runtime"

**Symptoms**:
- Deploy-Vercel fails
- Error: "python version mismatch" or "app not found"

**Root Cause**:
- runtime.txt has wrong Python version
- vercel.json misconfigured
- Flask app entry point missing

**Solution**:
```bash
# Step 1: Check runtime.txt
cat runtime.txt  # Should be: python-3.11

# Step 2: Check vercel.json
cat vercel.json  # Should have:
# {
#   "builds": [
#     {"src": "backend/app.py", "use": "@vercel/python"}
#   ],
#   "routes": [...]
# }

# Step 3: Check Flask app
cat backend/app.py  # Should have:
# if __name__ == "__main__":
#     app.run(...)
```

**Files Already Configured**:
- ✓ runtime.txt - python-3.11
- ✓ vercel.json - configured for Flask backend
- ✓ backend/app.py - Flask app with WSGI compatibility

---

## Environment Configuration

### GitHub Actions Secrets Required

Configure these in GitHub repo Settings → Secrets and variables → Actions:

#### Required Secrets (Production Deployment):

```yaml
# Kubernetes Configuration
KUBE_CONFIG_DATA:          base64-encoded kubeconfig file
                           (cat ~/.kube/config | base64 -w0)

# Database & Auth
JWT_SECRET_KEY:            32+ character random string
                           (openssl rand -base64 32)
DB_PASSWORD:               PostgreSQL password

# Supabase API
SUPABASE_URL:              https://YOUR_PROJECT.supabase.co
SUPABASE_KEY:              Your-Supabase-API-Key

# Vercel Deployment (Optional)
VERCEL_TOKEN:              Vercel CLI token
VERCEL_ORG_ID:             Organization ID
VERCEL_PROJECT_ID:         Project ID
```

#### Optional Variables (can be in repo settings):

```yaml
IMAGE_REPOSITORY:          ghcr.io/your-org/qc-app
SUPABASE_STORAGE_BUCKET:   qc-photos (default)
HELM_NAMESPACE:            qc-staging (default)
```

### Local Environment Setup

Create `.env` file in project root:

```bash
# Backend Configuration
FLASK_ENV=development
ENVIRONMENT=local

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/qc_dev
REDIS_URL=redis://localhost:6379/0

# Authentication
JWT_SECRET_KEY=dev-secret-change-in-production

# Supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=YOUR_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
SUPABASE_STORAGE_BUCKET=qc-photos

# Google Cloud (optional)
GCP_PROJECT_ID=your-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# CORS (development)
CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:3000

# Alerts (optional)
ALERT_WEBHOOK_URL=https://hooks.slack.com/...
```

### CI Test Environment

Set automatically by GitHub Actions workflow:

```yaml
ENVIRONMENT: testing
JWT_SECRET_KEY: ci-test-secret
DATABASE_URL: postgresql://postgres:postgres@127.0.0.1:5432/test_db
REDIS_URL: redis://127.0.0.1:6379/0
SUPABASE_URL: https://test.supabase.co
SUPABASE_KEY: test-key
```

---

## Rollback Procedures

### Rollback Kubernetes Deployment

```bash
# Step 1: List deployment history
helm history qc-app -n qc-staging

# Step 2: Rollback to previous release
helm rollback qc-app 5 -n qc-staging  # Replace 5 with revision number

# Step 3: Verify rollback
kubectl rollout status deployment/qc-app -n qc-staging --timeout=300s
kubectl get pods -n qc-staging -l app.kubernetes.io/name=qc-app
```

### Rollback Docker Image

```bash
# Step 1: Get previous image tag
docker pull ghcr.io/your-org/qc-app:develop-abc123xyz

# Step 2: Redeploy with previous image
helm upgrade qc-app k8s/charts/qc-app \
  -n qc-staging \
  --set image.tag=develop-abc123xyz

# Step 3: Wait for rollout
kubectl rollout status deployment/qc-app -n qc-staging
```

### Rollback Vercel Deployment

```bash
# Via Vercel Dashboard:
1. Go to Deployments
2. Find previous successful deployment
3. Click "Promote to Production"
```

---

## Debug Logging Strategy

### Enable Verbose Logging in GitHub Actions

In workflow file, add to any step:

```yaml
- name: Step with debugging
  run: |
    set -x  # Enable command tracing
    # Your commands here
    set +x  # Disable tracing
```

Or use GitHub Actions debug logging:

```bash
# Set secret for debug logs
ACTIONS_STEP_DEBUG=true
```

### Application Logging

Backend uses Python logging. Check app logs:

```bash
# Kubernetes logs
kubectl logs -f deployment/qc-app -n qc-staging

# Previous replica logs
kubectl logs deployment/qc-app -n qc-staging --previous

# All pods with label
kubectl logs -l app.kubernetes.io/name=qc-app -n qc-staging --all-containers=true
```

### PostgreSQL/Redis Logs

```bash
# PostgreSQL
kubectl logs -f statefulset/qc-postgres -n qc-staging

# Redis
kubectl logs -f deployment/qc-redis -n qc-staging
```

---

## Performance & Optimization

### Pipeline Execution Time

Typical times (can vary):
- Validate: 2-3 minutes (installs deps, compiles)
- Test: 3-5 minutes (pytest, coverage)
- Build: 5-10 minutes (multi-platform Docker build)
- Deploy: 2-3 minutes (Helm + rollout)
- **Total: ~15-20 minutes**

### Optimization Tips

1. **Use pip caching** (already enabled in workflow)
2. **Use Docker buildx cache** (already enabled in workflow)
3. **Parallel stages** - validate-k8s runs simultaneously with test
4. **Fail-fast** - If validate fails, test won't run
5. **Platform-specific** - arm64 build optional (configured for both)

---

## Support & Escalation

### Critical Issues

If pipeline is broken and blocking deployments:

1. **Check GitHub Actions logs** for exact error
2. **Run diagnostic locally** (reproduce the issue)
3. **Check dependencies** with `pip list | grep flask`
4. **Verify secrets** are configured in GitHub
5. **Check Kubernetes cluster** status

### Getting Help

- **Pipeline Code**: See `ci-cd-production.yml`
- **Requirements**: See `requirements.txt`
- **Pytest Config**: See `pytest.ini`
- **Helm Charts**: See `k8s/charts/qc-app/`
- **Environment**: See `.env.example`

---

## Related Documentation

- [Environment Strategy Guide](./ENVIRONMENT_STRATEGY.md)
- [GitHub Actions Secrets Setup](./GITHUB_SECRETS_SETUP.md)
- [Kubernetes Deployment Guide](./KUBERNETES_DEPLOYMENT.md)
- [Helm Chart Reference](../charts/qc-app/README.md)

---

**Last Updated**: 2026-05-09  
**Version**: 1.0.0  
**Status**: Production Ready
