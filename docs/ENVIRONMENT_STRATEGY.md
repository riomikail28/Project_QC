# Environment Strategy & Configuration

## Overview

This document defines the environment strategy for the QC Central Kitchen project, covering local development, CI/CD testing, staging, and production environments.

---

## Environment Matrix

| Aspect | Local Dev | CI/CD Test | Staging | Production |
|--------|-----------|-----------|---------|-----------|
| **Database** | PostgreSQL (local) | PostgreSQL (service) | AWS RDS | AWS RDS (HA) |
| **Cache** | Redis (local) | Redis (service) | AWS ElastiCache | AWS ElastiCache (cluster) |
| **Storage** | Local filesystem | Fakeredis | Supabase Storage | Supabase Storage |
| **Frontend** | Localhost:3000 | N/A | Vercel | Vercel (CDN) |
| **API** | Localhost:5000 | N/A | HTTPS/staging | HTTPS/prod |
| **Secrets** | .env file | GitHub secrets | AWS Secrets Manager | AWS Secrets Manager |
| **Logging** | Console | GitHub Actions logs | CloudWatch | CloudWatch + ELK |
| **Monitoring** | None | N/A | Prometheus/Grafana | Prometheus/Grafana + DataDog |
| **Python Version** | 3.11 | 3.11 | 3.11 | 3.11 |
| **Dependencies** | requirements.txt | requirements.txt (cached) | requirements.txt (locked) | requirements.txt (locked) |

---

## Local Development Environment

### Setup Instructions

```bash
# Step 1: Clone repository
git clone <repo-url>
cd Project_QC

# Step 2: Create Python virtual environment
python3.11 -m venv .venv

# Step 3: Activate virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Step 4: Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Step 5: Setup Docker services (PostgreSQL + Redis)
docker-compose up -d

# Step 6: Create .env file
cp .env.example .env
# Edit .env with your local values

# Step 7: Initialize database
alembic upgrade head

# Step 8: Run Flask app
python -m backend.app
# Or: python backend/app.py
```

### Environment Configuration (.env)

```bash
# Application
FLASK_ENV=development
ENVIRONMENT=local
DEBUG=true

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/qc_dev
REDIS_URL=redis://localhost:6379/0

# Authentication
JWT_SECRET_KEY=dev-secret-key-12345678901234567890

# Supabase (Development Project)
SUPABASE_URL=https://dev.supabase.co
SUPABASE_KEY=dev-anon-key
SUPABASE_SERVICE_ROLE_KEY=dev-service-key
SUPABASE_STORAGE_BUCKET=qc-photos-dev

# Google Cloud (optional)
GCP_PROJECT_ID=my-dev-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/dev-credentials.json

# CORS
CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:3000,http://localhost:3000

# Alerts (optional)
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/dev/webhook/url
```

### Local Services

#### PostgreSQL

```bash
# Via Docker
docker run -d \
  --name qc-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=qc_dev \
  -p 5432:5432 \
  postgres:15-alpine

# Via docker-compose (preferred)
docker-compose up -d postgres
```

#### Redis

```bash
# Via Docker
docker run -d \
  --name qc-redis \
  -p 6379:6379 \
  redis:7-alpine

# Via docker-compose
docker-compose up -d redis
```

### Local Testing

```bash
# Run unit tests
python -m pytest tests/ --ignore=tests/integration -v

# Run with coverage
python -m pytest tests/ --cov=backend --cov-report=html

# Run specific test
python -m pytest tests/test_qc_engine.py -v

# Run with markers
python -m pytest -m unit -v
```

---

## CI/CD Test Environment

### GitHub Actions Environment

**Trigger**: Every push/PR to main or develop branches

**Services**:
- PostgreSQL 15 (auto-started)
- Redis 7 (auto-started)
- Docker buildx (for multi-platform builds)

### Environment Variables (Set by Workflow)

```yaml
env:
  JWT_SECRET_KEY: ci-test-secret
  DATABASE_URL: postgresql://postgres:postgres@127.0.0.1:5432/test_db
  REDIS_URL: redis://127.0.0.1:6379/0
  ENVIRONMENT: testing
  SUPABASE_URL: https://test.supabase.co
  SUPABASE_KEY: test-key
```

### Workflow Stages

```
1. VALIDATE
   ├─ Python syntax check (compileall)
   ├─ Dependency validation
   └─ Import validation

2. TEST
   ├─ Unit tests (pytest)
   ├─ Coverage report
   └─ Test artifacts upload

3. VALIDATE-K8S
   ├─ Helm lint
   ├─ Template rendering
   └─ YAML validation

4. BUILD (if not PR)
   ├─ Docker build
   ├─ Multi-platform (amd64, arm64)
   └─ Push to GHCR

5. DEPLOY-STAGING (if develop)
   ├─ Helm deploy
   └─ Rollout verification

6. DEPLOY-VERCEL (if main)
   └─ Frontend deployment
```

### CI/CD Dependencies Installation

```yaml
# Installed by workflow
- pip install --upgrade pip
- pip install -r requirements.txt
- pip install pytest-cov pytest-xdist
```

**Note**: Uses pip caching to speed up subsequent runs.

### Test Database

```yaml
services:
  postgres:
    image: postgres:15-alpine
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: test_db
    ports: ["5432:5432"]
    options: >-
      --health-cmd "pg_isready -U postgres -d test_db"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

The database is automatically:
1. Created before tests run
2. Health-checked (pg_isready)
3. Destroyed after tests complete

---

## Staging Environment

### Deployment Method: Kubernetes + Helm

```bash
# Helm values override for staging
helm upgrade --install qc-app k8s/charts/qc-app \
  --namespace qc-staging \
  --set environment=staging \
  --set image.tag=develop-latest \
  --values k8s/charts/qc-app/values-staging.yaml
```

### Environment Configuration

**Database**: AWS RDS PostgreSQL (Multi-AZ)

```
Endpoint: staging-qc-db.xxxx.us-east-1.rds.amazonaws.com:5432
Database: qc_staging
Connection pooling: pgBouncer (25 connections)
Backups: Daily, 7-day retention
```

**Cache**: AWS ElastiCache Redis

```
Endpoint: staging-qc-cache.xxxx.ng.0001.use1.cache.amazonaws.com:6379
Node type: cache.t4g.small
Automatic failover: Enabled
Backups: Daily
```

**Storage**: Supabase Storage (Staging Bucket)

```
Bucket: qc-photos-staging
Public: No (signed URLs only)
TTL: 604800 seconds (7 days)
```

### Environment Variables

```bash
# Kubernetes ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: qc-staging-config
  namespace: qc-staging
data:
  FLASK_ENV: production
  ENVIRONMENT: staging
  LOG_LEVEL: INFO
  SUPABASE_STORAGE_BUCKET: qc-photos-staging
  REDIS_URL: redis://qc-redis-staging:6379/0
  CELERY_BROKER_URL: redis://qc-redis-staging:6379/1
```

**Kubernetes Secrets**:
```bash
# Database
DB_HOST: staging-qc-db.xxxx.rds.amazonaws.com
DB_USER: qc_user
DB_PASSWORD: [AWS Secrets Manager]
DATABASE_URL: postgresql://qc_user:pwd@host:5432/qc_staging

# JWT
JWT_SECRET_KEY: [AWS Secrets Manager]

# Supabase
SUPABASE_URL: https://staging-qc.supabase.co
SUPABASE_KEY: [AWS Secrets Manager]
```

### Health Checks

```yaml
readinessProbe:
  httpGet:
    path: /api/health/ready
    port: 5000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 2

livenessProbe:
  httpGet:
    path: /api/health/live
    port: 5000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 3
```

### Auto-Scaling

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 60
  targetMemoryUtilizationPercentage: 70
```

---

## Production Environment

### Deployment Method: Kubernetes + Helm (HA)

```bash
# High-availability deployment
helm upgrade --install qc-app k8s/charts/qc-app \
  --namespace qc-production \
  --set environment=production \
  --set replicaCount=3 \
  --set image.tag=vX.Y.Z \
  --values k8s/charts/qc-app/values-production.yaml \
  --atomic \
  --timeout 10m
```

### Environment Configuration

**Database**: AWS RDS PostgreSQL (Multi-AZ + Read Replicas)

```
Primary: prod-qc-db.xxxx.us-east-1.rds.amazonaws.com:5432
Read Replica 1: prod-qc-db-read1.xxxx.us-east-1.rds.amazonaws.com
Read Replica 2: prod-qc-db-read2.xxxx.us-east-1.rds.amazonaws.com
Database: qc_production
Connection pooling: pgBouncer (50 connections)
Backups: Hourly, 30-day retention, encrypted
Encryption: AWS KMS at-rest
```

**Cache**: AWS ElastiCache Redis (Cluster Mode)

```
Primary: prod-qc-cache.xxxx.ng.0001.use1.cache.amazonaws.com:6379
Read replicas: 3 replicas (automatic failover)
Node type: cache.r7g.xlarge
Automatic failover: Enabled
Encryption: TLS in-transit + KMS at-rest
AOF persistence: Enabled
```

**Storage**: Supabase Storage (Production Bucket)

```
Bucket: qc-photos-production
Public: No (signed URLs only)
TTL: 86400 seconds (24 hours)
Backup: Replicated to S3
```

### Environment Variables

```bash
# Kubernetes ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: qc-production-config
  namespace: qc-production
data:
  FLASK_ENV: production
  ENVIRONMENT: production
  LOG_LEVEL: WARNING
  SUPABASE_STORAGE_BUCKET: qc-photos-production
  REDIS_URL: redis://qc-redis-prod-cluster:6379/0
  CELERY_BROKER_URL: redis://qc-redis-prod-cluster:6379/1
  NEW_RELIC_APP_NAME: "QC Central Kitchen"
  SENTRY_ENVIRONMENT: production
```

**Kubernetes Secrets** (from AWS Secrets Manager):
```bash
# Synced via External Secrets Operator
DATABASE_URL: postgresql://prod_user:pwd@prod-host:5432/qc_production
JWT_SECRET_KEY: [64-char random key]
SUPABASE_URL: https://prod-qc.supabase.co
SUPABASE_KEY: [Production API key]
SENTRY_DSN: https://key@sentry.io/project
NEW_RELIC_LICENSE_KEY: [New Relic key]
```

### High-Availability Configuration

```yaml
# Pod Disruption Budget (maintain 2 healthy pods)
podDisruptionBudget:
  minAvailable: 2

# Pod Anti-Affinity (spread across nodes)
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchExpressions:
        - key: app.kubernetes.io/name
          operator: In
          values:
          - qc-app
      topologyKey: kubernetes.io/hostname

# Replica counts for HA
replicaCount: 3

# Resource limits for predictable performance
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### Production Security

```yaml
# Network Policy (restrict ingress/egress)
networkPolicy:
  enabled: true
  policyTypes:
  - Ingress
  - Egress

# Pod Security Policy
podSecurityPolicy: restricted

# RBAC
serviceAccount: qc-app
rbac:
  create: true
```

### Monitoring & Alerting

**Prometheus Scraping**:
```yaml
prometheus:
  scrape_interval: 15s
  targets:
  - /metrics
  - /actuator/prometheus
```

**Alert Rules**:
```
- High error rate (>5%)
- High latency (p95 > 500ms)
- Memory usage > 80%
- Pod restart loops
- Database connection failures
```

---

## Environment-Specific Dependencies

### Development-Only Packages

```
# requirements-dev.txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-xdist==3.5.0
black==23.12.0
flake8==6.1.0
mypy==1.8.0
ipython==8.20.0
```

Installation:
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### Production-Optimized

```
# Keep only production packages
flask==3.0.0
gunicorn==21.2.0  # WSGI server
redis==5.0.1
celery==5.3.1
prometheus_client==0.16.0

# Do NOT include:
pytest  (test only)
black, flake8, mypy  (development tools)
ipython  (debug shell)
```

---

## Secrets Management

### Local Development

**Store in**: `.env` file (git-ignored)

```bash
echo ".env" >> .gitignore
```

**Never commit**:
- API keys
- Database credentials
- JWT secrets
- Supabase keys

### CI/CD (GitHub Actions)

**Store in**: GitHub Secrets

```
Settings → Secrets and variables → Actions
```

**Reference in workflow**:
```yaml
env:
  JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY }}
  SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
```

### Staging & Production (AWS)

**Store in**: AWS Secrets Manager

```bash
# Create secret
aws secretsmanager create-secret \
  --name qc/staging/db-password \
  --secret-string "password123"

# Retrieve secret
aws secretsmanager get-secret-value \
  --secret-id qc/staging/db-password
```

**Kubernetes Integration**: External Secrets Operator

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1

---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: qc-secrets
spec:
  secretStoreRef:
    name: aws-secrets
    kind: SecretStore
  target:
    name: qc-app-secrets
    creationPolicy: Owner
  data:
  - secretKey: db-password
    remoteRef:
      key: qc/staging/db-password
```

---

## Environment Variables Quick Reference

| Variable | Dev | Test | Staging | Prod | Required |
|----------|-----|------|---------|------|----------|
| FLASK_ENV | development | testing | production | production | Yes |
| ENVIRONMENT | local | testing | staging | production | Yes |
| JWT_SECRET_KEY | dev-secret | ci-secret | (Secrets Manager) | (Secrets Manager) | Yes |
| DATABASE_URL | local:5432 | 127.0.0.1:5432 | RDS endpoint | RDS endpoint | Yes |
| REDIS_URL | 127.0.0.1:6379 | 127.0.0.1:6379 | ElastiCache | ElastiCache | Yes |
| SUPABASE_URL | dev.supabase.co | test.supabase.co | staging.supabase.co | prod.supabase.co | Yes |
| SUPABASE_KEY | dev-key | test-key | (Secrets Manager) | (Secrets Manager) | Yes |
| DEBUG | true | false | false | false | No |
| LOG_LEVEL | DEBUG | INFO | INFO | WARNING | No |

---

## Validation Checklist

### Before Deploying to Staging

- [ ] All environment variables configured in GitHub Secrets
- [ ] Database credentials updated in AWS Secrets Manager
- [ ] Supabase project created for staging
- [ ] JWT secret generated and stored securely
- [ ] Kubernetes namespace created: `qc-staging`
- [ ] RBAC roles and permissions configured
- [ ] Network policies configured (if required)
- [ ] SSL certificates valid
- [ ] Monitoring and alerting configured
- [ ] Backup strategies configured
- [ ] Disaster recovery plan documented

### Before Deploying to Production

- [ ] All staging validation passed
- [ ] Load testing completed (5000+ concurrent users)
- [ ] Security audit completed
- [ ] Penetration testing completed
- [ ] Compliance checks passed (GDPR, data privacy)
- [ ] Disaster recovery tested
- [ ] Rollback procedure tested
- [ ] Monitoring dashboards created
- [ ] Alert thresholds tuned
- [ ] On-call procedures documented
- [ ] Incident response plan reviewed
- [ ] Change management approval obtained

---

## Related Documentation

- [CI/CD Pipeline Troubleshooting](./CI_CD_TROUBLESHOOTING.md)
- [GitHub Secrets Setup](./GITHUB_SECRETS_SETUP.md)
- [Kubernetes Deployment Guide](./KUBERNETES_DEPLOYMENT.md)

---

**Last Updated**: 2026-05-09  
**Version**: 1.0.0  
**Status**: Production Ready
