# 部署清单：fnjerry / ai.24s.net

| 项 | 值 |
|----|-----|
| GitHub 用户 | [fnjerry](https://github.com/fnjerry) |
| 仓库地址 | `https://github.com/fnjerry/tg-nav-hub` |
| 线上域名 | **https://ai.24s.net** |
| 本地开发 | http://127.0.0.1:8765 |

---

## 1. 推代码到 GitHub

```powershell
cd C:\Users\Administrator\Projects\tg-nav-hub
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/fnjerry/tg-nav-hub.git
git push -u origin main
```

先在 GitHub 网页创建空仓库 `tg-nav-hub`（可不勾选 README）。

---

## 2. Render 部署

1. [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint** 或 **Web Service** → 选 `fnjerry/tg-nav-hub`。
2. 使用仓库内 `render.yaml`（含 1GB 磁盘 `/data`）。
3. **Environment**（Secret）从本地 `.env` 抄，**不要**把 `.env` 提交到 Git：

   - `TELEGRAM_API_ID` / `TELEGRAM_API_HASH`
   - `TELEGRAM_SESSION_STRING`
   - `TELEGRAM_CHANNELS`（如 `qumao`）
   - `ADMIN_SYNC_TOKEN`
   - `DATABASE_PATH` = `/data/nav.db`
   - 境外机房一般**不需要** `TELEGRAM_PROXY`

4. 部署成功后 Render 会给出 `https://xxx.onrender.com`，先能打开再绑域名。

---

## 3. 域名 ai.24s.net（Cloudflare 示例）

1. Render 服务 → **Settings** → **Custom Domains** → 添加 **`ai.24s.net`**。
2. Render 会显示目标主机名（形如 `xxx.onrender.com`）。
3. 在 **24s.net** 的 DNS（Cloudflare）添加：

   | 类型 | 名称 | 内容 | 代理 |
   |------|------|------|------|
   | CNAME | `ai` | Render 提供的主机名 | 可先「仅 DNS」便于证书 |

4. 等 SSL 生效后访问：**https://ai.24s.net**

---

## 4. GitHub Actions 每天自动采集

仓库 **Settings** → **Secrets and variables** → **Actions**：

| Name | Value |
|------|--------|
| `SITE_URL` | `https://ai.24s.net` |
| `ADMIN_SYNC_TOKEN` | 与 Render 里相同 |

保存后，`.github/workflows/sync.yml` 每天约北京时间 9:00 调用 `POST /api/sync`。

手动触发：GitHub → **Actions** → **Daily Telegram sync** → **Run workflow**。

---

## 5. 本地改完自动上线

```bash
git add .
git commit -m "update"
git push
```

Render 开启 Auto-Deploy 后会自动重建；数据在持久盘 `/data` 上。

---

## 6. 本机仍可用

- 开机自启：`.\scripts\install_startup.ps1`
- 手动采集：`.\.venv\Scripts\python.exe scripts\run_sync.py`
- 本地预览：**http://127.0.0.1:8765**（与线上域名无关）
