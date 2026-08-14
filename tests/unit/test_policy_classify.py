"""Unit tests for the policy vs. news classifier."""

from crawler.utils.policy_classify import is_policy_document, is_news


def test_policy_detail_accepted():
    url = "https://www.gov.cn/zhengce/2026-08/content_7072633.htm"
    title = "反洗钱特别预防措施管理办法"
    text = "现印发《反洗钱特别预防措施管理办法》，自2026年2月16日起施行。" + "条款内容" * 50
    assert is_policy_document(url, title, text) is True


def test_news_page_rejected_by_title():
    url = "https://www.gov.cn/xinwen/2026-08/13/content_1.htm"
    title = "国务院召开常务会议 研究部署稳增长工作"
    text = "新华社北京8月13日电 记者从国务院办公厅获悉" + "报道内容" * 50
    assert is_policy_document(url, title, text) is False
    assert is_news(url, title) is True


def test_news_page_rejected_by_path():
    url = "https://www.shanghai.gov.cn/news/2026-08/13/content_2.htm"
    title = "本市举办科技创新主题活动"
    text = "活动于昨日举行，现场气氛热烈。" + "活动详情" * 50
    assert is_policy_document(url, title, text) is False


def test_listing_page_rejected_short_text():
    # A listing page titled "政策文件" but with almost no prose body.
    url = "https://www.gov.cn/zhengce/"
    title = "政策文件"
    text = "政策文件列表"
    assert is_policy_document(url, title, text) is False


def test_generic_policy_title_needs_corroboration():
    # Title "政策" alone without URL fragment / body marker -> not a document.
    url = "https://www.example.com/somepage"
    title = "关于某项政策的解读"
    text = "本文对该政策进行解读。" * 5  # < 200 chars, and no body marker
    assert is_policy_document(url, title, text) is False


def test_government_doc_by_body_marker():
    url = "https://www.shanghai.gov.cn/xxgk/2026/08/content_9.htm"
    title = "上海市人民政府关于印发某办法的通知"
    text = "现将《某办法》印发给你们，请认真贯彻执行。" + "正文内容" * 100
    assert is_policy_document(url, title, text) is True


def test_shanghai_policy_accepted():
    url = "https://www.shanghai.gov.cn/nw12344/2026/08/13/content_x.htm"
    title = "上海市关于促进集成电路产业发展的若干措施"
    text = "为加快产业发展，现提出如下措施：" + "措施内容" * 50
    assert is_policy_document(url, title, text) is True


def test_mof_detail_accepted():
    # 财政部子站“政策发布”详情页：/zhengcefabu/ 路径 + .htm 后缀 + 文档型标题。
    url = "https://jrs.mof.gov.cn/zhengcefabu/gszl/202607/t20260731_3994642.htm"
    title = "财政部 金融监管司关于某事项的公告"
    text = "现将《某办法》印发给你们，请认真贯彻执行。" + "正文内容" * 50
    assert is_policy_document(url, title, text) is True


def test_mof_listing_rejected():
    # 同一栏目首页（无文件后缀、标题泛化）——必须是列表页，不能当政策存。
    url = "https://jrs.mof.gov.cn/zhengcefabu/gszl/"
    title = "政策发布"
    text = "政策发布列表 公告 通知 办法" * 10
    assert is_policy_document(url, title, text) is False


def test_mof_gss_detail_accepted():
    url = "https://gss.mof.gov.cn/gzdt/zhengcefabu/202604/t20260421_3988007.htm"
    title = "关税司关于印发某规定的通知"
    text = "现印发《某规定》，自公布之日起施行。" + "条款" * 50
    assert is_policy_document(url, title, text) is True


def test_detail_by_extension_and_body_marker():
    # 即使标题没有文档型关键词，只要有详情页后缀且正文带“印发”标记，仍保留。
    url = "https://szs.mof.gov.cn/zhengcefabu/202607/t20260724_3994261.htm"
    title = "关于某工作的说明"
    text = "现将有关要求印发给你们，请遵照执行。" + "正文" * 50
    assert is_policy_document(url, title, text) is True


# --- 新增：财政部其他司局子站栏目（用户提供的 25 个 URL 归纳）---
def test_mof_kjs_detail_accepted():
    url = "https://kjs.mof.gov.cn/zhengcefabu/202608/t20260805_3994927.htm"
    title = "国库司关于印发某管理办法的通知"
    text = "现将《某管理办法》印发给你们，请认真贯彻执行。" + "条款" * 50
    assert is_policy_document(url, title, text) is True


def test_mof_jjs_zhengcefagui_accepted():
    url = "https://jjs.mof.gov.cn/zhengcefagui/202606/t20260604_3991164.htm"
    title = "经济建设司关于某政策的实施意见"
    text = "经研究决定，现提出如下实施意见：" + "内容" * 50
    assert is_policy_document(url, title, text) is True


def test_mof_gks_guihangzhidu_accepted():
    url = "https://gks.mof.gov.cn/guizhangzhidu/202601/t20260121_3982332.htm"
    title = "国库司规章制度管理办法"
    text = "第一条 为规范相关工作，制定本办法。" + "条款" * 50
    assert is_policy_document(url, title, text) is True


def test_mof_nys_mixedcase_path_accepted():
    # nys 子站路径为混合大小写 czpjZhengCeFaBu_2_2，匹配需大小写不敏感。
    url = "https://nys.mof.gov.cn/czpjZhengCeFaBu_2_2/202603/t20260302_3984471.htm"
    title = "农业农村司关于某工作的通知"
    text = "现将有关事项通知如下，请遵照执行。" + "正文" * 50
    assert is_policy_document(url, title, text) is True


def test_mof_zwgls_zcgz_accepted():
    url = "https://zwgls.mof.gov.cn/zcgz/202604/t20260424_3988356.htm"
    title = "综合司关于某工作的指导意见"
    text = "现印发《指导意见》，自公布之日起施行。" + "条款" * 50
    assert is_policy_document(url, title, text) is True


def test_chinatax_fgk_zcfgk_accepted():
    url = "https://fgk.chinatax.gov.cn/zcfgk/2026-08/content_123.htm"
    title = "国家税务总局关于某政策的公告"
    text = "现予以公告，自2026年9月1日起施行。" + "条款" * 50
    assert is_policy_document(url, title, text) is True


def test_12366_sscx_accepted():
    url = "https://12366.chinatax.gov.cn/sscx/2026-08/content_456.htm"
    title = "关于研发费用加计扣除政策的通知"
    text = "现将研发费用加计扣除有关事项通知如下。" + "正文" * 50
    assert is_policy_document(url, title, text) is True


def test_mof_jjs_tongzhigonggao_accepted():
    url = "https://jjs.mof.gov.cn/tongzhigonggao/202604/t20260409_3987253.htm"
    title = "经济建设司关于某事项的通告"
    text = "现予公告，请各相关单位知悉。" + "正文" * 50
    assert is_policy_document(url, title, text) is True


def test_most_qykjzc_accepted():
    url = "https://www.most.gov.cn/ztzl/qykjzc/2026-08/content_789.htm"
    title = "科技部企业科技政策专区某措施"
    text = "为支持企业科技创新，现提出如下措施：" + "内容" * 50
    assert is_policy_document(url, title, text) is True
