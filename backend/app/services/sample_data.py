"""Sample policy documents used for local testing.

The generator is deterministic (fixed seed) so demos and screenshots stay
stable. Content is synthetic but structurally realistic: preamble, numbered
sections/ministries, and traceable metadata.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from typing import Any

CN_NUM = "一二三四五六七八九十"

ISSUERS = [
    ("国务院", "国发", "全国"),
    ("财政部", "财预", "全国"),
    ("国家税务总局", "税总", "全国"),
    ("国家发展和改革委员会", "发改", "全国"),
    ("工业和信息化部", "工信部", "全国"),
    ("科学技术部", "国科发", "全国"),
    ("商务部", "商", "全国"),
    ("中国人民银行", "银发", "全国"),
    ("国家市场监督管理总局", "市监", "全国"),
    ("生态环境部", "环", "全国"),
    ("人力资源和社会保障部", "人社部", "全国"),
    ("北京市人民政府", "京政发", "北京市"),
    ("上海市人民政府", "沪府发", "上海市"),
    ("广东省人民政府", "粤府", "广东省"),
    ("浙江省人民政府", "浙政发", "浙江省"),
    ("江苏省人民政府", "苏政发", "江苏省"),
    ("四川省人民政府", "川府发", "四川省"),
    ("深圳市人民政府", "深府", "深圳市"),
]

LAWS = [
    "中华人民共和国预算法",
    "中华人民共和国税收征收管理法",
    "中华人民共和国中小企业促进法",
    "中华人民共和国科学技术进步法",
    "中华人民共和国环境保护法",
    "优化营商环境条例",
    "中华人民共和国对外贸易法",
    "中华人民共和国数据安全法",
]

TAG_POOL = [
    "减税降费",
    "惠企政策",
    "营商环境",
    "高质量发展",
    "民生保障",
    "科技创新",
    "绿色转型",
    "数字化转型",
    "区域协同",
    "对外开放",
    "乡村振兴",
    "稳就业",
]

CATEGORY_SPECS: dict[str, dict[str, Any]] = {
    "税收优惠": {
        "topics": [
            "增值税留抵退税",
            "小微企业税收减免",
            "研发费用加计扣除",
            "企业所得税优惠",
            "个体工商户减税降费",
        ],
        "terms": ["增值税", "留抵退税", "企业所得税", "研发费用加计扣除", "小微企业", "税收减免", "纳税申报", "征管服务"],
        "clauses": [
            "对符合条件的小微企业，按照现行规定减征企业所得税，并进一步简化申报流程。",
            "落实增值税留抵退税政策，将增量留抵税额退还比例提高至规定上限，加快退税办理进度。",
            "企业开展研发活动中实际发生的研发费用，未形成无形资产计入当期损益的，按规定在税前加计扣除。",
            "持续优化纳税服务，推行“自行判别、自行申报、事后监管”的办理方式，降低制度性交易成本。",
            "加强部门数据共享，依托税收大数据精准识别符合条件的纳税人，推动政策直达快享。",
        ],
    },
    "财政补贴": {
        "topics": [
            "中小企业发展专项资金",
            "财政贴息支持",
            "转移支付资金管理",
            "产业扶持资金",
            "稳岗补贴",
        ],
        "terms": ["财政补贴", "专项资金", "转移支付", "贴息", "补助", "预算管理", "绩效评价"],
        "clauses": [
            "中央财政安排专项资金，采取事后补助、贷款贴息等方式支持项目建设。",
            "各地要加快预算执行进度，严禁挤占、挪用专项资金，确保资金安全规范高效使用。",
            "建立全过程预算绩效管理机制，将绩效评价结果作为后续资金安排的重要依据。",
            "对符合条件的项目给予一次性补助，单个项目补助金额原则上不超过项目总投资的百分之三十。",
            "强化资金监管，依托信息化手段实现资金分配、拨付、使用全链条可追溯。",
        ],
    },
    "产业政策": {
        "topics": [
            "专精特新中小企业培育",
            "制造业数字化转型",
            "产业链供应链韧性提升",
            "先进制造业集群建设",
            "中小企业梯度培育",
        ],
        "terms": ["专精特新", "制造业", "产业链", "产业集群", "数字化转型", "中小企业", "梯度培育"],
        "clauses": [
            "健全优质中小企业梯度培育体系，推动创新型中小企业、专精特新中小企业、专精特新“小巨人”企业协同发展。",
            "支持制造业企业加快数字化、网络化、智能化改造，推动规上工业企业数字化转型全覆盖。",
            "围绕重点产业链薄弱环节，实施强链补链延链工程，提升产业链供应链韧性和安全水平。",
            "培育一批具有国际竞争力的先进制造业集群，促进产业集聚和协同创新。",
            "发挥龙头企业带动作用，推动大中小企业融通创新，形成一批典型应用场景。",
        ],
    },
    "科技创新": {
        "topics": [
            "科技成果转化",
            "高新技术企业培育",
            "创新平台建设",
            "关键核心技术攻关",
            "科技人才评价改革",
        ],
        "terms": ["科技成果转化", "研发投入", "创新平台", "高新技术企业", "揭榜挂帅", "科技人才"],
        "clauses": [
            "完善科技成果转化收益分配机制，提高科研人员成果转化收益分享比例。",
            "支持企业牵头组建创新联合体，采取“揭榜挂帅”方式开展关键核心技术攻关。",
            "加大基础研究投入，引导企业和社会力量增加研发投入，提升全社会研发经费投入强度。",
            "加快建设高水平创新平台，推动重点实验室、技术创新中心等平台开放共享。",
            "深化科技人才评价改革，建立以创新价值、能力、贡献为导向的人才评价体系。",
        ],
    },
    "金融监管": {
        "topics": [
            "普惠金融服务",
            "绿色金融体系",
            "融资担保降费",
            "金融风险防控",
            "跨境支付便利化",
        ],
        "terms": ["普惠金融", "绿色金融", "融资担保", "风险防控", "跨境支付", "金融服务"],
        "clauses": [
            "引导金融机构加大对小微企业、乡村振兴等重点领域的信贷投放。",
            "完善政府性融资担保体系，降低小微企业综合融资成本。",
            "健全金融风险监测预警机制，压实地方金融监管责任，守住不发生系统性金融风险底线。",
            "推动绿色金融产品创新，支持符合条件的绿色企业通过资本市场融资。",
            "优化跨境支付结算服务，提升贸易投资便利化水平。",
        ],
    },
    "人才政策": {
        "topics": [
            "高层次人才引进",
            "青年人才安居",
            "职称评审改革",
            "技能人才培育",
            "人才服务保障",
        ],
        "terms": ["高层次人才", "人才引进", "住房补贴", "职称评审", "技能人才", "人才服务"],
        "clauses": [
            "对引进的高层次人才给予住房补贴、子女入学、医疗保障等综合支持。",
            "开辟职称评审绿色通道，对业绩突出的青年人才实行“直通车”评价。",
            "实施技能人才培育工程，深化产教融合、校企合作，扩大高技能人才供给。",
            "建设人才一站式服务平台，实现政策咨询、项目申报、待遇兑现“一网通办”。",
            "鼓励用人单位采取柔性引才方式，支持人才跨区域流动和共享。",
        ],
    },
    "环保节能": {
        "topics": [
            "碳达峰碳中和行动",
            "能耗双控转型",
            "绿色低碳产业发展",
            "排污许可管理",
            "重点行业节能降碳",
        ],
        "terms": ["碳达峰", "碳中和", "能耗双控", "绿色低碳", "排污许可", "节能降碳"],
        "clauses": [
            "稳妥有序推进碳达峰碳中和，加快构建绿色低碳循环发展经济体系。",
            "推动能耗双控逐步转向碳排放双控，强化重点行业节能降碳改造。",
            "严格排污许可管理，推动固定污染源全过程监管。",
            "支持绿色低碳技术研发和推广应用，培育壮大节能环保产业。",
            "建立健全碳排放统计核算体系，提升碳排放数据质量。",
        ],
    },
    "市场监管": {
        "topics": [
            "公平竞争审查",
            "反垄断执法",
            "信用监管体系建设",
            "食品安全监管",
            "价格监督检查",
        ],
        "terms": ["公平竞争", "反垄断", "信用监管", "食品安全", "价格监管", "市场秩序"],
        "clauses": [
            "全面落实公平竞争审查制度，清理废除妨碍统一市场和公平竞争的政策措施。",
            "加强反垄断和反不正当竞争执法，维护公平有序的市场环境。",
            "健全以信用为基础的新型监管机制，推行分级分类监管。",
            "强化食品安全全过程监管，压实企业主体责任和属地管理责任。",
            "加强重要民生商品价格监测，依法查处价格违法行为。",
        ],
    },
    "社会保障": {
        "topics": [
            "养老保险全国统筹",
            "灵活就业人员参保",
            "社会救助体系",
            "失业保险稳岗返还",
            "医疗保障制度改革",
        ],
        "terms": ["养老保险", "医疗保险", "失业保险", "社会救助", "灵活就业", "社会保障"],
        "clauses": [
            "完善基本养老保险全国统筹制度，确保养老金按时足额发放。",
            "支持灵活就业人员参加社会保险，简化参保缴费流程。",
            "健全分层分类的社会救助体系，加强对困难群体的兜底保障。",
            "延续实施失业保险稳岗返还政策，支持企业稳定就业岗位。",
            "深化医疗保障制度改革，推进支付方式改革和药品集中带量采购。",
        ],
    },
    "外贸外资": {
        "topics": [
            "跨境电商综合试验区",
            "自由贸易试验区提升",
            "外资准入负面清单",
            "出口退税便利化",
            "服务贸易创新发展",
        ],
        "terms": ["跨境电商", "自由贸易试验区", "外资准入", "出口退税", "服务贸易", "对外开放"],
        "clauses": [
            "支持跨境电商综合试验区扩容提质，完善海外仓和物流配送体系。",
            "稳步扩大制度型开放，对接国际高标准经贸规则。",
            "全面落实外资准入负面清单，保障外资企业依法平等参与市场竞争。",
            "优化出口退税办理流程，加快退税进度，减轻企业资金压力。",
            "推动服务贸易创新发展，扩大优质服务进口。",
        ],
    },
    "数据要素": {
        "topics": [
            "数据要素市场化配置",
            "公共数据授权运营",
            "数据资产入表",
            "数据安全治理",
            "数字经济创新发展",
        ],
        "terms": ["数据要素", "数据资产", "公共数据", "数据安全", "数字经济", "授权运营"],
        "clauses": [
            "加快数据要素市场化配置改革，建立健全数据产权、流通交易、收益分配制度。",
            "推进公共数据授权运营，在安全合规前提下释放公共数据价值。",
            "规范数据资产会计核算，推动数据资产入表和质押融资试点。",
            "健全数据分类分级保护制度，强化重要数据和个人信息保护。",
            "培育壮大数据产业，打造具有竞争力的数字产业集群。",
        ],
    },
    "乡村振兴": {
        "topics": [
            "乡村产业振兴",
            "粮食安全保障",
            "农村土地流转",
            "惠农补贴政策",
            "和美乡村建设",
        ],
        "terms": ["乡村振兴", "农业农村", "粮食安全", "土地流转", "惠农补贴", "乡村建设"],
        "clauses": [
            "严格落实耕地保护制度，坚决遏制耕地“非农化”、防止“非粮化”。",
            "支持乡村特色产业发展，推动一二三产业融合发展。",
            "规范农村土地经营权流转，保障农民合法权益。",
            "完善惠农补贴政策，提高补贴精准性和资金使用效益。",
            "扎实推进宜居宜业和美乡村建设，持续改善农村人居环境。",
        ],
    },
}

KINDS = ["通知", "意见", "办法", "实施方案", "指导意见", "实施细则", "若干措施"]
VERBS = ["进一步推进", "加快促进", "规范", "优化", "完善", "支持", "加强"]

PREAMBLES = [
    "为深入贯彻落实党中央、国务院决策部署，{verb}{topic}，根据《{law}》有关规定，结合{region}实际，现提出如下意见。",
    "为持续优化营商环境，激发市场主体活力，推动{topic}高质量发展，制定本{kind}。",
    "为贯彻落实国家关于{topic}的部署要求，进一步明确工作重点和政策措施，现就有关事项通知如下。",
    "为加快构建新发展格局，着力推动{topic}，经{issuer}研究同意，现印发给你们，请结合实际认真贯彻落实。",
]

GENERIC_SENTENCES = [
    "坚持问题导向和目标导向相结合，聚焦{topic}的关键环节和薄弱环节，加快形成可复制、可推广的经验做法。",
    "各地区、各有关部门要结合实际制定具体实施方案，明确时间表和路线图，确保各项任务落地见效。",
    "加大财政资金统筹力度，优化支出结构，重点支持{topic}相关项目建设。",
    "建立健全部门协同机制，加强信息共享和业务衔接，形成工作合力。",
    "强化督促检查，将{topic}工作纳入年度绩效考核，对工作推进不力的地区和部门予以通报。",
    "充分发挥市场在资源配置中的决定性作用，更好发挥政府作用，激发各类市场主体活力。",
    "加强政策宣传解读，及时回应社会关切，营造良好社会氛围。",
    "鼓励有条件的地方先行先试，形成一批可复制可推广的制度创新成果。",
    "坚持依法依规、稳妥有序，防范化解各类风险隐患，确保改革措施平稳落地。",
    "完善配套政策体系，加强政策协同联动，提升政策整体效能。",
]

SECTION_TITLES = ["总体要求", "重点任务", "支持政策", "保障措施", "组织实施", "监督管理"]


def _pick_dates(rng: random.Random) -> tuple[date, date]:
    start = date(2018, 1, 1)
    span = (date(2025, 12, 31) - start).days
    issue = start + timedelta(days=rng.randint(0, span))
    effective = issue + timedelta(days=rng.choice([0, 0, 7, 15, 30, 60, 90]))
    return issue, effective


def _build_content(
    rng: random.Random,
    category: str,
    topic: str,
    kind: str,
    issuer: str,
    region: str,
    law: str,
) -> str:
    spec = CATEGORY_SPECS[category]
    preamble = rng.choice(PREAMBLES).format(
        verb=rng.choice(VERBS),
        topic=topic,
        law=law,
        region=region,
        kind=kind,
        issuer=issuer,
    )

    blocks: list[str] = [preamble]

    sections = rng.sample(SECTION_TITLES, k=rng.randint(3, 5))
    for idx, section in enumerate(sections, start=1):
        lines = [f"{CN_NUM[idx]}、{section}"]
        for _ in range(rng.randint(2, 3)):
            lines.append(rng.choice(GENERIC_SENTENCES).format(topic=topic, region=region))
        for clause in rng.sample(spec["clauses"], k=min(2, len(spec["clauses"]))):
            lines.append(clause)
        blocks.append("\n".join(lines))

    # Add a clause-style section to mirror real regulatory documents.
    if rng.random() < 0.65:
        articles = []
        for n in range(1, rng.randint(3, 5)):
            sentence = rng.choice(spec["clauses"])
            articles.append(f"第{n}条 {sentence}")
        blocks.append("\n".join(articles))

    closing = (
        f"本{kind}自发布之日起施行，有效期五年。"
        if kind in {"办法", "实施细则"}
        else "各地区、各有关部门要按照职责分工，抓好贯彻落实，重大情况及时报告。"
    )
    blocks.append(closing)

    return "\n\n".join(blocks)


def generate_documents(count: int = 320, seed: int = 20261020) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    docs: list[dict[str, Any]] = []
    used_numbers: set[str] = set()

    categories = list(CATEGORY_SPECS)

    for i in range(count):
        issuer, prefix, issuer_region = rng.choice(ISSUERS)
        category = rng.choice(categories)
        spec = CATEGORY_SPECS[category]
        topic = rng.choice(spec["topics"])
        kind = rng.choice(KINDS)
        region = issuer_region if rng.random() < 0.75 else rng.choice(
            ["全国", "北京市", "上海市", "广东省", "浙江省", "江苏省", "四川省"]
        )
        law = rng.choice(LAWS)
        issue_date, effective_date = _pick_dates(rng)
        year = issue_date.year

        number = f"{prefix}〔{year}〕{rng.randint(1, 220)}号"
        while number in used_numbers:
            number = f"{prefix}〔{year}〕{rng.randint(1, 400)}号"
        used_numbers.add(number)

        title_pattern = rng.random()
        if title_pattern < 0.5:
            title = f"关于{rng.choice(VERBS)}{topic}的{kind}"
        elif title_pattern < 0.8:
            title = f"{issuer}关于印发《{topic}{rng.choice(['实施方案', '管理办法', '工作指引'])}》的通知"
        else:
            title = f"关于{topic}若干问题的{kind}"

        content = _build_content(
            rng, category, topic, kind, issuer, region, law
        )
        summary = content.split("\n\n")[0][:160]

        tags = rng.sample(TAG_POOL, k=rng.randint(2, 4))
        if category in tags:
            pass
        else:
            tags = [category] + tags[:3]

        digest = hashlib.sha256((title + content).encode("utf-8")).hexdigest()

        docs.append(
            {
                "doc_id": f"doc-{i + 1:06d}",
                "title": title,
                "doc_number": number,
                "issuer": issuer,
                "region": region,
                "category": category,
                "tags": tags,
                "issue_date": issue_date,
                "effective_date": effective_date,
                "content": content,
                "summary": summary,
                "source_url": f"https://example.gov.cn/policy/{year}/{i + 1:06d}.html",
                "file_hash": digest,
                "status": "active",
            }
        )

    return docs
