"""Five category spiders — all config-driven via ``gov_categories.yaml``.

Each subclass only declares its ``name`` and ``category``. The crawling engine
(``PolicyRootBaseSpider``) and the actual root URLs live elsewhere, so there is
**no per-site hard-coding** in this package — to add a site you edit YAML, to
add a category you add a YAML block plus one of these ~4-line classes.

Categories (matching the operator's brief)
------------------------------------------
* ``caishui``  — 财税政策（财政部各司 + 税务总局政策法规库 + 12366）
* ``gaoqi``    — 高新技术企业政策（高企认定网 + 国家政务服务平台 + 科技部）
* ``gongxin``  — 工信政策（工信部 + 优质中小企业梯度培育平台）
* ``yanfa``    — 研发费用政策（税务总局政策法规库 + 科技部企业科技政策专区）
* ``kexiao``   — 科技型中小企业政策（优质中小企业梯度培育平台）
"""

from crawler.spiders.policy_root_base import PolicyRootBaseSpider


class CaishuiSpider(PolicyRootBaseSpider):
    """财税政策：财政部各司子站、税务总局政策法规库、12366 纳税服务平台。"""
    name = "caishui"
    category = "caishui"


class GaoqiSpider(PolicyRootBaseSpider):
    """高新技术企业政策：高企认定管理工作网、国家政务服务平台高企专区、科技部。"""
    name = "gaoqi"
    category = "gaoqi"


class GongxinSpider(PolicyRootBaseSpider):
    """工信政策：工业和信息化部、优质中小企业梯度培育平台。"""
    name = "gongxin"
    category = "gongxin"


class YanfaSpider(PolicyRootBaseSpider):
    """研发费用政策：税务总局政策法规库、科技部企业科技政策专区。"""
    name = "yanfa"
    category = "yanfa"


class KexiaoSpider(PolicyRootBaseSpider):
    """科技型中小企业政策：优质中小企业梯度培育平台。"""
    name = "kexiao"
    category = "kexiao"
