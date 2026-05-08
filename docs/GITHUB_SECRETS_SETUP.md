# GitHub Actions Secrets Configuration Guide

## Quick Setup (5 minutes)

### Step 1: Navigate to Repository Settings

1. Go to your GitHub repository
2. Click **Settings** tab
3. In left sidebar, go to **Secrets and variables** → **Actions**

### Step 2: Add Required Secrets

Click **"New repository secret"** and add each secret below:

#### CRITICAL: Kubernetes Configuration

```
Name: KUBE_CONFIG_DATA
Value: [base64-encoded kubeconfig file]

How to generate:
  # On your machine with kubectl access:
  cat ~/.kube/config | base64 -w0 | xclip -selection clipboard
  
  # Or on Windows:
  certutil -encode C:\Users\[USER]\.kube\config config.txt
  # Then convert the entire output to base64 online
```

#### CRITICAL: Authentication Keys

```
Name: JWT_SECRET_KEY
Value: [32+ character random string]

How to generate:
  # On macOS/Linux:
  openssl rand -base64 32
  
  # On Windows (PowerShell):
  [Convert]::ToBase64String((1..32 | ForEach-Object {[byte](Get-Random -Minimum 0 -Maximum 256)}))
```

```
Name: DB_PASSWORD
Value: [Complex PostgreSQL password]

Example: MyP@ssw0rd!Secure#2024
Requirements:
  - 12+ characters
  - Mix of uppercase, lowercase, numbers, special chars
  - No spaces or shell-special characters
```

#### CRITICAL: Supabase API Keys

```
Name: SUPABASE_URL
Value: https://YOUR_PROJECT.supabase.co

Get from:
  1. supabase.com dashboard
  2. Project → Settings → General
  3. Copy "Project URL"
```

```
Name: SUPABASE_KEY
Value: [Your Supabase anon key]

Get from:
  1. supabase.com dashboard
  2. Project → Settings → API
  3. Copy "anon" key (public)
```

#### OPTIONAL: Vercel Deployment

```
Name: VERCEL_TOKEN
Value: [Your Vercel CLI token]

Get from:
  1. vercel.com → Settings → Tokens
  2. Create new token
  3. Copy token value
```

```
Name: VERCEL_ORG_ID
Value: [Your Vercel organization ID]

Get from:
  1. vercel.com → Settings → General
  2. Look for "Vercel ID"
```

```
Name: VERCEL_PROJECT_ID
Value: [Your Vercel project ID]

Get from:
  1. vercel.com → Project → Settings
  2. Look for "Project ID"
```

### Step 3: Verify Secrets

Run a test workflow to verify secrets are configured:

```yaml
# Add this temporary job to test secrets
name: Test Secrets

on: workflow_dispatch

jobs:
  test-secrets:
    runs-on: ubuntu-latest
    steps:
      - name: Check critical secrets
        run: |
          [[ -n "${{ secrets.KUBE_CONFIG_DATA }}" ]] && echo "✓ KUBE_CONFIG_DATA" || echo "✗ KUBE_CONFIG_DATA missing"
          [[ -n "${{ secrets.JWT_SECRET_KEY }}" ]] && echo "✓ JWT_SECRET_KEY" || echo "✗ JWT_SECRET_KEY missing"
          [[ -n "${{ secrets.DB_PASSWORD }}" ]] && echo "✓ DB_PASSWORD" || echo "✗ DB_PASSWORD missing"
          [[ -n "${{ secrets.SUPABASE_URL }}" ]] && echo "✓ SUPABASE_URL" || echo "✗ SUPABASE_URL missing"
          [[ -n "${{ secrets.SUPABASE_KEY }}" ]] && echo "✓ SUPABASE_KEY" || echo "✗ SUPABASE_KEY missing"
```

---

## Detailed Setup Instructions

### Setup Kubernetes kubeconfig Base64

**Prerequisites**: kubectl configured with your cluster

#### macOS/Linux:

```bash
# Step 1: Get kubeconfig path
echo $KUBECONFIG  # Usually ~/.kube/config

# Step 2: Base64 encode it
base64 < ~/.kube/config | pbcopy

# Step 3: Paste into GitHub secret

# Verify it's correct:
echo "$KUBE_CONFIG_DATA" | base64 -D | head -20
```

#### Windows (PowerShell):

```powershell
# Step 1: Read kubeconfig
$kubeconfig = Get-Content -Path "$env:USERPROFILE\.kube\config" -Raw

# Step 2: Convert to base64
$base64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($kubeconfig))

# Step 3: Copy to clipboard
$base64 | Set-Clipboard

# Step 4: Paste into GitHub secret

# Verify it's correct:
[System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($base64)) | head -20
```

#### Docker Container:

```bash
# If kubeconfig is in a pod
kubectl get secret kubeconfig-secret -o jsonpath='{.data.config}' | base64

# Or from config map
kubectl get configmap kubeconfig-cm -o jsonpath='{.data.config}'
```

### Setup JWT Secret Key

**What it is**: Encryption key for JWT tokens (authentication)  
**Length**: Must be 32+ characters  
**Uniqueness**: Must be random and unique per environment

#### Generate Methods:

```bash
# Method 1: OpenSSL (Recommended)
openssl rand -base64 32

# Method 2: Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Method 3: /dev/urandom
head -c 32 /dev/urandom | base64

# Output example:
# kT9mL7pQ2xY8vN3jH5bW6cZ1aF4gR9sE
```

**Never use**:
- Simple passwords like "secret123"
- Predictable values
- Same key across environments

### Setup Database Password

**What it is**: PostgreSQL password  
**Length**: 12+ characters minimum  
**Requirements**: Mix of upper, lower, numbers, special chars

#### Generate Methods:

```bash
# Method 1: OpenSSL (Recommended)
openssl rand -base64 20

# Method 2: Python (URL-safe)
python -c "import secrets; print(secrets.token_urlsafe(20))"

# Method 3: Manual (pattern)
# Combine: [SpecialChar][Uppercase][Lowercase][Number]
# Example: @MySecurePass2024!

# Verify it has complexity:
# - At least one uppercase: A-Z
# - At least one lowercase: a-z
# - At least one number: 0-9
# - At least one special char: !@#$%^&*
```

**Avoid characters in passwords**:
- Spaces: ` ` (breaks shell)
- Quotes: `'` `"` (breaks parsing)
- Backslashes: `\` (escaping issues)
- Semicolons: `;` (command terminator)
- Dollar signs: `$` (variable expansion)

**Recommended characters**:
```
Safe: @#$%^&*_+-=
Good examples:
- P@ss2024!Secure
- MyDB#Pass_2024
- K9*mX2$vL5@wQ
```

### Setup Supabase Keys

**Prerequisites**: supabase.com account with active project

#### Step 1: Get SUPABASE_URL

```
1. Log in to supabase.com
2. Select your project
3. Click "Settings" in left sidebar
4. Click "General" tab
5. Find "Project URL" section
6. Copy the URL (looks like: https://xxxxxxxxxxxx.supabase.co)
7. Add to GitHub secret
```

#### Step 2: Get SUPABASE_KEY

```
1. Stay in Settings → General
2. Scroll to "API" section
3. Copy "anon public" key (NOT the service_role key)
4. This is your SUPABASE_KEY
5. Add to GitHub secret
```

**Important**: 
- Use ANON key (public), NOT service_role key
- Service role key stays secret (use in backend only)
- Anon key is safe to commit to repo (read-only)

### Setup Vercel Secrets (Optional)

**Prerequisites**: vercel.com account

#### Step 1: Generate Vercel Token

```
1. Log in to vercel.com
2. Click avatar → Settings
3. Go to "Tokens" tab
4. Click "Create New"
5. Name: "github-actions"
6. Scope: "Full Access" or "Read + Write"
7. Copy token and add to GitHub as VERCEL_TOKEN
```

#### Step 2: Get Organization & Project IDs

```
1. Go to vercel.com dashboard
2. Select your project
3. Click "Settings" tab
4. Find:
   - "Vercel ID" (Organization ID) → VERCEL_ORG_ID
   - "Project ID" (Project ID) → VERCEL_PROJECT_ID
5. Copy both to GitHub
```

---

## Environment-Specific Configurations

### Staging Environment

```
# GitHub Environment: "staging"
# Settings → Environments → staging

Secrets:
- KUBE_CONFIG_DATA: staging-cluster-kubeconfig
- JWT_SECRET_KEY: staging-jwt-secret
- DB_PASSWORD: staging-db-password
- SUPABASE_URL: https://staging.supabase.co
- SUPABASE_KEY: staging-anon-key

Variables (visible):
- HELM_NAMESPACE: qc-staging
- IMAGE_REPOSITORY: ghcr.io/your-org/qc-app
```

### Production Environment

```
# GitHub Environment: "production"
# Settings → Environments → production

Secrets (same as above but for production)
- KUBE_CONFIG_DATA: prod-cluster-kubeconfig
- JWT_SECRET_KEY: prod-jwt-secret
- DB_PASSWORD: prod-db-password
- SUPABASE_URL: https://prod.supabase.co
- SUPABASE_KEY: prod-anon-key

Variables (visible):
- HELM_NAMESPACE: qc-production
- IMAGE_REPOSITORY: ghcr.io/your-org/qc-app
```

### Frontend (Vercel)

```
# GitHub Environment: "production-frontend"

Secrets:
- VERCEL_TOKEN: your-vercel-token
- VERCEL_ORG_ID: your-org-id
- VERCEL_PROJECT_ID: your-project-id

Public Variables:
- NEXT_PUBLIC_API_BASE_URL: https://api.example.com
```

---

## Testing & Validation

### Test Secrets Access in Workflow

Add to workflow temporarily:

```yaml
- name: Validate secrets are accessible
  run: |
    # Test that secrets are set (values won't print)
    if [ -z "${{ secrets.KUBE_CONFIG_DATA }}" ]; then
      echo "ERROR: KUBE_CONFIG_DATA not set"
      exit 1
    fi
    
    # Validate kubeconfig format
    echo "${{ secrets.KUBE_CONFIG_DATA }}" | base64 -d | grep "apiVersion:" > /dev/null
    if [ $? -eq 0 ]; then
      echo "✓ KUBE_CONFIG_DATA looks valid"
    else
      echo "✗ KUBE_CONFIG_DATA format invalid"
      exit 1
    fi
```

### Test Database Connection

```yaml
- name: Test database password
  run: |
    psql -h localhost \
         -U postgres \
         -d test_db \
         -c "SELECT version();"
  env:
    PGPASSWORD: ${{ secrets.DB_PASSWORD }}
```

### Test Kubernetes Access

```yaml
- name: Test kubeconfig
  run: |
    mkdir -p ~/.kube
    echo "${{ secrets.KUBE_CONFIG_DATA }}" | base64 -d > ~/.kube/config
    kubectl cluster-info
    kubectl get namespaces
```

---

## Rotating Secrets

### Update JWT Secret

```bash
# Step 1: Generate new key
NEW_KEY=$(openssl rand -base64 32)
echo "New JWT key: $NEW_KEY"

# Step 2: Update GitHub secret
# Settings → Secrets → JWT_SECRET_KEY → Edit

# Step 3: Update Kubernetes secret
kubectl set env deployment/qc-app \
  JWT_SECRET_KEY="$NEW_KEY" \
  -n qc-staging

# Step 4: Rollout new pods
kubectl rollout restart deployment/qc-app -n qc-staging
```

### Update Database Password

```bash
# Step 1: Update GitHub secret
# Settings → Secrets → DB_PASSWORD → Edit

# Step 2: Update PostgreSQL user password
ALTER USER qc_user WITH PASSWORD 'new-password';

# Step 3: Update Kubernetes secret
kubectl patch secret qc-secrets \
  -p='{"data":{"db-password":"'$(echo -n "new-password" | base64)'"}}' \
  -n qc-staging

# Step 4: Restart affected pods
kubectl rollout restart deployment/qc-app -n qc-staging
```

---

## Security Best Practices

### DO ✓

- [ ] Use unique secret per environment (staging ≠ production)
- [ ] Rotate secrets every 90 days
- [ ] Use strong, random secrets (32+ characters)
- [ ] Store secrets in GitHub secrets, NOT in code
- [ ] Document where each secret is used
- [ ] Review access logs for secret usage
- [ ] Use environment-specific deployments

### DON'T ✗

- [ ] DON'T commit secrets to repository
- [ ] DON'T use same secret for multiple environments
- [ ] DON'T share secrets in emails/chat
- [ ] DON'T log secrets in CI/CD output
- [ ] DON'T use simple passwords
- [ ] DON'T commit .kube/config to repository
- [ ] DON'T paste secrets in GitHub issues

---

## Troubleshooting

### Secret Not Found in Workflow

**Error**: `unset variable: secrets.XXX`

**Solution**:
1. Verify secret name spelled correctly (case-sensitive)
2. Verify environment is correct (staging vs production)
3. Verify secret is accessible from workflow's environment
4. Check GitHub Actions permissions

```yaml
# Debug: List available secrets
- name: List available secrets
  run: env | sort | grep -i secret
```

### Kubeconfig Decoding Fails

**Error**: `base64: invalid input`

**Solution**:
```bash
# Re-encode kubeconfig
cat ~/.kube/config | base64 -w0 > /tmp/kube_config.txt

# Verify it decodes
cat /tmp/kube_config.txt | base64 -d | head -5

# Copy clean output to GitHub
```

### Kubernetes Authentication Fails

**Error**: `Unable to connect to the server: unauthorized`

**Solution**:
1. Verify kubeconfig has correct cluster URL
2. Verify certificates are valid (not expired)
3. Verify user token has correct permissions
4. Test locally: `kubectl cluster-info`

---

## Reference: Secret Names Used in Workflow

```yaml
# ci-cd-production.yml references:
${{ secrets.KUBE_CONFIG_DATA }}
${{ secrets.JWT_SECRET_KEY }}
${{ secrets.DB_PASSWORD }}
${{ secrets.SUPABASE_URL }}
${{ secrets.SUPABASE_KEY }}

# cd_helm_deploy.yml references:
${{ secrets.JWT_SECRET_KEY }}
${{ secrets.DB_PASSWORD }}
${{ secrets.SUPABASE_URL }}
${{ secrets.SUPABASE_KEY }}

# docker/build-push-action references:
${{ secrets.GITHUB_TOKEN }}  # Automatic, built-in
```

---

**Last Updated**: 2026-05-09  
**Version**: 1.0.0
