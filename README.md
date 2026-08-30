# 抖音 / 小红书 外链卡片系统

独立运行的私域引流卡片工具，复刻「微信外链（抖音卡片插件）」核心能力，无付费授权、无需 MySQL，支持本地运行和 Render 一键部署。

## 功能

- 卡片管理：新增 / 编辑 / 删除 / 分页
- OG 卡片生成：抖音、小红书爬虫抓取页面元信息生成私信卡片预览
- 真实用户访问自动跳转到活码 / 落地页
- 访问日志：区分爬虫与真实用户，记录 IP / UA / 时间
- IP 黑名单：单卡片可开启
- 访问上限、过期时间、启停开关
- 后台登录鉴权
- 支持 Render 一键部署

## 本地运行

```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 启动
python3 app.py
```

启动后访问：
- 后台管理：http://127.0.0.1:8000/admin
- 默认账号：`admin` / `123456`
- 前台卡片入口：http://127.0.0.1:8000/?id=卡片ID

## Koyeb 部署（推荐，无需信用卡）

Koyeb 免费实例不需要绑定信用卡，支持从 GitHub 直接部署，自动给 `https://xxx.koyeb.app` 域名。

### 前置准备
1. 注册 Koyeb 账号：https://app.koyeb.com （用 GitHub 登录）
2. 代码已推送到 GitHub 仓库

### 部署步骤
1. 登录 Koyeb，点左上角「**Create Web Service**」
2. 选择「**GitHub**」，连接你的 GitHub 账号，选择仓库 `gaozhen25/card`
3. Branch 选 `main`
4. Builder 选择「**Dockerfile**」（项目根目录已有 Dockerfile）
5. 点「**Next**」
6. Service name 填 `wailian-card`（或任意名字）
7. Region 选 `Frankfurt` 或 `Singapore`（离国内近点）
8. Instance type 选「**Free**」（免费实例）
9. 点「**Advanced**」->「**Environment variables**」，添加：
   - `ADMIN_USER` = `admin`
   - `ADMIN_PASS` = `123456`
   - `SECRET_KEY` = 随便填一串随机字符（比如 `your-secret-key-change-me-123456`）
10. 点「**Deploy**」，等待构建完成（约 2-3 分钟）
11. 部署完成后，得到 `https://xxx.koyeb.app` 域名

### 部署后验证
- 后台：`https://xxx.koyeb.app/admin`
- 账号：`admin`，密码：`123456`
- 登录后新增卡片，复制链接发到抖音/小红书私信测试

### ⚠️ 数据持久化
Koyeb 免费实例的文件系统也是临时的，重启后 `data.db` 会重置。
- 测试用：免费版直接用，重启数据清空
- 正式用：升级付费实例并挂载持久化卷，或接入外部数据库

---

## Render 部署（需信用卡）

### 前置准备
1. 注册 Render 账号：https://render.com （用 GitHub 登录）
2. 把本项目推送到你自己的 GitHub 仓库

### 方式一：Blueprint 一键部署（推荐）
1. 登录 Render，进入 https://dashboard.render.com/blueprints
2. 点「New Blueprint Instance」，选择你的 GitHub 仓库
3. Render 会自动读取 `render.yaml`，点「Apply」
4. 等待部署完成（约 2-3 分钟），会得到一个 `https://xxx.onrender.com` 的域名
5. 部署完成后，在 Render Dashboard -> 你的服务 -> Environment 里查看自动生成的 `ADMIN_PASS`（这就是你的后台登录密码）

### 方式二：手动创建 Web Service
1. Render Dashboard -> New -> Web Service
2. 连接你的 GitHub 仓库
3. 填写配置：
   - **Runtime**：Python
   - **Build Command**：`pip install -r requirements.txt`
   - **Start Command**：`gunicorn app:app`
   - **Instance Type**：Free
4. 点「Advanced」->「Add Environment Variable」，添加：
   - `ADMIN_PASS`：你的后台密码（点「Generate」自动生成）
   - `SECRET_KEY`：点「Generate」自动生成
5. 点「Create Web Service」，等待部署完成

### 部署后验证
1. 访问 `https://你的域名.onrender.com/admin`
2. 用户名 `admin`，密码是 Environment 里的 `ADMIN_PASS`
3. 登录后新增卡片，复制链接发到抖音/小红书私信测试

### 环境变量说明
| 变量名 | 说明 | 默认值 |
|---|---|---|
| `PORT` | 监听端口（Render 自动注入，无需手动设置） | 8000 |
| `ADMIN_USER` | 后台登录用户名 | admin |
| `ADMIN_PASS` | 后台登录密码（**生产环境务必设置**） | 123456 |
| `SECRET_KEY` | Session 加密密钥（**生产环境务必设置**） | 内置默认值 |
| `DATABASE_PATH` | SQLite 数据库文件路径 | data.db |

### ⚠️ 数据持久化（重要）
Render 免费版实例的文件系统是**临时的**，每次重启或重新部署后，`data.db` 会被重置，你创建的卡片和日志会丢失。

**解决方案（二选一）：**

**方案 A：升级付费计划 + 挂载磁盘（推荐，$1/月起）**
1. 在 Render Dashboard 把实例升级到 Starter 或以上
2. 编辑 `render.yaml`，取消 `disk` 部分和 `DATABASE_PATH` 环境变量的注释
3. 重新部署，数据会持久化到 `/var/data/data.db`

**方案 B：接受数据丢失（仅测试用）**
- 免费版可以正常使用，但重启后数据清空
- 适合测试卡片效果，不适合正式运营

**方案 C：改用外部数据库**
- 可以接入 Render PostgreSQL、Supabase、Neon 等免费数据库
- 需要修改代码把 SQLite 换成 PostgreSQL（如需可联系协助）

## 使用流程

1. 登录后台，点击「新增卡片」
2. 填写标题、描述、封面图（**必须 HTTPS 公网图片地址**）、跳转目标（活码链接）
3. 设置访问上限、过期时间、是否启用黑名单
4. 保存后复制访问链接，粘贴到抖音 / 小红书私信
5. 平台爬虫抓取 OG 标签生成卡片预览，用户点击跳转到你的活码页面

## 目录结构

```
card/
├── app.py              # 主程序
├── requirements.txt    # 依赖（flask + gunicorn）
├── render.yaml         # Render Blueprint 部署配置
├── Procfile            # 启动命令（备选）
├── .gitignore          # Git 忽略规则
├── README.md           # 本文件
├── data.db             # SQLite 数据库（首次运行自动创建，勿提交）
└── templates/
    ├── base.html       # 后台布局
    ├── login.html      # 登录页
    ├── index.html      # 卡片列表
    ├── edit.html       # 新增/编辑
    ├── log.html        # 访问日志
    ├── blackip.html    # IP黑名单
    └── og.html         # 爬虫OG卡片页
```

## 注意事项

- 本地环境仅用于调试；要让平台真实抓取卡片，需部署到**公网 HTTPS**（Render 自动提供）
- 封面图必须 HTTPS，否则平台不会抓取
- 平台会更新爬虫 UA 规则，卡片效果不保证永久稳定
- 账号密码通过环境变量设置，不要硬编码
- 仅供技术学习，禁止用于违规营销
