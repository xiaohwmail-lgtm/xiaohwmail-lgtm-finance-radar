#!/usr/bin/env python3
"""财经信号评分引擎 — 替换 AI 相关性打分，用于财经新闻聚合器."""

from __future__ import annotations

import re
from typing import Any

# ── 财经核心信号词 ──────────────────────────────────────────
FINANCE_CORE_KEYWORDS = [
    # 宏观政策
    "央行", "加息", "降息", "降准", "货币政策", "财政政策", "利率", "汇率",
    "美联储", "fed", "fomc", "ecb", "通胀", "cpi", "ppi", "gdp",
    "关税", "出口", "进口", "贸易", "制裁", "供应链",
    # 股市
    "a股", "港股", "美股", "ipo", "上市", "退市", "停牌", "涨停", "跌停",
    "沪深", "上证", "深证", "创业板", "科创板", "北交所", "恒生", "纳斯达克",
    "标普", "道琼斯", "s&p", "nasdaq", "dow jones",
    "财报", "季报", "年报", "营收", "净利润", "毛利率", "roe", "eps",
    "分红", "回购", "减持", "增持", "并购", "重组",
    # 债市/外汇
    "国债", "企业债", "可转债", "信用债", "收益率", "利差",
    "人民币", "美元", "欧元", "日元", "外汇", "离岸",
    # 大宗/行业
    "大宗商品", "原油", "黄金", "铜", "锂", "稀土", "光伏", "半导体",
    "新能源", "电动车", "ai芯片", "算力芯片", "服务器",
    "房地产", "医药", "消费", "互联网", "平台经济",
    # 公司/事件
    "业绩预告", "业绩快报", "年报披露", "招股书", "问询函", "关注函",
    "监管", "证监会", "银保监", "sec",
    # 英文核心
    "stock", "bond", "equity", "market", "trading", "investor",
    "earnings", "revenue", "dividend", "acquisition", "merger",
    "tariff", "sanction", "export control",
]

# 财经泛信号词（单独出现不够强，但有其他信号词时加分）
FINANCE_BROAD_KEYWORDS = [
    "经济", "金融", "财经", "投资", "资本", "资金", "资产",
    "估值", "市值", "龙头", "蓝筹", "白马",
    "economy", "finance", "investment", "capital",
]

# 噪音词（纯消费/娱乐/体育类 — 过滤掉）
FINANCE_NOISE_KEYWORDS = [
    "娱乐", "明星", "八卦", "足球", "篮球", "彩票",
    "情感", "旅游", "美食", "综艺", "选秀",
]

# 电商噪音词
COMMERCE_NOISE_KEYWORDS = [
    "淘宝", "天猫", "京东", "拼多多", "券后", "热销总榜",
    "促销", "优惠", "补贴", "下单", "首发价",
]

# TopHub 财经频道白名单
TOPHUB_FINANCE_ALLOW_KEYWORDS = [
    "财联社", "华尔街见闻", "第一财经", "证券时报", "雪球",
    "东方财富", "同花顺", "36氪", "ft中文网", "bloomberg",
    "reuters", "cnbc", "yahoo finance",
    "财经", "经济", "金融", "股市", "投资",
]

TOPHUB_FINANCE_BLOCK_KEYWORDS = [
    "热销总榜", "淘宝", "天猫", "京东", "拼多多",
    "抖音", "快手", "微博", "小红书",
    "娱乐", "体育", "游戏", "搞笑",
]

# 英文财经信号正则
FINANCE_EN_SIGNAL_RE = re.compile(
    r"(?i)(?<![a-z0-9])(stock|bond|equity|forex|tariff|sanction|"
    r"acquisition|merger|dividend|earnings|revenue|ipo|"
    r"nasdaq|dow jones|s&p\s*500|fed|fomc|"
    r"inflation|cpi|ppi|gdp|interest rate)(?![a-z0-9])"
)

MEANINGFUL_FINANCE_EN_SIGNAL_RE = re.compile(
    r"(?i)(?<![a-z0-9])(stock|bond|equity|forex|tariff|sanction|"
    r"acquisition|merger|dividend|earnings|revenue|ipo|"
    r"nasdaq|dow jones|s&p\s*500|fed|fomc|"
    r"inflation|cpi|ppi|gdp)(?![a-z0-9])"
)

FINANCE_BROAD_TERMS = {"经济", "金融", "投资", "economy", "finance", "capital"}

FINANCE_RELEVANCE_THRESHOLD = 0.55

# 内置财经信源先验分（内置 RSS 源天然与财经相关，给一定加成）
SOURCE_PRIORS: dict[str, float] = {
    "finance_rss": 0.40,
    "finance_cls": 0.50,       # 财联社 — 天然财经
    "finance_caixin": 0.50,    # 财新 — 天然财经
    "finance_eastmoney": 0.50, # 东方财富 — 天然财经
    "finance_wsj": 0.50,       # 华尔街见闻 — 天然财经
    "finance_ft": 0.45,        # FT中文网
    "finance_bloomberg": 0.50, # Bloomberg
    "finance_reuters": 0.50,   # Reuters
    "opmlrss": 0.10,
    "xapi": 0.10,
}

FINANCE_DEFAULT_SOURCES = {
    "finance_cls", "finance_caixin", "finance_eastmoney",
    "finance_wsj", "finance_bloomberg", "finance_reuters",
}

LABEL_KEYWORDS: list[tuple[str, list[str]]] = [
    ("宏观政策", ["央行", "美联储", "fed", "fomc", "利率", "汇率", "货币政策",
                  "财政政策", "通胀", "cpi", "ppi", "gdp", "加息", "降息", "降准"]),
    ("股市", ["a股", "港股", "美股", "ipo", "上市", "涨停", "跌停", "上证", "深证",
              "创业板", "科创板", "恒生", "纳斯达克", "标普", "沪深", "北交所"]),
    ("公司事件", ["财报", "季报", "年报", "营收", "净利润", "减持", "增持", "并购",
                  "回购", "分红", "重组", "earnings", "revenue", "dividend"]),
    ("大宗商品", ["大宗", "原油", "黄金", "铜", "锂", "稀土", "光伏", "供应链",
                  "commodity", "oil", "gold", "copper"]),
    ("国际贸易", ["关税", "出口", "进口", "贸易", "制裁", "tariff", "sanction",
                  "export", "import"]),
    ("债汇", ["国债", "企业债", "可转债", "收益率", "人民币", "美元", "外汇",
              "bond", "forex", "yield"]),
    ("监管政策", ["证监会", "银保监", "监管", "问询函", "关注函", "合规", "sec"]),
    ("产业经济", ["新能源", "电动车", "芯片", "半导体", "房地产", "医药",
                  "消费", "互联网", "平台经济"]),
]


def contains_any_keyword(haystack: str, keywords: list[str]) -> bool:
    h = haystack.lower()
    return any(k in h for k in keywords)


def matched_keywords(haystack: str, keywords: list[str]) -> list[str]:
    h = haystack.lower()
    return sorted({k for k in keywords if k in h})


def contains_finance_signal(haystack: str) -> bool:
    """检查文本是否包含有意义的财经信号（排除过于宽泛的词）"""
    h = haystack.lower()
    if MEANINGFUL_FINANCE_EN_SIGNAL_RE.search(h):
        return True
    return any(k in h for k in FINANCE_CORE_KEYWORDS if k not in FINANCE_BROAD_TERMS)


def _label_for_text(text: str, has_broad: bool) -> str:
    for label, keywords in LABEL_KEYWORDS:
        if contains_any_keyword(text, keywords):
            return label
    if has_broad:
        return "财经综合"
    return "财经相关"


def _result(
    *,
    is_finance_related: bool,
    score: float,
    label: str,
    reason: str,
    signals: list[str] | None = None,
    noise: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "is_finance_related": bool(is_finance_related),
        "score": round(max(0.0, min(1.0, score)), 2),
        "label": label,
        "reason": reason,
        "signals": signals or [],
        "noise": noise or [],
    }


def score_finance_relevance(record: dict[str, Any]) -> dict[str, Any]:
    """对单条记录打分—财经敏感信号强度"""
    site_id = str(record.get("site_id") or "")
    title = str(record.get("title") or "")
    source = str(record.get("source") or "")
    site_name = str(record.get("site_name") or "")
    url = str(record.get("url") or "")
    text = f"{title} {source} {site_name} {url}".lower()

    finance_signals = matched_keywords(text, FINANCE_CORE_KEYWORDS)
    broad_signals = matched_keywords(text, FINANCE_BROAD_KEYWORDS)
    noise = (
        matched_keywords(text, FINANCE_NOISE_KEYWORDS)
        + matched_keywords(text, COMMERCE_NOISE_KEYWORDS)
    )
    source_prior = SOURCE_PRIORS.get(site_id, 0.0)

    # TopHub 特殊处理
    if site_id == "tophub":
        source_l = source.lower()
        if contains_any_keyword(source_l, TOPHUB_FINANCE_BLOCK_KEYWORDS):
            return _result(
                is_finance_related=False,
                score=0.05,
                label="噪音",
                reason="tophub_blocked_channel",
                signals=finance_signals + broad_signals,
                noise=noise or matched_keywords(source_l, TOPHUB_FINANCE_BLOCK_KEYWORDS),
            )
        if not contains_any_keyword(source_l, TOPHUB_FINANCE_ALLOW_KEYWORDS):
            return _result(
                is_finance_related=False,
                score=0.12,
                label="source_scope_drop",
                reason="tophub_channel_not_in_allowlist",
                signals=finance_signals + broad_signals,
                noise=noise,
            )

    # 内置财经信源默认放行
    if site_id in FINANCE_DEFAULT_SOURCES:
        return _result(
            is_finance_related=True,
            score=max(FINANCE_RELEVANCE_THRESHOLD, 0.72 + source_prior),
            label=_label_for_text(text, bool(broad_signals)),
            reason="trusted_finance_source_default_keep",
            signals=finance_signals or [site_id],
            noise=noise,
        )

    has_finance = contains_finance_signal(text)
    has_broad_finance = (
        contains_any_keyword(text, list(FINANCE_BROAD_TERMS))
        or FINANCE_EN_SIGNAL_RE.search(text) is not None
    )
    has_broad = bool(broad_signals)

    # 完全没有财经信号 → 丢弃
    if not (has_finance or (has_broad_finance and has_broad)):
        return _result(
            is_finance_related=False,
            score=source_prior + (0.28 if has_broad_finance else 0.0) + (0.06 if has_broad else 0.0),
            label="非财经",
            reason="missing_finance_signal",
            signals=finance_signals + broad_signals,
            noise=noise,
        )

    # 有噪音但无强财经信号 → 丢弃
    if contains_any_keyword(text, COMMERCE_NOISE_KEYWORDS) and not has_finance:
        return _result(
            is_finance_related=False,
            score=0.20 + source_prior,
            label="电商噪音",
            reason="commerce_noise_without_finance_signal",
            signals=finance_signals + broad_signals,
            noise=noise,
        )

    if contains_any_keyword(text, FINANCE_NOISE_KEYWORDS) and not has_finance:
        return _result(
            is_finance_related=False,
            score=0.22 + source_prior,
            label="噪音",
            reason="noise_without_finance_signal",
            signals=finance_signals + broad_signals,
            noise=noise,
        )

    # 计算得分
    score = (
        source_prior
        + (0.52 if has_finance else 0.30)
        + min(0.16, 0.04 * len(finance_signals))
        + min(0.10, 0.03 * len(broad_signals))
    )
    if noise:
        score -= min(0.16, 0.04 * len(noise))
    if has_broad_finance and has_broad and not has_finance:
        score = max(score, FINANCE_RELEVANCE_THRESHOLD)
    if has_finance:
        score = max(score, FINANCE_RELEVANCE_THRESHOLD)

    return _result(
        is_finance_related=True,
        score=score,
        label=_label_for_text(text, has_broad),
        reason="matched_finance_signal" if has_finance else "matched_broad_finance_signal",
        signals=finance_signals + broad_signals,
        noise=noise,
    )


def is_finance_related_record(record: dict[str, Any]) -> bool:
    return bool(score_finance_relevance(record)["is_finance_related"])


def add_finance_relevance_fields(record: dict[str, Any]) -> dict[str, Any]:
    relevance = score_finance_relevance(record)
    out = dict(record)
    out["finance_is_related"] = relevance["is_finance_related"]
    out["finance_score"] = relevance["score"]
    out["finance_label"] = relevance["label"]
    out["finance_relevance_reason"] = relevance["reason"]
    out["finance_signals"] = relevance["signals"]
    out["finance_noise"] = relevance["noise"]
    return out
