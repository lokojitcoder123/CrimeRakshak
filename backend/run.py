import os
import sys

# Ensure site-packages, local user packages, and current directory are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Common AppSail / pip install target paths
user_site = os.path.expanduser("~/.local/lib/python3.11/site-packages")
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

vendor_dir = os.path.join(current_dir, "vendor")
if os.path.exists(vendor_dir) and vendor_dir not in sys.path:
    sys.path.insert(0, vendor_dir)

if __name__ == "__main__":
    try:
        import uvicorn
        import fastapi
        print("FastAPI and Uvicorn successfully imported.")
    except Exception as exc:
        print(f"CRITICAL: Failed to import FastAPI/Uvicorn: {exc}", file=sys.stderr)
        sys.exit(1)

    raw_port = os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT") or os.environ.get("PORT") or "8000"
    try:
        port = int(raw_port)
    except ValueError:
        port = 8000

    print(f"Starting Uvicorn server on 0.0.0.0:{port}...")
    sys.stdout.flush()
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")
