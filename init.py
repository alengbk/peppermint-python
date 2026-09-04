#!/usr/bin/env python3
"""Interactive initialization menu."""
import subprocess, time, requests, os, sys

BASE = "http://127.0.0.1:5003"
DIR = os.path.dirname(__file__)
DB = os.path.join(DIR, "peppermint.db")


def server_start():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "5003", "--log-level", "warning"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=DIR,
    )
    time.sleep(4)
    return proc


def server_stop(proc):
    proc.terminate()
    proc.wait()


def rebuild_db():
    if os.path.exists(DB):
        os.remove(DB)
        print(f"🗑️  Removed {DB}")
    else:
        print("ℹ️  No existing database found")
    proc = server_start()
    proc.terminate()
    proc.wait()
    print("✅ Database rebuilt (tables created on first startup)")


def create_admin():
    if not os.path.exists(DB):
        print("❌ Database not found. Run option 1 first.")
        return
    proc = server_start()
    try:
        r = requests.post(f"{BASE}/api/v1/auth/user/register", json={
            "name": "admin", "email": "admin@peppermint.local",
            "password": "1qaz+2wsx", "admin": True,
        })
        if r.status_code == 200:
            print(f"✅ Admin created: {r.json()['name']}")
        else:
            print(f"❌ Register failed: {r.status_code} {r.text}")
            return
        r = requests.post(f"{BASE}/api/v1/auth/login", data={"username": "admin", "password": "1qaz+2wsx"})
        if r.status_code != 200:
            print(f"❌ Login failed: {r.status_code}")
            return
        token = r.json()["access_token"]
        print("✅ Login success")
        r = requests.post(f"{BASE}/api/v1/config/complete-setup", headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 200:
            print("✅ First-time setup completed")
        else:
            print(f"⚠️  Setup may have already been completed: {r.status_code}")
        print(f"\n🎉 Admin ready!")
        print(f"   Username: admin")
        print(f"   Password: 1qaz+2wsx")
    finally:
        server_stop(proc)


def main():
    print("=" * 50)
    print("  Peppermint-fork Initialization")
    print("=" * 50)
    print("  1. Rebuild database (delete + recreate tables)")
    print("  2. Create admin user (admin / 1qaz+2wsx)")
    print("  q. Quit")
    print("=" * 50)

    choice = input("Select option: ").strip()
    if choice == "1":
        rebuild_db()
    elif choice == "2":
        create_admin()
    elif choice == "q":
        return
    else:
        print("Invalid option")


if __name__ == "__main__":
    main()
