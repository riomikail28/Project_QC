# Project QC — Developer Guide

This guide describes how to set up the local development environment, run static analysis and linting, scan for security vulnerabilities, run unit/integration tests, and perform smoke tests.

---

## 1. Local Environment Setup

### Prerequisites
- Python 3.11 or later
- Access to a Supabase project (URL and keys)

### Step 1: Clone and Navigate
```bash
git clone <repository-url>
cd Project_QC
```

### Step 2: Create a Virtual Environment
Create a clean virtual environment to separate project dependencies from the system packages:
```bash
python -m venv .venv
```

Activate the virtual environment:
- **Windows (Command Prompt)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **macOS / Linux**:
  ```bash
  source .venv/bin/activate
  ```

---

## 2. Dependencies Structure

Dependencies are divided into two files:
- `requirements.txt`: Contains only production-critical packages required to run the application in serverless/production mode. Keeps deployment package size minimal.
- `requirements-dev.txt`: Inherits all production packages and adds static analysis, linting, and testing tools.

Install all development and testing dependencies:
```bash
pip install -r requirements-dev.txt
```

---

## 3. Code Quality & Code Style (Ruff)

We use **Ruff** for high-speed Python linting and formatting. Ruff rules are configured globally in [pyproject.toml](file:///c:/Users/rio/.gemini/antigravity/scratch/Project_QC/pyproject.toml).

### Run Lint Checks
```bash
ruff check .
```

### Automatically Fix Safe Lint Issues
```bash
ruff check --fix .
```

### Run Code Formatting Check
```bash
ruff format --check .
```

### Reformat Code Automatically
```bash
ruff format .
```

---

## 4. Security Scanning (Bandit)

We use **Bandit** to check Python code for common security bugs (like hardcoded keys, unsafe method usages).

Run a bandit security scan:
```bash
bandit -r backend api -ll
```
*(Use `-lll` if you want to inspect high-severity vulnerabilities only.)*

---

## 5. Dependency Vulnerability Checking (Safety)

We use **Safety** to scan third-party dependencies for known vulnerabilities (CVEs).

Run safety check on production dependencies:
```bash
safety check -r requirements.txt
```

---

## 6. Testing (Pytest)

All backend test cases are located in the `tests/` directory.

Run the entire test suite:
```bash
python -m pytest tests/ -v
```

---

## 7. Health Check & Smoke Test

The application exposes a public, database-independent health check endpoint at `/api/health` for load-balancer status validation.

### Step 1: Start the Local Flask Server
```bash
python -m flask --app api/app run --port 5000
```

### Step 2: Execute Smoke Test Script
In a separate terminal window, run the zero-dependency smoke test script:
```bash
python tests/smoke_test.py
```
To run it against a deployed URL (such as Vercel preview or production staging), configure the target via environment variable:
```bash
# Windows PowerShell
$env:SMOKE_TEST_URL="https://your-preview-url.vercel.app"; python tests/smoke_test.py

# Linux/macOS
SMOKE_TEST_URL="https://your-preview-url.vercel.app" python tests/smoke_test.py
```
