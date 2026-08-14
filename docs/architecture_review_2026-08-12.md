# 架构评审：高内聚低耦合专项（2026-08-12）

> 评审方式：独立子代理通读真实代码后产出，仅分析未改动任何文件。

## 总体评分

| 维度 | 分数 | 简述 |
|---|---|---|
| 高内聚 | **8 / 10** | 各 pipeline 单一职责、spider 极薄、notifiers 有抽象基类+工厂；扣分在"配置/数据与代码未分离"和"脚本上帝文件"。 |
| 低耦合 | **6 / 10** | 跨层 import 基本克制，但存在 settings 反向依赖 pipeline、推送逻辑三份漂移、脚本绕过 config_loader、存储路径字符串耦合、secret 明文入仓库。 |

## 内聚评估

- 模块级内聚高：validation / date_filter / deduplication / notify / storage 各司其职；spider 薄、复用 `policy_parse` / `loaders`；notifiers 有抽象基类 + 工厂。
- 扣分点：
  - `crawler/pipelines/validation.py:12` — 必填字段 `REQUIRED_FIELDS` 硬编码在管道里，与 Item 定义脱钩。
  - `crawler/pipelines/subsidy_filter.py:26-71` — 三张关键词表 + `matches_subsidy` 纯函数 + `SubsidyFilterPipeline` 类同文件（数据/逻辑/管道混合）。
  - `scripts/generate_report.py` — 一个文件兼任 读 .env、正则读 yaml token、读 jsonl、调 DeepSeek、调 pushplus、拼 markdown（职责过多）。

## 耦合评估

- 好的一面：spider 不直接 import pipeline/notify；分层大体清晰。
- 问题点：
  - `crawler/settings/base.py:184` — `from crawler.pipelines.subsidy_filter import DEFAULT_SUBSIDY_KEYWORDS`，**settings 层反向依赖 pipelines 层**，且 subsidy_filter 已关闭仍保留该 import（base.py:86 注释关闭），导入失败会拖垮整个 settings。
  - `crawler/pipelines/notify.py:58` — 每条 item 直接 `self.notifier.send(...)`（逐条推送），`notifier/base.py:43` 的 `send_batch` 未被使用。
  - 管道顺序隐式耦合：`base.py:83-91` 的 `ITEM_PIPELINES` 顺序即行为依赖（notify 要求 dedup(200) 先于 notify(250)，date_filter 须先于 deduplication）；顺序改动即改变语义。
  - 推送逻辑三份实现：`notifiers/webhook.py:52-53` vs `scripts/generate_report.py:32,158-175`(urllib) vs `scripts/weekly_digest.py:35,157-180`(requests)，模板/HTTP 库均不同，易漂移。
  - 配置读取被绕过：`scripts/generate_report.py:60-72` 用正则直读 `config/production.yaml`，无视 `config_loader.py` 与 `SCRAPY_ENV`（开发环境也会读生产 yaml）。
  - 存储布局字符串耦合：`storage.py:36-40` 写 `OUTPUT_DIR/<spider>/<date>.jsonl`；`generate_report.py:30` 硬编码 `DATA_DIR=".../data"`（与 production 的 `OUTPUT_DIR=/var/lib/crawler/data` 不一致，会读错目录）。

## Top 风险点（≤5）

1. **`crawler/settings/base.py:184`** — settings 反向依赖 pipelines，破坏分层；为已停用 subsidy_filter 保留强依赖，导入失败拖垮全局。
2. **`scripts/generate_report.py:30,60-72`** — 硬编码 `data/` + 正则直读 production.yaml token，绕过 config_loader、无视 `OUTPUT_DIR`/`SCRAPY_ENV`，环境切换即读错/读错密。
3. **`notifiers/webhook.py:52`、`generate_report.py:158`、`weekly_digest.py:157`** — pushplus 推送三份实现，改一处须同步三处。
4. **`config/development.yaml:35`、`config/production.yaml:29`** — pushplus token **明文硬编码进 VCS**，与 config_loader 的"secret 不出仓库"设计自相矛盾。
5. **`crawler/spiders/mof/fgk_spider.py:42,98,160`** — spider 直接用 `requests` 抓详情/搜索，绕过 Scrapy 下载器与 proxy/retry/UA 中间件，难以统一治理与测试。

## 可操作改进建议（按优先级，尽量不改外部行为）

1. **解耦 settings↔pipelines**：把 `DEFAULT_SUBSIDY_KEYWORDS` 移入 `crawler/utils/keywords.py`（或 config YAML），`base.py:184-186` 改为从新位置读取；subsidy_filter 关闭时 settings 不再触碰 pipeline 层。
2. **脚本复用 notifiers 与 config_loader**：`generate_report.py`/`weekly_digest.py` 的推送改为 `from crawler.notifiers import get_notifier` + `settings.get("NOTIFY_WEBHOOK_TOKEN")`；删掉 `_read_yaml_token`，统一走 `config_loader.load_config()`。三份推送收敛为一处。
3. **统一存储路径来源**：脚本用 `settings.get("OUTPUT_DIR")` 替换硬编码 `data/`（参考 `weekly_digest.py:195` 已正确做法），消除与 `storage.py` 布局的字符串耦合；或抽 `crawler/utils/jsonl_io.py` 供 storage 与脚本共用。
4. **secret 外置**：从 `config/*yaml` 删除明文 token，仅保留 `${NOTIFY_WEBHOOK_TOKEN}`（YAML 已有 `${VAR}` 展开机制，`config_loader.py:24`）。
5. **notify 批量 + LLM 抽象**：NotifyPipeline 改用 `notifier.send_batch` 降低逐条推送开销；`call_deepseek` 抽成 `crawler/llm.py:LLMClient` 接口，替换 provider 只换实现；mof spider 的 `requests` 抓取改为 Scrapy Request + 中间件，复用代理/重试。

## 默认不一致（附）

- `date_filter.py:26`（默认 False） vs `mof/fgk_spider.py:113`（默认 True）—— 同一语义 `CRAWL_TODAY_ONLY` 在两个地方默认值相反，易踩坑。
