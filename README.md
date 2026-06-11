# TG Nav Hub

从 Telegram 公开频道采集外链，分类展示为导航站。

- 本地开发：**http://127.0.0.1:8765**（端口固定，见 `.cursor/rules/port-8765.mdc`）
- 启动：`.\run.ps1` 或 `python -m app`
- **线上**：GitHub [`fnjerry/tg-nav-hub`](https://github.com/fnjerry/tg-nav-hub) → Render → **https://ai.24s.net**  
  → **详细图文步骤**：[部署教程（从零到上线）](docs/deploy-ai.24s.net.md)

---

## 能不能放 GitHub + 免费平台自动跑？

可以。推荐组合：

| 角色 | 平台 | 作用 |
|------|------|------|
| 代码仓库 | [GitHub](https://github.com)（私有库） | 存代码；本地 `git push` 即同步 |
| 运行网站 | [Render](https://render.com) 免费 Web 服务 | 自动构建、常驻/按需访问、可挂磁盘存 SQLite |
| 自定义域名 | [Cloudflare](https://cloudflare.com) 免费 DNS | 把 **`ai.24s.net`** 指到 Render |
| 定时采集 | GitHub Actions（本仓库 `sync.yml`） | 每天请求 `/api/sync`，不依赖本机开机 |

其它可选：Railway、Fly.io、自有 VPS + Docker（仓库已含 `Dockerfile`）。

---

## 部署流程（简版）

> 完整逐步教程（含 Cloudflare、环境变量、排错）：**[docs/deploy-ai.24s.net.md](docs/deploy-ai.24s.net.md)**

### 1. 推到 GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/fnjerry/tg-nav-hub.git
git push -u origin main
```

**不要提交** `.env`、`data/`（已在 `.gitignore`）。

### 2. 在 Render 创建 Web Service

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Web Service** → 连接 GitHub 仓库。
2. 若仓库有 `render.yaml`，选 **Apply from render.yaml**；否则：
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. 添加 **Persistent Disk**，挂载路径 **`/data`**（与 `DATABASE_PATH=/data/nav.db` 一致）。
4. **Environment** 中配置（与 `.env.example` 对应，值用 Render 的 Secret）：

   | 变量 | 说明 |
   |------|------|
   | `TELEGRAM_API_ID` | [my.telegram.org](https://my.telegram.org/apps) |
   | `TELEGRAM_API_HASH` | 同上 |
   | `TELEGRAM_SESSION_STRING` | 本地 `scripts/login_telegram.py` 生成 |
   | `TELEGRAM_CHANNELS` | 如 `qumao`（逗号分隔，无 @） |
   | `ADMIN_SYNC_TOKEN` | 同步接口密钥，务必随机强密码 |
   | `TELEGRAM_PROXY` | 若服务器访问 Telegram 需代理则填写 |
   | `DATABASE_PATH` | `/data/nav.db` |

5. **Auto-Deploy**：默认开启 → 之后每次 `git push` 到主分支，Render 自动重新部署。

### 3. 绑定自己的域名

1. Render 服务 → **Settings** → **Custom Domains** → 添加 **`ai.24s.net`**。
2. 在 **24s.net** 的 DNS（推荐 Cloudflare）为子域 **`ai`** 添加 Render 提示的 **CNAME**（指向 `*.onrender.com`）。
3. 等待证书生效后，用 **https://ai.24s.net** 访问。

### 4. 定时同步（推荐）

免费实例可能休眠，内置「每天 9:00」调度在休眠时不会执行。请在 GitHub 仓库配置 **Secrets**：

| Secret | 示例 |
|--------|------|
| `SITE_URL` | `https://ai.24s.net`（不要末尾 `/`） |
| `ADMIN_SYNC_TOKEN` | 与 Render 环境变量一致 |

推送后，`.github/workflows/sync.yml` 会每天 UTC 01:00 左右调用 `POST /api/sync`。

也可手动：

```bash
curl -X POST "https://ai.24s.net/api/sync" \
  -H "Authorization: Bearer 你的ADMIN_SYNC_TOKEN"
```

---

## 本地改代码 → 线上自动更新

```bash
git add .
git commit -m "描述改动"
git push
```

Render 检测到 push 后自动构建、发布；数据库在持久盘上，**一般不会被清空**（勿在 Render 上删盘）。

---

## 注意事项

1. **会话与密钥**只放在平台环境变量，不要写进 GitHub。
2. **Telegram**：云服务器若在境外，通常不需要代理；在国内机房可能需要 `TELEGRAM_PROXY`。
3. **Render 免费档**：一段时间无访问会休眠，首次打开较慢；重要场景可考虑付费档或换 VPS。
4. 本地端口仍为 **8765**；云端由平台注入 `PORT`，与本地互不影响。

---

## Windows 开机自启动

```powershell
.\scripts\install_startup.ps1
```

会在「启动」文件夹创建快捷方式，登录后后台启动站点（**http://127.0.0.1:8765**）。取消自启动：

```powershell
.\scripts\install_startup.ps1 -Remove
```

---

## 每天自动采集（本机）

两种方式任选其一（不要重复配置到同一时刻）：

| 方式 | 条件 | 说明 |
|------|------|------|
| **内置调度** | `.\run.ps1` 常驻不关 | `.env` 中 `ENABLE_DAILY_SYNC=true`、`DAILY_SYNC_TIME=09:00`，到点自动采集 |
| **Windows 计划任务** | 不必开网站 | 管理员 PowerShell 执行 `.\scripts\install_daily_task.ps1`，每天 9:00 跑 `scripts\run_sync.py` |

手动立即采集：

```powershell
.\.venv\Scripts\python.exe scripts\run_sync.py
```

查看上次结果：`data\last_sync.json` 或 `http://127.0.0.1:8765/api/sync/status`

---

## 常用命令

```powershell
# 本地
.\run.ps1
.\.venv\Scripts\python.exe scripts\run_sync.py

# 释放被占用的 8765
.\scripts\free_port.ps1
```
