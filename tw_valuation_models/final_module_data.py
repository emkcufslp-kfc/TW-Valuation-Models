from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Iterable

import requests
import urllib3

from .config import WorkspacePaths
from .csv_utils import read_csv_rows, write_csv_rows

PILOT_TICKERS = ("2330", "2881", "2603", "2412")

_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TWValuationModels/1.0; +https://openai.com)"
}

_CATEGORY_STALE_DAYS = {
    "institutional": 30,
    "news": 14,
    "public": 14,
}

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_INSTITUTION_SCORE = {
    "strong_buy": 1.0,
    "buy": 0.7,
    "outperform": 0.4,
    "hold": 0.0,
    "underperform": -0.5,
    "sell": -1.0,
}

_PUBLIC_STANCE_SCORE = {
    "buy": 1.0,
    "accumulate": 0.7,
    "hold": 0.0,
    "reduce": -0.5,
    "avoid": -1.0,
}

_NEWS_SENTIMENT_SCORE = {
    "bullish": 1.0,
    "neutral": 0.0,
    "bearish": -1.0,
}


FINAL_MODULE_SOURCE_CATALOG: list[dict[str, object]] = [
    {
        "source_id": "2330_factset_consensus_2026_04_18",
        "ticker": "2330",
        "category": "institutional",
        "source_name": "鉅亨網 FactSet",
        "institution_name": "FactSet Consensus",
        "report_date": "2026-04-18",
        "publish_date": "2026-04-18",
        "rating_raw": "Consensus positive",
        "rating_normalized": "buy",
        "target_price": 2387.5,
        "target_price_low": 0.0,
        "target_price_high": 0.0,
        "eps_fy1": 93.01,
        "eps_fy2": 0.0,
        "title": "FactSet 最新調查：台積電 EPS 預估上修至 93.01 元，目標價 2387.5 元",
        "summary": "市場共識持續上修台積電 EPS 與目標價，主軸仍是 AI 需求與先進製程動能。",
        "thesis_summary": "AI 需求與高階製程動能延續，分析師共識維持偏多。",
        "url": "https://news.cnyes.com/news/id/6422450",
    },
    {
        "source_id": "2330_udn_target_2026_02_17",
        "ticker": "2330",
        "category": "institutional",
        "source_name": "經濟日報",
        "institution_name": "外資券商彙整",
        "report_date": "2026-02-17",
        "publish_date": "2026-02-17",
        "rating_raw": "買進",
        "rating_normalized": "buy",
        "target_price": 2600.0,
        "target_price_low": 2000.0,
        "target_price_high": 2600.0,
        "eps_fy1": 0.0,
        "eps_fy2": 0.0,
        "title": "外資升台積電目標價 最高 2600",
        "summary": "法說會後多家外資券商上修台積電目標價，反映先進製程與 AI 需求能見度。",
        "thesis_summary": "法說會後市場願意給台積電更高的 AI 成長溢價。",
        "url": "https://money.udn.com/money/amp/story/5607/9270865",
    },
    {
        "source_id": "2330_ftv_revenue_2026_05_08",
        "ticker": "2330",
        "category": "news",
        "source_name": "Yahoo 股市",
        "publish_date": "2026-05-08",
        "title": "台積電前4月合併營收1.54兆元，年增29.9%",
        "summary": "4 月營收年增 17.5%，前四月累計年增近 30%，市場持續聚焦 AI 與高階製程需求。",
        "sentiment": "bullish",
        "theme": "demand",
        "is_company_specific": True,
        "url": "https://tw.stock.yahoo.com/news/%E5%8F%B0%E7%A9%8D%E9%9B%BB%E5%89%8D4%E6%9C%88%E5%90%88%E4%BD%B5%E7%87%9F%E6%94%B61-54%E5%85%86%E5%85%83-%E5%B9%B4%E5%A2%9E29-9-062000203.html",
    },
    {
        "source_id": "2330_uanalyze_revenue_2026_05_08",
        "ticker": "2330",
        "category": "news",
        "source_name": "優分析",
        "publish_date": "2026-05-08",
        "title": "台積電 4 月營收達成率約 33%",
        "summary": "4 月營收對第二季財測達成率約三分之一，新聞解讀仍偏向全年營運續強。",
        "sentiment": "bullish",
        "theme": "earnings",
        "is_company_specific": True,
        "url": "https://uanalyze.com.tw/articles/2092451454",
    },
    {
        "source_id": "2330_vocus_earnings_note_2026_04_16",
        "ticker": "2330",
        "category": "public",
        "source_name": "Vocus",
        "channel_type": "blog",
        "author_name": "法說會筆記作者",
        "publish_date": "2026-04-16",
        "title": "台積電法說會：AI 需求爆發，全年營收成長上看 30%+",
        "summary": "偏多解讀法說會，強調 AI 與 HPC 需求帶來的長期成長與毛利率優勢。",
        "sentiment": "bullish",
        "stance": "hold",
        "evidence_strength": "medium",
        "url": "https://vocus.cc/article/69df7731fd89780001aaaf7b",
    },
    {
        "source_id": "2330_ptt_live_2026_04_16",
        "ticker": "2330",
        "category": "public",
        "source_name": "PTT Web",
        "channel_type": "forum",
        "author_name": "Stock 版討論",
        "publish_date": "2026-04-16",
        "title": "台積電法說會 LIVE 討論串",
        "summary": "散戶討論聚焦法說會對第二季營收、全年成長與資本支出的影響，情緒偏樂觀但也擔心利多出盡。",
        "sentiment": "neutral",
        "stance": "hold",
        "evidence_strength": "low",
        "url": "https://www.pttweb.cc/bbs/Stock/M.1776318029.A.62E",
    },
    {
        "source_id": "2881_factset_consensus_2026_05_09",
        "ticker": "2881",
        "category": "institutional",
        "source_name": "鉅亨網 FactSet",
        "institution_name": "FactSet Consensus",
        "report_date": "2026-05-09",
        "publish_date": "2026-05-09",
        "rating_raw": "Consensus positive",
        "rating_normalized": "buy",
        "target_price": 97.0,
        "target_price_low": 0.0,
        "target_price_high": 0.0,
        "eps_fy1": 8.35,
        "eps_fy2": 0.0,
        "title": "FactSet 最新調查：富邦金 EPS 預估上修至 8.35 元，目標價 97 元",
        "summary": "分析師對富邦金 EPS 與目標價略為上修，但整體仍屬合理偏多區間。",
        "thesis_summary": "金控獲利與配息能力具支撐，但並非極端低估。",
        "url": "https://news.cnyes.com/news/id/6444627",
    },
    {
        "source_id": "2881_fintel_target_2026_05_05",
        "ticker": "2881",
        "category": "institutional",
        "source_name": "Yahoo 股市",
        "institution_name": "Yahoo 估價",
        "report_date": "2026-05-05",
        "publish_date": "2026-05-05",
        "rating_raw": "Valuation range snapshot",
        "rating_normalized": "hold",
        "target_price": 0.0,
        "target_price_low": 0.0,
        "target_price_high": 0.0,
        "eps_fy1": 0.0,
        "eps_fy2": 0.0,
        "title": "富邦金 Yahoo 估價頁",
        "summary": "Yahoo 估價頁提供富邦金以 PE、PB 與現金股利角度的合理區間，可作為市場評價快照補充。",
        "thesis_summary": "以公開估價區間作為市場合理價格帶輔助，不直接代表單一券商明確買賣建議。",
        "url": "https://tw.stock.yahoo.com/quote/2881.TW/price-valuations",
    },
    {
        "source_id": "2881_cnyes_revenue_2026_05_14",
        "ticker": "2881",
        "category": "news",
        "source_name": "鉅亨網",
        "publish_date": "2026-05-14",
        "title": "富邦金 4 月營收 533.56 億元年增 219.79%",
        "summary": "4 月營收強勁反彈，新聞偏向正面解讀獲利與子公司表現。",
        "sentiment": "bullish",
        "theme": "earnings",
        "is_company_specific": True,
        "url": "https://news.cnyes.com/news/id/6458960",
    },
    {
        "source_id": "2881_yahoo_dividend_2026_05_01",
        "ticker": "2881",
        "category": "news",
        "source_name": "Yahoo 股市",
        "publish_date": "2026-05-01",
        "title": "富邦金配息 4.25 元、殖利率約 4.72%",
        "summary": "市場聚焦富邦金維持 4.25 元現金股利，凸顯配息題材與存股吸引力。",
        "sentiment": "bullish",
        "theme": "dividend",
        "is_company_specific": True,
        "url": "https://tw.stock.yahoo.com/news/40%E8%90%AC%E8%82%A1%E6%B0%91%E7%88%BD%E9%A0%98%E9%8C%A2-%E5%AF%8C%E9%82%A6%E9%87%91%E9%85%8D%E6%81%AF4-25%E5%85%83-%E8%B1%AA%E6%92%92595%E5%84%84-%E6%AE%96%E5%88%A9%E7%8E%87%E9%81%944-044000967.html",
    },
    {
        "source_id": "2881_businesstoday_dividend_2026_05_05",
        "ticker": "2881",
        "category": "public",
        "source_name": "今周刊",
        "channel_type": "retail_media",
        "author_name": "今周刊編輯部",
        "publish_date": "2026-05-05",
        "title": "富邦金配息完整解析",
        "summary": "以散戶與存股族角度解析股息、殖利率與除息規劃，整體情緒偏多。",
        "sentiment": "bullish",
        "stance": "accumulate",
        "evidence_strength": "medium",
        "url": "https://www.businesstoday.com.tw/article/category/183017/post/202605050012/",
    },
    {
        "source_id": "2881_cmoney_forum_2026_01_09",
        "ticker": "2881",
        "category": "public",
        "source_name": "Senya",
        "channel_type": "blog",
        "author_name": "Senya 分析頁",
        "publish_date": "2026-01-09",
        "title": "富邦金每日分析報告",
        "summary": "偏公眾與零售投資者閱讀的分析頁，聚焦除息後反應、價格表現與中期趨勢。",
        "sentiment": "neutral",
        "stance": "hold",
        "evidence_strength": "medium",
        "url": "https://report.senya.com.tw/report/2026-01-09/2881",
    },
    {
        "source_id": "2603_factset_consensus_2026_04_27",
        "ticker": "2603",
        "category": "institutional",
        "source_name": "鉅亨網 FactSet",
        "institution_name": "FactSet Consensus",
        "report_date": "2026-04-27",
        "publish_date": "2026-04-27",
        "rating_raw": "Consensus mixed",
        "rating_normalized": "hold",
        "target_price": 226.0,
        "target_price_low": 0.0,
        "target_price_high": 0.0,
        "eps_fy1": 22.87,
        "eps_fy2": 0.0,
        "title": "FactSet 最新調查：長榮 EPS 預估下修至 22.87 元，目標價 226 元",
        "summary": "共識目標價仍高於現價，但已反映週期下修與供需風險。",
        "thesis_summary": "高股息與現金流有支撐，但市場對長期獲利中樞較保守。",
        "url": "https://news.cnyes.com/news/id/6433108",
    },
    {
        "source_id": "2603_factset_consensus_2026_03_31",
        "ticker": "2603",
        "category": "institutional",
        "source_name": "鉅亨網 FactSet",
        "institution_name": "FactSet Consensus",
        "report_date": "2026-03-31",
        "publish_date": "2026-03-31",
        "rating_raw": "Consensus positive",
        "rating_normalized": "buy",
        "target_price": 238.5,
        "target_price_low": 0.0,
        "target_price_high": 0.0,
        "eps_fy1": 22.39,
        "eps_fy2": 0.0,
        "title": "FactSet 最新調查：長榮 EPS 預估上修至 22.39 元，目標價 238.5 元",
        "summary": "前一輪共識目標價更高，顯示市場對景氣與運價看法曾更樂觀。",
        "thesis_summary": "景氣回升時市場願意上修長榮目標價，但幅度受供給風險約束。",
        "url": "https://news.cnyes.com/news/id/6410002",
    },
    {
        "source_id": "2603_cnyes_revenue_2026_05_08",
        "ticker": "2603",
        "category": "news",
        "source_name": "鉅亨網",
        "publish_date": "2026-05-08",
        "title": "長榮 4 月營收 313.59 億元年增 4.51%",
        "summary": "4 月營收雙成長，短線利多主要來自運價與旺季提前拉貨預期。",
        "sentiment": "bullish",
        "theme": "earnings",
        "is_company_specific": True,
        "url": "https://news.cnyes.com/news/id/6450228",
    },
    {
        "source_id": "2603_yahoo_announcement_2026_04_21",
        "ticker": "2603",
        "category": "news",
        "source_name": "Yahoo 股市",
        "publish_date": "2026-04-21",
        "title": "長榮受邀參加法人說明會",
        "summary": "法人說明會安排強化市場對第二、三季航運需求與運價的關注。",
        "sentiment": "neutral",
        "theme": "industry_cycle",
        "is_company_specific": True,
        "url": "https://tw.stock.yahoo.com/quote/2603.TW/",
    },
    {
        "source_id": "2603_cmnews_revenue_2026_05_12",
        "ticker": "2603",
        "category": "public",
        "source_name": "CMNews",
        "channel_type": "retail_media",
        "author_name": "CMoney 團隊",
        "publish_date": "2026-05-12",
        "title": "長榮 4 月營收表現亮眼、創近 3 個月新高",
        "summary": "偏散戶角度強調營收雙成長與高股息吸引力，情緒偏多。",
        "sentiment": "bullish",
        "stance": "accumulate",
        "evidence_strength": "medium",
        "url": "https://cmnews.com.tw/article/cmoneyaicurator-e0dfac51-4d10-11f1-af13-841b21cb0e17",
    },
    {
        "source_id": "2603_poorstock_earningcall_2026_04_24",
        "ticker": "2603",
        "category": "public",
        "source_name": "散戶鬥嘴鼓",
        "channel_type": "blog",
        "author_name": "AI 法說整理",
        "publish_date": "2026-04-24",
        "title": "長榮法說會 AI 重點整理",
        "summary": "公眾視角偏正向解讀法說會內容，但更容易放大運價與配息題材。",
        "sentiment": "bullish",
        "stance": "hold",
        "evidence_strength": "low",
        "url": "https://poorstock.com/earningcall/2603",
    },
    {
        "source_id": "2412_fintel_target_2026_04_28",
        "ticker": "2412",
        "category": "institutional",
        "source_name": "Yahoo 股市",
        "institution_name": "Yahoo 估價",
        "report_date": "2026-04-28",
        "publish_date": "2026-04-28",
        "rating_raw": "Valuation range snapshot",
        "rating_normalized": "hold",
        "target_price": 0.0,
        "target_price_low": 0.0,
        "target_price_high": 0.0,
        "eps_fy1": 0.0,
        "eps_fy2": 0.0,
        "title": "中華電 Yahoo 估價頁",
        "summary": "Yahoo 估價頁提供中華電以 PE、PB 與現金股利角度的合理區間，可作為防守型估值快照補充。",
        "thesis_summary": "收益型標的的合理價區主要由配息與估值區間支撐，而非高成長重估。",
        "url": "https://tw.stock.yahoo.com/quote/2412.TW/price-valuations",
    },
    {
        "source_id": "2412_broker_preview_2026_05_09",
        "ticker": "2412",
        "category": "institutional",
        "source_name": "法人彙整頁",
        "institution_name": "市場共識彙整",
        "report_date": "2026-05-09",
        "publish_date": "2026-05-09",
        "rating_raw": "Neutral",
        "rating_normalized": "hold",
        "target_price": 138.0,
        "target_price_low": 133.79,
        "target_price_high": 160.65,
        "eps_fy1": 5.02,
        "eps_fy2": 0.0,
        "title": "中華電防守型評價共識區間",
        "summary": "市場對中華電多以收益與穩定性定價，普遍認為接近合理。",
        "thesis_summary": "配息與防守性支撐評價，但成長有限壓抑上行空間。",
        "url": "https://tw.stock.yahoo.com/quote/2412.TW/price-valuations",
    },
    {
        "source_id": "2412_cnyes_guidance_2026_01_23",
        "ticker": "2412",
        "category": "news",
        "source_name": "鉅亨網",
        "publish_date": "2026-01-23",
        "title": "中華電公布 2026 年財測 EPS 4.82 至 5.02 元",
        "summary": "公司財測強調穩定成長與 AI、ICT 新業務布局，新聞解讀偏中性偏多。",
        "sentiment": "bullish",
        "theme": "guidance",
        "is_company_specific": True,
        "url": "https://news.cnyes.com/news/id/6320740",
    },
    {
        "source_id": "2412_yahoo_q1_2026_05_07",
        "ticker": "2412",
        "category": "news",
        "source_name": "Yahoo 股市",
        "publish_date": "2026-05-07",
        "title": "中華電第 1 季營收創 2012 年以來同期新高",
        "summary": "Q1 營收與 EPS 優於財測高標，市場進一步強化其防守與穩定獲利形象。",
        "sentiment": "bullish",
        "theme": "earnings",
        "is_company_specific": True,
        "url": "https://tw.stock.yahoo.com/quote/2412.TW",
    },
    {
        "source_id": "2412_senya_analysis_2026_01_23",
        "ticker": "2412",
        "category": "public",
        "source_name": "Senya / CMoney",
        "channel_type": "retail_media",
        "author_name": "分析頁作者",
        "publish_date": "2026-01-23",
        "title": "中華電信公布 2026 年財測 EPS 4.82 至 5.02 元",
        "summary": "偏散戶與策略解讀視角，強調財測高位區間對收益穩健信心的加分。",
        "sentiment": "bullish",
        "stance": "hold",
        "evidence_strength": "medium",
        "url": "https://insight.senya.com.tw/analysis/82bd5c21",
    },
    {
        "source_id": "2412_vocus_earnings_note_2026_04_16",
        "ticker": "2412",
        "category": "public",
        "source_name": "Vocus",
        "channel_type": "blog",
        "author_name": "法說會筆記作者",
        "publish_date": "2026-04-16",
        "title": "中華電信法說會：EPS 創高、配息 5.2 元，AI 與衛星布局啟動",
        "summary": "偏正向的公開評論，主打穩定現金流、超額配息與新業務布局。",
        "sentiment": "bullish",
        "stance": "accumulate",
        "evidence_strength": "medium",
        "url": "https://vocus.cc/article/69e60f77fd89780001ce9c4b",
    },
]


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _today_iso() -> str:
    return datetime.now().date().isoformat()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")
    return slug or "source"


def _normalize_tickers(tickers: Iterable[str] | None) -> set[str]:
    if not tickers:
        return set(PILOT_TICKERS)
    return {str(item).strip() for item in tickers if str(item).strip()}


def _iter_catalog_entries(tickers: Iterable[str] | None = None) -> list[dict[str, object]]:
    allowed = _normalize_tickers(tickers)
    return [entry for entry in FINAL_MODULE_SOURCE_CATALOG if str(entry["ticker"]) in allowed]


def _entry_raw_path(paths: WorkspacePaths, entry: dict[str, object]) -> Path:
    publish_date = str(entry.get("publish_date", "undated")).replace("-", "")
    return (
        paths.final_module_raw_root
        / str(entry["ticker"])
        / str(entry["category"])
        / f"{publish_date}_{_slugify(str(entry['source_id']))}.html"
    )


def _entry_manifest_path(paths: WorkspacePaths, entry: dict[str, object]) -> Path:
    return (
        paths.final_module_manifest_root
        / str(entry["ticker"])
        / f"{_slugify(str(entry['source_id']))}.json"
    )


def _is_stale(entry: dict[str, object], as_of_date: str) -> bool:
    category = str(entry["category"])
    max_age = _CATEGORY_STALE_DAYS[category]
    publish_date = datetime.fromisoformat(str(entry["publish_date"])).date()
    anchor = datetime.fromisoformat(as_of_date).date()
    return (anchor - publish_date).days > max_age


def fetch_final_module_sources(
    paths: WorkspacePaths,
    tickers: Iterable[str] | None = None,
    overwrite: bool = False,
) -> dict[str, object]:
    entries = _iter_catalog_entries(tickers)
    generated_at = _utc_now_iso()
    as_of_date = _today_iso()
    results: list[dict[str, object]] = []
    downloaded_count = 0
    cached_count = 0
    error_count = 0

    for entry in entries:
        raw_path = _entry_raw_path(paths, entry)
        manifest_path = _entry_manifest_path(paths, entry)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        status = "cached"
        byte_count = 0
        error_message = ""
        content_type = ""

        if raw_path.exists() and not overwrite:
            cached_count += 1
            byte_count = raw_path.stat().st_size
        else:
            try:
                response, content_type, used_insecure_ssl = _download_source(
                    str(entry["url"])
                )
                if used_insecure_ssl:
                    content_type = f"{content_type}; insecure_ssl_retry=true" if content_type else "insecure_ssl_retry=true"
                response.raise_for_status()
                raw_path.write_bytes(response.content)
                status = "downloaded"
                downloaded_count += 1
                byte_count = len(response.content)
            except Exception as exc:  # pragma: no cover - exercised via tests with fake transport
                status = "error"
                error_count += 1
                error_message = str(exc)

        record = {
            "source_id": entry["source_id"],
            "ticker": entry["ticker"],
            "category": entry["category"],
            "url": entry["url"],
            "title": entry["title"],
            "publish_date": entry["publish_date"],
            "raw_file": str(raw_path),
            "manifest_file": str(manifest_path),
            "status": status,
            "byte_count": byte_count,
            "content_type": content_type,
            "error": error_message,
            "as_of_date": as_of_date,
            "downloaded_at": generated_at,
        }
        manifest_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        results.append(record)

    summary = {
        "generated_at": generated_at,
        "as_of_date": as_of_date,
        "shared_data_root": str(paths.shared_data_root),
        "final_module_shared_root": str(paths.final_module_shared_root),
        "raw_root": str(paths.final_module_raw_root),
        "manifest_root": str(paths.final_module_manifest_root),
        "tickers": sorted(_normalize_tickers(tickers)),
        "entry_count": len(entries),
        "downloaded_count": downloaded_count,
        "cached_count": cached_count,
        "error_count": error_count,
        "results": results,
    }
    summary_path = paths.final_module_shared_root / "latest_fetch_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def _download_source(url: str) -> tuple[requests.Response, str, bool]:
    try:
        response = requests.get(url, headers=_HTTP_HEADERS, timeout=30)
        return response, response.headers.get("content-type", ""), False
    except requests.exceptions.SSLError:
        response = requests.get(url, headers=_HTTP_HEADERS, timeout=30, verify=False)
        return response, response.headers.get("content-type", ""), True


def _extract_html_title(content: bytes) -> str:
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        return ""
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _build_live_source_entries(ticker: str) -> list[dict[str, object]]:
    publish_date = _today_iso()
    ticker = str(ticker).strip()
    tw_suffix = f"{ticker}.TW"
    return [
        {
            "source_id": f"{ticker}_yahoo_price_valuations_live",
            "ticker": ticker,
            "category": "institutional",
            "source_name": "Yahoo 估值頁",
            "institution_name": "Yahoo Valuation Snapshot",
            "report_date": publish_date,
            "publish_date": publish_date,
            "rating_raw": "Live snapshot",
            "rating_normalized": "hold",
            "target_price": 0.0,
            "target_price_low": 0.0,
            "target_price_high": 0.0,
            "eps_fy1": 0.0,
            "eps_fy2": 0.0,
            "title": f"{ticker} Yahoo 估值頁",
            "summary": "最新估值頁已重新抓取，提供最新市場估值頁面作為輔助脈絡。",
            "thesis_summary": "最新估值頁已更新，應搭配內部模型與獨立 AI 一起判讀。",
            "url": f"https://tw.stock.yahoo.com/quote/{tw_suffix}/price-valuations",
        },
        {
            "source_id": f"{ticker}_yahoo_news_live",
            "ticker": ticker,
            "category": "news",
            "source_name": "Yahoo 新聞頁",
            "publish_date": publish_date,
            "title": f"{ticker} Yahoo 新聞頁",
            "summary": "最新新聞頁已重新抓取，提供當前公開市場新聞脈絡。",
            "sentiment": "neutral",
            "theme": "valuation",
            "is_company_specific": True,
            "url": f"https://tw.stock.yahoo.com/quote/{tw_suffix}/news",
        },
        {
            "source_id": f"{ticker}_ptt_search_live",
            "ticker": ticker,
            "category": "public",
            "source_name": "PTT Web 搜尋",
            "channel_type": "forum",
            "author_name": "PTT Web",
            "publish_date": publish_date,
            "title": f"{ticker} PTT Web 搜尋",
            "summary": "最新公眾討論搜尋頁已重新抓取，提供散戶討論脈絡參考。",
            "sentiment": "neutral",
            "stance": "hold",
            "evidence_strength": "low",
            "url": f"https://www.pttweb.cc/search?q={ticker}",
        },
    ]


def _merge_rows_for_tickers(
    path: Path,
    fieldnames: list[str],
    new_rows: list[dict[str, object]],
    tickers: set[str],
) -> int:
    existing_rows: list[dict[str, object]] = []
    if path.exists():
        existing_rows = [
            row for row in read_csv_rows(path) if str(row.get("ticker", "")) not in tickers
        ]
    merged = existing_rows + new_rows
    return write_csv_rows(path, fieldnames, merged)


def refresh_live_final_module_context(
    paths: WorkspacePaths,
    tickers: Iterable[str],
) -> dict[str, object]:
    selected = {str(item).strip() for item in tickers if str(item).strip()}
    generated_at = _utc_now_iso()
    as_of_date = _today_iso()
    entries = [entry for ticker in sorted(selected) for entry in _build_live_source_entries(ticker)]
    fetch_results: list[dict[str, object]] = []
    institutional_rows: list[dict[str, object]] = []
    news_rows: list[dict[str, object]] = []
    public_rows: list[dict[str, object]] = []

    for entry in entries:
        raw_path = _entry_raw_path(paths, entry)
        manifest_path = _entry_manifest_path(paths, entry)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        status = "downloaded"
        error_message = ""
        content_type = ""
        used_insecure_ssl = False
        title = str(entry.get("title", ""))
        try:
            response, content_type, used_insecure_ssl = _download_source(str(entry["url"]))
            response.raise_for_status()
            raw_path.write_bytes(response.content)
            title = _extract_html_title(response.content) or title
        except Exception as exc:
            status = "error"
            error_message = str(exc)
        manifest_record = {
            "source_id": entry["source_id"],
            "ticker": entry["ticker"],
            "category": entry["category"],
            "url": entry["url"],
            "title": title,
            "publish_date": entry["publish_date"],
            "raw_file": str(raw_path),
            "manifest_file": str(manifest_path),
            "status": status,
            "content_type": content_type,
            "error": error_message,
            "downloaded_at": generated_at,
            "used_insecure_ssl": used_insecure_ssl,
        }
        manifest_path.write_text(
            json.dumps(manifest_record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        fetch_results.append(manifest_record)
        if status == "error":
            continue

        category = str(entry["category"])
        if category == "institutional":
            institutional_rows.append(
                {
                    "ticker": entry["ticker"],
                    "as_of_date": as_of_date,
                    "source_name": entry["source_name"],
                    "institution_name": entry.get("institution_name", ""),
                    "report_date": entry.get("report_date", entry["publish_date"]),
                    "rating_raw": entry.get("rating_raw", ""),
                    "rating_normalized": entry.get("rating_normalized", ""),
                    "target_price": entry.get("target_price", 0.0),
                    "target_price_low": entry.get("target_price_low", 0.0),
                    "target_price_high": entry.get("target_price_high", 0.0),
                    "eps_fy1": entry.get("eps_fy1", 0.0),
                    "eps_fy2": entry.get("eps_fy2", 0.0),
                    "thesis_summary": f"{title}；最新估值頁已更新，請搭配內部模型判讀。",
                    "url": entry["url"],
                    "raw_file": str(raw_path),
                    "is_stale": False,
                    "ingested_at": generated_at,
                }
            )
        elif category == "news":
            news_rows.append(
                {
                    "ticker": entry["ticker"],
                    "as_of_date": as_of_date,
                    "publish_date": entry["publish_date"],
                    "source_name": entry["source_name"],
                    "headline": title,
                    "summary": f"{title}；最新新聞頁已更新，提供即時市場消息脈絡。",
                    "sentiment": entry.get("sentiment", "neutral"),
                    "theme": entry.get("theme", "valuation"),
                    "is_company_specific": entry.get("is_company_specific", True),
                    "url": entry["url"],
                    "raw_file": str(raw_path),
                    "is_stale": False,
                    "ingested_at": generated_at,
                }
            )
        elif category == "public":
            public_rows.append(
                {
                    "ticker": entry["ticker"],
                    "as_of_date": as_of_date,
                    "publish_date": entry["publish_date"],
                    "source_name": entry["source_name"],
                    "channel_type": entry.get("channel_type", ""),
                    "author_name": entry.get("author_name", ""),
                    "headline_or_topic": title,
                    "summary": f"{title}；最新公眾討論搜尋頁已更新，提供散戶脈絡參考。",
                    "sentiment": entry.get("sentiment", "neutral"),
                    "stance": entry.get("stance", "hold"),
                    "evidence_strength": entry.get("evidence_strength", "low"),
                    "url": entry["url"],
                    "raw_file": str(raw_path),
                    "is_stale": False,
                    "ingested_at": generated_at,
                }
            )

    paths.final_module_normalized_root.mkdir(parents=True, exist_ok=True)
    institutional_path = paths.final_module_normalized_root / "institutional_consensus.csv"
    news_path = paths.final_module_normalized_root / "news_commentary.csv"
    public_path = paths.final_module_normalized_root / "public_commentary.csv"
    market_path = paths.final_module_normalized_root / "market_view_snapshot.csv"

    _merge_rows_for_tickers(
        institutional_path,
        [
            "ticker","as_of_date","source_name","institution_name","report_date","rating_raw",
            "rating_normalized","target_price","target_price_low","target_price_high","eps_fy1",
            "eps_fy2","thesis_summary","url","raw_file","is_stale","ingested_at",
        ],
        institutional_rows,
        selected,
    )
    _merge_rows_for_tickers(
        news_path,
        [
            "ticker","as_of_date","publish_date","source_name","headline","summary","sentiment",
            "theme","is_company_specific","url","raw_file","is_stale","ingested_at",
        ],
        news_rows,
        selected,
    )
    _merge_rows_for_tickers(
        public_path,
        [
            "ticker","as_of_date","publish_date","source_name","channel_type","author_name",
            "headline_or_topic","summary","sentiment","stance","evidence_strength","url",
            "raw_file","is_stale","ingested_at",
        ],
        public_rows,
        selected,
    )

    market_rows = _build_market_view_rows(entries, as_of_date, generated_at)
    _merge_rows_for_tickers(
        market_path,
        [
            "ticker","as_of_date","institution_sentiment_score","public_sentiment_score",
            "institution_avg_target_price","institution_target_count","institution_positive_count",
            "institution_negative_count","public_bullish_count","public_bearish_count",
            "news_bullish_count","news_bearish_count","divergence_flag","divergence_summary",
            "generated_at",
        ],
        market_rows,
        selected,
    )

    summary = {
        "generated_at": generated_at,
        "as_of_date": as_of_date,
        "tickers": sorted(selected),
        "entry_count": len(entries),
        "success_count": sum(1 for item in fetch_results if item["status"] == "downloaded"),
        "error_count": sum(1 for item in fetch_results if item["status"] == "error"),
        "results": fetch_results,
    }
    summary_path = paths.final_module_artifacts_root / "live_context_refresh_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def build_final_module_snapshot(
    paths: WorkspacePaths,
    tickers: Iterable[str] | None = None,
) -> dict[str, object]:
    entries = _iter_catalog_entries(tickers)
    as_of_date = _today_iso()
    generated_at = _utc_now_iso()
    paths.final_module_normalized_root.mkdir(parents=True, exist_ok=True)

    institutional_rows = []
    news_rows = []
    public_rows = []
    for entry in entries:
        raw_path = _entry_raw_path(paths, entry)
        raw_file = str(raw_path) if raw_path.exists() else ""
        stale = _is_stale(entry, as_of_date)
        category = str(entry["category"])

        if category == "institutional":
            institutional_rows.append(
                {
                    "ticker": entry["ticker"],
                    "as_of_date": as_of_date,
                    "source_name": entry["source_name"],
                    "institution_name": entry.get("institution_name", ""),
                    "report_date": entry.get("report_date", entry["publish_date"]),
                    "rating_raw": entry.get("rating_raw", ""),
                    "rating_normalized": entry.get("rating_normalized", ""),
                    "target_price": entry.get("target_price", 0.0),
                    "target_price_low": entry.get("target_price_low", 0.0),
                    "target_price_high": entry.get("target_price_high", 0.0),
                    "eps_fy1": entry.get("eps_fy1", 0.0),
                    "eps_fy2": entry.get("eps_fy2", 0.0),
                    "thesis_summary": entry.get("thesis_summary", ""),
                    "url": entry["url"],
                    "raw_file": raw_file,
                    "is_stale": stale,
                    "ingested_at": generated_at,
                }
            )
        elif category == "news":
            news_rows.append(
                {
                    "ticker": entry["ticker"],
                    "as_of_date": as_of_date,
                    "publish_date": entry["publish_date"],
                    "source_name": entry["source_name"],
                    "headline": entry["title"],
                    "summary": entry["summary"],
                    "sentiment": entry.get("sentiment", "neutral"),
                    "theme": entry.get("theme", ""),
                    "is_company_specific": entry.get("is_company_specific", True),
                    "url": entry["url"],
                    "raw_file": raw_file,
                    "is_stale": stale,
                    "ingested_at": generated_at,
                }
            )
        elif category == "public":
            public_rows.append(
                {
                    "ticker": entry["ticker"],
                    "as_of_date": as_of_date,
                    "publish_date": entry["publish_date"],
                    "source_name": entry["source_name"],
                    "channel_type": entry.get("channel_type", ""),
                    "author_name": entry.get("author_name", ""),
                    "headline_or_topic": entry["title"],
                    "summary": entry["summary"],
                    "sentiment": entry.get("sentiment", "neutral"),
                    "stance": entry.get("stance", "hold"),
                    "evidence_strength": entry.get("evidence_strength", "medium"),
                    "url": entry["url"],
                    "raw_file": raw_file,
                    "is_stale": stale,
                    "ingested_at": generated_at,
                }
            )

    institutional_path = paths.final_module_normalized_root / "institutional_consensus.csv"
    news_path = paths.final_module_normalized_root / "news_commentary.csv"
    public_path = paths.final_module_normalized_root / "public_commentary.csv"
    market_path = paths.final_module_normalized_root / "market_view_snapshot.csv"

    institutional_count = write_csv_rows(
        institutional_path,
        [
            "ticker",
            "as_of_date",
            "source_name",
            "institution_name",
            "report_date",
            "rating_raw",
            "rating_normalized",
            "target_price",
            "target_price_low",
            "target_price_high",
            "eps_fy1",
            "eps_fy2",
            "thesis_summary",
            "url",
            "raw_file",
            "is_stale",
            "ingested_at",
        ],
        institutional_rows,
    )
    news_count = write_csv_rows(
        news_path,
        [
            "ticker",
            "as_of_date",
            "publish_date",
            "source_name",
            "headline",
            "summary",
            "sentiment",
            "theme",
            "is_company_specific",
            "url",
            "raw_file",
            "is_stale",
            "ingested_at",
        ],
        news_rows,
    )
    public_count = write_csv_rows(
        public_path,
        [
            "ticker",
            "as_of_date",
            "publish_date",
            "source_name",
            "channel_type",
            "author_name",
            "headline_or_topic",
            "summary",
            "sentiment",
            "stance",
            "evidence_strength",
            "url",
            "raw_file",
            "is_stale",
            "ingested_at",
        ],
        public_rows,
    )

    market_rows = _build_market_view_rows(entries, as_of_date, generated_at)
    market_count = write_csv_rows(
        market_path,
        [
            "ticker",
            "as_of_date",
            "institution_sentiment_score",
            "public_sentiment_score",
            "institution_avg_target_price",
            "institution_target_count",
            "institution_positive_count",
            "institution_negative_count",
            "public_bullish_count",
            "public_bearish_count",
            "news_bullish_count",
            "news_bearish_count",
            "divergence_flag",
            "divergence_summary",
            "generated_at",
        ],
        market_rows,
    )

    summary = {
        "generated_at": generated_at,
        "as_of_date": as_of_date,
        "shared_data_root": str(paths.shared_data_root),
        "final_module_shared_root": str(paths.final_module_shared_root),
        "normalized_root": str(paths.final_module_normalized_root),
        "tickers": sorted(_normalize_tickers(tickers)),
        "counts": {
            "institutional_consensus": institutional_count,
            "news_commentary": news_count,
            "public_commentary": public_count,
            "market_view_snapshot": market_count,
        },
        "files": {
            "institutional_consensus": str(institutional_path),
            "news_commentary": str(news_path),
            "public_commentary": str(public_path),
            "market_view_snapshot": str(market_path),
        },
    }
    summary_path = paths.final_module_artifacts_root / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def run_final_module_pilot(
    paths: WorkspacePaths,
    tickers: Iterable[str] | None = None,
    overwrite: bool = False,
) -> dict[str, object]:
    return {
        "fetch": fetch_final_module_sources(paths, tickers=tickers, overwrite=overwrite),
        "build": build_final_module_snapshot(paths, tickers=tickers),
    }


def _build_market_view_rows(
    entries: list[dict[str, object]],
    as_of_date: str,
    generated_at: str,
) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, list[dict[str, object]]]] = defaultdict(
        lambda: {"institutional": [], "news": [], "public": []}
    )
    for entry in entries:
        grouped[str(entry["ticker"])][str(entry["category"])].append(entry)

    rows: list[dict[str, object]] = []
    for ticker in sorted(grouped):
        bucket = grouped[ticker]
        inst_rows = bucket["institutional"]
        public_rows = bucket["public"]
        news_rows = bucket["news"]

        institution_scores = [
            _INSTITUTION_SCORE.get(str(row.get("rating_normalized", "")), 0.0) for row in inst_rows
        ]
        public_scores = [
            _PUBLIC_STANCE_SCORE.get(str(row.get("stance", "hold")), 0.0) for row in public_rows
        ]
        news_scores = [
            _NEWS_SENTIMENT_SCORE.get(str(row.get("sentiment", "neutral")), 0.0) for row in news_rows
        ]
        target_prices = [
            float(row.get("target_price", 0.0))
            for row in inst_rows
            if float(row.get("target_price", 0.0) or 0.0) > 0
        ]

        inst_score = round(mean(institution_scores), 4) if institution_scores else 0.0
        public_score = round(mean(public_scores), 4) if public_scores else 0.0
        _ = mean(news_scores) if news_scores else 0.0

        divergence_flag = abs(inst_score - public_score) >= 0.25
        divergence_summary = _build_divergence_summary(inst_score, public_score, news_scores)

        rows.append(
            {
                "ticker": ticker,
                "as_of_date": as_of_date,
                "institution_sentiment_score": inst_score,
                "public_sentiment_score": public_score,
                "institution_avg_target_price": round(mean(target_prices), 4) if target_prices else 0.0,
                "institution_target_count": len(target_prices),
                "institution_positive_count": sum(1 for value in institution_scores if value > 0),
                "institution_negative_count": sum(1 for value in institution_scores if value < 0),
                "public_bullish_count": sum(1 for value in public_scores if value > 0),
                "public_bearish_count": sum(1 for value in public_scores if value < 0),
                "news_bullish_count": sum(1 for value in news_scores if value > 0),
                "news_bearish_count": sum(1 for value in news_scores if value < 0),
                "divergence_flag": divergence_flag,
                "divergence_summary": divergence_summary,
                "generated_at": generated_at,
            }
        )
    return rows


def _build_divergence_summary(
    institution_score: float,
    public_score: float,
    news_scores: list[float],
) -> str:
    if abs(institution_score - public_score) < 0.25:
        if news_scores and mean(news_scores) > 0.25:
            return "法人與公眾方向大致一致，近期新聞偏多。"
        if news_scores and mean(news_scores) < -0.25:
            return "法人與公眾方向大致一致，但近期新聞偏空。"
        return "法人與公眾方向大致一致。"
    if public_score > institution_score:
        return "公眾觀點比法人更樂觀。"
    return "法人觀點比公眾更樂觀。"
