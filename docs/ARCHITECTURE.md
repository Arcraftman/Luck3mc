# 架构说明（ARCHITECTURE）

> 本文档描述 `StateTaxationAdminCrawler` 的**分层架构**、**数据流**与**推送链路**。
> 内容为纯文本 + ASCII 图，便于在任何终端 / 渲染器查看（无 mermaid 依赖）。

## 1. 分层总览（依赖倒置）

```
+----------------------------+  接口层 / Interface
|  spiders/  (Scrapy 爬虫)   |      - 极薄：只声明 start_urls / 解析规则
|  scripts/  (CLI 入口)      |      - generate_report / weekly_digest 仅做 argparse + 打印
+------------+---------------+
             | 调用（依赖抽象，不依赖实现细节）
             v
+------------+---------------+  应用层 / Application Services
|  crawler/services/         |      - report_generator: 日报(读jsonl→DeepSeek→拼报告→推送)
|    report_generator.py     |      - digest_builder:    周报(读jsonl→补贴过滤→聚合→推送)
+------------+---------------+
       |              |
       | 依赖         | 依赖
       v              v
+------+-----+  +-----+-----------+  领域层 / Domain           基础设施层 / Infrastructure
| crawler/    |  | crawler/        |      Domain:                    Infra:
|  utils/     |  |  notifiers/     |       keywords (补贴词表)        notifiers (WebhookNotifier)
|   keywords  |  |    __init__     |       subsidy_filter.matches_   webhook / wechaty / base
|   policy_parse         |         subsidy (匹配规则)        storage (JsonLinesExportPipeline)
|  pipelines/            |                                 config_loader (YAML→settings)
|   subsidy_filter       |                                 config (AppConfig 类型化)
+------------------------+
```

依赖方向：**接口层 → 应用层 → 领域/基础设施层**。应用层（services）只依赖
`crawler.domain`（关键词 / 补贴匹配）与 `crawler.notifiers`，**不在 services 内直接
`urllib`/`requests` 做推送**——推送统一收敛到 `WebhookNotifier.send_markdown`。

## 2. 配置类型化（crawler/config.py）

```
config/<env>.yaml  ──load_config()──>  dict
                                      │
                                      v  AppConfig.load()
                          +-----------------------------------+
                          |  AppConfig (frozen dataclass)     |
                          |   ├─ ScrapeConfig  (robots/delay) |
                          |   ├─ StorageConfig (output_path)  |
                          |   └─ NotifyConfig  (as_notifier_  |
                          |                     settings())   |
                          +-----------------------------------+
                                      │ get_settings() 单例
                                      v
                        scripts/ 与 services/ 读取 data_dir / notifier 配置
```

- `get_settings(env=None)` 进程内缓存，避免重复读 YAML。
- `StorageConfig.output_path` 把 `storage.output_dir` 相对路径锚定到项目根，与
  `JsonLinesExportPipeline` 的 `OUTPUT_DIR` 语义一致（消除脚本硬编码 `data/` 的漂移）。
- `NotifyConfig.webhook_token` **原样透传**，不修改 `config/*yaml` 中的明文值。

## 3. 数据流（日报 generate_report）

```
                         data/<spider>/<date>.jsonl (JsonLinesExportPipeline 写出)
                                         │
                                         v  report_generator.collect_items()
                         [ {spider,title,url,pub_date,authority,content} ... ]
                                         │
                                         v  call_deepseek()  (urllib → DeepSeek API)
                         报告摘要 (Markdown, ≤900字)
                                         │  + build_links_section()  (追加“## 原文链接”)
                                         v
                                 完整 Markdown (摘要 + 原文链接)
                                         │
                                         v  notifier.send_markdown(title, md)
                                 微信 (pushplus, template=markdown)
```

- `collect_items` 只读、无网络；`call_deepseek` 是唯一对外网络调用（内容源，非通知传输）。
- 推送与 spider 抓取、notify pipeline 的逐条 `txt` 推送**互不影响**（既有行为保留）。

## 4. 推送链路（统一收敛）

```
旧实现（三份漂移）:                     新实现（单一收敛点）:
  notifiers/webhook.py  (pipeline 逐条 txt)
  scripts/generate_report.py (urllib 直推)     ──┐
  scripts/weekly_digest.py  (requests 直推)     ──┼──>  get_notifier(settings)
                                                  │       │
                                                  │       v
                                                  │   WebhookNotifier.send_markdown()
                                                  │       │ (pushplus, template=markdown)
                                                  │       v
                                                  └──>   微信 pushplus
```

- 三处推送逻辑统一为 `crawler.notifiers.get_notifier(settings)` + `send_markdown`。
- `notify` pipeline 的**逐条 txt 推送**保持原行为不变（约束要求不改动）。

## 5. 测试分层

```
tests/
  unit/       纯函数 / 单类: matches_subsidy, extract_content, send_markdown,
               report_generator.collect_items (只读 data/*.jsonl)
  integration/ 跨模块: notify loop / spiders (离线或打标 offline)
  conftest.py 注入项目根到 sys.path, 默认 SCRAPY_ENV=testing
```

所有单测不触发真实网络 / DeepSeek / 推送（DeepSeek 调用与 `_post` 均 mock）。
