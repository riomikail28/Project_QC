# GitHub Actions Workflows

## Overview

This directory contains GitHub Actions CI/CD workflows for the QC Central Kitchen project.

---

## Workflow Files

### 1. **ci-cd-production.yml** ⭐ PRIMARY

**Status**: ✓ PRODUCTION-READY  
**Purpose**: Complete CI/CD pipeline  
**Triggers**: Push to main/develop/staging, PRs, manual dispatch  

**Stages**:
```
1. VALIDATE - Python syntax, imports, dependencies
2. TEST - Unit tests, coverage
3. VALIDATE-K8S - Helm lint, YAML validation
4. BUILD - Docker image (multi-platform)
5. DEPLOY-STAGING - Helm deployment to staging
6. DEPLOY-VERCEL - Frontend deployment
7. SUMMARY - Pipeline status reporting
```

**When to use**: 
- PRIMARY workflow for all CI/CD tasks
- Recommended for all new projects
- Use for development, staging, and production deployments

**Link**: [ci-cd-production.yml](./ci-cd-production.yml)

---

### 2. **ci.yml** (DEPRECATED)

**Status**: ⚠️ DEPRECATED - Maintained for backward compatibility  
**Purpose**: Basic validation and tests  
**Triggers**: Same as ci-cd-production.yml  

**Why deprecated**:
- Incomplete pipeline (no K8s validation, no deployment)
- Duplicate logic with ci-cd-production.yml
- Confusing to maintain two workflows

**Migration**:
- All new workflows should use **ci-cd-production.yml**
- Old workflow runs but prints deprecation notice
- Will be removed in Q3 2026

**Link**: [ci.yml](./ci.yml)

---

### 3. **cd_helm_deploy.yml** (MANUAL ONLY)

**Status**: ✓ ACTIVE - Manual trigger only  
**Purpose**: Standalone Helm deployment (no CI)  
**Triggers**: Manual `workflow_dispatch` only  

**Use cases**:
- Manual deployment without rebuilding image
- Rollback to previous image
- Redeployment after secret rotation
- Helm chart updates without code changes

**Example usage**:
```bash
gh workflow run cd_helm_deploy.yml \
  -f namespace=qc-staging \
  -f image_tag=develop-abc123
```

**Link**: [cd_helm_deploy.yml](./cd_helm_deploy.yml)

---

### 4. **security-scan.yml** (OPTIONAL)

**Status**: ✓ ACTIVE - Optional integration  
**Purpose**: Security scanning and SAST  
**Triggers**: Manual, scheduled (weekly)  

**Checks**:
- Dependency vulnerability scan
- SAST (static analysis)
- Secret detection
- License compliance

**Link**: [security-scan.yml](./security-scan.yml)

---

### 5. **load-and-chaos.yml** (EXPERIMENTAL)

**Status**: 🔬 EXPERIMENTAL - For testing only  
**Purpose**: Load testing and chaos engineering  
**Triggers**: Manual only  

**Features**:
- Load test (simulates concurrent users)
- Chaos monkey (random failures)
- Performance profiling
- Baseline comparison

**Link**: [load-and-chaos.yml](./load-and-chaos.yml)

---

### 6. **full-restore-validate.yml** (MAINTENANCE)

**Status**: ✓ ACTIVE - Scheduled  
**Purpose**: Database backup/restore validation  
**Triggers**: Scheduled (weekly), manual  

**Validates**:
- Backup integrity
- Restore procedures
- Recovery time objective (RTO)
- Data consistency

**Link**: [full-restore-validate.yml](./full-restore-validate.yml)

---

### 7. **backup-restore-verify.yml** (MAINTENANCE)

**Status**: ✓ ACTIVE - Scheduled  
**Purpose**: Backup verification  
**Triggers**: Scheduled (daily), manual  

**Checks**:
- Backup completion
- Backup size tracking
- Restore test
- Data integrity

**Link**: [backup-restore-verify.yml](./backup-restore-verify.yml)

---

## Quick Reference

### For CI/CD Pipelines

Use **ci-cd-production.yml**:

```yaml
# Automatic trigger on push
git push origin develop
# → Workflow runs automatically

# Manual trigger
gh workflow run ci-cd-production.yml
```

---

### For Manual Deployment

Use **cd_helm_deploy.yml**:

```yaml
# Deploy to staging with specific image
gh workflow run cd_helm_deploy.yml \
  -f namespace=qc-staging \
  -f image_tag=develop-xyz789

# Rollback to previous version
gh workflow run cd_helm_deploy.yml \
  -f namespace=qc-staging \
  -f image_tag=develop-previous
```

---

### For Security Scanning

Use **security-scan.yml**:

```yaml
# Manual trigger
gh workflow run security-scan.yml

# Scheduled: Weekly (automatic)
```

---

## Workflow Dependencies

```
┌──────────────────────────────────┐
│   Event Triggered                │
│   (Push/PR/Manual)               │
└──────────────┬───────────────────┘
               │
        ┌──────▼──────┐
        │ ci.yml       │ ← DEPRECATED
        │ (basic test) │
        └──────────────┘
               
        ┌─────────────────────────────┐
        │ ci-cd-production.yml         │ ← PRIMARY
        │ (validate→test→build→deploy) │
        └─────────────────────────────┘
               │
        ┌──────▼─────────┐
        │ cd_helm_deploy │ ← Manual only
        │ (standalone)   │
        └────────────────┘
```

---

## Environment Requirements

### Required Secrets (GitHub Settings → Secrets)

```
KUBE_CONFIG_DATA          Base64-encoded kubeconfig
JWT_SECRET_KEY            JWT signing key (32+ chars)
DB_PASSWORD               PostgreSQL password
SUPABASE_URL              https://...supabase.co
SUPABASE_KEY              Supabase API key
```

### Optional Secrets

```
VERCEL_TOKEN              Vercel deployment token
VERCEL_ORG_ID             Vercel organization ID
VERCEL_PROJECT_ID         Vercel project ID
SLACK_WEBHOOK_URL         Slack notifications
```

See [GITHUB_SECRETS_SETUP.md](../../docs/GITHUB_SECRETS_SETUP.md) for detailed setup.

---

## Configuration Files

| File | Purpose |
|------|---------|
| requirements.txt | Python dependencies |
| pytest.ini | Pytest configuration |
| backend/Dockerfile.optimized | Docker image config |
| k8s/charts/qc-app | Helm charts |
| .env.example | Local environment template |
| vercel.json | Vercel configuration |
| runtime.txt | Python version specification |

---

## Troubleshooting

### Workflow Won't Run

**Check**:
1. Is trigger configured? (push to main/develop, PR, manual?)
2. Do you have required secrets? (KUBE_CONFIG_DATA, etc.)
3. Is branch protected? (may require approval)

```bash
# Check workflow syntax
gh workflow view ci-cd-production.yml

# List recent runs
gh run list --workflow=ci-cd-production.yml

# View specific run
gh run view <run-id> --log
```

---

### Workflow Fails at Stage X

**Validate Stage**:
- Check: `pip install -r requirements.txt` works locally
- Check: `python -m compileall backend/` succeeds
- Check: `from backend import create_app` works

**Test Stage**:
- Check: `python -m pytest tests/ -v` works locally
- Check: PostgreSQL/Redis services running
- Check: `pytest.ini` exists and is valid

**Build Stage**:
- Check: `docker build -f backend/Dockerfile.optimized .`
- Check: Dockerfile at correct path
- Check: GHCR credentials valid

**Deploy Stage**:
- Check: `kubectl cluster-info` works
- Check: Kubeconfig valid and not expired
- Check: Kubernetes secrets exist

See [CI_CD_TROUBLESHOOTING.md](../../docs/CI_CD_TROUBLESHOOTING.md) for detailed solutions.

---

## Viewing Logs

### Via GitHub UI

```
1. Go to Actions tab
2. Click workflow run
3. Click job to expand
4. Click step to see logs
```

### Via GitHub CLI

```bash
# List runs
gh run list --workflow=ci-cd-production.yml

# Watch live
gh run watch <run-id>

# View logs
gh run view <run-id> --log

# Download logs
gh run download <run-id> --dir ./logs
```

### Via Local Tools

```bash
# View with `act` (runs locally)
brew install act
act -j validate
act -j test
```

---

## Performance Tips

**Speed up builds**:
- Use pip cache (enabled in workflow)
- Use Docker buildx cache (enabled in workflow)
- Run stages in parallel (validate-k8s runs with test)
- Use multi-platform builds (amd64, arm64)

**Typical execution time**:
- Validate: 2-3 min
- Test: 3-5 min
- Build: 5-10 min
- Deploy: 2-3 min
- **Total: ~15-20 min**

---

## Best Practices

✓ Use `ci-cd-production.yml` for all new CI/CD  
✓ Keep `ci.yml` for backward compatibility (deprecated)  
✓ Use `cd_helm_deploy.yml` for manual deployments  
✓ Regularly rotate secrets (every 90 days)  
✓ Review logs for errors and optimize  
✓ Test workflows locally with `act`  
✓ Document any custom environment variables  
✓ Use branch protection + required status checks  

---

## Support & Documentation

**Need help?**
- [CI/CD Troubleshooting Guide](../../docs/CI_CD_TROUBLESHOOTING.md)
- [Environment Configuration](../../docs/ENVIRONMENT_STRATEGY.md)
- [GitHub Secrets Setup](../../docs/GITHUB_SECRETS_SETUP.md)
- [Pipeline Production Ready](../../docs/PIPELINE_PRODUCTION_READY.md)

---

**Last Updated**: 2026-05-09  
**Version**: 1.0.0  
**Status**: Production Ready
