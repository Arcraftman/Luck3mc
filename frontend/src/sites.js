// Registry mapping a crawler/spider name to its official government website.
// Used by the report + policy views so a user can see *which* official site a
// record / daily report covers.
//
// Add new entries here as new spiders / roots come online. Unknown keys fall
// back to a prettified name so the UI never shows a raw internal id.

// Category labels (the 5 business categories the spiders are grouped by).
export const CATEGORY_LABELS = {
  caishui: '财税政策',
  gaoqi: '高新技术企业政策',
  gongxin: '工信政策',
  yanfa: '研发费用政策',
  kexiao: '科技型中小企业政策',
  gov_general: '综合政府政策',
}

export function categoryLabel(cat) {
  return CATEGORY_LABELS[cat] || cat || '未分类'
}

export const SITE_REGISTRY = {
  // —— 5 大分类 spider 名（也作为报告来源标签）——
  caishui: { label: '财税政策', home: 'https://www.mof.gov.cn' },
  gaoqi: { label: '高新技术企业政策', home: 'http://www.innocom.gov.cn' },
  gongxin: { label: '工信政策', home: 'https://www.miit.gov.cn' },  // 暂为空占位（miit+zjtx 已划归科小）
  yanfa: { label: '研发费用政策', home: 'https://www.chinatax.gov.cn' },
  kexiao: { label: '科技型中小企业政策', home: 'https://zjtx.miit.gov.cn' },
  gov_policy_root: { label: '综合政府政策', home: 'https://www.gov.cn/zhengce/' },

  // —— 财税：财政部各司子站（按 gov_categories.yaml 的 root name 打标）——
  mof_kjs: { label: '财政部·国库司', home: 'https://kjs.mof.gov.cn' },
  mof_jrs_gszl: { label: '财政部·金融司(公示)', home: 'https://jrs.mof.gov.cn' },
  mof_jrs_phjr: { label: '财政部·金融司(普惠)', home: 'https://jrs.mof.gov.cn' },
  mof_szs: { label: '财政部·szs子站', home: 'https://szs.mof.gov.cn' },
  mof_sbs: { label: '财政部·sbs子站', home: 'https://sbs.mof.gov.cn' },
  mof_gss: { label: '财政部·关税司', home: 'https://gss.mof.gov.cn' },
  mof_zwgls: { label: '财政部·综合司', home: 'https://zwgls.mof.gov.cn' },
  mof_jjs_zcfg: { label: '财政部·经济建设司(法规)', home: 'https://jjs.mof.gov.cn' },
  mof_jjs_tzgg: { label: '财政部·经济建设司(公告)', home: 'https://jjs.mof.gov.cn' },
  mof_nys: { label: '财政部·农业农村司', home: 'https://nys.mof.gov.cn' },
  mof_gks: { label: '财政部·国库司(规章)', home: 'https://gks.mof.gov.cn' },
  mof_fgk: { label: '财政部·财政法规库', home: 'https://fgk.mof.gov.cn' },

  // —— 财税：税务核心站 ——
  chinatax_fgk: { label: '税务总局·政策法规库', home: 'https://fgk.chinatax.gov.cn' },
  chinatax_www: { label: '国家税务总局', home: 'https://www.chinatax.gov.cn' },
  chinatax_12366: { label: '12366纳税服务平台', home: 'https://12366.chinatax.gov.cn' },

  // —— 高新 ——
  innocom_www: { label: '高企认定管理工作网', home: 'http://www.innocom.gov.cn' },
  innocom_gqrdw: { label: '高企认定管理工作网·高企认定', home: 'http://www.innocom.gov.cn/gqrdw' },
  gjzwfw_gaoqi: { label: '国家政务服务平台·高企专区', home: 'http://gjzwfw.www.gov.cn' },
  gjzwfw_art: { label: '国家政务服务平台·高企政策', home: 'https://zc.gjzwfw.gov.cn/art' },
  most_www: { label: '科学技术部', home: 'https://www.most.gov.cn' },
  most_xxgk: { label: '科学技术部·信息公开', home: 'https://www.most.gov.cn/xxgk/xinxifenlei/fdzdgknr' },
  most_qykjzc: { label: '科技部·企业科技政策专区', home: 'https://www.most.gov.cn' },

  // —— 工信 / 科小 ——
  miit_www: { label: '工业和信息化部', home: 'https://www.miit.gov.cn' },
  miit_xwfb_zxzc: { label: '工业和信息化部·政策性文件', home: 'https://www.miit.gov.cn/xwfb/zxzc' },
  miit_zjtx: { label: '优质中小企业梯度培育平台', home: 'https://zjtx.miit.gov.cn' },

  // —— 旧 per-site spider（保留兼容）——
  chinatax_news: { label: '国家税务总局', home: 'https://www.chinatax.gov.cn' },
  miit_policy: { label: '工业和信息化部', home: 'https://www.miit.gov.cn' },
  most_news: { label: '国务院/时政', home: 'https://www.gov.cn' },
}

export function siteLabel(spider) {
  return SITE_REGISTRY[spider]?.label || spider.replace(/_/g, ' ')
}

export function siteHome(spider) {
  return SITE_REGISTRY[spider]?.home || ''
}

// "mof_fgk,gov_policy_root" -> [{key,label,home}, ...]
export function parseSpiders(blob = '') {
  return blob
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((key) => ({ key, label: siteLabel(key), home: siteHome(key) }))
}
