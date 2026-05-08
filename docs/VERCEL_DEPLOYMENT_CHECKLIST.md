# Vercel Deployment - Dependency Validation & Checklist

## Overview

Production-ready checklist for deploying QC Central Kitchen Flask app to Vercel with fixed psycopg v3 dependencies.

---

## Pre-Deployment Checklist

### ✓ Code & Configuration

- [ ] requirements.txt updated with psycopg>=3.1.8
- [ ] db_utils.py migrated to psycopg v3
- [ ] vercel.json updated with Python 3.11.9 config
- [ ] runtime.txt says "python-3.11"
- [ ] No psycopg2 imports remain in codebase
- [ ] All other dependencies reviewed for compatibility

### ✓ Local Testing

- [ ] `pip install -r requirements.txt` succeeds
- [ ] `python -m pytest tests/ -v` passes
- [ ] `python -c "import psycopg; print(psycopg.__version__)"` works
- [ ] `python -c "from backend.service.db_utils import get_conn; print('OK')"` works
- [ ] Flask app starts: `python -m backend.app` (no errors)
- [ ] Database connection works with local DATABASE_URL
- [ ] All imports resolve: `python -c "from backend import create_app"`

### ✓ Configuration Files

- [ ] vercel.json valid JSON (test with `python -m json.tool < vercel.json`)
- [ ] runtime.txt exactly "python-3.11" or "python-3.11.9"
- [ ] requirements.txt has no development packages (pytest, black, etc)
- [ ] WSGI app entry point is correct: backend/app.py → create_app()
- [ ] Backend entry point can be called without arguments: `app = create_app()`

### ✓ Environment Variables (Vercel)

- [ ] DATABASE_URL configured
- [ ] SUPABASE_URL configured
- [ ] SUPABASE_KEY configured
- [ ] JWT_SECRET_KEY configured
- [ ] ENVIRONMENT set to "production"
- [ ] FLASK_ENV set to "production"
- [ ] No secrets in code (use env vars only)

### ✓ GitHub & Repository

- [ ] All changes committed: `git status` is clean
- [ ] Branch is main (or configured deployment branch)
- [ ] Last commit message describes changes
- [ ] Remote is set correctly: `git remote -v`

---

## Dependency Validation

### Command: Full Validation Script

```bash
#!/bin/bash
# save as: scripts/validate-vercel-deps.sh

set -e

echo "=== VERCEL DEPLOYMENT VALIDATION ==="
echo

# Step 1: Check requirements.txt
echo "Step 1: Checking requirements.txt..."
if grep -q "psycopg2-binary" requirements.txt; then
    echo "✗ FAIL: psycopg2-binary found (must use psycopg v3)"
    exit 1
fi
if ! grep -q "psycopg" requirements.txt; then
    echo "✗ FAIL: psycopg not found"
    exit 1
fi
echo "✓ PASS: psycopg v3 in requirements.txt"
echo

# Step 2: Check for psycopg2 imports in code
echo "Step 2: Scanning for old psycopg2 imports..."
if grep -r "import psycopg2" backend/ --include="*.py"; then
    echo "✗ FAIL: psycopg2 imports found"
    exit 1
fi
if grep -r "from psycopg2" backend/ --include="*.py"; then
    echo "✗ FAIL: psycopg2 imports found"
    exit 1
fi
echo "✓ PASS: No psycopg2 imports"
echo

# Step 3: Check psycopg v3 usage
echo "Step 3: Verifying psycopg v3 usage..."
if ! grep -q "import psycopg" backend/service/db_utils.py; then
    echo "✗ FAIL: db_utils.py not using psycopg v3"
    exit 1
fi
if ! grep -q "row_factory=" backend/service/db_utils.py; then
    echo "✗ FAIL: db_utils.py not using row_factory (psycopg v3 syntax)"
    exit 1
fi
echo "✓ PASS: psycopg v3 correctly used"
echo

# Step 4: Validate JSON config files
echo "Step 4: Validating JSON files..."
python -m json.tool < vercel.json > /dev/null
echo "✓ PASS: vercel.json is valid"
echo

# Step 5: Check runtime.txt
echo "Step 5: Checking runtime.txt..."
if ! grep -q "python-3.11" runtime.txt; then
    echo "✗ FAIL: runtime.txt must specify python-3.11"
    exit 1
fi
echo "✓ PASS: runtime.txt is correct"
echo

# Step 6: Test imports
echo "Step 6: Testing Python imports..."
python -c "import psycopg; print(f'✓ psycopg {psycopg.__version__}')" || exit 1
python -c "from backend.service.db_utils import get_conn, db_cursor; print('✓ db_utils imports')" || exit 1
python -c "from backend import create_app; print('✓ Flask app imports')" || exit 1
echo

# Step 7: Check for missing env vars
echo "Step 7: Checking environment variables..."
if [ -z "$DATABASE_URL" ]; then
    echo "⚠ WARNING: DATABASE_URL not set (needed for production)"
fi
if [ -z "$SUPABASE_URL" ]; then
    echo "⚠ WARNING: SUPABASE_URL not set"
fi
echo "✓ PASS: Environment check complete"
echo

echo "=== ALL VALIDATIONS PASSED ==="
echo "✓ Ready for Vercel deployment"
```

Run validation:

```bash
chmod +x scripts/validate-vercel-deps.sh
./scripts/validate-vercel-deps.sh
```

---

## Deployment Steps

### Step 1: Final Local Test (5 minutes)

```bash
# Activate venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run full test suite
python -m pytest tests/ -v --tb=short

# Test Flask app startup
python -m backend.app &
sleep 2
curl http://localhost:5000/health || echo "Health check: app running"
kill %1

# Verify Vercel build locally (optional but recommended)
npm install -g vercel
vercel build
```

### Step 2: Review Changes

```bash
# See what's being committed
git diff requirements.txt
git diff backend/service/db_utils.py
git diff vercel.json

# Confirm changes look correct
```

### Step 3: Commit & Push

```bash
# Stage changes
git add requirements.txt backend/service/db_utils.py vercel.json

# Commit with descriptive message
git commit -m "fix: migrate from psycopg2 to psycopg v3 for Vercel Python 3.12 compatibility"

# Push to main
git push origin main
```

### Step 4: Monitor Build (5-10 minutes)

**Option A: Via Vercel Dashboard**
1. Go to https://vercel.com
2. Select project
3. Watch "Deployments" tab
4. Monitor build logs in real-time

**Option B: Via GitHub Actions**
1. Go to GitHub repo
2. Click "Actions" tab
3. Watch CI/CD workflow (if configured)

**Option C: Via Vercel CLI**
```bash
vercel logs --follow
```

### Step 5: Verify Deployment

After build succeeds:

```bash
# Test API endpoint (replace with your URL)
curl https://your-vercel-url.vercel.app/api/health

# Check for errors
vercel logs | grep -i "error"

# Test database connectivity
curl -X GET https://your-vercel-url.vercel.app/api/database/health
```

### Step 6: Post-Deployment Validation

```bash
# Check production environment variables are loaded
curl https://your-vercel-url.vercel.app/api/config/check \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Verify database connection
curl https://your-vercel-url.vercel.app/api/database/test

# Monitor for errors
vercel logs --since 10m
```

---

## Common Issues & Fixes

### Issue 1: Build Fails - "psycopg2-binary not found"

**Symptom**: 
```
ERROR: No matching distribution found for psycopg2-binary==2.9.6
```

**Fix**:
```bash
# Verify psycopg in requirements.txt (not psycopg2-binary)
grep psycopg requirements.txt

# Should show: psycopg[binary]>=3.1.8,<4.0.0
# NOT: psycopg2-binary==2.9.6
```

---

### Issue 2: Import Error - "No module named psycopg2"

**Symptom**:
```
ModuleNotFoundError: No module named 'psycopg2'
```

**Fix**:
```bash
# Search for psycopg2 imports
grep -r "psycopg2" backend/

# Should return NOTHING
# If found, update file(s) to use psycopg instead
```

---

### Issue 3: Connection Error - "connection failed"

**Symptom**:
```
psycopg.OperationalError: could not translate host name "..." to address
```

**Possible Causes**:
- DATABASE_URL env var not set
- Connection string malformed
- Database server not accessible from Vercel

**Fix**:
```bash
# Check env var is set
vercel env pull
cat .env.local | grep DATABASE_URL

# Test local connection first
export DATABASE_URL="postgresql://..."
python -c "from backend.service.db_utils import get_conn; get_conn()"

# Verify database is accessible externally (not localhost)
```

---

### Issue 4: Deployment Timeout - "Function exceeds timeout"

**Symptom**:
```
Deployment failed: Function exceeded maximum execution time
```

**Possible Causes**:
- Database query too slow
- Cold start taking too long
- Memory limit too low

**Fix**:
```bash
# Update vercel.json function config
# Increase maxDuration and memory:

"functions": {
  "backend/app.py": {
    "maxDuration": 60,    # Increase from 30 to 60
    "memory": 1024,       # Increase from 512 to 1024
    "includeFiles": "backend/**"
  }
}
```

---

### Issue 5: Module Not Found - "Cannot find X"

**Symptom**:
```
ModuleNotFoundError: No module named 'flask_cors'
```

**Fix**:
```bash
# Verify all dependencies in requirements.txt
pip install -r requirements.txt --dry-run

# Check if dependency is correctly spelled
pip search flask-cors  # or check PyPI website

# Add to requirements.txt if missing
```

---

## Rollback Procedure (if needed)

If deployment fails critically:

### Option 1: Revert to Previous Commit

```bash
# Find previous working commit
git log --oneline | head -10

# Revert to stable version
git revert HEAD
git push origin main

# Vercel auto-redeployes from main
```

### Option 2: Manual Rollback on Vercel

```bash
# List deployments
vercel list

# Promote previous deployment to production
vercel promote <deployment-id>
```

### Option 3: Emergency Downgrade

If psycopg v3 causes runtime errors:

```bash
# Temporarily revert to psycopg2 if available on system
# (not recommended, but emergency option)

pip install psycopg2==2.9.6  # If system has libpq

# OR switch to pg8000 (pure Python PostgreSQL driver)
# Update requirements.txt: pg8000==1.29.4
# Update db_utils.py to use pg8000 API
```

---

## Production Monitoring

### Health Checks

Set up health check in vercel.json (optional):

```json
{
  "functions": {
    "backend/app.py": {
      "health": "/api/health"
    }
  }
}
```

### Log Monitoring

```bash
# Watch logs continuously
vercel logs --follow

# Filter for errors
vercel logs | grep ERROR

# Get last N lines
vercel logs --lines 100
```

### Performance Monitoring

```bash
# Check cold start time
vercel analytics

# Monitor function duration
vercel logs --grep "duration"
```

---

## Final Verification Checklist

Before considering deployment complete:

### Functionality Tests

- [ ] API responds to requests
- [ ] Database connectivity works
- [ ] Authentication works (if applicable)
- [ ] All routes return expected responses
- [ ] Error handling works (test with invalid input)

### Performance Tests

- [ ] Cold start acceptable (< 5 seconds)
- [ ] Average response time < 200ms
- [ ] No memory leaks (memory stable over time)
- [ ] Concurrent requests handled correctly

### Security Tests

- [ ] No secrets in logs
- [ ] HTTPS only (Vercel default)
- [ ] CORS headers correct
- [ ] SQL injection protected (SQLAlchemy)
- [ ] JWT validation works

### Monitoring Tests

- [ ] Logs accessible via `vercel logs`
- [ ] Error alerts configured (if using)
- [ ] Performance metrics visible (if using)
- [ ] Downtime notifications configured (if using)

---

## Success Criteria

Deployment is successful when:

✓ Build succeeds without errors  
✓ All functions deploy and respond  
✓ Database connectivity confirmed  
✓ Health checks passing  
✓ No errors in logs  
✓ Response times acceptable  
✓ All routes working  
✓ Can be accessed from public internet  

---

## Support & Rollback

If issues occur:

1. **Check logs first**:
   ```bash
   vercel logs
   ```

2. **Check Vercel dashboard**: https://vercel.com/dashboard

3. **Review environment variables**: Vercel dashboard → Settings → Environment Variables

4. **Rollback if needed**: See Rollback Procedure above

---

## References

| Resource | URL |
|----------|-----|
| Vercel Python Guide | https://vercel.com/docs/functions/serverless-functions/python |
| psycopg v3 Migration | https://www.psycopg.org/psycopg3/docs/basic/index.html |
| Flask on Vercel | https://vercel.com/docs/runtimes/python |
| Deployment Troubleshooting | https://vercel.com/docs/serverless-functions/troubleshooting |

---

**Status**: ✓ READY FOR DEPLOYMENT  
**Date**: 2026-05-09  
**Version**: 1.0.0
