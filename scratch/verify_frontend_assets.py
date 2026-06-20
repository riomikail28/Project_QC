import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "link" and "href" in attrs_dict:
            href = attrs_dict["href"]
            if not href.startswith(("http://", "https://", "data:")):
                self.assets.append(("stylesheet", href))
        elif tag == "script" and "src" in attrs_dict:
            src = attrs_dict["src"]
            if not src.startswith(("http://", "https://", "data:")):
                self.assets.append(("script", src))
        elif tag == "img" and "src" in attrs_dict:
            src = attrs_dict["src"]
            if not src.startswith(("http://", "https://", "data:")):
                self.assets.append(("image", src))


def test_url(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Asset-Tester", "Connection": "close"})
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, len(res.read())
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception as e:
        print(f"Exception requesting {url}: {e}")
        return 999, 0


def main():
    print("Starting local Flask server...")
    env = os.environ.copy()
    env["JWT_SECRET_KEY"] = "test-secret-change-me"
    env["SUPABASE_URL"] = "https://example.supabase.co"
    env["SUPABASE_KEY"] = "test-key"
    env["PYTHONPATH"] = "c:\\Users\\rio\\.gemini\\antigravity\\scratch\\Project_QC"
    env["FLASK_APP"] = "backend:create_app"

    proc = subprocess.Popen(
        [sys.executable, "backend/app.py"],
        cwd="c:\\Users\\rio\\.gemini\\antigravity\\scratch\\Project_QC",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for server to start
    time.sleep(5)

    pages = [
        "/",
        "/admin/",
        "/admin/admin_panel.html",
        "/staff/dashboard.html",
        "/dashboard.html",
        "/monitoring.html",
        "/inspection.html",
        "/profile.html",
        "/alerts.html",
        "/sw.js",
        "/manifest.json",
    ]

    failed = []
    checked = set()

    try:
        for page in pages:
            page_url = f"http://127.0.0.1:5000{page}"
            print(f"\nFetching page: {page_url}")
            status, content_len = test_url(page_url)
            print(f"Status: {status}, Length: {content_len}")
            if status != 200:
                failed.append((page_url, status, "Page load failed"))
                continue

            # Fetch content to parse assets
            try:
                req = urllib.request.Request(page_url, headers={"Connection": "close"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read().decode("utf-8")
            except Exception as e:
                print(f"Error reading page content: {e}")
                continue

            parser = AssetParser()
            parser.feed(content)

            for asset_type, ref in parser.assets:
                # Resolve relative URL using the page URL as base
                resolved_url = urllib.parse.urljoin(page_url, ref)
                if resolved_url in checked:
                    continue
                checked.add(resolved_url)

                astatus, alen = test_url(resolved_url)
                print(f"  Asset: {ref} -> Resolved: {resolved_url} -> Status: {astatus}, Length: {alen}")
                if astatus != 200:
                    failed.append((resolved_url, astatus, f"Asset of type '{asset_type}' referenced in page '{page}'"))

    finally:
        print("\nTerminating Flask server...")
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=5)
            print("--- Flask Server STDOUT ---")
            print(stdout)
            print("--- Flask Server STDERR ---")
            print(stderr)
        except Exception as e:
            print(f"Could not read Flask outputs: {e}")
            proc.kill()

    if failed:
        print("\n=== VERIFICATION FAILED ===")
        for url, code, reason in failed:
            print(f"[-] {url} returned {code} ({reason})")
        sys.exit(1)
    else:
        print("\n=== VERIFICATION PASSED ===")
        print("All HTML pages and static assets checked out OK!")
        sys.exit(0)


if __name__ == "__main__":
    main()
