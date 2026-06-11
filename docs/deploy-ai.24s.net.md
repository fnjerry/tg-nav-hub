# 完整部署教程：fnjerry → GitHub → Render → ai.24s.net

把本机项目发布到公网，实现：

- 访问 **https://ai.24s.net** 看导航站
- 本地改代码 `git push` 后线上自动更新
- 每天自动从 Telegram 频道采集新链接

| 项 | 你的配置 |
|----|----------|
| GitHub 用户 | [fnjerry](https://github.com/fnjerry) |
| 仓库 | https://github.com/fnjerry/tg-nav-hub |
| 线上域名 | **https://ai.24s.net** |
| 本地开发 | http://127.0.0.1:8765 |

---

## 第 0 步：准备清单（部署前核对）

### 必须已有

- [ ] 本机项目能跑：`.\run.ps1` 后打开 http://127.0.0.1:8765 有数据
- [ ] 本机 `.env` 已配好 Telegram（`TELEGRAM_API_ID`、`TELEGRAM_API_HASH`、`TELEGRAM_SESSION_STRING`、`TELEGRAM_CHANNELS`）
- [ ] 本机采集成功过：`.\.venv\Scripts\python.exe scripts\run_sync.py` 无致命错误
- [ ] GitHub 空仓库已建好：`fnjerry/tg-nav-hub`
- [ ] 域名 **24s.net** 的 DNS 能管理（推荐 [Cloudflare](https://dash.cloudflare.com)）
- [ ] [Render](https://render.com) 账号（可用 GitHub 登录）

### 绝对不要提交到 GitHub

以下已在 `.gitignore`，推送前可用 `git status` 确认没有出现：

- `.env`（含 Session、Token、API Hash）
- `data/`（SQLite 数据库）
- `.venv/`

---

## 第 1 步：把代码推到 GitHub

### 1.1 若本地还没 commit

在项目目录 PowerShell：

```powershell
cd C:\Users\Administrator\Projects\tg-nav-hub
git status
```

若显示 `nothing to commit`，说明已提交，跳到 **1.3**。

若还有未提交文件：

```powershell
git add .
git commit -m "Initial commit"
git branch -M main
```

### 1.2 绑定远程仓库（只需做一次）

```powershell
git remote remove origin 2>$null
git remote add origin https://github.com/fnjerry/tg-nav-hub.git
git remote -v
```

应看到：

```
origin  https://github.com/fnjerry/tg-nav-hub.git (fetch)
origin  https://github.com/fnjerry/tg-nav-hub.git (push)
```

### 1.3 推送

```powershell
git push -u origin main
```

**成功标志**：浏览器打开 https://github.com/fnjerry/tg-nav-hub 能看到 `app/`、`render.yaml`、`README.md` 等文件。

### 1.4 推送失败：连接 GitHub 超时

国内常见，可任选一种：

**方式 A：临时 HTTP 代理（不改全局 git 配置）**

```powershell
git -c http.proxy=http://192.168.50.5:7890 -c https.proxy=http://192.168.50.5:7890 push -u origin main
```

把 `192.168.50.5:7890` 换成你 Clash/v2rayN 的 HTTP 代理地址。

**方式 B：SSH**

```powershell
git remote set-url origin git@github.com:fnjerry/tg-nav-hub.git
git push -u origin main
```

需先在 GitHub → **Settings** → **SSH and GPG keys** 添加公钥。

**方式 C：GitHub Desktop / gh cli**

用图形工具登录后推送同一仓库。

---

## 第 2 步：在 Render 创建服务

### 2.1 登录并连接 GitHub

1. 打开 https://dashboard.render.com
2. 用 GitHub 账号登录
3. 首次会要求 **Authorize Render** 访问 GitHub → 点 **Authorize**
4. 若看不到私有仓库：GitHub → **Settings** → **Applications** → **Render** → 授予 `fnjerry/tg-nav-hub` 权限

### 2.2 用 Blueprint 一键部署（推荐）

仓库里已有 `render.yaml`，适合整条流水线创建：

1. Render 控制台左上角 **New +**
2. 选 **Blueprint**
3. **Connect a repository** → 选 **`fnjerry/tg-nav-hub`**
4. Render 会读取 `render.yaml`，预览里应看到：
   - 服务名：`tg-nav-hub`
   - 类型：Web Service
   - 磁盘：`/data` 1GB
5. 点 **Apply**

若列表里没有 Blueprint，用下面 **2.3 手动创建**。

### 2.3 手动创建 Web Service（备用）

1. **New +** → **Web Service**
2. 连接仓库 `fnjerry/tg-nav-hub`
3. 填写：

   | 字段 | 值 |
   |------|-----|
   | Name | `tg-nav-hub` |
   | Region | 选离用户近的（如 Singapore / Oregon） |
   | Branch | `main` |
   | Runtime | `Python 3` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Plan | Free |

4. **Advanced** → **Health Check Path** 填：`/health`
5. **Disks** → Add disk：
   - Name: `tg-nav-data`
   - Mount Path: `/data`
   - Size: 1 GB
6. **Create Web Service**

### 2.4 第一次部署会先失败——正常

还没填 Telegram 密钥时，服务能启动但同步会失败；先把下面环境变量配齐再测。

---

## 第 3 步：配置 Render 环境变量

路径：**你的服务 `tg-nav-hub`** → 左侧 **Environment**

点 **Add Environment Variable**，逐个添加（值从本机 `.env` 复制，**不要**发到聊天/截图）：

| Key | 填什么 | 说明 |
|-----|--------|------|
| `TELEGRAM_API_ID` | 数字，如 `39150558` | https://my.telegram.org/apps |
| `TELEGRAM_API_HASH` | 一串字母数字 | 同上 |
| `TELEGRAM_SESSION_STRING` | 很长的一行 | 本地 `scripts/login_telegram.py` 生成；粘贴时**不要换行** |
| `TELEGRAM_CHANNELS` | 如 `qumao` | 多个用英文逗号，**不要** `@`，**不要**末尾逗号 |
| `ADMIN_SYNC_TOKEN` | 随机强密码 | 与本地 `.env` 相同即可；用于 `/api/sync` 鉴权 |
| `DATABASE_PATH` | `/data/nav.db` | 必须配合磁盘挂载，数据才持久 |
| `ENABLE_DAILY_SYNC` | `true` | 服务常驻时内置每天采集 |
| `DAILY_SYNC_TIME` | `09:00` | 服务器**本地时区**的 9 点（Render 多为 UTC） |

**一般不要填**（境外机房）：

| Key | 说明 |
|-----|------|
| `TELEGRAM_PROXY` | 仅当 Render 机器连不上 Telegram 时再试 |
| `PORT` | Render 自动注入，不要手填 |
| `HOST` | 云端自动 `0.0.0.0` |

敏感项建议点 **Secret**（打勾隐藏）。

填完后点 **Save, rebuild, and deploy**（或 **Manual Deploy** → **Deploy latest commit**）。

### 3.1 看部署日志

**Logs** 标签页应出现：

```
INFO:     Uvicorn running on http://0.0.0.0:xxxx
INFO:     Application startup complete.
```

### 3.2 验证线上接口

Render 会给临时地址，形如 `https://tg-nav-hub-xxxx.onrender.com`：

```powershell
curl.exe https://tg-nav-hub-xxxx.onrender.com/health
```

应返回：`{"status":"ok","api":"2"}`

```powershell
curl.exe https://tg-nav-hub-xxxx.onrender.com/api/links
```

应返回 JSON 数组（首次可能为空，同步后会有数据）。

---

## 第 4 步：绑定域名 ai.24s.net

### 4.1 在 Render 添加自定义域

1. 服务页 → **Settings** → 下滚到 **Custom Domains**
2. **Add Custom Domain**
3. 输入：`ai.24s.net`
4. 点 **Save**

Render 会显示需要配置的 DNS，通常是：

- **类型**：CNAME  
- **名称/Host**：`ai`（或完整 `ai.24s.net`，视 DNS 面板而定）  
- **目标/Target**：类似 `tg-nav-hub-xxxx.onrender.com`（以 Render 页面显示为准）

状态先会是 **Pending**。

### 4.2 在 Cloudflare 添加 DNS（24s.net 在 CF 时）

1. 登录 https://dash.cloudflare.com
2. 选域名 **24s.net** → 左侧 **DNS** → **Records**
3. **Add record**：

   | Type | Name | Target | Proxy status |
   |------|------|--------|--------------|
   | CNAME | `ai` | Render 给的 `xxx.onrender.com` | 初次建议 **DNS only**（灰云） |

4. 保存

**若 24s.net 不在 Cloudflare**：到购买域名的服务商后台，同样添加 CNAME，逻辑一致。

### 4.3 等待证书

回到 Render **Custom Domains**：

- 几分钟后状态变 **Verified**
- **SSL** 显示 **Certificate Issued**

浏览器访问：**https://ai.24s.net**

### 4.4 可选：开启 Cloudflare 橙云代理

证书稳定后，可把 CNAME 改为 **Proxied**（橙云）做 CDN/防护。若出现 5xx，先改回灰云排查。

---

## 第 5 步：线上首次采集

把 `你的TOKEN` 换成 Render 里 `ADMIN_SYNC_TOKEN` 的值：

```powershell
curl.exe -X POST "https://ai.24s.net/api/sync" -H "Authorization: Bearer 你的TOKEN"
```

**成功示例**：

```json
{"channels":1,"new_links":10,"messages_seen":10,"errors":[]}
```

再打开 https://ai.24s.net 应能看到卡片列表。

查看上次同步：

```powershell
curl.exe https://ai.24s.net/api/sync/status
```

### 常见错误

| 返回 / 现象 | 原因 | 处理 |
|-------------|------|------|
| `401 Invalid or missing Authorization` | Token 不对或没写 `Bearer ` | 检查 Header 格式 |
| `连接 Telegram 失败` | Session 无效或服务器连不上 TG | 重新跑 `login_telegram.py` 更新 Session；境外一般不需代理 |
| `No user has "xxx" as username` | 频道名错误 | 改 `TELEGRAM_CHANNELS`，只要真实 @ 后面的名字 |
| 页面空 | 还没 sync 成功 | 先 POST `/api/sync` |
| 打开很慢 | Render 免费休眠 | 等 30～60 秒；或见第 6 步用 Actions 定时唤醒+采集 |

---

## 第 6 步：GitHub Actions 每天自动采集（强烈推荐）

Render 免费实例会休眠，仅靠内置 `09:00` 调度可能错过。用 GitHub 每天请求一次 `/api/sync` 更稳。

### 6.1 添加 Secrets

1. 打开 https://github.com/fnjerry/tg-nav-hub
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret**，添加两个：

   | Name | Secret 值 |
   |------|-----------|
   | `SITE_URL` | `https://ai.24s.net`（**无**末尾 `/`） |
   | `ADMIN_SYNC_TOKEN` | 与 Render **完全相同** |

### 6.2 手动试跑一次

1. 仓库 **Actions** 标签
2. 左侧选 **Daily Telegram sync**
3. 右侧 **Run workflow** → **Run workflow**
4. 点进本次运行，应绿色成功；Logs 里是 `curl` 到 `/api/sync`

### 6.3 自动时间

`.github/workflows/sync.yml` 设为 UTC `01:00`，约等于北京时间 **09:00**（夏令时可能差 1 小时）。要改时间可编辑该文件里的 `cron`。

---

## 第 7 步：日常开发 → 自动上线

本地改完代码：

```powershell
cd C:\Users\Administrator\Projects\tg-nav-hub
git add .
git commit -m "说明本次改动"
git push
```

Render 默认 **Auto-Deploy** 监听 `main` 分支：

1. 收到 push 后开始 **Building**
2. 完成后 **Live**
3. 数据库在磁盘 `/data/nav.db`，**一般不会因为部署而清空**

确认：Render → **Settings** → **Build & Deploy** → **Auto-Deploy** 为 **Yes**。

---

## 第 8 步：本机与线上分工

| 场景 | 用哪里 |
|------|--------|
| 改界面、改分类逻辑 | 本地 8765 调试 → push → 线上自动更新 |
| 公网访问 | https://ai.24s.net |
| 本机开机就要本地站 | `.\scripts\install_startup.ps1` |
| 本机手动采集 | `.\.venv\Scripts\python.exe scripts\run_sync.py` |
| 线上采集 | Actions 定时 或 `curl POST .../api/sync` |

本地端口固定 **8765**，与域名无关。

---

## 故障排查速查

### Git push 失败

- 开代理后重试（见 1.4）
- `git status` 确认没有 `.env`

### Render Build 失败

- **Logs** 里看 `pip install` 是否报错
- `requirements.txt` 是否在仓库里

### Render 启动后马上退出

- **Start Command** 必须是：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- 不要写死 `8765`（云端端口由 Render 分配）

### 域名打不开

- `nslookup ai.24s.net` 看是否指向 Render
- Cloudflare 先灰云再橙云
- Render Custom Domains 是否 **Verified**

### 数据丢了

- 是否删过 Render 的 **Disk**
- `DATABASE_PATH` 是否为 `/data/nav.db`
- 磁盘 Mount 是否为 `/data`

### 想重新部署但不改代码

Render → **Manual Deploy** → **Deploy latest commit**

---

## 完成后检查表

- [ ] https://github.com/fnjerry/tg-nav-hub 有代码
- [ ] Render 服务 **Live**，`/health` 返回 ok
- [ ] https://ai.24s.net 能打开首页
- [ ] `POST /api/sync` 返回 `new_links` ≥ 0 或 `errors` 为空
- [ ] GitHub Actions **Daily Telegram sync** 跑通一次
- [ ] 本地 `git push` 后 Render 自动部署成功

全部打勾即部署完成。
