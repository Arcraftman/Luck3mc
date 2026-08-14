# ADR-001: 关闭补贴过滤 + DeepSeek 基于原文生成报告 + pushplus markdown 推送

- 状态（Status）: 已采纳（Accepted）
- 日期（Date）: 2026-08-12
- 决策人（Deciders）: 工程负责人 / 架构师

## 背景（Context）

运营目标从“全量政策火库（firehose）”收敛为“聚焦财税补贴政策”，但有两个并行的
诉求需要同时被满足：

1. **周报**仍需要“补贴过滤”视角：每周把新发现的财税补贴政策按来源聚合推送给
   运营者。因此 `subsidy_filter.matches_subsidy` 与 `weekly_digest` 的补贴重筛逻辑
   **必须保留**（仅 `SubsidyFilterPipeline` 在 `ITEM_PIPELINES` 中被注释关闭，spider
   落库不再过滤，但周报读取 JSONL 时仍用 `matches_subsidy` 重新筛选）。
2. **日报**需要一份面向微信推送的、可读的“政策摘要”：基于当日爬取的**原文**
   （标题 / 发布机关 / 发布日期 / 正文）由 DeepSeek 生成中文 Markdown 摘要，并在
   文末附上**原文链接**，方便一键回溯。

此前 `scripts/generate_report.py` / `scripts/weekly_digest.py` 各自内联了“读 jsonl
+ 调 LLM/聚合 + 推送”的完整逻辑，并分别用 `urllib` / `requests` 直推，与
`notifiers/webhook.py` 形成**三份漂移的推送实现**，且绕过 `config_loader` 直接读 YAML。

## 决策（Decision）

1. **补贴日过滤关闭、周过滤保留**：`ITEM_PIPELINES` 中 `SubsidyFilterPipeline` 保持
   注释关闭（全局落库不再因关键词丢条目）；`weekly_digest` 在读取 `data/*.jsonl`
   时仍调用 `crawler.pipelines.subsidy_filter.matches_subsidy` 做“补贴命中”重筛。
2. **日报基于原文生成**：`report_generator` 读取当日 `data/<spider>/<date>.jsonl` 原文，
   调用 DeepSeek（`deepseek-chat`）生成 ≤900 字中文 Markdown 摘要，分“概述 / 主题分类
   / 可操作要点”三段；文末追加 `## 原文链接` 区块列出每条政策标题+日期+机关+URL。
3. **统一 pushplus markdown 推送**：日报与周报均经
   `crawler.notifiers.get_notifier(settings)` 取得 `WebhookNotifier`，并调用
   `send_markdown(title, content_md)`（pushplus `template=markdown`）。脚本不再直连
   网络推送。
4. **业务核心下沉到 `crawler/services/`**：`report_generator.py` 与 `digest_builder.py`
   承载编排逻辑，`scripts/` 退化为薄 CLI（仅 argparse + 打印），实现依赖倒置与可测试性。
5. **配置类型化**：新增 `crawler/config.py`（`AppConfig`/`NotifyConfig`/
   `StorageConfig`/`ScrapeConfig` + `get_settings()` 单例），封装 `config_loader`
   并统一解析 `data_dir` 与 notifier 设置。

## 权衡（Consequences / Trade-offs）

- **Secret 暂留 YAML**：`notify.webhook_token` 仍以明文写在 `config/development.yaml`
  与 `config/production.yaml`。短期可接受（与既有现状一致、约束禁止改动该明文值）；
  长期应迁移到 `${NOTIFY_WEBHOOK_TOKEN}` 环境变量（config_loader 已支持 `${VAR}` 展开）。
- **spider 仍用 `requests`**：`crawler/spiders/mof/fgk_spider.py` 内部直接用 `requests`
  抓详情/搜索，绕过 Scrapy 下载器与 proxy/retry/UA 中间件。本次**未改动**（约束要求
  保持 spider 抓取逻辑不变）；统一治理留待后续 ADR。
- **DeepSeek 调用未抽象为 Provider 接口**：`call_deepseek` 仍是 `urllib` 直连单实现。
  当前只有 DeepSeek 一个供应商，先求“逻辑收敛到 services”而非过度设计；若后续引入
  多 LLM，再抽 `crawler/llm.py:LLMClient` 接口替换实现。
- **推送仍可能失败静默**：`send_markdown` 网络异常返回 `False` 且不抛出，避免死 webhook
  拖垮报告生成；代价是推送失败需依赖调用方打印/退出码暴露（脚本已打印“推送失败”）。
- **`data_dir` 单一来源**：`StorageConfig.output_path` 取代脚本里硬编码的 `DATA_DIR`，
  消除“脚本读错目录 / 与生产 `OUTPUT_DIR` 不一致”的风险；副作用是 services 与
  `config_loader.apply_config` 对输出目录的解析逻辑需保持一致（均以项目根为锚）。

## 正向影响（Positive）

- 推送实现从 3 处收敛为 1 处（`WebhookNotifier.send_markdown`），改一处即全局生效。
- 业务核心可单测：日报/周报逻辑不再与 CLI 耦合，`collect_items` 可只读 `data/*.jsonl`
  验证，DeepSeek 与 `_post` 均可 mock，无真实网络。
- 配置读取统一走 `config_loader` + `get_settings()`，尊重 `SCRAPY_ENV`，不再直读特定
  YAML 文件。
