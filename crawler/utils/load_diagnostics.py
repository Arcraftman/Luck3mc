"""集中配置自检：启动时检查关键配置，缺失则 warning。

让"配了 DEEPSEEK_API_KEY 但没生效"这类问题一眼可见，而不是跑到 DeepSeek
调用时才莫名其妙报错。
"""

import os

from crawler.utils.log_config import get_logger

logger = get_logger(__name__)

# (环境变量名, 缺失时的提示)
_REQUIRED = [
    ("DEEPSEEK_API_KEY", "生成每日报告必需；缺失时 `scrapy monitor` 的报告环节会失败"),
]
_OPTIONAL = [
    ("DATABASE_URL", "跨运行去重依赖；缺失时每次 monitor 都会把全部条目当新链接重复处理"),
    ("NOTIFY_WEBHOOK_TOKEN", "微信推送必需（pushplus/Server酱 token）；缺失时报告无法推送到微信"),
]


def check_config() -> None:
    """打印配置缺失告警。无返回值，不中断流程。"""
    for name, hint in _REQUIRED:
        if not os.environ.get(name):
            logger.warning("配置缺失 [必需]: %s 未设置 — %s", name, hint)
    for name, hint in _OPTIONAL:
        if not os.environ.get(name):
            logger.warning("配置缺失 [可选]: %s 未设置 — %s", name, hint)
