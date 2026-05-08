# Vercel Deployment - Complete Command Reference

## Quick Start (5 Minutes)

```bash
# 1. Update dependencies
pip install -r requirements.txt

# 2. Test locally
python -m pytest tests/ -v

# 3. Commit & push
git add .
git commit -m "fix: migrate from psycopg2 to psycopg v3"
git push origin main

# 4. Monitor build on Vercel
vercel logs --follow
```

---

## Detailed Commands

### Phase 1: Prepare Environment (10 minutes)

```bash
# Activate Python virtual environment
source .venv/bin/activate                    # macOS/Linux
.venv\Scripts\activate                       # Windows PowerShell

# Verify Python version
python --version                             # Should be 3.11.x

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### Phase 2: Install Dependencies (2 minutes)

```bash
# Install all required packages
pip install -r requirements.txt

# Verify psycopg v3 installed
python -c "import psycopg; print(f'psycopg {psycopg.__version__}')"

# List installed packages with versions
pip list | grep -E "psycopg|SQLAlchemy|Flask|gunicorn"
```

Expected output:
```
psycopg   3.1.8 or higher
SQLAlchemy    2.0.23
Flask         3.0.0
gunicorn      21.2.0
```

### Phase 3: Verify Code Migration (5 minutes)

```bash
# Check db_utils.py imports
python -c "from backend.service.db_utils import db_cursor, get_conn; print('✓ Imports OK')"

# Scan for old psycopg2 imports
grep -r "import psycopg2" backend/
# Should return NOTHING

# Check vercel.json syntax
python -m json.tool < vercel.json | head -20

# Check runtime.txt
cat runtime.txt
# Should show: python-3.11
```

### Phase 4: Run Full Test Suite (3-5 minutes)

```bash
# Run all unit tests
python -m pytest tests/ -v --tb=short

# Run with coverage
python -m pytest tests/ --cov=backend --cov-report=term-missing

# Test specific module
python -m pytest tests/test_qc_engine.py -v

# Test database utilities
python -c "
import os
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test_db'
from backend.service.db_utils import get_conn
try:
    conn = get_conn()
    print('✓ Database connection works')
    conn.close()
except Exception as e:
    print(f'⚠ Database test failed (expected if no local DB): {e}')
"
```

### Phase 5: Test Flask App (3 minutes)

```bash
# Start Flask development server
python -m backend.app

# In another terminal, test endpoints
curl http://localhost:5000/health

# Test API endpoint
curl http://localhost:5000/api/

# Stop server
# Ctrl+C
```

### Phase 6: Verify Vercel Configuration (2 minutes)

```bash
# Validate JSON
python -m json.tool < vercel.json > /dev/null && echo "✓ vercel.json valid"

# Check required fields
grep -q "runtimeVersion" vercel.json && echo "✓ Runtime version specified"
grep -q "@vercel/python" vercel.json && echo "✓ Python builder specified"

# Verify entry point
grep -q "backend/app.py" vercel.json && echo "✓ Entry point correct"
```

### Phase 7: Git Commit (2 minutes)

```bash
# Check what changed
git status

# Show diff
git diff requirements.txt
git diff backend/service/db_utils.py
git diff vercel.json

# Stage all changes
git add requirements.txt backend/service/db_utils.py vercel.json

# Create commit
git commit -m "fix: migrate from psycopg2 to psycopg v3 for Vercel Python 3.12 compatibility

BREAKING: psycopg2-binary replaced with psycopg v3
- Updated requirements.txt: psycopg[binary]>=3.1.8
- Migrated db_utils.py to psycopg v3 API
- Updated vercel.json with Python 3.11.9 runtime
- Updated cursor creation: cursor_factory -> row_factory

Why: psycopg2-binary fails to compile on Vercel's Python 3.12 runtime.
psycopg v3 is pure Python by default, compatible with all platforms.

Migration impact:
- Connection strings unchanged (same format)
- SQLAlchemy unchanged (auto-detects driver)
- Query syntax unchanged (backward compatible)
- Minimal code changes (3 files only)

Tests: All unit tests pass locally
Verified: psycopg v3 imports, API compatibility, vercel config"

# View commit
git log -1

# Push to main
git push origin main
```

### Phase 8: Monitor Vercel Build (10 minutes)

```bash
# Install Vercel CLI (if not already installed)
npm install -g vercel

# Option A: Watch logs live
vercel logs --follow

# Option B: List recent deployments
vercel list

# Option C: Get specific deployment logs
vercel logs <deployment-url>

# Option D: Check deployment status
vercel status

# Option E: View project info
vercel projects ls
```

Expected build log output:
```
$ pip install -r requirements.txt
...
Collecting psycopg[binary]>=3.1.8,<4.0.0
  Downloading psycopg-3.1.8-py3-none-...
Installing collected packages: psycopg, ...
Successfully installed psycopg-3.1.8
...
✓ Build successful
```

### Phase 9: Test Production Deployment (5 minutes)

```bash
# Get Vercel app URL (from Vercel dashboard or):
VERCEL_URL=$(vercel ls | grep "your-project" | awk '{print $3}')

# Test health endpoint
curl https://$VERCEL_URL/api/health

# Test database connectivity
curl https://$VERCEL_URL/api/database/check

# Check production logs
vercel logs https://$VERCEL_URL

# Test specific endpoint
curl -H "Content-Type: application/json" \
     https://$VERCEL_URL/api/endpoint
```

### Phase 10: Verify Production Environment (5 minutes)

```bash
# Check environment variables are set on Vercel
vercel env pull

# Should create .env.local with production vars
cat .env.local | grep DATABASE_URL

# Verify all required env vars present
for var in DATABASE_URL SUPABASE_URL SUPABASE_KEY JWT_SECRET_KEY ENVIRONMENT; do
    if grep -q "$var" .env.local; then
        echo "✓ $var configured"
    else
        echo "✗ $var MISSING"
    fi
done
```

---

## Debugging Commands

### If Build Fails

```bash
# Check exact error
vercel logs --format=json | jq '.message'

# Rebuild with verbose output
vercel rebuild

# Test build locally
vercel build --debug

# Check Python version used
vercel env list | grep PYTHON
```

### If Runtime Errors

```bash
# Stream live logs
vercel logs --follow --since 5m

# Get error stack traces
vercel logs | grep -A 5 "ERROR"

# Check function invocations
vercel analytics

# Test endpoint with verbose output
curl -v https://your-url/api/endpoint
```

### If Database Connection Fails

```bash
# Check DATABASE_URL
vercel env pull
cat .env.local | grep DATABASE_URL

# Verify format is correct
# Should be: postgresql://user:password@host:port/database

# Test connection string locally
python -c "
import os
os.environ['DATABASE_URL'] = open('.env.local').read().split('DATABASE_URL=')[1].split('\n')[0]
from backend.service.db_utils import get_conn
try:
    get_conn()
    print('✓ Connection works')
except Exception as e:
    print(f'✗ Connection failed: {e}')
"
```

---

## Rollback Commands

If deployment needs to be reverted:

```bash
# Option 1: Revert last commit
git revert HEAD
git push origin main
# Vercel auto-redeploys from main

# Option 2: Rollback via Vercel CLI
vercel rollback                          # Interactive prompt
vercel rollback <deployment-id>          # Specific deployment

# Option 3: Manual revert in Git
git checkout HEAD~1 requirements.txt
git checkout HEAD~1 backend/service/db_utils.py
git checkout HEAD~1 vercel.json
git commit -m "revert: rollback psycopg migration"
git push origin main

# Option 4: Switch to previous branch
git checkout previous-stable-branch
git push origin main
```

---

## Validation Commands

### Full Validation Script

```bash
#!/bin/bash
# Run comprehensive validation

echo "=== VERCEL DEPLOYMENT VALIDATION ==="

# 1. Check dependencies
echo "1. Checking requirements.txt..."
if grep -q "psycopg2-binary" requirements.txt; then
    echo "  ✗ FAIL: psycopg2-binary still present"
    exit 1
fi
grep "psycopg" requirements.txt
echo "  ✓ PASS"

# 2. Check code
echo "2. Checking source code..."
if grep -r "psycopg2" backend/ --include="*.py"; then
    echo "  ✗ FAIL: psycopg2 imports found"
    exit 1
fi
grep "row_factory=" backend/service/db_utils.py
echo "  ✓ PASS"

# 3. Check config
echo "3. Checking configuration..."
python -m json.tool < vercel.json > /dev/null || exit 1
grep "python-3.11" runtime.txt || exit 1
echo "  ✓ PASS"

# 4. Test imports
echo "4. Testing imports..."
python -c "import psycopg; from backend import create_app" || exit 1
echo "  ✓ PASS"

# 5. Run tests
echo "5. Running tests..."
python -m pytest tests/ -q || exit 1
echo "  ✓ PASS"

echo ""
echo "=== ALL VALIDATIONS PASSED ==="
echo "Ready for Vercel deployment!"
```

Save as `scripts/validate.sh` and run:
```bash
chmod +x scripts/validate.sh
./scripts/validate.sh
```

---

## Dependency Inspection Commands

```bash
# Show all installed packages with versions
pip list

# Show only database-related packages
pip list | grep -E "psycopg|sql|postgres"

# Show detailed info about psycopg
pip show psycopg

# Check package dependencies
pipdeptree | grep -A 5 psycopg

# Export current environment
pip freeze > requirements-current.txt

# Compare with requirements.txt
diff requirements.txt requirements-current.txt
```

---

## Production Verification Commands

After deployment:

```bash
# 1. Test connectivity
curl -I https://your-project.vercel.app/api/health

# 2. Check database
curl https://your-project.vercel.app/api/database/test

# 3. Verify psycopg version (if endpoint available)
curl https://your-project.vercel.app/api/info/psycopg

# 4. Check logs for errors
vercel logs | grep -i error

# 5. Monitor performance
vercel analytics | head -20

# 6. Full health check
./scripts/health-check.sh your-project.vercel.app
```

---

## Summary Table

| Phase | Duration | Key Commands |
|-------|----------|--------------|
| Prepare | 10 min | `python --version`, `pip install --upgrade pip` |
| Install | 2 min | `pip install -r requirements.txt` |
| Verify | 5 min | `python -c "import psycopg"`, `git diff` |
| Test | 5 min | `python -m pytest tests/ -v` |
| Config | 2 min | `python -m json.tool < vercel.json` |
| Commit | 2 min | `git add`, `git commit`, `git push` |
| Build | 10 min | `vercel logs --follow` |
| Validate | 5 min | `curl https://url/api/health` |
| **Total** | **~40 min** | — |

---

## Cheat Sheet

```bash
# Quick deployment
pip install -r requirements.txt && \
python -m pytest tests/ -q && \
git add . && \
git commit -m "fix: psycopg migration" && \
git push origin main

# Watch deployment
vercel logs --follow

# Rollback if needed
vercel rollback

# Verify live
curl https://your-project.vercel.app/api/health
```

---

**Status**: ✓ COMPLETE  
**Date**: 2026-05-09  
**Version**: 1.0.0
