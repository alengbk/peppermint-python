# Peppermint-fork Python

Python FastAPI + SQLite 重寫 [Peppermint](https://github.com/Peppermint-Lab/peppermint) 工單/客服系統（原始專案為 Node.js/TypeScript/PostgreSQL，已不再維護）。

## 技術棧

- **框架**: FastAPI + SQLModel (SQLAlchemy ORM)
- **資料庫**: SQLite（WAL 模式 + FK 啟用，無需外部資料庫）
- **認證**: JWT（人類）+ API Key（程式），PBKDF2 密碼雜湊
- **權限**: RBAC（管理員/一般人員/API）

## 快速開始

```bash
# 建立虛擬環境
python -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

### 一鍵初始化（清除資料庫 + 建立管理員）

```bash
venv/bin/python init.py
```

執行選單：
- **1**: 重建資料庫（刪除 `peppermint.db` + 重建空白資料表）
- **2**: 建立管理員 `admin`（密碼 `......`）+ 完成首次設定

密碼中的 `+` 在瀏覽器登入時需編碼為 `%2B`。

## 啟動伺服器

```bash
venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 5003 --reload
```

伺服器將在 http://127.0.0.1:5003 運行（自動跳轉至 `/login`），API 文件位於 `/docs`。

### 手動初始化

系統首次啟動時處於「首次設定」模式，第一個註冊的使用者必須是管理員。

1. 刪除 `peppermint.db`（如已存在）
2. 啟動伺服器: `venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 5003`
3. 註冊管理員: `POST /api/v1/auth/user/register` 帶 `name: "admin"`, `admin: true`
4. 登入: `POST /api/v1/auth/login`（form data: `username=admin` + `password=...`）
5. 完成設定: `POST /api/v1/config/complete-setup`
6. 管理員完成設定後可註冊一般人員

## 前端頁面

| 路徑 | 說明 |
|------|------|
| `/login` | 登入頁面（使用使用者名稱） |
| `/dashboard` | 儀表板（統計卡片 + 近期工單） |
| `/tickets` | 工單列表（可篩選、建立工單、匯出 CSV） |
| `/ticket/{id}` | 工單詳情（留言、結單、修改指派/優先級/狀態、管理員刪除） |
| `/users` | 使用者管理（管理員限定，含 create/edit/delete 對話框） |
| `/clients` | 客戶管理（管理員限定，含 create/edit/delete 對話框） |
| `/audit` | 稽核日誌（管理員限定，可依動作/Email/Source 篩選，附分頁瀏覽） |
| `/service-accounts` | API Key 管理（管理員限定） |

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/v1/auth/user/register` | 註冊（首個須為管理員） |
| `POST` | `/api/v1/auth/login` | 登入（form data, username + password） |
| `GET` | `/api/v1/auth/me` | 取得當前使用者 |
| `POST` | `/api/v1/auth/logout` | 登出 |
| `GET` | `/api/v1/auth/check-first-setup` | 檢查是否首次設定 |
| `PUT` | `/api/v1/auth/language` | 切換語言（`{"language": "en"}` / `{"language": "zh"}`） |
| `POST` | `/api/v1/ticket` | 建立工單 |
| `GET` | `/api/v1/ticket` | 工單列表 |
| `GET` | `/api/v1/ticket/export/csv` | 匯出 CSV（支援篩選參數） |
| `GET` | `/api/v1/ticket/{id}` | 工單詳情 |
| `PUT` | `/api/v1/ticket/{id}` | 更新工單 |
| `DELETE` | `/api/v1/ticket/{id}` | 刪除工單（管理員限定） |
| `POST` | `/api/v1/client` | 建立客戶 |
| `GET` | `/api/v1/client` | 客戶列表 |
| `PUT` | `/api/v1/client/{id}` | 更新客戶 |
| `DELETE` | `/api/v1/client/{id}` | 刪除客戶 |
| `POST` | `/api/v1/team` | 建立團隊 |
| `GET` | `/api/v1/team` | 團隊列表 |
| `POST` | `/api/v1/comment/{ticket_id}` | 新增留言 |
| `GET` | `/api/v1/comment/{ticket_id}` | 留言列表 |
| `DELETE` | `/api/v1/comment/{id}` | 刪除留言 |
| `POST` | `/api/v1/time` | 新增工時 |
| `GET` | `/api/v1/time` | 工時列表 |
| `GET` | `/api/v1/config` | 取得設定 |
| `PUT` | `/api/v1/config` | 更新設定 |
| `POST` | `/api/v1/config/complete-setup` | 完成首次設定 |
| `GET` | `/api/v1/notifications` | 通知列表 |
| `PUT` | `/api/v1/notifications/{id}/read` | 標記通知已讀 |
| `PUT` | `/api/v1/notifications/read-all` | 標記全部已讀 |
| `GET` | `/api/v1/audit/logs` | 稽核日誌列表（管理員，支援 action/source/email/日期篩選） |
| `POST` | `/api/v1/service-account` | 建立 API Key（管理員，回傳完整 key 僅一次） |
| `GET` | `/api/v1/service-account` | API Key 列表（管理員） |
| `DELETE` | `/api/v1/service-account/{id}` | 撤銷 API Key（管理員） |
| `POST` | `/api/v1/service-account/{id}/regenerate` | 重新產生 API Key（管理員） |
| `GET` | `/api/v1/health` | 健康檢查 |

## CSV 匯出

`GET /api/v1/ticket/export/csv` — 支援與工單列表相同的篩選參數（`status`、`priority`、`type`、`search`、`userId`、`clientId`、`teamId`），回傳 UTF-8 BOM CSV 檔案供 Excel 直接開啟。

## 稽核日誌

所有修改性操作均自動記錄至 `AuditLog` 資料表，每筆記錄包含 `source`（`human` 或 `api`），管理員可在 `/audit` 頁面依來源篩選：

| 類別 | 記錄動作 |
|------|----------|
| 認證 | login / login_failed / register |
| 工單 | create / close / assign / update / delete / dedup / csv_export |
| 使用者 | create / delete |
| 客戶 | create / delete |
| 留言 | create / delete |
| 設定 | complete_setup |
| API Key | service_account.create / service_account.delete / service_account.regenerate |

管理員可在 `/api/v1/audit/logs`（GET）搭配 `action`、`source`、`email`、`from`、`to`、`page`、`pageSize` 參數篩查，亦可直接在前端 `/audit` 頁面操作（支援分頁：頁數切換、上/下頁、每頁 50/100/200 筆）。

## 重點實作細節

### 密碼處理
使用 PBKDF2-SHA256 自實作（非 passlib/bcrypt），避免套件版本衝突。雜湊格式：`pbkdf2_sha256${iterations}${salt_hex}${hash_hex}`。

### 登入機制
使用**使用者名稱 (`name`)** 登入，非 Email。`User.name` 具備唯一性約束。

### Email 驗證
所有 Pydantic schema 使用 `str` 而非 `EmailStr`，避免過度嚴格的 email 格式驗證（例如 `user@company` 等合法 email 被拒絕）。

### 權限模型
- **人類（JWT）**: 前端登入取得 JWT，API 用 Bearer header，前端頁面用 cookie
- **程式（API Key）**: 格式 `pep_<64_hex>`，使用 `Authorization: Bearer pep_xxx`
- `is_admin=true` 可存取所有端點；一般人員受限於權限檢查
- 稽核日誌自動區分 `source=human` 與 `source=api`
- 首次設定模式下第一個使用者強制為管理員
- 工單刪除僅限管理員（後端 + 前端按鈕皆有限制）

### SQLite 注意事項
- 啟用 WAL 模式提升併發讀取效能
- 啟用 `PRAGMA foreign_keys=ON`（透過 SQLAlchemy event listener 每個連線啟用）
- 檔案預設為 `peppermint.db`，可透過環境變數 `DATABASE_URL` 自訂路徑
- 初次啟動自動建立資料表
- DB schema 有變更時需砍掉 `peppermint.db` 重建（無 migration 系統）

### 工單自動去重（Dedup）
告警系統重複發送相同內容時，`POST /api/v1/ticket` 自動合併：
- Fingerprint = SHA256(`title + "|" + detail`) 前 16 字元
- 查詢 `fingerprint` 相同且 `status != "done"` 的工單
  - **命中** → `dedup_count++` + `last_seen_at = now` + 記錄本次時間至 `dedup_timestamps[]`，回傳同張工單（audit: `ticket.dedup`）
  - **未命中** → 建立新工單，記錄 `fingerprint`、`dedup_count=1`、`last_seen_at`、`dedup_timestamps=[now]`

#### 前端顯示

| 位置 | 顯示 |
|------|------|
| 工單列表 / Dashboard | 標題旁 `×N` badge（重複次數）+ `Human` / `API` 來源 badge |
| 工單詳情側邊欄 | Alert Count 卡片 — 大字 `×N`、最後告警時間、每次重複的時間列表（#1 ~ #N） |

#### 來源區分（Human / API）
- 透過 JWT token 建立的工單 → `createdBy.role = "admin"` → 標籤 `Human`
- 透過 API Key (`pep_xxx`) 建立的工單 → `createdBy.role = "api"` → 標籤 `API`
- Audit log 同樣記錄 `source="human"` / `source="api"`

### FK 關聯刪除
- `Comment.ticket_id` 使用 `ondelete="CASCADE"`
- `Ticket.comments` 關係設定 `passive_deletes=True`，避免 SQLAlchemy 在刪除時先 SET NULL 再刪除導致 NOT NULL 約束錯誤

### 多國語系（EN / 中文）

側邊欄底部（`sidebar-footer`）提供 EN/中 切換按鈕，偏好設定儲存於：
- 前端: `localStorage`（`lang` key）+ 即時套用
- 後端: `User.language` 欄位（`PUT /api/v1/auth/language`）

文字翻譯使用 HTML `data-en`/`data-zh` 屬性及 JavaScript `__()` 輔助函式。所有 9 個頁面模板及 JS 動態字串均已完整翻譯。

### 環境變數（`.env`）
```
SECRET_KEY=change-this-in-production
DATABASE_URL=sqlite:///./peppermint.db
```

### 部屬注意事項（ISO 27001）
- 需啟用 HTTPS（反向代理如 Nginx/Caddy）
- SQLite 檔案加密需依賴檔案系統層級加密（如 LUKS、eCryptfs）
- JWT Secret Key 需更換為強密碼

## 初始化 / 重置

```bash
venv/bin/python init.py               # 選單式：1=重建DB，2=建立admin
```

## 產生測試資料

```bash
venv/bin/python seed_tickets.py        # 20 筆隨機工單（自動註冊 admin + 啟動伺服器）
venv/bin/python seed_tickets.py 100    # 自訂數量
```

## 外部程式 HTTP POST API 範例

其他機器可透過 API Key 向本系統發送 HTTP POST 建立工單，適合監控告警系統整合：

```bash
# 命令列工具（支援 --title / --detail / --priority / --type）
venv/bin/python http_post_sample.py --title "Server Down" --detail "Main DB unreachable" --priority critical --type incident

# 也可指定自訂 API Key 與伺服器位址
venv/bin/python http_post_sample.py --title "Alert" --detail "CPU 95%" --api-key pep_xxx --base-url http://your-server:5003
```

另提供 `create_via_api.py` 作為簡潔的 Python 範例腳本，展示多筆工單批次建立的寫法。

> **前置需求**：需先在 `/service-accounts` 頁面建立 API Key（格式 `pep_<64_hex>`），或使用 `init.py` 產生的預設 key。

## 測試

```bash
venv/bin/python test_api.py            # API 整合測試（需先啟動伺服器）
venv/bin/python test_e2e.py            # 完整 E2E 流程（註冊→登入→建立工單→結案→CSV）
venv/bin/python test_audit.py          # 驗證稽核操作紀錄（含 source=human/api）
```
