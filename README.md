# StateTaxationAdminCrawler

企业级、基于 **Scrapy** 的税务/政策数据采集项目，用于结构化抓取国家税务总局、财政部、科技部、工信部、高企认定办等官网公开发布的政策法规、通知公告、新闻动态等公开信息。

> 本仓库是一个**工程化脚手架**：目录结构、配置体系、中间件/管道、持久化层、增量爬取与测试骨架均已就位。主包名为 `crawler`。业务选择器（XPath/CSS）按目标站点真实 DOM 调校后投入生产。

## 特性

- **环境隔离配置**：`development` / `production` / `testing` 三套 settings，通过 `SCRAPY_ENV` 切换。
- **外部化 YAML 配置**：`config/<env>.yaml` 通过 `${ENV_VAR}` 引用环境变量，真实生效（已接入 settings），可调并发、延迟、代理、存储、日志。
- **配置驱动爬虫**：所有站点根 URL / 允许域名 / 分类全部写在 `crawler/spiders/gov_categories.yaml`；spider 子类只声明 `name` + `category`，**不含任何 `.gov.cn` 字面量**（单测 `test_no_hardcoded_domains` 强制约束）。新增站点 = 改 YAML，不碰代码。
- **通用解析层**：`crawler/utils/policy_parse.py` 用「多选择器择优 + 正则」策略抽取标题/正文/发布日期/文号/发文机关，跨政府站点复用，spider 只关心分类与合规。
- **ItemLoader 清洗**：字段级 `input/output` 处理器在数据边界统一清洗（中文日期→ISO、URL 归一、整数抽取），spider 只关心抽取。
- **可插拔中间件**：随机 UA、代理轮换（静态池/API）、礼貌重试（带抖动退避）。
- **分层管道**：校验 → 去重 → 存储（JSONL 默认；数据库幂等 upsert）。
- **网页原样存盘（HTML）**：可选功能，`SAVE_HTML = True` 时把每个抓取的列表/详情页原始 HTML 落盘（默认 `False`，监控场景只需 URL）。
- **系统代理自动绕过**：`HTTPPROXY_ENABLED = False`，Scrapy 不读取 `http_proxy`/`https_proxy` 环境变量（避免无效/死代理让请求失败）；代理只走本项目自带的 `PROXY_POOL`/`PROXY_API_URL`。
- **持久化去重**：`crawled_urls` 表让去重**跨运行 / 跨机器**生效（无 DB 时自动退化为进程内去重）。
- **关系型持久化层**：SQLAlchemy 模型 + Alembic 迁移 + `createdb` 命令，把去重与存储落库。
- **增量 / 水位线爬取**：`IncrementalMixin` + `WatermarkStore`，跳过早于上次运行最大发布日期的旧条目。
- **可观测性**：统一日志（按 `SCRAPY_ENV` 分层：dev=DEBUG 落盘 / prod=INFO 落盘 / test=WARNING 不落盘）+ 启动配置自检（缺失 `DEEPSEEK_API_KEY` / `DATABASE_URL` / `NOTIFY_WEBHOOK_TOKEN` 时 WARNING 提示）+ 爬取结束统计扩展。
- **可测试 & CI**：离线 fixtures 驱动的 spider 集成测试 + `policy_parse` 单测、`pyproject.toml`（ruff/mypy/black/isort）、GitHub Actions CI、Dockerfile / docker-compose。

## 目录结构

```
StateTaxationAdminCrawler/
├── scrapy.cfg                 # Scrapy 部署配置（指向 crawler.settings）
├── pyproject.toml             # ruff / mypy / black / isort / pytest 配置
├── alembic.ini                # 数据库迁移配置
├── Dockerfile / docker-compose.yml / docker-entrypoint.sh / .dockerignore  # 根级 Docker（不再有 docker/ 子目录）
├── requirements/              # 依赖分层：base / dev / production + lock.txt
├── config/                    # 外部化 YAML 配置（按环境，真实生效）
├── migrations/                # Alembic 迁移（env.py + versions/）
├── deploy/                    # systemd 单元（tax-monitor.service / .timer）
├── scripts/                   # setup.sh / crawl.sh / monitor.bat / MonitorTask.xml 运维脚本
├── tests/                     # unit / integration + fixtures（离线）
├── data/  reports/  logs/     # 运行产物（gitignore，data/ 含 crawler.db / backend.db）
└── crawler/                   # 主包（BOT_NAME = "crawler"）
    ├── items/                 # 数据模型（TaxPolicyItem / TaxNewsItem）
    ├── spiders/               # 全部爬虫（配置驱动）
    │   ├── gov_categories.yaml    # ★ 唯一数据源：所有根 URL / 域名 / 分类
    │   ├── policy_root_base.py    # 通用基类（CrawlSpider + 分类器 + 合规守卫 + 礼貌）
    │   ├── gov_categories/        # 5 大分类瘦子类（caishui/gaoqi/gongxin/yanfa/kexiao）
    │   └── gov_policy/            # gov_policy_root（通用兜底，category=gov_general）
    ├── pipelines/             # 校验 / 去重 / 存储（JSONL + DB upsert）/ 通知
    ├── middlewares/           # UA / 代理 / 重试
    ├── downloaders/           # 可选 Playwright 下载处理器（JS 站点，由 js:true 触发）
    ├── notifiers/             # 可插拔通知后端（webhook / wechaty）
    ├── settings/              # base + 各环境覆盖
    ├── utils/                 # 解析 / 日期 / 代理池 / 日志 / 配置加载 / 增量 / 合规
    ├── db/                    # SQLAlchemy 模型 / 引擎 / 会话（持久化层）
    ├── extensions.py          # 自定义扩展（爬取统计）
    └── commands/              # 自定义 scrapy 命令（createdb / monitor）
```

> **目录清晰化已完成的清理**：删除重复的 `docker/` 子目录（保留根级 `Dockerfile`/`docker-compose.yml`）；删除三代旧硬编码 per-site spider（`chinatax/` `mof/` `most/` `miit/` `innocom/` 及 `base_spider.py`/`policy_base.py`），统一为 YAML 驱动；运行时产物（`*.db` / `report_*.md` / `monitor_run.log`）移出仓库根、归位到 `data/` `reports/` `logs/`。

## 已接入的爬虫（`scrapy list`）

全部由 `gov_categories.yaml` 配置驱动，共 **6 个 spider**。`scrapy list` 输出：

```
caishui  gaoqi  gongxin  gov_policy_root  kexiao  yanfa
```

| spider name | 对应分类（YAML 块） | 说明 |
|-------------|---------------------|------|
| `gov_policy_root` | `gov_general` | 通用兜底（国务院政策文件库 + 地方政府占位），接 `-a roots=` 可一次性临时扫描 |
| `caishui` | `caishui` | 财税政策（财政部各司子站 + 税务总局政策法规库 + 12366） |
| `gaoqi` | `gaoqi` | 高新技术企业政策（高企认定网 + 国家政务服务平台 + 科技部） |
| `gongxin` | `gongxin` | 工信政策（**当前为空占位** `roots: []`，待补充） |
| `yanfa` | `yanfa` | 研发费用政策（税务总局政策法规库 + 科技部企业科技政策专区） |
| `kexiao` | `kexiao` | 科技型中小企业政策（工信部政策性文件 + 优质中小企业梯度培育平台） |

> **没有单独的"JS/静态"清单了**：旧架构里 10 个硬编码 spider（含 4 个 JS 站）已合并。JS 渲染的站点（如 `12366`、`miit_zjtx`）现在只是 YAML 里带 `js: true` 标记的根，spider 在 `start()` / `process_request` 中自动给这些请求注入 `meta["playwright"]`——**不写任何域名常量**。要加一个 JS 站，只需在对应分类块加一条 `js: true` 的根。

## 前后端同时启动（本地开发）

前端 Vite 开发服务器使用 `5200` 端口，后端 FastAPI 使用 `8000` 端口。建议先完成依赖安装，再分别启动两个服务。

### Cloudflare Pages 部署前端

前端部署到 Cloudflare 时，在 `frontend/` 目录执行：

```bash
cd /home/steve/PythonC/Luck3mc/frontend
npm install
npm run build
npx wrangler deploy
```

`frontend/wrangler.jsonc` 已将 `dist/` 配置为静态资源目录。Cloudflare 项目配置应使用：

- 构建命令：`npm run build`
- 输出目录：`dist`
- 部署目录：`frontend`

> 不要执行 `npm audit fix --force` 来解决部署问题；本次失败原因是 Vite 版本和 Wrangler 自动配置要求不兼容，已将 Vite 升级到 6.x。

### 方式一：两个终端启动（推荐）

终端一，启动后端：

```bash
cd /home/steve/PythonC/Luck3mc
source .venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

终端二，启动前端：

```bash
cd /home/steve/PythonC/Luck3mc/frontend
npm install                         # 首次运行执行；已有依赖可跳过
npm run dev -- --host 0.0.0.0
```

启动后访问：

- 前端：<http://localhost:5200>
- 后端健康检查：<http://localhost:8000/health>
- 后端 API 文档：<http://localhost:8000/docs>

### 方式二：一条命令同时启动

在项目根目录执行。需要系统已安装 `tmux`，并且 Python 虚拟环境及前端依赖已经准备好：

```bash
cd /home/steve/PythonC/Luck3mc
source .venv/bin/activate
tmux new-session -d -s luck3mc-dev 'uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000' \; split-window -h 'cd frontend && npm run dev -- --host 0.0.0.0' \; attach-session -t luck3mc-dev
```

关闭两个服务：在 tmux 中按 `Ctrl-B`，再按 `D` 离开会话；需要彻底停止时执行：

```bash
tmux kill-session -t luck3mc-dev
```

## 快速开始

```bash
# 1. 初始化本地环境（venv + 依赖 + .env）
bash scripts/setup.sh
source .venv/bin/activate        # Windows: .\.venv\Scripts\activate

# 2. 配置密钥（重要：代码只读取 .env，不读 .env.example！）
cp .env.example .env
#   编辑 .env，至少填入：
#     DEEPSEEK_API_KEY=sk-xxxx        # 生成每日报告必需
#     NOTIFY_WEBHOOK_TOKEN=xxxx       # 微信推送必需（可选）
#   不建 .env 时，启动时日志会 WARNING 提示缺失的配置项。
scrapy monitor --help            # 确认能跑起来（会打印配置自检结果）

# 3. 准备数据库（可选；不配置 DATABASE_URL 也能跑，数据落 JSONL）
export DATABASE_URL="sqlite:///data/crawler.db"
scrapy createdb                  # 建表 / 跑 Alembic 迁移

# 4. 运行一个分类爬虫（从 gov_categories.yaml 读该分类的 roots）
SCRAPY_ENV=development scrapy crawl caishui

# 或用临时 roots 覆盖 YAML，抓任意站点（不写代码）：
scrapy crawl gov_policy_root -a roots=https://www.gov.cn/zhengce/

# 5. 运行测试（含离线 spider 集成测试，无需联网）
pytest
```

> **密钥入口是 `.env`，不是 `.env.example`**：所有 `DEEPSEEK_API_KEY` / `NOTIFY_WEBHOOK_TOKEN` / `DATABASE_URL` 等真实值都写在仓库根目录的 `.env`（已被 gitignore）。`.env.example` 只是模板，**代码不会读取它**——把 key 写进 `.env.example` 会导致"配了但没生效"的假象（本项目早期就踩过这个坑）。`.env` 不存在时，启动会有 WARNING 提示，但爬虫照常运行（仅报告/推送环节会失败）。

## JS 站点：启用 Playwright（可选）

`gov_categories.yaml` 中标记了 `js: true` 的根（当前为 `12366` 与 `miit_zjtx`，均在分类块内）需要 Playwright 才能抓取：

```bash
pip install scrapy-playwright
playwright install chromium       # 下载浏览器二进制
```

`crawler/settings/{production,development}.py` 中已**条件式**接入 Playwright 下载处理器（仅当 `scrapy-playwright` 已安装时生效，其余 spider 不受影响，未安装时项目照常运行）。启用后 Scrapy 自动切换为 asyncio reactor。`js: true` 标记是驱动 Playwright 的唯一开关——spider 源码里没有任何站点域名常量。

## 运行环境切换

| 环境 | 命令 | 说明 |
|------|------|------|
| 开发 | `SCRAPY_ENV=development scrapy crawl <name>` | 低并发、DEBUG 日志、本地 JSONL 输出 |
| 生产 | `SCRAPY_ENV=production scrapy crawl <name>` | 高并发、AUTOTHROTTLE、JSONL + 数据库幂等写入 |
| 测试 | `SCRAPY_ENV=testing scrapy crawl <name>` | 关闭礼貌约束，供测试断言 |

也可通过 Docker 运行生产爬虫：

```bash
docker compose -f docker-compose.yml run --rm crawler scrapy crawl caishui
```

## 日期过滤（只爬指定起点之后）

`DateFilterPipeline` 提供两个**正交、可独立开关**的日期闸门（都在 `crawler/settings/base.py` 有默认值，可通过环境变量或 `-s` 覆盖）：

| 设置 | 含义 | 默认 |
|------|------|------|
| `CRAWL_FROM_DATE` | 丢弃发布日期**早于**该日期的条目（ISO `YYYY-MM-DD`） | `2026-01-01` |
| `CRAWL_TODAY_ONLY` | 只保留**当天**发布的条目（严格日级巡检用） | `false` |

- 两个闸门互不耦合：可只开其一、都开、或都关（都关 = 全量，不过滤）。
- 解析失败的发布日期**不会被丢弃**（仅 WARNING 保留），避免误删。
- 阈值由 settings 注入 pipeline，pipeline 自身不写死任何日期——保持解耦。

常用场景：

```bash
# 默认：只保留 2026-01-01 起的政策（历史回溯也只留 2026+）
scrapy monitor

# 只要今天新发的（严格日级巡检）
scrapy monitor -s CRAWL_TODAY_ONLY=1

# 自定义起点，例如只要 2025 年以来的
scrapy crawl caishui -s CRAWL_FROM_DATE=2025-01-01
```

> 本项目当前目标为"**只爬 2026 年 1 月 1 日起**"，因此 `CRAWL_FROM_DATE` 全局默认已设为 `2026-01-01`。`monitor` 命令默认尊重该值（不再强制只抓当天），需要当天模式时显式 `-s CRAWL_TODAY_ONLY=1`。

## 统一日志与配置自检

- **日志按环境分层**：由 `SCRAPY_ENV` 决定（`development`=DEBUG 落盘 / `production`=INFO 落盘 / `testing`=WARNING 不落盘），日志统一写入 `logs/crawler.log` 并同时打印到控制台。入口命令（`scrapy monitor` / `scrapy createdb`）在启动时按当前环境的 `LOG_*` 设置初始化，不写死。
- **配置自检**：启动时 `crawler/utils/diagnostics.py` 会检查关键环境变量，缺失则打印 `WARNING`，例如：
  ```
  WARNING: 配置缺失 [必需]: DEEPSEEK_API_KEY 未设置 — 生成每日报告必需…
  WARNING: 配置缺失 [可选]: DATABASE_URL 未设置 — 跨运行去重依赖…
  WARNING: 配置缺失 [可选]: NOTIFY_WEBHOOK_TOKEN 未设置 — 微信推送必需…
  ```
  这比"跑到 DeepSeek 调用时才报错"更早暴露问题。

## 配置优先级

`base.py` 默认值  <  `config/<env>.yaml`（外部化配置）  <  `development/production/testing.py`（环境覆盖，最终权威）

其中 `config/*.yaml` 里的 `proxy.pool` / `proxy.api_url` / `storage.database_url` 还桥接到环境变量，便于运行时覆盖（显式环境变量优先于 YAML 空值）。

> **系统代理被默认绕过**：`base.py` 设置了 `HTTPPROXY_ENABLED = False`，Scrapy 不会读取 `http_proxy` / `https_proxy` 环境变量。这样即使宿主机注入了无效/死代理（如本机 `127.0.0.1:7897`），请求也会直连而非走代理失败。若确实要用系统代理，把该值改为 `True` 即可；本项目自带的代理池（`PROXY_POOL` / `PROXY_API_URL`）不受影响，始终通过 `meta['proxy']` 生效。

## 持久化与去重

- **`DatabasePipeline`**：以 `(source_url, item_type)` 为唯一键做幂等 upsert——重复爬取同一页只会更新已有行，不会新增重复记录。未配置 `DATABASE_URL` 时为安全 no-op（仅告警）。
- **`DeduplicatePipeline`**：配置了 `DATABASE_URL` 时写入 `crawled_urls` 表，去重**跨运行/跨机器**生效；未配置时退化为进程内 `set`（单次运行内去重）。
- **增量爬取**：spider 继承 `IncrementalMixin`，在 `parse_detail` 中 `if self.is_new(item): self.record_seen(...); yield item`，按 `data/watermarks/<spider>.json` 记录的水位线跳过旧条目。

## 下载为 HTML（SAVE_HTML）

除结构化字段（JSONL / 数据库）外，每个抓取的页面还会**原样保存为 `.html` 文件**，方便归档、复核或离线解析（监控场景默认不需要，故默认关闭）：

```
<OUTPUT_DIR>/html/<spider>/list/<url>.html     # 列表页
<OUTPUT_DIR>/html/<spider>/detail/<url>.html   # 详情页
```

- 文件名由页面 URL 派生（去掉协议、非法字符，超长则截断 + MD5），唯一且可读。
- 由 `crawler/utils/html_export.py` 的 `save_response_html` 落盘，**失败静默吞掉**，绝不影响爬取。
- 开关：`SAVE_HTML`（默认 `False`）。开启后会把每个页面原样存为 HTML 文件；监控场景一般保持关闭，只拿 URL。

## 24 小时监控 + 微信通知

本项目的核心用途之一：**持续巡检这些官网，一旦发现新的政策 URL，就推送到微信**。

### 工作原理
1. `scrapy monitor` 命令一次性跑完 `config/*.yaml` 里 `monitor.spiders` 列出的所有分类 spider（默认 5 个：`gov_policy_root` / `caishui` / `gaoqi` / `yanfa` / `kexiao`，`gongxin` 因暂无根而留空）。默认尊重 `CRAWL_FROM_DATE=2026-01-01`，即只保留 2026 年起的政策；需严格当天模式时加 `-s CRAWL_TODAY_ONLY=1`。
2. 依赖 `crawled_urls` 去重表做**跨运行**判断：只有数据库里没见过的新 URL 才会被当作"新增"。
3. 新增条目在经过 `NotifyPipeline`（位于去重管线之后，order 250）时，调用通知器把 `{标题, URL, 发布日期, 来源}` 推送到微信。

### ?? 个人微信没有官方机器人 API
个人微信（私人微信号建的群）**没有开放的机器人接口**，和企业微信机器人是两码事。本项目提供两条路：

| 后端 | 默认 | 说明 | 风险 |
|------|------|------|------|
| `webhook`（推荐） | ? | 对接 **Server酱 / pushplus**（扫码绑定个人微信，消息以"服务通知"形式到达你个人微信）+ 企业微信机器人 / 任意 webhook。最稳、零封号风险。 | 低 |
| `wechaty` | ? | 把某个真实个人微信账号当机器人登录，才能往群里发。需 `pip install wechaty` + 付费 puppet token。 | 有封号/合规风险，脚手架未默认启用 |

**推荐**：用 Server酱 或 pushplus 拿到 webhook 地址后填到配置里，个人微信就能 24h 收到新政策链接。若必须要"真·群聊机器人"，再考虑 `wechaty`（请先评估账号风险）。

### 配置（`config/production.yaml` 或环境变量）
```yaml
notify:
  enabled: true
  backend: "webhook"
  webhook_kind: "serverchan"       # serverchan | pushplus | wecom | generic
  webhook_token: "你的SendKey"      # serverchan/pushplus 用；wecom/generic 用下方 webhook_url
  # webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
monitor:
  spiders: [ gov_policy_root, caishui, gaoqi, yanfa, kexiao ]
```
环境变量覆盖同名：`NOTIFY_ENABLED` / `NOTIFY_BACKEND` / `NOTIFY_WEBHOOK_URL` / `NOTIFY_WEBHOOK_KIND` / `NOTIFY_WEBHOOK_TOKEN`。

### 让监控真正 24 小时跑起来
沙箱 / WorkBuddy 不是常驻服务器，真正的定时轮询要跑在你自己的机器上。仓库已给出 Windows 调度：

```bat
rem scripts/monitor.bat —— 设好 SCRAPY_ENV 与 Python 后执行 scrapy monitor
rem scripts/MonitorTask.xml —— 每 6 小时触发一次的 Windows 任务计划
schtasks /Create /TN "TaxPolicyMonitor" /XML scripts\MonitorTask.xml
rem 或等价的一行命令（每 6 小时）：
schtasks /Create /SC HOURLY /MO 6 /TN "TaxPolicyMonitor" /TR "C:\...\scripts\monitor.bat"
```
Linux / macOS 用 `crontab -e` 加 `0 */6 * * * cd /path && python -m scrapy monitor` 即可。

### ?? 监控机首次部署必须先建库
跨运行去重靠数据库（SQLite 零配置即可）：
```bash
scrapy createdb          # 生成 data/crawler.db
```
不建库则每次轮询都会把全部条目当"新"重复推送。

### 已验证的端到端效果
实测：真实抓取 `most.gov.cn` 企业科技政策专栏 → 12 条新政策 → webhook 收到 12 次 POST，每条携带真实政策 URL。

## Docker 部署（Linux 服务器）

项目是纯 Python + Scrapy，**跨平台可直接运行**，无 Windows 专属代码。以下把整套监控 + 微信通知闭环打包成镜像，在 Linux 服务器上 24 小时常驻。

### 1. 构建镜像

```bash
# 默认镜像包含无头 Chromium（YAML 里 js:true 的根需要，如 12366 / miit_zjtx）
docker build -t tax-policy-crawler:latest .

# 若暂不需要 JS 站，可去掉 Chromium 得到更小镜像：
docker build --build-arg INSTALL_CHROMIUM=false -t tax-policy-crawler:latest .
```

### 2. 配置密钥（不写进镜像）

```bash
cp .env.example .env
# 编辑 .env，填入你的 Server酱 / pushplus SendKey：
#   NOTIFY_WEBHOOK_KIND=serverchan
#   NOTIFY_WEBHOOK_TOKEN=你的SendKey
```

### 3. 跑一次看看 / 定时调度

```bash
# 先确保去重库表存在（容器启动时也会自动 createdb，这里显式跑一次也行）
docker compose run --rm crawler createdb

# 立即跑一轮监控（抓 5 个分类 spider、识别新增、推微信）
docker compose run --rm crawler monitor

# 手动爬单个分类 spider
docker compose run --rm crawler crawl caishui
```

**每 6 小时自动跑**（推荐用宿主机 systemd timer，容器保持一次性、无状态，去重库在命名卷里跨轮持久）：

```bash
sudo cp deploy/tax-monitor.service deploy/tax-monitor.timer /etc/systemd/system/
# 编辑两个文件里的 /opt/tax-crawler 路径为你克隆仓库的位置
sudo systemctl daemon-reload
sudo systemctl enable --now tax-monitor.timer
```

或退而求其次用 cron：

```cron
0 */6 * * *  cd /opt/tax-crawler && docker compose run --rm crawler monitor >> /var/log/tax-monitor.log 2>&1
```

### 关键注意点

- **去重库必须落卷**：`DATABASE_URL=sqlite:////var/lib/crawler/data/crawler.db` 已指向挂载卷 `crawler_data`。若改成不落卷，每次运行都会把全部历史当"新"重复推送（刷屏）。
- **密钥走环境变量**：webhook token 通过 `.env` → compose → 容器环境变量注入，绝不进镜像。
- **JS 站点依赖 Chromium**：`INSTALL_CHROMIUM=true`（默认）时镜像较大；若不需要 YAML 里 `js: true` 的根（如 12366 / miit_zjtx），设为 `false`。
- **个人微信推送**：通过 Server酱 / pushplus 以"微信服务通知"触达你本人（个人微信无官方机器人 API）。真·群聊机器人需 `wechaty`（脚手架，未在 Docker 中默认启用）。

## 新增一个数据源

配置驱动，绝大多数情况**不用写代码**，只需改 YAML：

1. 在 `crawler/spiders/gov_categories.yaml` 找到（或新增）一个分类块（`categories.<category>`），在 `roots:` 下加一条：
   ```yaml
   - name: my_site        # 稳定标识（也是 source_site 标签）
     url: https://x.gov.cn/zhengce/   # 栏目根地址（列表/索引页）
     domain: x.gov.cn                  # 允许域名
     js: false                         # 列表若为 JS 渲染则设 true（自动走 Playwright）
   ```
2. 若是一个**全新分类**（不是现有 5 类之一），在 `crawler/spiders/gov_categories/__init__.py` 加一个 ~4 行的瘦子类，只声明 `name` + `category`：
   ```python
   class MySpider(PolicyRootBaseSpider):
       name = "mycategory"
       category = "mycategory"
   ```
   所有爬取机制（规则 / 合规守卫 / 政策分类 / 字段抽取 / 礼貌设置）都从 `PolicyRootBaseSpider` 继承，**spider 源码里不出现任何站点域名常量**（单测 `test_no_hardcoded_domains` 会卡住违规）。
3. 选择器按目标站点真实 DOM 调校；通用抽取逻辑集中在 `crawler/utils/policy_parse.py`。

## 测试

- `tests/integration/test_spiders.py`：用 `http.server` 离线伺服真实 HTML fixture，跑通 `gaoqi` 全链路（spider → ItemLoader 清洗 → 校验 → 去重 → 采集），不联网、确定性。
- `tests/unit/test_policy_classify.py` / `test_gov_categories.py`：针对政策/新闻分类器与 YAML 解析（含"无硬编码域名"约束）做单测。

```bash
pytest -q                          # 全部（含离线集成 + 单测）
pytest tests/integration -m offline  # 仅离线集成
```

## 合规说明

项目默认 `ROBOTSTXT_OBEY = True` 并设置了下载延迟与自动限速，请遵守目标站点的 `robots.txt` 与服务条款，控制抓取频率，避免对站点造成压力。
