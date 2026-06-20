import os
import sys
import time
import subprocess
import urllib.request

def main():
    env = os.environ.copy()
    env['JWT_SECRET_KEY'] = 'test-secret-change-me'
    env['SUPABASE_URL'] = 'https://example.supabase.co'
    env['SUPABASE_KEY'] = 'test-key'
    env['PYTHONPATH'] = 'c:\\Users\\rio\\.gemini\\antigravity\\scratch\\Project_QC'
    
    proc = subprocess.Popen(
        [sys.executable, '-m', 'backend.app'],
        cwd='c:\\Users\\rio\\.gemini\\antigravity\\scratch\\Project_QC',
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(3)
    
    try:
        url = "http://localhost:5000/profile.html"
        print(f"Requesting: {url}")
        req = urllib.request.Request(url, headers={'Connection': 'close'})
        with urllib.request.urlopen(req, timeout=5) as res:
            print(f"Status: {res.status}")
            print(f"Length: {len(res.read())}")
    except Exception as e:
        print(f"Request failed: {e}")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == '__main__':
    main()
