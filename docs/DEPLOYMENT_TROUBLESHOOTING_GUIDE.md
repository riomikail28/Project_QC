# QC Central Kitchen - Deployment Failure Troubleshooting Guide
================================================================

# 🚨 **DEPLOYMENT FAILURE ANALYSIS**

## **Current Status Assessment**
- **Vercel Deployment**: FAILED
- **Helm CD Deploy**: FAILED  
- **CI/test**: FAILED
- **Supabase Preview**: SUCCESS
- **CI/build**: SKIPPED

---

# 🔍 **ROOT CAUSE ANALYSIS**

## **Most Likely Failure Scenarios**

### **1. Vercel Deployment Failure (Primary)**
**Root Cause**: Python build process failure due to missing or incompatible dependencies
- `backend/app.py` uses `from backend import create_app` - Relative import issue
- Missing `backend/__init__.py` or incorrect import structure
- Python version mismatch with Vercel runtime
- Missing environment variables for Flask app initialization

### **2. CI Test Failure (Cascading)**
**Root Cause**: Test suite failing due to missing test environment setup
- Missing test dependencies in requirements.txt
- Database connection failures in test environment
- Missing environment variables for tests
- Import path issues in test modules

### **3. Helm Deploy Failure (Infrastructure)**
**Root Cause**: Kubernetes deployment configuration issues  
- Missing values.yaml configuration
- Incorrect image references or registry settings
- Missing Kubernetes secrets for environment variables
- Resource constraints or health check failures

### **4. CI Build Skipped (Dependency)**
**Root Cause**: GitHub Actions conditional logic preventing build
- Missing required secrets
- Branch protection rules blocking workflow
- Previous job failures preventing build step

---

# 🛠️ **SYSTEMATIC DEBUGGING APPROACH**

## **Phase 1: Local Environment Debugging**

### **1.1 Python Application Debugging**
```bash
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Test Flask application startup
python backend/app.py

# Check for import errors
python -c "from backend import create_app; print('Imports successful')"

# Test application creation
python -c "from backend import create_app; app = create_app(); print(f'App created: {app}')"
```

### **1.2 Environment Variables Check**
```bash
# Check current environment
env | grep -E "(DB_|REDIS_|JWT_|SUPABASE_)"

# Test database connectivity
python -c "
import os
from supabase import create_client
try:
    client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
    print('Supabase connection successful')
except Exception as e:
    print(f'DB connection failed: {e}')
"
```

### **1.3 Frontend Static Files Check**
```bash
# Verify frontend structure
ls -la frontend/
ls -la frontend/css/
ls -la frontend/js/
ls -la frontend/dashboard/

# Test static file serving
python -m http.server 8000 --directory frontend
```

---

## **Phase 2: CI/CD Pipeline Debugging**

### **2.1 GitHub Actions Local Testing**
```bash
# Install act for local GitHub Actions testing
# Windows (using Chocolatey)
choco install act

# Linux/Mac
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run workflow locally
act -j security-scan
act -j test-and-build
```

### **2.2 Repository Structure Check**
```bash
# Verify critical files exist
test -f backend/__init__.py || echo "Missing backend/__init__.py"
test -f backend/app.py || echo "Missing backend/app.py"
test -f requirements.txt || echo "Missing requirements.txt"
test -f vercel.json || echo "Missing vercel.json"

# Check Python path structure
python -c "
import sys
sys.path.append('.')
try:
    from backend import create_app
    print('Import path works correctly')
except ImportError as e:
    print(f'Import error: {e}')
"
```

### **2.3 Test Suite Debugging**
```bash
# Run tests with verbose output
python -m pytest tests/ -v --tb=short

# Run specific test file
python -m pytest tests/test_routes.py -v

# Check test coverage
python -m pytest --cov=backend tests/

# Install test dependencies if missing
pip install pytest pytest-cov pytest-mock
```

---

## **Phase 3: Vercel Deployment Debugging**

### **3.1 Vercel CLI Commands**
```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Link project
vercel link

# Inspect failed deployment
npx vercel inspect dpl_3hzYG9MUMuKrd4CxNktyQYPBvQyG --logs

# Local development testing
vercel dev

# Check build logs
vercel logs

# Redeploy with debug
vercel --debug
```

### **3.2 Vercel Configuration Fix**
```bash
# Check current vercel.json
cat vercel.json

# Test build locally
vercel build

# Verify Python version compatibility
python --version
# Should match Vercel Python runtime (3.9, 3.10, or 3.11)
```

### **3.3 Environment Variables in Vercel**
```bash
# Set environment variables
vercel env add SUPABASE_URL
vercel env add SUPABASE_KEY
vercel env add REDIS_URL
vercel env add JWT_SECRET

# Pull environment for local testing
vercel env pull .env.local

# Test with pulled environment
vercel dev
```

---

## **Phase 4: Helm/Kubernetes Debugging**

### **4.1 Helm Commands**
```bash
# Check Helm charts
helm lint k8s/charts/

# Dry run deployment
helm install qc-system k8s/charts/ --dry-run --debug

# Check values
helm get values qc-system

# List deployments
helm list

# Uninstall for clean redeploy
helm uninstall qc-system
```

### **4.2 Kubernetes Debugging**
```bash
# Check cluster status
kubectl cluster-info

# Check namespaces
kubectl get namespaces

# Check pods
kubectl get pods -n qc-system

# Check pod logs
kubectl logs -f deployment/qc-system -n qc-system

# Describe pod for errors
kubectl describe pod <pod-name> -n qc-system

# Check services
kubectl get services -n qc-system

# Check ingress
kubectl get ingress -n qc-system
```

### **4.3 Docker Image Debugging**
```bash
# Build image locally
docker build -t qc-system:latest .

# Run container locally
docker run -p 5000:5000 --env-file .env qc-system:latest

# Check container logs
docker logs <container-id>

# Debug container interactively
docker run -it --entrypoint /bin/sh qc-system:latest
```

---

# 🔧 **IMMEDIATE FIXES REQUIRED**

## **Fix 1: Backend Import Structure**
```bash
# Create missing __init__.py files
touch backend/__init__.py

# Update backend/__init__.py with proper imports
cat > backend/__init__.py << 'EOF'
"""
QC Central Kitchen Backend Package
==================================
"""

from backend.app import create_app
from backend.core import create_response
from backend.database import supabase_client

__all__ = ['create_app', 'create_response', 'supabase_client']
EOF
```

## **Fix 2: Vercel Configuration Update**
```json
{
  "version": 2,
  "builds": [
    {
      "src": "backend/app.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "15mb",
        "runtime": "python3.11"
      }
    },
    {
      "src": "frontend/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "backend/app.py"
    },
    {
      "src": "/(.*)",
      "dest": "frontend/$1"
    }
  ],
  "functions": {
    "backend/app.py": {
      "runtime": "python3.11"
    }
  }
}
```

## **Fix 3: Requirements.txt Update**
```txt
Flask==3.0.0
Flask-CORS==4.0.0
supabase==2.11.0
python-dotenv==1.0.0
google-cloud-vision==3.4.5
gunicorn==21.2.0
PyJWT==2.8.0
redis==5.0.1
alembic==1.11.1
psycopg2-binary==2.9.6
prometheus_client==0.16.0
fakeredis==2.1.0
celery==5.3.1
pytest==7.4.0
pytest-cov==4.1.0
pytest-mock==3.11.1
```

## **Fix 4: GitHub Actions Environment Variables**
```yaml
# Add to .github/workflows/ci-cd.yml
env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
  # Add required environment variables
  SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
  SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
  REDIS_URL: ${{ secrets.REDIS_URL }}
  JWT_SECRET: ${{ secrets.JWT_SECRET }}
```

---

# 📋 **COMPREHENSIVE TROUBLESHOOTING CHECKLIST**

## **Environment Setup Checklist**
- [ ] Python 3.11 installed and accessible
- [ ] Node.js 18+ installed for Vercel CLI
- [ ] Virtual environment activated
- [ ] All dependencies installed
- [ ] Environment variables configured
- [ ] Database connectivity verified
- [ ] Redis connectivity verified

## **Build Process Checklist**
- [ ] backend/__init__.py exists and properly configured
- [ ] Import paths work correctly
- [ ] Flask app creates without errors
- [ ] Gunicorn server starts successfully
- [ ] Static files accessible
- [ ] API endpoints respond correctly

## **Testing Checklist**
- [ ] Test dependencies installed
- [ ] Test database configured
- [ ] Unit tests run successfully
- [ ] Integration tests pass
- [ ] API tests validate endpoints
- [ ] Coverage meets requirements

## **Deployment Checklist**
- [ ] Vercel.json configured correctly
- [ ] Environment variables set in Vercel
- [ ] Python runtime compatible
- [ ] Build process completes successfully
- [ ] Deployment health checks pass
- [ ] DNS routing configured

## **Infrastructure Checklist**
- [ ] Kubernetes cluster accessible
- [ ] Helm charts validated
- [ ] Docker registry accessible
- [ ] Secrets configured correctly
- [ ] Resource limits appropriate
- [ ] Health checks configured

---

# 🚀 **PRODUCTION-READY SOLUTIONS**

## **Solution 1: Fixed Deployment Pipeline**

### **Create .github/workflows/fix-deployment.yml**
```yaml
name: Fix Deployment Pipeline

on:
  workflow_dispatch:
  push:
    branches: [main]

jobs:
  fix-deployment:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
        
    - name: Create missing __init__.py
      run: |
        touch backend/__init__.py
        
    - name: Test imports
      run: |
        python -c "from backend import create_app; print('Import success')"
        
    - name: Run tests
      run: |
        python -m pytest tests/ -v --tb=short
        
    - name: Deploy to Vercel
      run: |
        npm i -g vercel
        vercel --prod --token ${{ secrets.VERCEL_TOKEN }}
```

## **Solution 2: Zero-Downtime Deployment**

### **Create blue-green deployment script**
```bash
#!/bin/bash
# blue-green-deploy.sh

set -e

CURRENT_ENV_VER=$(vercel env ls | grep production | wc -l)
NEW_ENV_VER="v$((CURRENT_ENV_VER + 1))"

echo "Deploying blue-green version: $NEW_ENV_VER"

# Deploy to new environment
vercel --prod --confirm

# Health check
sleep 30
curl -f https://qc-system.vercel.app/api/health || exit 1

echo "Deployment successful: $NEW_ENV_VER"
```

## **Solution 3: Comprehensive Monitoring**

### **Add health check endpoint**
```python
# backend/routes/health.py
from flask import Blueprint, jsonify
import os
import redis
from supabase import create_client

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """Comprehensive health check"""
    status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {}
    }
    
    # Database check
    try:
        client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
        # Simple ping
        status['services']['database'] = 'healthy'
    except Exception as e:
        status['services']['database'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Redis check
    try:
        r = redis.from_url(os.getenv('REDIS_URL'))
        r.ping()
        status['services']['redis'] = 'healthy'
    except Exception as e:
        status['services']['redis'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    return jsonify(status), 200 if status['status'] == 'healthy' else 503
```

---

# 🔄 **ROLLBACK STRATEGY**

## **Immediate Rollback Commands**
```bash
# Vercel rollback
vercel rollback [deployment-url]

# Helm rollback
helm rollback qc-system 1

# Git rollback
git revert --no-commit HEAD~1
git push origin main

# Emergency: Disable application
vercel rm --yes
```

## **Rollback Validation**
```bash
# Test rollback
curl -f https://qc-system.vercel.app/api/health
kubectl get pods -n qc-system
helm status qc-system
```

---

# 📊 **EXPECTED RECOVERY TIME**

- **Local debugging**: 15-30 minutes
- **CI/CD fix**: 30-45 minutes  
- **Vercel deployment**: 10-15 minutes
- **Helm deployment**: 20-30 minutes
- **Total recovery**: 1-2 hours

---

# 🎯 **SUCCESS CRITERIA**

- [ ] All CI/CD jobs pass
- [ ] Vercel deployment succeeds
- [ ] Helm deployment completes
- [ ] Health checks pass
- [ ] API endpoints responsive
- [ ] No new errors in logs
- [ ] Zero-downtime achieved

---

**Execute this troubleshooting plan systematically. Start with Phase 1 (Local debugging), then proceed through each phase. Document all findings and fixes applied.**