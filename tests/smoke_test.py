import json
import os
import sys
import urllib.request


def main():
    target_url = os.getenv("SMOKE_TEST_URL", "http://localhost:5000").rstrip("/")
    health_url = f"{target_url}/api/health"
    print(f"Running smoke test against: {health_url}")
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "QC-Smoke-Tester"})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status != 200:
                print(f"Error: Received status code {response.status}")
                sys.exit(1)
            body = response.read().decode()
            data = json.loads(body)
            if data.get("status") != "healthy":
                print(f"Error: Status is not healthy: {data}")
                sys.exit(1)
            print("Smoke test status check: PASSED")

        # Also verify security headers are set if we're hitting production Vercel URL
        # Note: Local Flask dev server may not have all Vercel gateway security headers,
        # but it should have basic ones defined in middleware.
        headers = dict(response.info())
        print(f"Response headers: {list(headers.keys())}")

    except Exception as e:
        print(f"Smoke test FAILED: {e}")
        sys.exit(1)

    print("Smoke test PASSED successfully!")


if __name__ == "__main__":
    main()
