#!/usr/bin/env python3
"""Verify audit logs are recorded for all operations"""
import subprocess, time, requests, json

BASE = "http://127.0.0.1:5003"
proc = subprocess.Popen(
    ["python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "5003", "--log-level", "warning"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd="/home/allen/peppermint-python"
)
time.sleep(4)

try:
    # Register + complete setup
    r = requests.post(f"{BASE}/api/v1/auth/user/register", json={"email":"admin@test.com","password":"admin123","name":"管理員","admin":True})
    token = requests.post(f"{BASE}/api/v1/auth/login", data={"username":"管理員","password":"admin123"}).json()["access_token"]
    requests.post(f"{BASE}/api/v1/config/complete-setup", headers={"Authorization":f"Bearer {token}"})
    h = {"Authorization":f"Bearer {token}", "Content-Type":"application/json"}

    # Failed login
    requests.post(f"{BASE}/api/v1/auth/login", data={"username":"管理員","password":"wrong"})
    # Create ticket
    r = requests.post(f"{BASE}/api/v1/ticket", json={"title":"測試工單","priority":"high"}, headers=h)
    tid = r.json()["id"]
    # Close ticket
    requests.put(f"{BASE}/api/v1/ticket/{tid}", json={"status":"done"}, headers=h)
    # Re-open ticket
    requests.put(f"{BASE}/api/v1/ticket/{tid}", json={"status":"needs_support"}, headers=h)
    # Assign ticket
    requests.put(f"{BASE}/api/v1/ticket/{tid}", json={"userId":"nonexistent"}, headers=h)
    # Comment
    r = requests.post(f"{BASE}/api/v1/comment/{tid}", json={"text":"測試留言"}, headers=h)
    cid = r.json()["id"]
    # Delete comment
    requests.delete(f"{BASE}/api/v1/comment/{cid}", headers=h)
    # CSV export
    requests.get(f"{BASE}/api/v1/ticket/export/csv", headers={"Authorization":f"Bearer {token}"})
    # Delete ticket
    requests.delete(f"{BASE}/api/v1/ticket/{tid}", headers=h)

    # Now check audit logs
    r = requests.get(f"{BASE}/api/v1/audit/logs?pageSize=200", headers={"Authorization":f"Bearer {token}"})
    assert r.status_code == 200, f"Audit API: {r.status_code}"
    logs = r.json()["logs"]
    actions = [log["action"] for log in logs]
    print(f"📋 共 {len(logs)} 筆稽核紀錄:")
    for log in logs:
        print(f"   [{log['action']:30s}] {log['email']:25s} | {log.get('detail','')[:60]}")

    expected = ["auth.login", "auth.login_failed", "config.complete_setup",
                "ticket.create", "ticket.close", "ticket.update",
                "comment.create", "comment.delete", "ticket.csv_export", "ticket.delete"]
    for e in expected:
        found = e in actions
        print(f"   {'✅' if found else '❌'} {e}")

    # Verify audit page renders (cookie-based auth)
    r = requests.get(f"{BASE}/audit", cookies={"token": token})
    assert r.status_code == 200 and "Audit Log" in r.text
    print(f"\n✅ Audit page renders: 200 OK")

    all_ok = all(e in actions for e in expected)
    print(f"\n{'🎉 All audit logs recorded!' if all_ok else '❌ Some logs missing!'}")
finally:
    proc.terminate()
    proc.wait()
