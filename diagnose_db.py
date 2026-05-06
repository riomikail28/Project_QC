import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

print(f"--- Supabase Diagnostic ---")
print(f"URL: {url}")
print(f"Key Found: {'Yes' if key else 'No'}")

if not url or not key:
    print("ERROR: Missing credentials in .env")
    exit(1)

try:
    print("Connecting...")
    sb = create_client(url, key)
    # Try a simple query
    res = sb.table("staff_accounts").select("count", count="exact").limit(1).execute()
    print("SUCCESS: Connected to Supabase!")
    print(f"Found {res.count} staff accounts.")
except Exception as e:
    print(f"FAILED: {str(e)}")
