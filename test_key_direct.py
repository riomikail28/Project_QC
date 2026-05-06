import os
import json
import urllib.request

def load_env_manual():
    env_data = {}
    try:
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_data[key.strip()] = value.strip().strip('"').strip("'")
    except Exception:
        pass
    return env_data

def test_supabase_direct():
    env = load_env_manual()
    
    url = env.get("SUPABASE_URL", "").strip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY", env.get("SUPABASE_KEY", "")).strip()
    
    if not url or not key:
        print("ERROR: SUPABASE_URL atau KEY tidak ditemukan di file .env")
        return

    print(f"Sedang mengetes koneksi ke: {url}...")
    
    # Using 'staff_accounts' as it was confirmed in the schema
    api_url = f"{url}/rest/v1/staff_accounts?select=id&limit=1"
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}"
    }
    
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            if status == 200:
                print("\n=========================================")
                print("✅ KONEKSI BERHASIL!")
                print("API Key Anda VALID dan bisa mengakses database.")
                print("=========================================")
                print("\nAnalisis: Karena di lokal berhasil tapi di Vercel gagal,")
                print("berarti ada kesalahan copy-paste saat memasukkan")
                print("Environment Variables di Dashboard Vercel.")
            else:
                print(f"\n❌ KONEKSI GAGAL (Status: {status})")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"\n❌ KONEKSI GAGAL")
        print(f"Error Code: {e.code}")
        print(f"Pesan Error: {body}")
        if e.code == 401 or e.code == 403:
            print("\nAnalisis: API Key Anda SALAH atau TIDAK BERLAKU untuk URL ini.")
    except Exception as e:
        print(f"\n❌ TERJADI KESALAHAN TEKNIS: {str(e)}")

if __name__ == "__main__":
    test_supabase_direct()
