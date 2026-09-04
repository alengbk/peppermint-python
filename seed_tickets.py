#!/usr/bin/env python3
"""Generate random test tickets via POST /api/v1/ticket"""
import random
import subprocess
import sys
import time

import requests

BASE = "http://127.0.0.1:5003"
COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 20

TITLES = [
    "資料庫連線逾時", "ERP 無法登入", "印表機沒反應", "郵件伺服器異常",
    "VPN 連線中斷", "檔案伺服器空間不足", "DNS 解析失敗", "備份排程未執行",
    "防火牆規則衝突", "憑證即將到期", "LDAP 同步失敗", "API 回應緩慢",
    "磁碟 I/O 瓶頸", "記憶體使用率過高", "SSL Handshake 失敗",
    "資料表索引損毀", "排程任務未觸發", "容器重啟循環", "網路延遲異常",
    "監控告警誤報", "SSH 連線被拒", "S3 上傳失敗", "Redis 快取擊穿",
    "資料傾印還原錯誤", "HA Proxy 切換異常", "K8s Pod 狀態 CrashLoopBackOff",
    "TLS 版本不相容", "OOM Killer 觸發", "硬碟 SMART 警告", "機房溫度過高",
    "UPS 電池更換", "交換器埠 err-disable", "VLAN Trunk 設定錯誤",
    "路由表收斂異常", "BGP session 中斷", "NTP 時間偏移", "Syslog 未轉發",
    "ELK 索引爆炸", "Grafana 圖表空白", "Webhook 未送達",
]

DETAILS = [
    "發生時間 {}，影響範圍包含所有用戶，目前緊急處理中。",
    "使用者回報從 {} 開始出現此問題，重開機後仍然無法排除。",
    "已確認不是用戶端問題，同一網段其他使用者正常。",
    "初步判斷與上週版本更新有關，正在進行 root cause 分析。",
    "需協同 infrastructure 團隊排查，已開 bridge ticket {}。",
    "LOG 顯示 {} 出現大量 timeout，疑似 upstream 服務異常。",
    "緊急程度依 SLA 為 P1，已通報主管並成立 war room。",
    "預計 {} 前提出 hotfix，目前先手動 workaround。",
    "該問題每日約影響 {} 人次，需優先處理。",
]

PRIORITIES = ["low", "medium", "high", "urgent"]
TYPES = ["bug", "feature", "support", "incident", "service", "maintenance", "access", "feedback"]

# Auto-start server if not running
proc = None
try:
    requests.get(f"{BASE}/api/v1/health", timeout=2)
except requests.ConnectionError:
    print("Starting server...")
    env = {"PYTHONWARNINGS": "ignore"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5003", "--log-level", "error"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
    )
    for _ in range(15):
        try:
            requests.get(f"{BASE}/api/v1/health", timeout=1)
            break
        except requests.ConnectionError:
            time.sleep(1)
    else:
        print("Server failed to start")
        sys.exit(1)

# Login — if first time, register admin first
r = requests.post(f"{BASE}/api/v1/auth/login", data={"username": "admin", "password": "1qaz+2wsx"})
if r.status_code == 401:
    print("First-time setup: registering admin...")
    r = requests.post(f"{BASE}/api/v1/auth/user/register",
        json={"email": "admin@peppermint.com", "password": "1qaz+2wsx", "name": "admin", "admin": True})
    if r.status_code != 200:
        print(f"Register failed: {r.status_code} {r.text}")
        sys.exit(1)
    token = requests.post(f"{BASE}/api/v1/auth/login", data={"username": "admin", "password": "1qaz+2wsx"}).json()["access_token"]
    requests.post(f"{BASE}/api/v1/config/complete-setup", headers={"Authorization": f"Bearer {token}"})
    r = requests.post(f"{BASE}/api/v1/auth/login", data={"username": "admin", "password": "1qaz+2wsx"})
elif r.status_code != 200:
    print(f"Login failed: {r.status_code} {r.text}")
    sys.exit(1)

token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

ok = 0
for i in range(COUNT):
    title = random.choice(TITLES)
    if not title.endswith(("!", ".", "?")):
        title = title + random.choice(["！", "？", "。", ""])
    detail = random.choice(DETAILS).format(
        f"{random.randint(1,28)}/{random.randint(1,12)} {random.randint(0,23):02d}:{random.randint(0,59):02d}",
    )
    payload = {
        "title": title,
        "detail": detail,
        "priority": random.choice(PRIORITIES),
        "type": random.choice(TYPES),
    }
    r = requests.post(f"{BASE}/api/v1/ticket", json=payload, headers=headers)
    if r.status_code == 200:
        ok += 1
        data = r.json()
        print(f"  [{i+1}/{COUNT}] #{data['number']:>4} {data['priority']:7s} {data['type']:12s} {title[:30]}")
    else:
        print(f"  [{i+1}/{COUNT}] FAILED: {r.status_code} {r.text[:80]}")

print(f"\n{'✅' if ok == COUNT else '⚠️'} Created {ok}/{COUNT} tickets")

if proc:
    proc.terminate()
