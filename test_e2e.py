#!/usr/bin/env python3
"""E2E test: create ticket via API, then close via frontend simulation"""
import subprocess, time, requests, json, sys

BASE = "http://127.0.0.1:5003"

proc = subprocess.Popen(
    [sys.executable or "venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "5003", "--log-level", "warning"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd="/home/allen/peppermint-python"
)
time.sleep(4)

try:
    r = requests.get(f"{BASE}/api/v1/health")
    assert r.status_code == 200, f"Health: {r.status_code}"

    # Register admin
    r = requests.post(f"{BASE}/api/v1/auth/user/register", json={"email":"admin@test.com","password":"admin123","name":"管理員","admin":True})
    assert r.status_code == 200, f"Register: {r.status_code} {r.text}"
    print(f"✅ 註冊管理員: {r.json()['name']}")

    # Login
    r = requests.post(f"{BASE}/api/v1/auth/login", data={"username":"管理員","password":"admin123"})
    assert r.status_code == 200, f"Login: {r.status_code}"
    token = r.json()["access_token"]
    print(f"✅ 登入成功")

    # Complete setup
    r = requests.post(f"{BASE}/api/v1/config/complete-setup", headers={"Authorization":f"Bearer {token}"})
    assert r.status_code == 200, f"Setup: {r.status_code}"
    print(f"✅ 完成首次設定")

    # Create ticket via HTTP POST API
    r = requests.post(f"{BASE}/api/v1/ticket", json={"title":"數據庫連線異常","detail":"ERP 資料庫無法連線","priority":"high","type":"incident"}, headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"})
    assert r.status_code == 200, f"Create: {r.status_code} {r.text}"
    tid = r.json()["id"]
    num = r.json()["number"]
    print(f"✅ 建立工單 #{num}: {r.json()['title']} [狀態: {r.json()['status']}]")

    # Verify frontend pages (cookie-based auth)
    cookies = {"token": token}
    r = requests.get(f"{BASE}/login")
    assert r.status_code == 200 and "Peppermint-fork" in r.text
    print(f"✅ 登入頁面: 200 OK")

    r = requests.get(f"{BASE}/dashboard", cookies=cookies)
    assert r.status_code == 200
    print(f"✅ 儀表板頁面: 200 OK")

    r = requests.get(f"{BASE}/tickets", cookies=cookies)
    assert r.status_code == 200 and "New Ticket" in r.text
    print(f"✅ 工單列表頁面: 200 OK (工單資料由 JS 動態載入)")

    r = requests.get(f"{BASE}/ticket/{tid}", cookies=cookies)
    assert r.status_code == 200 and "Close Issue" in r.text
    print(f"✅ 工單詳情頁面: 顯示 Close Issue 按鈕")

    # Close ticket (模擬前端點擊 Close Issue)
    r = requests.put(f"{BASE}/api/v1/ticket/{tid}", json={"status":"done"}, headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"})
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    print(f"✅ 結案成功: 工單 #{num} → status: done")

    # Verify via API that ticket is done
    r = requests.get(f"{BASE}/api/v1/ticket/{tid}", headers={"Authorization":f"Bearer {token}"})
    assert r.json()["status"] == "done"
    print(f"✅ API 確認工單已結案: status = done")

    # CSV export
    r = requests.get(f"{BASE}/api/v1/ticket/export/csv", headers={"Authorization":f"Bearer {token}"})
    assert r.status_code == 200
    assert "數據庫連線異常" in r.text
    print(f"✅ CSV 匯出成功: {len(r.text)} bytes")

    print("\n🎉 全部測試通過！完整流程：")
    print("   POST /api/v1/ticket (建立工單)")
    print("   → 瀏覽器登入 /login")
    print("   → 從 /tickets 找到工單")
    print("   → 進入 /ticket/{id} 查看詳情")
    print("   → 點擊 Close Issue 結案")
    print("   → 可從工具列 Export CSV 匯出")
finally:
    proc.terminate()
    proc.wait()
