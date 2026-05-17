from __future__ import annotations

import base64
import json
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from textwrap import dedent

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from tw_valuation_models.config import WorkspacePaths
from tw_valuation_models.dataset import (
    build_top100_dataset,
    load_top100_dataset,
    read_annual_financials,
    read_price_history,
    read_quarterly_financials,
)
from tw_valuation_models.final_module_data import (
    refresh_live_final_module_context,
    run_final_module_pilot,
)
from tw_valuation_models.final_module_payloads import build_final_module_payloads
from tw_valuation_models.portfolio_builder import (
    build_all_model_results,
    build_single_ticker_model_result,
)
from tw_valuation_models.reporting import (
    build_buffett3_export_notes,
    build_model_ranking_comparison,
    summarize_manifest_for_ticker,
)


WORKSPACE_ROOT = Path(__file__).resolve().parent
PATHS = WorkspacePaths(workspace_root=WORKSPACE_ROOT)
RESULTS_PATH = WORKSPACE_ROOT / "artifacts" / "results" / "top100_model_results.csv"
SUMMARY_PATH = WORKSPACE_ROOT / "artifacts" / "results" / "top100_model_results_summary.json"
BUFFETT3_PAYLOAD_DIR = WORKSPACE_ROOT / "artifacts" / "results" / "buffett3_payloads"
FINAL_MODULE_PAYLOAD_DIR = WORKSPACE_ROOT / "artifacts" / "final_module" / "payloads"
FINAL_MODULE_INDEPENDENT_AI_DIR = FINAL_MODULE_PAYLOAD_DIR / "independent_ai"
FINAL_MODULE_COMMENTARY_DIR = FINAL_MODULE_PAYLOAD_DIR / "final_commentary"

plt.rcParams["font.sans-serif"] = [
    "Microsoft JhengHei",
    "Microsoft YaHei",
    "SimHei",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False

MODEL_ORDER = ["buffett_v1", "buffett_v2", "buffett3", "imfs", "quant", "hybrid"]
MODEL_META = {
    "buffett_v1": {
        "label": "巴菲特 TW",
        "short_label": "巴菲特TW",
        "symbol": "◉",
        "color": "#0f5d59",
        "value_label": "估值折價",
    },
    "buffett_v2": {
        "label": "巴菲特 2.0",
        "short_label": "巴菲特2.0",
        "symbol": "◎",
        "color": "#a77224",
        "value_label": "估值折價",
    },
    "buffett3": {
        "label": "Buffett 3.0",
        "short_label": "Buffett 3.0",
        "symbol": "B3",
        "color": "#2d8f6f",
        "value_label": "價值差距",
    },
    "imfs": {
        "label": "IMFS",
        "short_label": "IMFS",
        "symbol": "▲",
        "color": "#476f9f",
        "value_label": "估值折價",
    },
    "quant": {
        "label": "台股 Buffett Quant",
        "short_label": "台股Buffett Quant",
        "symbol": "◌",
        "color": "#db6158",
        "value_label": "綜合分數",
    },
    "hybrid": {
        "label": "混合模型",
        "short_label": "混合模型",
        "symbol": "◍",
        "color": "#0f6d67",
        "value_label": "預期報酬",
    },
}

VALUE_RULES = [
    ("低估", ">= 25%", "內在價值相對目前股價有明顯安全邊際。"),
    ("合理偏低", "10% 至 25%", "估值仍有折價，但安全邊際不如深度低估。"),
    ("合理", "-5% 至 10%", "價格大致接近合理價值區間。"),
    ("合理偏高", "-20% 至 -5%", "股價已略高於合理價值。"),
    ("昂貴", "-50% 至 -20%", "股價高於內在價值，報酬風險比轉差。"),
    ("非常昂貴", "<= -50%", "股價顯著高於內在價值，安全邊際不足。"),
]

QUANT_RULES = [
    ("低估", ">= 80", "品質、動能與估值訊號同時偏強。"),
    ("合理偏低", "65 至 79.9", "多數條件健康，偏向正向配置。"),
    ("合理", "50 至 64.9", "訊號中性，維持觀察或中性持有。"),
    ("合理偏高", "40 至 49.9", "風險報酬比轉弱，需要提高要求。"),
    ("昂貴", "25 至 39.9", "多項訊號不利，追價吸引力偏低。"),
    ("非常昂貴", "< 25", "整體配置價值不足，需高度保守。"),
]

HYBRID_RULES = [
    ("低估", ">= 20%", "模型預估未來報酬具明顯上行空間。"),
    ("合理偏低", "8% 至 19.9%", "仍有正向報酬空間，但不屬深度低估。"),
    ("合理", "-3% 至 7.9%", "預期報酬接近中性區。"),
    ("合理偏高", "-10% 至 -3.1%", "風險報酬開始轉弱。"),
    ("昂貴", "-20% 至 -10.1%", "預期報酬偏差，不宜提高部位。"),
    ("非常昂貴", "<= -20%", "預期下行風險高於報酬補償。"),
]

BADGE_STYLE = {
    "低估": "badge-good",
    "合理偏低": "badge-good",
    "合理": "badge-neutral",
    "合理偏高": "badge-warm",
    "昂貴": "badge-risk",
    "非常昂貴": "badge-risk",
    "品質訊號": "badge-neutral",
    "資料不足": "badge-muted",
}


MODEL_REFERENCE_ROWS = [
    {
        "模型": "巴菲特 TW",
        "核心計算": "以 EPS / 平滑 EPS 為基礎做 DCF 折現，再與現價比較得到估值折價。",
        "主要輸入": "EPS、ROE、股利率、歷史 EPS、自由現金流轉換率、負債權益比、流動比率。",
        "資料來源": "本地 TOP100 fundamentals / prices 快照，公式常數沿用原始 Buffett DCF 專案。",
        "輸出": "內在價值、估值折價、信號。",
        "適用情境": "成熟獲利企業、重視長期股東回報與保守折現。",
    },
    {
        "模型": "巴菲特 2.0",
        "核心計算": "以每股自由現金流 / 平滑 FCF 為基礎做 DCF 折現，重視現金流品質。",
        "主要輸入": "自由現金流、股本、ROE、成長率、歷史財務資料。",
        "資料來源": "本地 TOP100 fundamentals / prices 快照，公式常數沿用原始 Buffett DCF 專案。",
        "輸出": "內在價值、估值折價、信號。",
        "適用情境": "現金流穩定、資本配置紀律重要的企業。",
    },
    {
        "模型": "IMFS",
        "核心計算": "先做 Route A/B/C/D 分流；Route B 原始只給品質分數，我們再橋接 projected EPS × justified P/E。",
        "主要輸入": "營收成長、利潤率、股本、產業輪廓、資產負債、股價。",
        "資料來源": "原始 IMFS route classifier / valuation engine + 本地 TOP100 fundamentals / prices 快照。",
        "輸出": "Route、模型名稱、品質分數 / 內在價值、估值折價、溢價資格。",
        "適用情境": "想先按企業類型分流，再選估值框架的情境。",
    },
    {
        "模型": "台股 Buffett Quant",
        "核心計算": "整合品質、估值、動能、河流訊號做綜合分數，再映射動作與估值標籤。",
        "主要輸入": "ROE、現金流、月營收趨勢、價格動能、市場河流訊號。",
        "資料來源": "原始 strict mode engine + 本地整合月營收、價格與基本面。",
        "輸出": "綜合分數、建議動作、估值標籤。",
        "適用情境": "需要價值 + 品質 + 技術面綜合排序。",
    },
    {
        "模型": "混合模型",
        "核心計算": "使用 hybrid strategy 技術特徵與模型推論預測未來報酬，再映射為評級。",
        "主要輸入": "價格歷史、技術特徵、模型預測輸出。",
        "資料來源": "原始 Taiwan stock hybrid strategy + 本地模型輸入 bundle。",
        "輸出": "目標價、預期報酬、估值標籤。",
        "適用情境": "偏重價格行為與模型預測的情境。",
    },
]

st.set_page_config(
    page_title="台股多模型估值平台",
    page_icon="TW",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
    :root {
        --bg: #0a1211;
        --bg-soft: #0f1a18;
        --panel: rgba(13, 22, 21, 0.94);
        --panel-strong: rgba(10, 18, 17, 0.98);
        --panel-soft: rgba(18, 31, 29, 0.92);
        --line: rgba(109, 143, 120, 0.16);
        --line-strong: rgba(200, 169, 107, 0.24);
        --teal: #7ad7c6;
        --teal-strong: #2f9b8c;
        --gold: #c8a96b;
        --gold-soft: #ecd6a7;
        --text: #edf3ee;
        --muted: #97aaa2;
        --muted-soft: #788780;
        --good: #7fd6a4;
        --warm: #e2ac57;
        --risk: #f16f64;
        --chip: rgba(255, 255, 255, 0.04);
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(40, 110, 93, 0.22), transparent 22%),
            radial-gradient(circle at top center, rgba(200, 169, 107, 0.18), transparent 18%),
            linear-gradient(180deg, #091111 0%, #0b1413 28%, #0c1414 100%);
        color: var(--text);
        font-family: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3 {
        font-family: "Noto Serif TC", "PMingLiU", serif;
        color: var(--text);
    }

    h2 {
        letter-spacing: 0.02em;
    }

    div[data-testid="stAppViewContainer"] > .main {
        background: transparent;
    }

    div[data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, rgba(8, 17, 17, 0.98) 0%, rgba(10, 22, 21, 0.98) 100%);
        border-right: 1px solid rgba(109, 143, 120, 0.14);
    }

    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div,
    div[data-testid="stSidebarContent"],
    div[data-testid="stSidebarUserContent"] {
        background:
            linear-gradient(180deg, rgba(8, 17, 17, 0.99) 0%, rgba(10, 22, 21, 0.99) 100%) !important;
    }

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"] {
        background: transparent !important;
    }

    .stDeployButton,
    div[data-testid="stAppDeployButton"],
    button[title="Deploy"],
    button[aria-label="Deploy"] {
        display: none !important;
    }

    div[data-testid="stSidebar"] .block-container {
        padding-top: 0.8rem;
    }

    .surface,
    .hero-surface,
    .toolbar-surface,
    .card-surface,
    .side-surface,
    .warning-surface {
        background:
            linear-gradient(180deg, rgba(14, 26, 25, 0.96) 0%, rgba(10, 19, 18, 0.96) 100%);
        border: 1px solid var(--line);
        border-radius: 18px;
        box-shadow: 0 16px 36px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }

    .hero-surface {
        padding: 1rem 1.3rem;
        margin-bottom: 0.85rem;
    }

    .toolbar-surface {
        padding: 0.8rem 1rem;
        margin-bottom: 0.85rem;
    }

    .surface {
        padding: 1rem;
    }

    .side-surface {
        padding: 1.15rem 1.2rem;
        margin-bottom: 0.9rem;
    }

    .detail-section {
        padding: 0.95rem 1rem 1rem 1rem;
        margin-top: 0.8rem;
    }

    .warning-surface {
        padding: 0.85rem 1rem;
        border-color: rgba(200, 169, 107, 0.28);
        background: linear-gradient(180deg, rgba(42, 31, 11, 0.85) 0%, rgba(28, 22, 10, 0.92) 100%);
        margin-top: 0.9rem;
    }

    .title-row {
        display: flex;
        justify-content: space-between;
        align-items: start;
        gap: 1rem;
    }

    .title-main {
        font-size: 2.15rem;
        margin: 0;
        letter-spacing: 0.02em;
        color: #f5efe4;
    }

    .title-kicker {
        font-size: 0.78rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--gold-soft);
        margin-bottom: 0.45rem;
    }

    .hero-subcopy {
        margin-top: 0.55rem;
        color: var(--muted);
        font-size: 0.93rem;
        line-height: 1.7;
        max-width: 860px;
    }

    .title-meta {
        font-size: 0.92rem;
        color: var(--muted);
        text-align: right;
        line-height: 1.7;
    }

    .title-meta strong {
        color: #f5efe4;
        font-weight: 600;
    }

    .left-rail-title {
        background: linear-gradient(135deg, #123c3a 0%, #0d5452 100%);
        color: #f6f1e8;
        padding: 0.9rem 1.15rem;
        border-radius: 20px;
        font-size: 1.44rem;
        font-family: "Noto Serif TC", "PMingLiU", serif;
        margin: 0 0 1.1rem 0;
        box-shadow: 0 12px 28px rgba(5, 16, 15, 0.45), 0 0 0 1px rgba(200, 169, 107, 0.16);
        width: 100%;
        box-sizing: border-box;
        line-height: 1.2;
        min-height: 68px;
        display: flex;
        align-items: center;
        overflow: visible;
    }

    .sidebar-note-card {
        border: 1px solid rgba(109, 143, 120, 0.18);
        border-radius: 16px;
        padding: 0.85rem 0.95rem;
        margin-bottom: 0.9rem;
        background: linear-gradient(180deg, rgba(17, 35, 33, 0.92) 0%, rgba(11, 23, 22, 0.96) 100%);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }

    .sidebar-note-title {
        color: #f5efe4;
        font-size: 0.88rem;
        margin-bottom: 0.22rem;
    }

    .sidebar-note-copy {
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.6;
    }

    .section-note {
        color: var(--muted);
        font-size: 0.84rem;
    }

    .toolbar-chip {
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 0.55rem 0.75rem;
        background: var(--chip);
        min-height: 64px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }

    .toolbar-chip-name {
        font-size: 0.94rem;
        color: var(--text);
        margin-bottom: 0.12rem;
    }

    .toolbar-chip-state {
        font-size: 0.8rem;
        color: var(--muted);
    }

    .card-surface {
        padding: 0.95rem;
        min-height: 360px;
        background:
            radial-gradient(circle at top right, rgba(200, 169, 107, 0.08), transparent 24%),
            linear-gradient(180deg, rgba(12, 24, 23, 0.98) 0%, rgba(10, 18, 17, 0.98) 100%);
    }

    .overview-row {
        margin-bottom: 1rem;
    }

    .card-top {
        display: flex;
        justify-content: space-between;
        align-items: start;
        gap: 0.5rem;
        margin-bottom: 0.45rem;
    }

    .card-title {
        font-size: 1.2rem;
        color: #f0f4ef;
        margin: 0;
        line-height: 1.3;
        min-height: 3rem;
    }

    .badge {
        display: inline-block;
        padding: 0.24rem 0.66rem;
        border-radius: 999px;
        font-size: 0.78rem;
        border: 1px solid transparent;
        white-space: nowrap;
    }

    .badge-good {
        color: var(--good);
        background: rgba(44, 138, 103, 0.08);
        border-color: rgba(44, 138, 103, 0.16);
    }

    .badge-neutral {
        color: var(--teal);
        background: rgba(18, 60, 58, 0.06);
        border-color: rgba(18, 60, 58, 0.12);
    }

    .badge-warm {
        color: var(--warm);
        background: rgba(207, 147, 65, 0.08);
        border-color: rgba(207, 147, 65, 0.16);
    }

    .badge-risk {
        color: var(--risk);
        background: rgba(219, 97, 88, 0.08);
        border-color: rgba(219, 97, 88, 0.16);
    }

    .badge-muted {
        color: var(--muted);
        background: rgba(111, 122, 126, 0.08);
        border-color: rgba(111, 122, 126, 0.16);
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.84rem;
        margin-top: 0.35rem;
    }

    .metric-value {
        font-family: "JetBrains Mono", "Consolas", monospace;
        font-size: 1.9rem;
        color: #f1f7f3;
        margin: 0.12rem 0 0.3rem 0;
    }

    .mini-row {
        display: flex;
        justify-content: space-between;
        gap: 0.7rem;
        font-size: 0.88rem;
        color: var(--muted);
        margin: 0.24rem 0;
    }

    .mini-row strong {
        color: #f1f7f3;
        font-family: "JetBrains Mono", "Consolas", monospace;
        font-weight: 600;
    }

    .card-comment {
        color: var(--muted);
        font-size: 0.83rem;
        line-height: 1.55;
        margin-top: 0.35rem;
    }

    .card-stats {
        margin-top: 0.2rem;
        padding-top: 0.18rem;
        border-top: 1px solid rgba(109, 143, 120, 0.12);
    }

    .sparkline-shell {
        margin: 0.2rem 0 0.25rem 0;
        padding: 0.1rem 0 0 0;
        border-top: 1px solid rgba(109, 143, 120, 0.08);
        border-bottom: 1px solid rgba(109, 143, 120, 0.08);
    }

    .sparkline-shell img {
        width: 100%;
        height: 64px;
        object-fit: cover;
        display: block;
        opacity: 0.94;
    }

    .card-stat-row {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 0.75rem;
        align-items: center;
        padding: 0.15rem 0;
        font-size: 0.92rem;
    }

    .card-stat-label {
        color: var(--muted);
    }

    .card-stat-value {
        color: #f0f4ef;
        font-family: "JetBrains Mono", "Consolas", monospace;
        font-weight: 600;
        text-align: right;
    }

    .confidence-track {
        width: 100%;
        height: 6px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
        overflow: hidden;
        margin: 0.28rem 0 0.45rem 0;
    }

    .confidence-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #c8a96b 0%, #0f6d67 100%);
    }

    .side-divider {
        border: 0;
        border-top: 1px solid rgba(109, 143, 120, 0.14);
        margin: 1rem 0;
    }

    .metric-shell {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.9rem;
        background: linear-gradient(180deg, rgba(14, 25, 24, 0.96) 0%, rgba(12, 20, 20, 0.96) 100%);
        min-height: 312px;
    }

    .metric-shell h3,
    .metric-shell p {
        margin-top: 0;
    }

    .detail-stat {
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.2rem;
        margin-top: 0.8rem;
        color: var(--muted);
        font-size: 0.88rem;
    }

    .detail-stat strong {
        color: #f5efe4;
        font-family: "JetBrains Mono", "Consolas", monospace;
        font-size: 1rem;
    }

    .chart-shell {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.75rem 0.8rem 0.55rem 0.8rem;
        background: linear-gradient(180deg, rgba(9, 18, 17, 0.98) 0%, rgba(7, 14, 14, 0.98) 100%);
        min-height: 410px;
    }

    .chart-caption {
        color: var(--muted);
        font-size: 0.76rem;
        margin-top: 0.2rem;
    }

    .key-metric-table {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.75rem 0.85rem;
        background: rgba(255, 255, 255, 0.025);
        min-height: 312px;
    }

    .key-metric-row {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 0.8rem;
        padding: 0.38rem 0;
        border-bottom: 1px solid rgba(109, 143, 120, 0.10);
        font-size: 0.86rem;
    }

    .key-metric-row:last-child {
        border-bottom: 0;
    }

    .key-metric-name {
        color: var(--muted);
    }

    .key-metric-value {
        color: #f5efe4;
        font-family: "JetBrains Mono", "Consolas", monospace;
        text-align: right;
    }

    .model-summary-strip {
        border: 1px solid rgba(109, 143, 120, 0.16);
        border-radius: 8px;
        padding: 0.7rem 0.85rem;
        margin-top: 0.75rem;
        background: linear-gradient(90deg, rgba(16, 64, 55, 0.30), rgba(12, 24, 22, 0.82));
        color: var(--muted);
        font-size: 0.88rem;
        line-height: 1.65;
    }

    .model-summary-strip strong {
        color: #f5efe4;
    }

    .detail-headline {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.8rem;
        margin-bottom: 0.25rem;
    }

    .detail-submeta {
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.7;
    }

    .detail-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.28rem 0.7rem;
        border-radius: 999px;
        background: rgba(18, 60, 58, 0.24);
        color: #dff5ee;
        border: 1px solid rgba(109, 143, 120, 0.16);
        font-size: 0.82rem;
    }

    .insight-list {
        margin: 0.55rem 0 0 0;
        padding-left: 1.1rem;
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.7;
    }

    .rail-card-title {
        font-size: 1rem;
        font-weight: 700;
        color: var(--text);
        margin-top: 0.15rem;
        margin-bottom: 0.55rem;
    }

    .spec-copy,
    .rail-copy {
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.7;
    }

    .right-stack {
        display: grid;
        gap: 0.9rem;
    }

    .rating-grid {
        display: grid;
        gap: 0.45rem;
        margin-top: 0.7rem;
    }

    .rating-row {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 0.7rem;
        align-items: start;
    }

    .rating-meta {
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.45;
        margin-top: 0.15rem;
    }

    .action-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.55rem;
        margin-top: 0.85rem;
    }

    .action-tile {
        padding: 0.85rem 0.55rem;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.03);
        text-align: center;
        color: var(--text);
        font-size: 0.82rem;
        line-height: 1.45;
    }

    .file-card {
        display: grid;
        gap: 0.5rem;
        border-radius: 8px;
        padding: 0.9rem;
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.03);
        margin-top: 0.75rem;
    }

    .file-meta,
    .feed-meta {
        color: var(--muted);
        font-size: 0.78rem;
    }

    .feed-list {
        display: grid;
        gap: 0.7rem;
        margin-top: 0.85rem;
    }

    .feed-item {
        display: flex;
        gap: 0.7rem;
        align-items: start;
    }

    .feed-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: var(--gold);
        margin-top: 0.38rem;
        flex: 0 0 9px;
    }

    .feed-copy {
        color: var(--text);
        font-size: 0.88rem;
        line-height: 1.55;
    }

    .feed-copy strong {
        color: #f5efe4;
    }

    .warning-grid {
        display: grid;
        gap: 0.8rem;
        margin-top: 0.65rem;
    }

    .warning-card {
        border: 1px solid rgba(200, 169, 107, 0.16);
        border-radius: 12px;
        padding: 0.8rem 0.9rem;
        background: rgba(255, 255, 255, 0.025);
    }

    .warning-card-title {
        color: #f5efe4;
        font-size: 0.92rem;
        margin-bottom: 0.3rem;
    }

    .warning-card-copy {
        color: var(--muted);
        font-size: 0.86rem;
        line-height: 1.65;
    }

    .summary-grid {
        display: grid;
        gap: 0.55rem;
    }

    .summary-row {
        display: grid;
        grid-template-columns: 1fr auto auto;
        gap: 0.6rem;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(109, 143, 120, 0.12);
        font-size: 0.88rem;
    }

    .summary-row:last-child {
        border-bottom: 0;
    }

    .summary-row-model {
        color: var(--text);
    }

    .summary-row-value {
        color: #edf3ee;
        font-family: "JetBrains Mono", "Consolas", monospace;
        text-align: right;
    }

    .stat-band {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 0.65rem;
        margin-bottom: 0.85rem;
    }

    .stat-card {
        padding: 0.9rem 1rem;
        border-radius: 16px;
        border: 1px solid var(--line);
        background:
            radial-gradient(circle at top right, rgba(200, 169, 107, 0.10), transparent 30%),
            linear-gradient(180deg, rgba(13, 25, 24, 0.96) 0%, rgba(10, 18, 18, 0.96) 100%);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }

    .stat-label {
        color: var(--muted);
        font-size: 0.8rem;
        margin-bottom: 0.35rem;
    }

    .stat-value {
        color: #f6f1e8;
        font-size: 1.2rem;
        font-family: "JetBrains Mono", "Consolas", monospace;
        font-weight: 700;
        line-height: 1.25;
    }

    .stat-note {
        color: var(--muted);
        font-size: 0.78rem;
        margin-top: 0.25rem;
        line-height: 1.45;
    }

    .side-list {
        display: grid;
        gap: 0.55rem;
        margin-top: 0.75rem;
    }

    .side-list-row {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 0.75rem;
        align-items: center;
        padding-bottom: 0.45rem;
        border-bottom: 1px solid rgba(109, 143, 120, 0.10);
        font-size: 0.86rem;
    }

    .side-list-row:last-child {
        border-bottom: 0;
        padding-bottom: 0;
    }

    .side-list-row span:first-child {
        color: var(--muted);
    }

    .side-list-row span:last-child {
        color: #f5efe4;
        font-family: "JetBrains Mono", "Consolas", monospace;
        text-align: right;
    }

    .health-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.24rem 0.62rem;
        border-radius: 999px;
        font-size: 0.78rem;
        border: 1px solid rgba(109, 143, 120, 0.18);
        background: rgba(255, 255, 255, 0.04);
        color: #edf3ee;
        margin-top: 0.55rem;
    }

    .threshold-line {
        display: flex;
        justify-content: space-between;
        gap: 0.75rem;
        padding: 0.34rem 0;
        border-bottom: 1px solid rgba(109, 143, 120, 0.10);
        font-size: 0.82rem;
    }

    .threshold-line:last-child {
        border-bottom: 0;
    }

    .threshold-line span:last-child {
        color: var(--muted);
        font-family: "JetBrains Mono", "Consolas", monospace;
        text-align: right;
    }

    .download-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
    }

    .tab-note {
        color: var(--muted);
        font-size: 0.86rem;
        margin-top: -0.3rem;
        margin-bottom: 0.55rem;
    }

    .strong-button button {
        background: linear-gradient(135deg, #123c3a 0%, #0d5452 100%);
        color: #f6f1e8 !important;
        border: 1px solid rgba(200, 169, 107, 0.9);
        box-shadow: 0 0 0 1px rgba(200, 169, 107, 0.25), 0 0 20px rgba(200, 169, 107, 0.25);
    }

    .secondary-button button {
        background: rgba(255, 255, 255, 0.03);
        color: #edf3ee !important;
        border: 1px solid rgba(109, 143, 120, 0.24);
    }

    button[kind],
    div[data-testid="stDownloadButton"] button,
    div[data-testid="stButton"] button {
        background: linear-gradient(180deg, rgba(19, 45, 41, 0.98) 0%, rgba(10, 25, 23, 0.98) 100%) !important;
        color: #edf3ee !important;
        border: 1px solid rgba(109, 143, 120, 0.32) !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }

    button[kind]:hover,
    div[data-testid="stDownloadButton"] button:hover,
    div[data-testid="stButton"] button:hover {
        border-color: rgba(200, 169, 107, 0.62) !important;
        color: #f6f1e8 !important;
    }

    button:disabled,
    button[disabled],
    div[data-testid="stDownloadButton"] button:disabled,
    div[data-testid="stButton"] button:disabled {
        background: rgba(20, 35, 32, 0.66) !important;
        color: rgba(237, 243, 238, 0.52) !important;
        border-color: rgba(109, 143, 120, 0.16) !important;
    }

    .small-muted {
        color: var(--muted);
        font-size: 0.82rem;
    }

    div[data-testid="stSidebar"] label,
    div[data-testid="stSidebar"] p,
    div[data-testid="stSidebar"] span,
    div[data-testid="stSidebar"] div[data-baseweb="select"] *,
    div[data-testid="stSidebar"] .stRadio label,
    div[data-testid="stSidebar"] .stCheckbox label,
    div[data-testid="stSidebar"] h3 {
        color: var(--text) !important;
    }

    div[data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
    div[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #f1f6ef !important;
        opacity: 1 !important;
    }

    div[data-testid="stSidebar"] .stDateInput input,
    div[data-testid="stSidebar"] .stTextInput input,
    div[data-testid="stSidebar"] div[data-baseweb="select"] > div,
    div[data-testid="stSidebar"] div[data-baseweb="select"] input,
    div[data-testid="stSidebar"] div[data-baseweb="select"] [role="combobox"] {
        background: rgba(13, 31, 29, 0.94) !important;
        border: 1px solid rgba(109, 143, 120, 0.30) !important;
        color: var(--text) !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }

    div[data-testid="stSidebar"] input:disabled,
    div[data-testid="stSidebar"] textarea:disabled,
    div[data-testid="stSidebar"] div[data-baseweb="select"] [aria-disabled="true"] {
        background: rgba(16, 29, 27, 0.88) !important;
        color: rgba(237, 243, 238, 0.62) !important;
        -webkit-text-fill-color: rgba(237, 243, 238, 0.62) !important;
    }

    div[data-testid="stSidebar"] div[data-baseweb="checkbox"] label,
    div[data-testid="stSidebar"] div[data-baseweb="radio"] label {
        color: #d9e7df !important;
        opacity: 1 !important;
    }

    div[data-testid="stSidebar"] div[data-baseweb="checkbox"] div,
    div[data-testid="stSidebar"] div[data-baseweb="radio"] div {
        color: #d9e7df !important;
    }

    div[data-testid="stSidebar"] svg {
        color: #dff5ee !important;
        fill: currentColor !important;
    }

    div[data-testid="stSidebar"] .stProgress > div > div > div {
        background: linear-gradient(90deg, #c8a96b 0%, #0f6d67 100%);
    }

    div[data-testid="stSidebar"] .stProgress > div > div {
        background: rgba(255, 255, 255, 0.08);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state() -> None:
    if "active_models" not in st.session_state:
        st.session_state.active_models = MODEL_ORDER.copy()
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "卡片"
    if "page_mode" not in st.session_state:
        st.session_state.page_mode = "主頁總覽"
    if "previous_page_mode" not in st.session_state:
        st.session_state.previous_page_mode = st.session_state.page_mode


DEMO_TICKERS = ["2330", "2881", "2603", "2412"]


def normalized_shared_data_available() -> bool:
    normalized_root = PATHS.normalized_root
    required = [
        normalized_root / "universe_snapshot.csv",
        normalized_root / "valuation_snapshot.csv",
        normalized_root / "fundamentals_snapshot.csv",
    ]
    return all(path.exists() for path in required)


def bootstrap_public_demo_results() -> None:
    for ticker in DEMO_TICKERS:
        try:
            build_single_ticker_model_result(PATHS, ticker)
            refresh_live_final_module_context(PATHS, [ticker])
        except Exception:
            continue
    build_final_module_payloads(PATHS, tickers=DEMO_TICKERS)


def ensure_outputs() -> None:
    has_top100_dataset = (PATHS.artifacts_root / "datasets" / "top100" / "dataset_summary.json").exists()
    has_results = RESULTS_PATH.exists()
    if has_top100_dataset and has_results:
        return

    if normalized_shared_data_available():
        if not has_top100_dataset:
            build_top100_dataset(PATHS)
        if not has_results:
            build_all_model_results(PATHS)
        return

    bootstrap_public_demo_results()


def should_refresh_final_ai(page_mode: object, previous_page_mode: object) -> bool:
    return str(page_mode) == "Final AI 專區" and str(previous_page_mode) != "Final AI 專區"


def refresh_all_outputs_for_final_ai() -> None:
    build_top100_dataset(PATHS)
    build_all_model_results(PATHS)
    run_final_module_pilot(PATHS, overwrite=True)
    build_final_module_payloads(PATHS)


def refresh_selected_ticker_for_final_ai(ticker: str) -> None:
    ticker = normalize_ticker(ticker)
    if not ticker:
        return
    build_single_ticker_model_result(PATHS, ticker)
    refresh_live_final_module_context(PATHS, [ticker])
    build_final_module_payloads(PATHS, tickers=[ticker])


def normalize_ticker(raw_value: object) -> str:
    return "".join(char for char in str(raw_value or "").strip() if char.isalnum()).upper()


@st.cache_data(show_spinner=False)
def load_results() -> tuple[pd.DataFrame, dict[str, object], dict[str, object]]:
    ensure_outputs()
    if RESULTS_PATH.exists():
        results_df = pd.read_csv(RESULTS_PATH)
    else:
        results_df = pd.DataFrame()
    dataset: dict[str, object]
    result_summary: dict[str, object]
    if (PATHS.artifacts_root / "datasets" / "top100" / "dataset_summary.json").exists():
        dataset = load_top100_dataset(PATHS)
        result_summary = (
            json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
            if SUMMARY_PATH.exists()
            else {"generated_at": dataset.get("summary", {}).get("generated_at", ""), "demo_mode": False}
        )
    else:
        dataset = {
            "summary": {
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "top100_count": 0,
                    "monthly_revenue_rows": 0,
                },
                "demo_mode": True,
            },
            "dataset_root": PATHS.on_demand_datasets_root,
            "top100_universe": pd.DataFrame(columns=["ticker", "company_name", "industry", "market_cap"]),
            "top100_valuation": pd.DataFrame(),
            "top100_fundamentals_snapshot": pd.DataFrame(),
            "monthly_revenue": pd.DataFrame(),
        }
        result_summary = {
            "generated_at": dataset["summary"]["generated_at"],
            "result_count": 0,
            "demo_mode": True,
        }
    if not results_df.empty and "ticker" in results_df.columns:
        results_df["ticker"] = results_df["ticker"].astype(str)
    if not results_df.empty and "dataset_root" not in results_df.columns:
        results_df["dataset_root"] = str(dataset["dataset_root"])
    if PATHS.on_demand_results_root.exists():
        on_demand_rows: list[dict[str, object]] = []
        for path in sorted(PATHS.on_demand_results_root.glob("*.json")):
            payload = load_json_optional(str(path))
            row = payload.get("row")
            if isinstance(row, dict):
                on_demand_rows.append(row)
        if on_demand_rows:
            on_demand_df = pd.DataFrame(on_demand_rows)
            if not on_demand_df.empty:
                on_demand_df["ticker"] = on_demand_df["ticker"].astype(str)
                results_df = (
                    pd.concat([results_df, on_demand_df], ignore_index=True, sort=False)
                    .drop_duplicates(subset=["ticker"], keep="last")
                    .reset_index(drop=True)
                )
    if results_df.empty and PATHS.on_demand_results_root.exists():
        synthesized_rows: list[dict[str, object]] = []
        for path in sorted(PATHS.on_demand_results_root.glob("*.json")):
            payload = load_json_optional(str(path))
            row = payload.get("row")
            if isinstance(row, dict):
                synthesized_rows.append(row)
        if synthesized_rows:
            results_df = pd.DataFrame(synthesized_rows)

    if not results_df.empty:
        results_df["ticker"] = results_df["ticker"].astype(str)
        if "dataset_root" not in results_df.columns:
            results_df["dataset_root"] = str(dataset["dataset_root"])
        if dataset["top100_universe"].empty:
            dataset["top100_universe"] = pd.DataFrame(
                [
                    {
                        "ticker": row.get("ticker"),
                        "company_name": row.get("name"),
                        "industry": row.get("industry"),
                        "market_cap": row.get("market_cap"),
                    }
                    for row in results_df.to_dict("records")
                ]
            )
    if "ticker" in dataset["top100_universe"].columns:
        dataset["top100_universe"]["ticker"] = dataset["top100_universe"]["ticker"].astype(str)
    result_summary["result_count"] = int(len(results_df))
    return results_df, dataset, result_summary


@st.cache_data(show_spinner=False)
def load_json_optional(path_str: str) -> dict[str, object]:
    path = Path(path_str)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


@st.cache_data(show_spinner=False)
def load_final_module_payload(ticker: str, payload_type: str) -> dict[str, object]:
    if payload_type == "independent_ai":
        base_dir = FINAL_MODULE_INDEPENDENT_AI_DIR
    elif payload_type == "final_commentary":
        base_dir = FINAL_MODULE_COMMENTARY_DIR
    else:
        return {}
    return load_json_optional(str(base_dir / f"{ticker}.json"))


@st.cache_data(show_spinner=False)
def load_dataset_diagnostics(dataset_root: str) -> dict[str, object]:
    dataset_path = Path(dataset_root)
    dataset_summary = load_json_optional(str(dataset_path / "dataset_summary.json"))
    manifest = load_json_optional(str(dataset_path / "buffett3_source_manifest.json"))
    normalization = load_json_optional(str(WORKSPACE_ROOT / "artifacts" / "normalized" / "normalization_summary.json"))
    validation = load_json_optional(str(WORKSPACE_ROOT / "artifacts" / "validation" / "validation_summary.json"))
    return {
        "dataset_summary": dataset_summary,
        "buffett3_manifest": manifest,
        "normalization_summary": normalization,
        "validation_summary": validation,
    }


def get_manifest_entry(manifest: dict[str, object], domain: str) -> dict[str, object]:
    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        return {}
    for entry in entries:
        if isinstance(entry, dict) and str(entry.get("domain")) == domain:
            return entry
    return {}


def build_data_diagnostic_snapshot(
    dataset: dict[str, object],
    diagnostics: dict[str, object],
    ticker: str,
) -> dict[str, object]:
    dataset_summary = diagnostics.get("dataset_summary", {})
    manifest = diagnostics.get("buffett3_manifest", {})
    validation = diagnostics.get("validation_summary", {})
    normalization = diagnostics.get("normalization_summary", {})
    monthly_revenue_df = dataset.get("monthly_revenue", pd.DataFrame()).copy()
    if not monthly_revenue_df.empty and "stock_id" in monthly_revenue_df.columns:
        monthly_revenue_df["stock_id"] = monthly_revenue_df["stock_id"].astype(str)
        ticker_monthly_rows = int((monthly_revenue_df["stock_id"] == str(ticker)).sum())
    else:
        ticker_monthly_rows = 0

    monthly_entry = get_manifest_entry(manifest, "monthly_revenue_history")
    annual_entry = get_manifest_entry(manifest, "annual_fundamentals_official")
    quarterly_entry = get_manifest_entry(manifest, "quarterly_fundamentals_official")
    valuation_entry = get_manifest_entry(manifest, "valuation_snapshot_current")
    dividend_entry = get_manifest_entry(manifest, "dividend_history")

    monthly_covered = set(str(item) for item in monthly_entry.get("covered_tickers", []) if item is not None)
    monthly_missing = set(str(item) for item in monthly_entry.get("missing_tickers", []) if item is not None)
    annual_covered = set(str(item) for item in annual_entry.get("covered_tickers", []) if item is not None)
    quarterly_covered = set(str(item) for item in quarterly_entry.get("covered_tickers", []) if item is not None)
    financial_tickers = set(str(item) for item in manifest.get("financial_tickers", []) if item is not None)
    validation_checks = validation.get("checks", [])
    warning_tables = [
        str(check.get("table"))
        for check in validation_checks
        if isinstance(check, dict) and str(check.get("status")) == "warning"
    ]
    normalization_tables = normalization.get("tables", [])
    warning_sources = [
        str(table.get("name"))
        for table in normalization_tables
        if isinstance(table, dict) and str(table.get("status")) == "warning"
    ]

    ticker_has_monthly_revenue = ticker_monthly_rows > 0
    if monthly_covered or monthly_missing:
        ticker_has_monthly_revenue = str(ticker) in monthly_covered

    top100_count = int(dataset_summary.get("summary", {}).get("top100_count", 0) or 0)
    official_statement_tickers = dataset_summary.get("buffett3_official", {}).get("official_statement_tickers", [])
    return {
        "top100_count": top100_count,
        "monthly_revenue_covered_count": len(monthly_covered),
        "monthly_revenue_missing_count": len(monthly_missing),
        "monthly_revenue_missing_tickers": sorted(monthly_missing),
        "monthly_revenue_missing_financials": sorted(ticker for ticker in monthly_missing if ticker in financial_tickers),
        "ticker_monthly_revenue_rows": ticker_monthly_rows,
        "ticker_has_monthly_revenue": ticker_has_monthly_revenue,
        "ticker_statement_route": "financial" if str(ticker) in financial_tickers else "general",
        "ticker_has_annual_statement": str(ticker) in annual_covered,
        "ticker_has_quarterly_statement": str(ticker) in quarterly_covered,
        "official_statement_ticker_count": len(set(str(item) for item in official_statement_tickers)),
        "valuation_covered_count": len(set(str(item) for item in valuation_entry.get("covered_tickers", []))),
        "dividend_covered_count": len(set(str(item) for item in dividend_entry.get("covered_tickers", []))),
        "validation_warning_tables": warning_tables,
        "normalization_warning_tables": warning_sources,
    }


@st.cache_data(show_spinner=False)
def get_price_frame(dataset_root: str, ticker: str) -> pd.DataFrame:
    price_df = read_price_history(Path(dataset_root), ticker).copy()
    price_df["Date"] = pd.to_datetime(price_df["Date"], errors="coerce")
    price_df["Close"] = pd.to_numeric(price_df["Close"], errors="coerce")
    return price_df.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def get_financial_frames(dataset_root: str, ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    annual_df = read_annual_financials(Path(dataset_root), ticker).copy()
    quarterly_df = read_quarterly_financials(Path(dataset_root), ticker).copy()
    for frame in (annual_df, quarterly_df):
        if "date" in frame.columns:
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return annual_df, quarterly_df


@st.cache_data(show_spinner=False)
def load_buffett3_payload(ticker: str) -> dict[str, object]:
    payload_path = BUFFETT3_PAYLOAD_DIR / f"{ticker}.json"
    if not payload_path.exists():
        return {}
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    normalized_inputs = payload.get("normalized_inputs", {})
    input_snapshot = payload.get("input_snapshot", {})
    if isinstance(normalized_inputs, dict) and isinstance(input_snapshot, dict):
        merged_snapshot = dict(input_snapshot)
        merged_snapshot.setdefault("normalized_eps", normalized_inputs.get("normalized_eps"))
        merged_snapshot.setdefault(
            "normalized_fcf_per_share",
            normalized_inputs.get("normalized_fcf_per_share"),
        )
        merged_snapshot.setdefault("bvps", normalized_inputs.get("normalized_bvps"))
        merged_snapshot.setdefault("normalized_roe", normalized_inputs.get("normalized_roe"))
        payload["input_snapshot"] = merged_snapshot
    compatibility_aliases = {
        "company_type": payload.get("classification"),
        "blended_fair_value": payload.get("blended_normalized_valuation"),
        "final_fair_value": payload.get("final_fair_value_per_share"),
    }
    for key, fallback_value in compatibility_aliases.items():
        if payload.get(key) is None and fallback_value is not None:
            payload[key] = fallback_value
    if payload.get("rating") is None:
        fair_value = safe_float(payload.get("final_fair_value"))
        latest_price = safe_float(
            normalized_inputs.get("latest_price") if isinstance(normalized_inputs, dict) else None
        )
        if fair_value is not None and latest_price not in {None, 0}:
            payload["rating"] = classify_value(((fair_value - latest_price) / latest_price) * 100)
    return payload


def safe_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(number):
        return None
    return number


def normalize_pct(value: object) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    if abs(number) <= 2:
        return number * 100
    return number


def fmt_currency(value: object) -> str:
    number = safe_float(value)
    if number is None:
        return "資料不足"
    return f"{number:,.2f}"


def fmt_pct(value: object) -> str:
    number = safe_float(value)
    if number is None:
        return "資料不足"
    return f"{number:+.1f}%"


def fmt_pct_plain(value: object) -> str:
    number = safe_float(value)
    if number is None:
        return "資料不足"
    return f"{number:.1f}%"


def fmt_score(value: object) -> str:
    number = safe_float(value)
    if number is None:
        return "資料不足"
    return f"{number:.1f}"


def classify_value(mos_pct: float | None) -> str:
    if mos_pct is None:
        return "資料不足"
    if mos_pct >= 25:
        return "低估"
    if mos_pct >= 10:
        return "合理偏低"
    if mos_pct >= -5:
        return "合理"
    if mos_pct >= -20:
        return "合理偏高"
    if mos_pct >= -50:
        return "昂貴"
    return "非常昂貴"


def classify_quant(score: float | None) -> str:
    if score is None:
        return "資料不足"
    if score >= 80:
        return "低估"
    if score >= 65:
        return "合理偏低"
    if score >= 50:
        return "合理"
    if score >= 40:
        return "合理偏高"
    if score >= 25:
        return "昂貴"
    return "非常昂貴"


def classify_hybrid(expected_return_pct: float | None) -> str:
    if expected_return_pct is None:
        return "資料不足"
    if expected_return_pct >= 20:
        return "低估"
    if expected_return_pct >= 8:
        return "合理偏低"
    if expected_return_pct >= -3:
        return "合理"
    if expected_return_pct >= -10:
        return "合理偏高"
    if expected_return_pct >= -20:
        return "昂貴"
    return "非常昂貴"


def badge_class(rating: str) -> str:
    return BADGE_STYLE.get(rating, "badge-muted")


def badge_rank(rating: str) -> int:
    order = {
        "badge-good": 4,
        "badge-neutral": 3,
        "badge-warm": 2,
        "badge-risk": 1,
        "badge-muted": 0,
    }
    return order.get(badge_class(rating), 0)


def compute_confidence(row: pd.Series, model_id: str) -> int:
    warning_penalty = 0
    try:
        warnings_payload = json.loads(str(row.get("data_warnings", "{}")))
        warning_penalty = len(warnings_payload.get(model_id, [])) * 8
    except Exception:
        warning_penalty = 10

    value_penalty = 0
    if model_id == "buffett_v1" and safe_float(row.get("buffett_v1_intrinsic")) is None:
        value_penalty += 35
    if model_id == "buffett_v2" and safe_float(row.get("buffett_v2_intrinsic")) is None:
        value_penalty += 35
    if model_id == "buffett3" and safe_float(row.get("buffett3_intrinsic")) is None:
        value_penalty += 35
    if model_id == "imfs" and safe_float(row.get("imfs_intrinsic")) is None:
        value_penalty += 32
    if model_id == "quant" and safe_float(row.get("quant_score")) is None:
        value_penalty += 28
    if model_id == "hybrid" and safe_float(row.get("hybrid_target")) is None:
        value_penalty += 28

    confidence = max(42, 84 - warning_penalty - value_penalty)
    return int(min(92, confidence))


def build_model_summary(model_id: str, rating: str) -> str:
    if model_id == "buffett3":
        return f"Buffett 3.0 依企業類型切換估值框架，目前評級為 {rating}。"
    if model_id == "buffett_v1":
        return f"依歷史 EPS 與保守折現框架估算內在價值，目前評級為 {rating}。"
    if model_id == "buffett_v2":
        return f"依標準化自由現金流與獲利能力交叉估值，目前評級為 {rating}。"
    if model_id == "imfs":
        return f"依 IMFS 路由與成長品質框架判讀目前價位，目前評級為 {rating}。"
    if model_id == "quant":
        return f"依台股 Buffett Quant 因子分數與操作訊號判讀，目前評級為 {rating}。"
    return f"依混合模型的預期報酬與風險權重判讀，目前評級為 {rating}。"


def build_model_basis(model_id: str) -> str:
    if model_id == "buffett3":
        return "Buffett 3.0 會依企業性質綜合本益比、股價淨值比、股利能力、自由現金流與情境權重。"
    if model_id == "buffett_v1":
        return "折價率 = (內在價值 - 現價) / 現價，主軸偏向歷史獲利與保守折現。"
    if model_id == "buffett_v2":
        return "折價率 = (內在價值 - 現價) / 現價，並提高自由現金流與資本效率的權重。"
    if model_id == "imfs":
        return "依 IMFS 路由切換 projected EPS、justified P/E 或品質分數，不同路徑代表不同估值語言。"
    if model_id == "quant":
        return "Quant 分數整合估值、品質、成長與技術條件，再轉成操作等級。"
    return "Hybrid 以綜合目標價與預期報酬為核心，結合多訊號做最終判讀。"


def format_buffett3_type(type_name: object) -> str:
    mapping = {
        "high_quality_compounder": "高品質複利股",
        "financial": "金融股",
        "cyclical": "景氣循環股",
        "defensive_dividend": "防禦收益股",
    }
    key = str(type_name or "").strip()
    return mapping.get(key, key or "無資料")


def format_buffett3_label(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "無"
    mapping = {
        "normalized_pe": "標準化本益比",
        "fcf_yield": "自由現金流殖利率",
        "residual_earnings": "剩餘盈餘",
        "dividend_yield_or_ddm": "股利殖利率或 DDM",
        "roe_adjusted_pb": "ROE 調整後股價淨值比",
        "ddm": "股利折現模型",
        "residual_income": "剩餘收益",
        "mid_cycle_eps": "景氣中樞 EPS",
        "normalized_ev_ebitda": "標準化 EV/EBITDA",
        "replacement_asset_value": "重置或資產價值",
        "trough_pb_downside": "景氣谷底 PB",
        "macro_regime_modifier": "總體環境修正",
        "taiwan_risk_modifier": "台灣風險修正",
        "reality_validation_modifier": "現實驗證修正",
        "supportive": "偏正向",
        "neutral": "中性",
        "supported": "資料支持",
        "strained": "營運承壓",
        "headwind": "逆風",
        "insufficient_data": "資料不足",
        "mixed_index_trend": "指數趨勢混合",
        "mixed_or_missing_operating_signals": "營運訊號混合或不足",
        "default_country_risk_haircut": "預設國家風險折減",
        "latest_above_50d_and_200d_trend": "指數位於 50 日與 200 日均線上方",
        "latest_below_50d_and_200d_trend": "指數位於 50 日與 200 日均線下方",
        "v1_uses_conservative_taiwan_risk_discount": "V1 採保守台灣風險折減",
        "latest_quarter_eps_positive,monthly_revenue_yoy_supportive": "最新季 EPS 為正且月營收年增支持",
        "latest_quarter_eps_positive": "最新季 EPS 為正",
        "monthly_revenue_yoy_supportive": "月營收年增支持",
        "monthly_revenue_yoy_weak": "月營收年增偏弱",
        "current_ratio_below_1": "流動比率低於 1",
        "high_debt_to_equity": "負債權益比偏高",
        "latest_eps_below_3y_average": "最新 EPS 低於 3 年平均",
        "negative_average_fcf": "平均自由現金流為負",
        "leg_has_missing_required_inputs": "必要輸入不足",
        "negative_equity_leg_value_floored_to_zero": "負值股權支線已保守下限為 0",
        "v1_keeps_ev_ebitda_visible_but_uncomputed": "EV/EBITDA 支線先保留可見但暫不估值",
        "some_valuation_legs_not_ready": "部分估值支線尚未就緒",
        "cyclical_ev_ebitda_not_ready_without_clean_ebitda": "景氣股缺少乾淨 EBITDA，EV/EBITDA 支線暫停",
        "cyclical_model_uses_partial_leg_set": "景氣股目前只用部分支線估值",
        "valuation_weights_reallocated_over_ready_legs": "權重已重新分配到可用支線",
        "current_ratio_missing": "流動比率缺失",
        "debt_to_equity_missing": "負債權益比缺失",
        "bvps_missing": "每股淨值缺失",
        "normalized_eps_missing": "標準化 EPS 缺失",
        "dividend_history_missing_or_proxy_used": "股利歷史不足或改用代理值",
        "dividend_leg_proxy_used": "股利支線使用代理值",
        "industry_matches_compounder_rules": "產業特徵符合高品質複利股規則",
        "industry_matches_cyclical_rules": "產業特徵符合景氣循環股規則",
        "industry_exact_matches_cyclical_bucket": "精確產業桶符合景氣循環股規則",
        "industry_exact_matches_defensive_bucket": "精確產業桶符合防禦收益股規則",
        "industry_or_ticker_matches_financial_rules": "產業或代號符合金融股規則",
        "ticker_matches_cyclical_override": "明確代號覆寫為景氣循環股",
        "defaulted_to_compounder_rule": "無明確特殊規則，預設歸入高品質複利股",
        "total_debt_missing_in_source_tables": "來源表缺少總負債數列",
        "cash_and_equivalents_missing_in_source_tables": "來源表缺少現金及約當現金數列",
        "clean_ebitda_series_not_available_in_current_dataset": "目前資料集沒有可直接驗證的乾淨 EBITDA 數列",
    }
    if text in mapping:
        return mapping[text]
    if "," in text:
        parts = [part.strip() for part in text.split(",") if part.strip()]
        if len(parts) > 1:
            return "、".join(format_buffett3_label(part) for part in parts)
    return text.replace("_", " ")


def format_buffett3_modifier(modifier: object) -> str:
    number = safe_float(modifier)
    if number is None:
        return "無"
    return f"{number:.2f}x"


def join_buffett3_labels(values: object) -> str:
    if values is None:
        return "無"
    if isinstance(values, list):
        labels = [format_buffett3_label(item) for item in values if str(item or "").strip()]
        return "、".join(labels) if labels else "無"
    text = str(values).strip()
    if not text:
        return "無"
    if "," in text:
        parts = [part.strip() for part in text.split(",") if part.strip()]
        if len(parts) > 1:
            return "、".join(format_buffett3_label(part) for part in parts)
    return format_buffett3_label(text)


def chunked(items: list[object], size: int) -> list[list[object]]:
    if size <= 0:
        return [items]
    return [items[index:index + size] for index in range(0, len(items), size)]


def choose_focus_model(active_models: list[str], current: object = None) -> str:
    valid_models = [model_id for model_id in active_models if model_id in MODEL_META]
    if not valid_models:
        return MODEL_ORDER[0]
    current_text = str(current or "").strip()
    if current_text in valid_models:
        return current_text
    if "buffett3" in valid_models:
        return "buffett3"
    return valid_models[0]


def get_model_payload(row: pd.Series, model_id: str) -> dict[str, object]:
    price = safe_float(row.get("price"))
    summary = None
    basis = None
    fair_label = "內在價值"
    value_label = MODEL_META[model_id]["value_label"]

    if model_id == "buffett_v1":
        fair_value = safe_float(row.get("buffett_v1_intrinsic"))
        gap = normalize_pct(row.get("buffett_v1_mos"))
        rating = classify_value(gap)
        signal = str(row.get("buffett_v1_signal", ""))
        metric_text = fmt_pct(gap)
        fair_text = fmt_currency(fair_value)
    elif model_id == "buffett_v2":
        fair_value = safe_float(row.get("buffett_v2_intrinsic"))
        gap = normalize_pct(row.get("buffett_v2_mos"))
        rating = classify_value(gap)
        signal = str(row.get("buffett_v2_signal", ""))
        metric_text = fmt_pct(gap)
        fair_text = fmt_currency(fair_value)
    elif model_id == "buffett3":
        buffett3_payload = load_buffett3_payload(str(row.get("ticker", "")))
        fair_value = safe_float(row.get("buffett3_intrinsic"))
        if fair_value is None:
            fair_value = safe_float(buffett3_payload.get("final_fair_value"))
        gap = normalize_pct(row.get("buffett3_mos"))
        if gap is None and fair_value is not None and price not in {None, 0}:
            gap = ((fair_value - price) / price) * 100
        rating = classify_value(gap)
        if gap is None and buffett3_payload.get("rating"):
            rating = str(buffett3_payload.get("rating"))
        signal = str(row.get("buffett3_signal", ""))
        metric_text = fmt_pct(gap)
        fair_text = fmt_currency(fair_value)
        fair_label = "合理價"
        buffett3_type = format_buffett3_type(
            row.get("buffett3_type")
            or buffett3_payload.get("company_type")
            or buffett3_payload.get("classification")
        )
        summary = f"Buffett 3.0 將此標的歸為「{buffett3_type}」，並用對應框架估算內在價值與安全邊際。"
        basis = "資料來自 buffett3_* 官方優先資料表，並依公司類型套用不同的標準化與估值權重。"
    elif model_id == "imfs":
        fair_value = safe_float(row.get("imfs_intrinsic"))
        gap = normalize_pct(row.get("imfs_gap_pct"))
        imfs_model = str(row.get("imfs_model", ""))
        imfs_route = str(row.get("imfs_route", ""))
        quality_score = safe_float(row.get("imfs_quality_score"))
        premium_eligible = row.get("imfs_premium_eligible")
        est_growth = safe_float(row.get("imfs_est_revenue_growth_pct"))
        est_margin = safe_float(row.get("imfs_est_profit_margin_pct"))
        justified_pe = safe_float(row.get("imfs_justified_pe"))
        value_label = "估值折價"
        if fair_value is None and gap is None and imfs_model == "RULE_OF_40" and imfs_route == "B":
            rating = "資料不足"
            value_label = "品質分數" if quality_score is not None else "路由狀態"
            metric_text = fmt_score(quality_score) if quality_score is not None else "品質訊號模式"
            fair_text = "不提供內在價值"
            fair_label = "估值輸出"
            summary = "IMFS Route B / Rule of 40 目前走品質訊號模式，因此只輸出品質分數，不強制給出內在價值。"
            basis = "這是 IMFS Route B 的正常設計；當 quality score only 路徑成立時，重點在成長與獲利品質，而不是單一目標價。"
        elif imfs_model == "RULE_OF_40" and imfs_route == "B":
            rating = classify_value(gap)
            value_label = "品質分數" if quality_score is not None else "估值折價"
            metric_text = fmt_score(quality_score) if quality_score is not None else fmt_pct(gap)
            fair_text = fmt_currency(fair_value)
            fair_label = "合理價"
            premium_text = "可給溢價" if str(premium_eligible).lower() == "true" else "不給溢價"
            growth_text = fmt_pct_plain(est_growth)
            margin_text = fmt_pct_plain(est_margin)
            pe_text = fmt_score(justified_pe)
            summary = (
                f"IMFS Route B / Rule of 40 品質分數 {fmt_score(quality_score)}，"
                f"營收成長 {growth_text}、利潤率 {margin_text}，{premium_text}。"
            )
            basis = f"此路徑以 projected EPS 與 justified P/E 建立合理價，當前 justified P/E = {pe_text}。"
        else:
            rating = classify_value(gap)
            metric_text = fmt_pct(gap)
            fair_text = fmt_currency(fair_value)
        signal = str(row.get("imfs_signal", ""))
    elif model_id == "quant":
        fair_value = None
        gap = safe_float(row.get("quant_score"))
        rating = classify_quant(gap)
        signal = str(row.get("quant_signal", ""))
        metric_text = fmt_score(gap)
        fair_text = str(row.get("quant_action", "未提供"))
        fair_label = "操作建議"
    else:
        fair_value = safe_float(row.get("hybrid_target"))
        gap = safe_float(row.get("hybrid_return_pct"))
        rating = classify_hybrid(gap)
        signal = str(row.get("hybrid_signal", ""))
        metric_text = fmt_pct(gap)
        fair_text = fmt_currency(fair_value)
        fair_label = "目標價"

    return {
        "model_id": model_id,
        "name": MODEL_META[model_id]["label"],
        "short_name": MODEL_META[model_id]["short_label"],
        "symbol": MODEL_META[model_id]["symbol"],
        "color": MODEL_META[model_id]["color"],
        "value_label": value_label,
        "gap_value": gap,
        "gap_text": metric_text,
        "fair_value_text": fair_text,
        "fair_label": fair_label,
        "current_price_text": fmt_currency(price),
        "price": price,
        "fair_value": fair_value,
        "rating": rating,
        "signal": signal,
        "confidence": compute_confidence(row, model_id),
        "summary": summary if summary is not None else build_model_summary(model_id, rating),
        "basis": basis if basis is not None else build_model_basis(model_id),
    }


def count_warning_items(row: pd.Series, active_models: list[str]) -> int:
    try:
        warnings_payload = json.loads(str(row.get("data_warnings", "{}")))
    except Exception:
        return 0
    return sum(len(warnings_payload.get(model_id, [])) for model_id in active_models)


def build_dashboard_snapshot(
    row: pd.Series,
    active_models: list[str],
    dataset: dict[str, object],
    dataset_summary: dict[str, object],
    updated_at: str,
    diagnostics: dict[str, object] | None = None,
    ticker: str | None = None,
) -> dict[str, object]:
    payloads = [get_model_payload(row, model_id) for model_id in active_models]
    ranked_payloads = sorted(
        payloads,
        key=lambda payload: (badge_rank(str(payload["rating"])), int(payload["confidence"])),
        reverse=True,
    )
    best_payload = ranked_payloads[0]
    good_count = sum(1 for payload in payloads if badge_class(str(payload["rating"])) == "badge-good")
    risk_count = sum(1 for payload in payloads if badge_class(str(payload["rating"])) in {"badge-warm", "badge-risk"})
    average_confidence = round(sum(int(payload["confidence"]) for payload in payloads) / len(payloads))
    warning_count = count_warning_items(row, active_models)
    monthly_revenue_rows = int(dataset_summary.get("summary", {}).get("monthly_revenue_rows", 0) or 0)
    diagnostic_snapshot = {}
    if diagnostics and ticker:
        diagnostic_snapshot = build_data_diagnostic_snapshot(
            dataset,
            diagnostics,
            ticker,
        )
    return {
        "best_payload": best_payload,
        "good_count": good_count,
        "risk_count": risk_count,
        "average_confidence": average_confidence,
        "warning_count": warning_count,
        "monthly_revenue_rows": monthly_revenue_rows,
        "updated_at": updated_at or "未提供",
        "data_diagnostic_snapshot": diagnostic_snapshot,
    }


def render_sparkline(price_series: pd.Series, color: str) -> str:
    series = pd.to_numeric(price_series, errors="coerce").dropna().tail(40)
    if series.empty:
        return '<div class="chart-caption">價格資料不足</div>'
    series = series.reset_index(drop=True)
    series_min = float(series.min())
    series_max = float(series.max())
    spread = max(series_max - series_min, max(abs(series_max), 1.0) * 0.01)
    pad = spread * 0.22
    floor = series_min - pad * 0.35
    fig, ax = plt.subplots(figsize=(3.1, 1.05), dpi=180)
    ax.plot(series.index, series.values, color=color, linewidth=1.9)
    ax.fill_between(series.index, series.values, floor, color=color, alpha=0.16)
    ax.set_ylim(series_min - pad, series_max + pad)
    ax.margins(x=0.01, y=0.0)
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", transparent=True, dpi=180, pad_inches=0)
    plt.close(fig)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f'<div class="sparkline-shell"><img src="data:image/png;base64,{encoded}" alt="model sparkline"></div>'


def render_detail_chart(price_df: pd.DataFrame, reference_value: float | None, color: str) -> None:
    chart_df = price_df.tail(150).copy()
    if chart_df.empty:
        st.info("缺少足夠價格資料，無法繪製圖表。")
        return

    chart_df["Open"] = pd.to_numeric(chart_df.get("Open", chart_df["Close"]), errors="coerce")
    chart_df["High"] = pd.to_numeric(chart_df.get("High", chart_df["Close"]), errors="coerce")
    chart_df["Low"] = pd.to_numeric(chart_df.get("Low", chart_df["Close"]), errors="coerce")
    chart_df["Close"] = pd.to_numeric(chart_df["Close"], errors="coerce")
    chart_df["Volume"] = pd.to_numeric(chart_df.get("Volume", 0), errors="coerce").fillna(0)
    chart_df = chart_df.dropna(subset=["Date", "Open", "High", "Low", "Close"]).reset_index(drop=True)
    if chart_df.empty:
        st.info("缺少足夠價格資料，無法繪製圖表。")
        return

    closes = chart_df["Close"]
    x_values = range(len(chart_df))
    rolling = closes.rolling(20, min_periods=5).mean()
    rolling_std = closes.rolling(20, min_periods=5).std()
    upper_band = rolling + rolling_std
    lower_band = rolling - rolling_std

    fig, (ax, volume_ax) = plt.subplots(
        2,
        1,
        figsize=(9.0, 4.75),
        dpi=190,
        sharex=True,
        gridspec_kw={"height_ratios": [4.2, 1.0], "hspace": 0.03},
    )

    up_color = "#40c982"
    down_color = "#e05a4f"
    wick_color = "#8aa299"
    body_width = 0.56
    for idx, candle in chart_df.iterrows():
        open_price = float(candle["Open"])
        close_price = float(candle["Close"])
        high_price = float(candle["High"])
        low_price = float(candle["Low"])
        candle_color = up_color if close_price >= open_price else down_color
        ax.vlines(idx, low_price, high_price, color=wick_color, linewidth=0.65, alpha=0.62)
        body_bottom = min(open_price, close_price)
        body_height = abs(close_price - open_price)
        if body_height == 0:
            body_height = max(closes.std(skipna=True) * 0.015, close_price * 0.001)
        ax.add_patch(
            plt.Rectangle(
                (idx - body_width / 2, body_bottom),
                body_width,
                body_height,
                facecolor=candle_color,
                edgecolor=candle_color,
                linewidth=0.45,
                alpha=0.9,
            )
        )

    ax.plot(x_values, closes, color=color, linewidth=1.25, alpha=0.92, label="收盤價")
    ax.plot(x_values, rolling, color="#e5c778", linewidth=1.15, linestyle="--", label="20日均線 / 估值中線")
    ax.fill_between(x_values, lower_band, upper_band, color="#24584e", alpha=0.30, label="波動帶")
    if reference_value is not None:
        ax.axhline(reference_value, color="#e3bf71", linestyle="--", linewidth=1.25, label="內在價值 / 目標價")
        ax.axhline(reference_value * 0.85, color="#7fd6a4", linestyle=":", linewidth=1.0, alpha=0.78, label="安全邊際下緣")
        ax.axhline(reference_value * 1.10, color="#d98f5f", linestyle=":", linewidth=1.0, alpha=0.78, label="安全邊際上緣")

    volume_colors = [up_color if close >= open_ else down_color for open_, close in zip(chart_df["Open"], chart_df["Close"])]
    volume_ax.bar(x_values, chart_df["Volume"] / 1_000_000, color=volume_colors, width=0.58, alpha=0.34, label="成交量")

    tick_count = min(6, len(chart_df))
    tick_positions = [round(i * (len(chart_df) - 1) / max(tick_count - 1, 1)) for i in range(tick_count)]
    tick_labels = [chart_df.loc[pos, "Date"].strftime("%Y/%m") for pos in tick_positions]
    volume_ax.set_xticks(tick_positions)
    volume_ax.set_xticklabels(tick_labels)

    latest_close = closes.iloc[-1]
    ax.text(
        0.012,
        0.96,
        f"價格走勢與估值區間　最新收盤 {fmt_currency(latest_close)}",
        transform=ax.transAxes,
        color="#f5efe4",
        fontsize=9.5,
        fontweight="bold",
        va="top",
    )

    for axis in (ax, volume_ax):
        axis.set_facecolor("#0d1515")
        axis.grid(True, axis="y", linestyle="--", linewidth=0.45, alpha=0.22, color="#6b8577")
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_color("#40534d")
        axis.spines["bottom"].set_color("#40534d")
        axis.tick_params(axis="x", labelsize=7.4, colors="#93a39b")
        axis.tick_params(axis="y", labelsize=7.4, colors="#93a39b")

    ax.legend(frameon=False, fontsize=7.4, loc="upper left", bbox_to_anchor=(0.0, 0.89), labelcolor="#b8c9c0")
    volume_ax.set_ylabel("百萬股", fontsize=7.2, color="#93a39b")
    ax.margins(x=0.01)
    volume_ax.margins(x=0.01)
    fig.patch.set_facecolor("#0d1515")
    fig.subplots_adjust(left=0.08, right=0.985, top=0.965, bottom=0.13)

    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", facecolor="#0d1515", dpi=190)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    plt.close(fig)
    st.markdown(
        (
            '<div class="chart-shell">'
            f'<img src="data:image/png;base64,{encoded}" style="width:100%; display:block;" alt="估值走勢圖">'
            '<div class="chart-caption">圖表狀態：非即時串流；每次重跑或切換股票時，依目前載入的最新價格資料重繪。安全邊際區間僅供研究判讀，不代表保證報酬。</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def build_key_metrics(dataset_root: str, ticker: str) -> pd.DataFrame:
    annual_df, quarterly_df = get_financial_frames(dataset_root, ticker)
    annual_df = annual_df.sort_values("date", ascending=False)
    quarterly_df = quarterly_df.sort_values("date", ascending=False)

    annual_valid = annual_df.dropna(subset=["date"]).copy()
    latest_annual = annual_valid.iloc[0] if not annual_valid.empty else pd.Series(dtype=object)

    quarterly_valid = quarterly_df.dropna(subset=["date"]).copy()
    for column in [
        "revenue",
        "net_income",
        "operating_cash_flow",
        "free_cash_flow",
        "eps",
        "roe",
        "book_value_per_share",
    ]:
        if column in quarterly_valid.columns:
            quarterly_valid[column] = pd.to_numeric(quarterly_valid[column], errors="coerce")
    ttm = quarterly_valid.head(4)

    revenue_ttm = ttm["revenue"].sum(min_count=1) if "revenue" in ttm else None
    net_income_ttm = ttm["net_income"].sum(min_count=1) if "net_income" in ttm else None
    ocf_ttm = ttm["operating_cash_flow"].sum(min_count=1) if "operating_cash_flow" in ttm else None
    fcf_ttm = ttm["free_cash_flow"].sum(min_count=1) if "free_cash_flow" in ttm else None
    eps_ttm = ttm["eps"].sum(min_count=1) if "eps" in ttm else None
    margin_ttm = None
    if safe_float(revenue_ttm) not in (None, 0) and safe_float(net_income_ttm) is not None:
        margin_ttm = float(net_income_ttm / revenue_ttm * 100)

    rows = [
        ("ROE（最新年度）", fmt_pct_plain(latest_annual.get("roe"))),
        ("EPS（近四季）", fmt_currency(eps_ttm)),
        ("淨利率（TTM）", fmt_pct_plain(margin_ttm)),
        ("營收（TTM）", fmt_currency(revenue_ttm)),
        ("營業現金流（TTM）", fmt_currency(ocf_ttm)),
        ("自由現金流（TTM）", fmt_currency(fcf_ttm)),
        ("每股淨值（最新年度）", fmt_currency(latest_annual.get("book_value_per_share"))),
    ]
    return pd.DataFrame(rows, columns=["關鍵指標", "數值"])


def render_key_metrics_panel(metrics_df: pd.DataFrame) -> None:
    rows_html = []
    for _, metric in metrics_df.iterrows():
        rows_html.append(
            '<div class="key-metric-row">'
            f'<div class="key-metric-name">{escape(str(metric["關鍵指標"]))}</div>'
            f'<div class="key-metric-value">{escape(str(metric["數值"]))}</div>'
            "</div>"
        )
    st.markdown(
        (
            '<div class="key-metric-table">'
            '<h3 style="margin:0 0 0.65rem 0;">關鍵指標（TTM）</h3>'
            f'{"".join(rows_html)}'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_rating_thresholds() -> None:
    lines = [
        ("低估", "折價 >= 25%"),
        ("合理偏低", "10% 至 25%"),
        ("合理", "-5% 至 10%"),
        ("合理偏高", "-20% 至 -5%"),
        ("昂貴", "-50% 至 -20%"),
        ("非常昂貴", "<= -50%"),
    ]
    rows = []
    for label, threshold in lines:
        rows.append(
            '<div class="threshold-line">'
            f'<span><span class="badge {badge_class(label)}">{label}</span></span>'
            f"<span>{threshold}</span>"
            "</div>"
        )
    st.markdown(
        (
            '<div class="side-surface">'
            '<h2 style="margin-top:0;">評級說明</h2>'
            '<div class="rail-copy">價值型模型採折價率；Quant 與 Hybrid 會在模型解釋頁顯示各自門檻。</div>'
            f'<div style="margin-top:0.75rem;">{"".join(rows)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_rules_table(title: str, rows: list[tuple[str, str, str]]) -> None:
    st.markdown(f"#### {title}")
    st.caption("以下門檻用來把模型輸出映射成一致的儀表板評級，方便橫向比較。")
    rules_df = pd.DataFrame(rows, columns=["標籤", "判準", "說明"])
    st.dataframe(rules_df.astype(str), width="stretch", hide_index=True)


def render_reference_tab(diagnostics: dict[str, object], data_snapshot: dict[str, object]) -> None:
    st.markdown("#### 模型參考總覽")
    st.caption("整理各模型的計算邏輯、主要輸入、資料來源與輸出，方便快速理解整個研究頁的估值語言。")
    st.dataframe(pd.DataFrame(MODEL_REFERENCE_ROWS).astype(str), width="stretch", hide_index=True)

    st.markdown("#### IMFS Route 對照")
    route_rows = pd.DataFrame(
        [
            {"Route": "A", "模型": "EPV", "邏輯": "成熟企業，以 earnings power value 估值。"},
            {"Route": "B", "模型": "RULE_OF_40", "邏輯": "高成長企業，原始 IMFS 先做品質打分；本專案再橋接每股合理價。"},
            {"Route": "C", "模型": "ROE_PB", "邏輯": "金融或類金融企業，以 ROE / PB 框架估值。"},
            {"Route": "D", "模型": "NORMALIZED_PE", "邏輯": "循環或半導體類型，以 normalized P/E 估值。"},
        ]
    )
    st.dataframe(route_rows.astype(str), width="stretch", hide_index=True)

    st.markdown("#### 目前整合原則")
    st.write("1. 先用各模型原始邏輯或原始核心函式跑出結果。")
    st.write("2. 再把不同模型輸出映射到同一個儀表板欄位，例如內在價值、折價、信心度與評級。")
    st.write("3. 若原始模型只有品質訊號、沒有每股合理價，才在整合層補上橋接邏輯，並在說明中明確標示。")

    manifest = diagnostics.get("buffett3_manifest", {})
    validation = diagnostics.get("validation_summary", {})
    normalization = diagnostics.get("normalization_summary", {})
    source_rows = [
        {
            "資料域": "Buffett 3.0 估值快照",
            "覆蓋": f"{data_snapshot.get('valuation_covered_count', 0)} / {data_snapshot.get('top100_count', 0)}",
            "來源": "TWSE BWIBBU_ALL",
            "備註": "目前為單日 snapshot，尚非歷史估值序列。",
        },
        {
            "資料域": "Buffett 3.0 股利歷史",
            "覆蓋": f"{data_snapshot.get('dividend_covered_count', 0)} / {data_snapshot.get('top100_count', 0)}",
            "來源": "TWSE t187ap45_L",
            "備註": "已寫入可重用的 dividend history 資料表。",
        },
        {
            "資料域": "Buffett 3.0 月營收",
            "覆蓋": f"{data_snapshot.get('monthly_revenue_covered_count', 0)} / {data_snapshot.get('top100_count', 0)}",
            "來源": "TWSE t187ap05_L",
            "備註": (
                f"目前缺 {data_snapshot.get('monthly_revenue_missing_count', 0)} 檔，"
                f"實際缺口為 {'、'.join(data_snapshot.get('monthly_revenue_missing_financials', [])) or '無'}。"
            ),
        },
        {
            "資料域": "Buffett 3.0 官方/回退財報",
            "覆蓋": f"{data_snapshot.get('official_statement_ticker_count', 0)} / {data_snapshot.get('top100_count', 0)} 官方財報路由",
            "來源": "TWSE statements + yfinance fallback",
            "備註": "年報與季報已做 financial / general 分流；不足處由 fallback 補齊。",
        },
    ]
    st.markdown("#### 資料來源覆蓋")
    st.caption("以下覆蓋率直接來自本機 `buffett3_source_manifest.json`，不是手寫說明。")
    st.dataframe(pd.DataFrame(source_rows).astype(str), width="stretch", hide_index=True)

    validation_rows = []
    for check in validation.get("checks", []):
        if not isinstance(check, dict):
            continue
        validation_rows.append(
            {
                "檢查表": str(check.get("table", "")),
                "狀態": str(check.get("status", "")),
                "重點": " / ".join(str(note) for note in check.get("notes", [])) or "無",
            }
        )
    for table in normalization.get("tables", []):
        if not isinstance(table, dict):
            continue
        validation_rows.append(
            {
                "檢查表": f"{table.get('name', '')}（normalize）",
                "狀態": str(table.get("status", "")),
                "重點": " / ".join(str(note) for note in table.get("notes", [])) or "無",
            }
        )
    if validation_rows:
        st.markdown("#### 正規化 / 驗證摘要")
        st.caption("顯示目前共享資料層已知的真實限制，例如 snapshot-only 或缺少 fiscal period。")
        st.dataframe(pd.DataFrame(validation_rows).astype(str), width="stretch", hide_index=True)
    if manifest:
        st.caption(f"來源清單檔案：{manifest.get('generated_at', '未提供')} 生成")


def render_warning_panel(warnings_payload: dict[str, object], active_models: list[str]) -> None:
    st.markdown("#### 風險與資料警示")
    st.caption("先確認資料缺口與降級情況，再決定是否要把目前輸出視為可直接比較的估值結論。")

    cards: list[str] = []
    for model_id in active_models:
        entries = warnings_payload.get(model_id, [])
        if not isinstance(entries, list) or not entries:
            continue
        payload = MODEL_META[model_id]
        body = "、".join(str(entry) for entry in entries)
        cards.append(
            '<div class="warning-card">'
            f'<div class="warning-card-title">{escape(str(payload["label"]))}</div>'
            f'<div class="warning-card-copy">{escape(body)}</div>'
            "</div>"
        )

    if cards:
        st.markdown(f'<div class="warning-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="warning-card"><div class="warning-card-title">目前未發現額外警示</div>'
            '<div class="warning-card-copy">此標的在目前啟用模型下沒有額外資料警示，可優先回到估值與模型解釋區閱讀。</div></div>',
            unsafe_allow_html=True,
        )


def format_final_module_confidence(value: object) -> str:
    mapping = {
        "low": "\u4f4e",
        "medium": "\u4e2d",
        "medium_high": "\u4e2d\u9ad8",
        "high": "\u9ad8",
        "\u4f4e": "\u4f4e",
        "\u4e2d": "\u4e2d",
        "\u4e2d\u9ad8": "\u4e2d\u9ad8",
        "\u9ad8": "\u9ad8",
    }
    text = str(value or "").strip().lower()
    return mapping.get(text, "\u8cc7\u6599\u4e0d\u8db3")


def render_final_module_panel(ticker: str) -> None:
    commentary_payload = load_final_module_payload(ticker, "final_commentary")
    independent_payload = load_final_module_payload(ticker, "independent_ai")

    if not commentary_payload or not independent_payload:
        st.info("\u6700\u7d42 AI \u8a55\u8ad6\u6a21\u7d44\u5c1a\u672a\u751f\u6210\u5b8c\u6574 payload\u3002")
        return

    final_conclusion = commentary_payload.get("final_conclusion", {})
    independent_snapshot = commentary_payload.get("independent_ai_snapshot", {})
    internal_snapshot = commentary_payload.get("internal_model_snapshot", {})
    news_snapshot = commentary_payload.get("news_snapshot", {})
    divergence_snapshot = commentary_payload.get("public_vs_institution_snapshot", {})
    risk_summary = commentary_payload.get("risk_summary", [])
    change_view_conditions = commentary_payload.get("change_view_conditions", [])

    st.markdown("### \u6700\u7d42 AI \u7d50\u8ad6")
    hero_cols = st.columns(3, gap="medium")
    with hero_cols[0]:
        st.markdown(
            dedent(
                f"""
                <div class="metric-shell">
                    <h3>\u6700\u7d42\u4f30\u503c</h3>
                    <div class="metric-value">{escape(str(final_conclusion.get('valuation_label', '-')))}</div>
                    <div class="detail-stat"><span>\u5efa\u8b70</span><strong>{escape(str(final_conclusion.get('action_label', '-')))}</strong></div>
                    <div class="detail-stat"><span>\u4fe1\u5fc3</span><strong>{escape(format_final_module_confidence(independent_snapshot.get('confidence')))}</strong></div>
                </div>
                """
            ).strip(),
            unsafe_allow_html=True,
        )
    with hero_cols[1]:
        st.markdown(
            dedent(
                f"""
                <div class="metric-shell">
                    <h3>\u7368\u7acb AI \u5408\u7406\u50f9</h3>
                    <div class="metric-value">{escape(str(independent_snapshot.get('base_fair_value', '-')))}</div>
                    <div class="detail-stat"><span>\u5408\u7406\u5340\u9593</span><strong>{escape(str(independent_snapshot.get('fair_value_range', '-')))}</strong></div>
                    <div class="detail-stat"><span>\u65b9\u6cd5</span><strong>{escape(str(independent_payload.get('valuation_method_primary', '-')))}</strong></div>
                </div>
                """
            ).strip(),
            unsafe_allow_html=True,
        )
    with hero_cols[2]:
        st.markdown(
            dedent(
                f"""
                <div class="metric-shell">
                    <h3>\u5e02\u5834\u89c0\u9ede</h3>
                    <div class="metric-label">\u65b0\u805e\u60c5\u7dd2</div>
                    <div class="metric-value" style="font-size:1.6rem;">{escape(str(news_snapshot.get('sentiment', '-')))}</div>
                    <div class="detail-stat"><span>\u516c\u773e vs \u6cd5\u4eba</span><strong>{escape(str(divergence_snapshot.get('divergence', '-')))}</strong></div>
                </div>
                """
            ).strip(),
            unsafe_allow_html=True,
        )

    st.markdown(
        dedent(
            f"""
            <div class="model-summary-strip">
                <strong>\u6838\u5fc3\u7d50\u8ad6</strong> | {escape(str(final_conclusion.get('summary', '-')))}
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )

    compare_cols = st.columns([1.45, 1.1], gap="large")
    with compare_cols[0]:
        st.markdown("#### \u5167\u90e8\u6a21\u578b\u6bd4\u8f03")
        compare_rows = []
        model_order = ["buffett3", "imfs", "hybrid", "quant"]
        model_labels = {"buffett3": "Buffett 3.0", "imfs": "IMFS", "hybrid": "Hybrid", "quant": "Quant"}
        for model_id in model_order:
            snapshot = internal_snapshot.get(model_id, {})
            if not isinstance(snapshot, dict) or not snapshot:
                continue
            compare_rows.append(
                {
                    "\u6a21\u578b": model_labels[model_id],
                    "\u7d50\u8ad6": str(snapshot.get("conclusion", "-")),
                    "\u52d5\u4f5c": str(snapshot.get("action", "-")),
                    "\u8aaa\u660e": str(snapshot.get("comment", "-")),
                }
            )
        if compare_rows:
            st.dataframe(pd.DataFrame(compare_rows).astype(str), width="stretch", hide_index=True)
        st.markdown("#### \u6a21\u578b\u5dee\u7570\u89e3\u91cb")
        st.write(str(commentary_payload.get("model_difference_explanation", "-")))

    with compare_cols[1]:
        st.markdown("#### \u7368\u7acb AI \u908f\u8f2f")
        st.write(str(independent_payload.get("reasoning_summary", "-")))
        st.write(str(independent_payload.get("calculation_logic_summary", "-")))
        assumption_rows = independent_payload.get("key_assumptions", [])
        if isinstance(assumption_rows, list) and assumption_rows:
            st.markdown("#### \u95dc\u9375\u5047\u8a2d")
            for item in assumption_rows:
                st.markdown(f"- {item}")

    market_cols = st.columns(2, gap="large")
    with market_cols[0]:
        st.markdown("#### \u65b0\u805e\u8207\u5e02\u5834\u89c0\u9ede")
        st.write(str(news_snapshot.get("summary", "-")))
        st.write(str(news_snapshot.get("comment", "-")))
    with market_cols[1]:
        st.markdown("#### \u516c\u773e vs \u6cd5\u4eba")
        st.markdown(f"**\u516c\u773e\u89c0\u9ede**：{divergence_snapshot.get('public_view', '-')}")
        st.markdown(f"**\u6cd5\u4eba\u89c0\u9ede**：{divergence_snapshot.get('institution_view', '-')}")
        st.markdown(f"**\u5206\u6b67**：{divergence_snapshot.get('divergence', '-')}")

    footer_cols = st.columns(2, gap="large")
    with footer_cols[0]:
        st.markdown("#### \u4e3b\u8981\u98a8\u96aa")
        if isinstance(risk_summary, list) and risk_summary:
            for item in risk_summary:
                st.markdown(f"- {item}")
        else:
            st.write("-")
    with footer_cols[1]:
        st.markdown("#### \u4ec0\u9ebc\u60c5\u6cc1\u4e0b\u6703\u8abf\u6574\u770b\u6cd5")
        if isinstance(change_view_conditions, list) and change_view_conditions:
            for item in change_view_conditions:
                st.markdown(f"- {item}")
        else:
            st.write("-")


def render_dashboard_band(snapshot: dict[str, object], active_models: list[str], price_text: str) -> None:
    best_payload = snapshot["best_payload"]
    data_snapshot = snapshot.get("data_diagnostic_snapshot", {})
    top100_count = data_snapshot.get("top100_count", 0)
    if top100_count:
        data_status_value = (
            f"{data_snapshot.get('monthly_revenue_covered_count', 0)} / {top100_count}"
        )
        data_status_note = "官方月營收覆蓋"
    else:
        data_status_value = "未提供"
        data_status_note = str(snapshot["updated_at"])
    cards = [
        ("目前股價", price_text, "最新收盤價"),
        ("啟用模型", f"{len(active_models)} / {len(MODEL_ORDER)}", "總覽與單模型區同步更新"),
        ("最佳評級", str(best_payload["rating"]), str(best_payload["name"])),
        ("平均信心", f"{snapshot['average_confidence']}%", f"警示項目 {snapshot['warning_count']} 筆"),
        ("資料狀態", data_status_value, data_status_note),
    ]
    html_parts = ['<div class="stat-band">']
    for label, value, note in cards:
        html_parts.append(
            '<div class="stat-card">'
            f'<div class="stat-label">{escape(str(label))}</div>'
            f'<div class="stat-value">{escape(str(value))}</div>'
            f'<div class="stat-note">{escape(str(note))}</div>'
            "</div>"
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_consensus_panel(snapshot: dict[str, object]) -> None:
    st.markdown(
        dedent(f"""
        <div class="side-surface">
            <h2 style="margin-top:0;">共識速覽</h2>
            <div class="rail-copy">先看整體共識，再決定要不要深入單一模型的估值依據與警示內容。</div>
            <div class="side-list">
                <div class="side-list-row"><span>最佳模型</span><span>{escape(str(snapshot['best_payload']['name']))}</span></div>
                <div class="side-list-row"><span>最佳評級</span><span>{escape(str(snapshot['best_payload']['rating']))}</span></div>
                <div class="side-list-row"><span>偏多模型數</span><span>{snapshot['good_count']}</span></div>
                <div class="side-list-row"><span>風險模型數</span><span>{snapshot['risk_count']}</span></div>
            </div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )


def render_data_health_panel(snapshot: dict[str, object], ticker_keyword: str) -> None:
    data_snapshot = snapshot.get("data_diagnostic_snapshot", {})
    top100_count = data_snapshot.get("top100_count", 0)
    monthly_coverage = (
        f"{data_snapshot.get('monthly_revenue_covered_count', 0)} / {top100_count}"
        if top100_count
        else "未提供"
    )
    ticker_monthly = "有" if data_snapshot.get("ticker_has_monthly_revenue") else "缺"
    statement_route = "金融路由" if data_snapshot.get("ticker_statement_route") == "financial" else "一般路由"
    st.markdown(
        dedent(f"""
        <div class="side-surface">
            <h2 style="margin-top:0;">資料健康度</h2>
            <div class="rail-copy">這個區塊聚焦資料覆蓋與模型執行可靠度，方便先判斷結果該看多深。</div>
            <div class="side-list">
                <div class="side-list-row"><span>Top100 月營收覆蓋</span><span>{monthly_coverage}</span></div>
                <div class="side-list-row"><span>本檔月營收</span><span>{ticker_monthly}</span></div>
                <div class="side-list-row"><span>財報路由</span><span>{statement_route}</span></div>
                <div class="side-list-row"><span>資料警示數</span><span>{snapshot['warning_count']}</span></div>
                <div class="side-list-row"><span>平均信心</span><span>{snapshot['average_confidence']}%</span></div>
                <div class="side-list-row"><span>搜尋關鍵字</span><span>{escape(ticker_keyword or '全市場')}</span></div>
            </div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )


def render_insight_panel() -> None:
    st.markdown(
        dedent("""
        <div class="side-surface">
            <h2 style="margin-top:0;">研究觀點</h2>
            <ul class="insight-list" style="margin-top:0.2rem;">
                <li>高資訊密度保留六模型差異，避免單一分數掩蓋邏輯差異。</li>
                <li>IMFS 若走品質訊號路徑，明確說明其不提供內在價值而非泛稱資料不足。</li>
                <li>所有模型以原始專案公式與邏輯為準，這裡只做展示與整合，不改動估值公式。</li>
            </ul>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )


def render_related_files_panel(
    ticker: str,
    updated_at: str,
    active_models: list[str],
    diagnostics: dict[str, object],
) -> None:
    manifest = diagnostics.get("buffett3_manifest", {})
    validation = diagnostics.get("validation_summary", {})
    normalization = diagnostics.get("normalization_summary", {})
    st.markdown(
        dedent(f"""
        <div class="side-surface">
            <h2 style="margin-top:0;">相關檔案</h2>
            <div class="file-card download-card">
                <div>
                    <strong>{ticker}_valuation_report.json</strong>
                    <div class="file-meta">模型輸出摘要 · JSON · {updated_at or '未提供'}</div>
                    <div class="file-meta">包含 {len(active_models)} 個啟用模型的評級、資料警示、透明門檻與原始欄位快照。</div>
                </div>
                <div class="detail-chip">下載</div>
            </div>
            <div class="file-card" style="margin-top:0.85rem;">
                <div>
                    <strong>buffett3_source_manifest.json</strong>
                    <div class="file-meta">來源覆蓋清單 · JSON · {escape(str(manifest.get('generated_at', '未提供')))}</div>
                    <div class="file-meta">用來驗證月營收、股利、估值快照與官方/回退財報覆蓋率。</div>
                </div>
            </div>
            <div class="file-card" style="margin-top:0.85rem;">
                <div>
                    <strong>validation_summary.json / normalization_summary.json</strong>
                    <div class="file-meta">共享資料稽核 · JSON</div>
                    <div class="file-meta">目前驗證警示 {len(validation.get('checks', []))} 筆、正規化表 {len(normalization.get('tables', []))} 張。</div>
                </div>
            </div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )


def render_action_panel() -> None:
    st.markdown(
        dedent("""
        <div class="side-surface">
            <h2 style="margin-top:0;">快速操作</h2>
            <div class="action-grid">
                <div class="action-tile">圖表<br>檢視</div>
                <div class="action-tile">模型<br>比較</div>
                <div class="action-tile">匯出<br>報告</div>
                <div class="action-tile">資料<br>備註</div>
                <div class="action-tile">風險<br>說明</div>
                <div class="action-tile">研究<br>紀錄</div>
            </div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )


def render_model_snapshot_panel(row: pd.Series, active_models: list[str]) -> None:
    summary_html = [
        '<div class="side-surface">'
        '<h2 style="margin-top:0;">模型快照</h2>'
        '<div class="rail-copy">把目前啟用模型的評級與核心數值壓縮成同一張表，方便先橫向掃描，再決定深入哪一個模型。</div>'
        '<div class="summary-grid">'
    ]
    for model_id in active_models:
        payload = get_model_payload(row, model_id)
        summary_html.append(
            '<div class="summary-row">'
            f'<div class="summary-row-model">{escape(str(payload["short_name"]))}</div>'
            f'<div><span class="badge {badge_class(payload["rating"])}">{escape(str(payload["rating"]))}</span></div>'
            f'<div class="summary-row-value">{escape(str(payload["gap_text"]))}</div>'
            "</div>"
        )
    summary_html.append("</div></div>")
    st.markdown("".join(summary_html), unsafe_allow_html=True)


def render_feed_panel(title: str, copy: str, items: list[dict[str, str]], meta_key: str) -> None:
    html_parts = [
        '<div class="side-surface">'
        f'<h2 style="margin-top:0;">{escape(title)}</h2>'
        f'<div class="rail-copy">{escape(copy)}</div>'
        '<div class="feed-list">'
    ]
    for item in items:
        html_parts.append(
            '<div class="feed-item">'
            '<div class="feed-dot"></div>'
            '<div>'
            f'<div class="feed-copy"><strong>{escape(str(item["title"]))}</strong><br>{escape(str(item["detail"]))}</div>'
            f'<div class="feed-meta">{escape(str(item[meta_key]))}</div>'
            "</div>"
            "</div>"
        )
    html_parts.append("</div></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def build_activity_log(
    row: pd.Series,
    active_models: list[str],
    dataset_summary: dict[str, object],
    updated_at: str,
    data_snapshot: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    summary = dataset_summary.get("summary", {})
    data_snapshot = data_snapshot or {}
    entries = [
        {"time": updated_at or "剛剛", "title": "最新模型同步完成", "detail": f"目前載入 {len(active_models)} 個模型輸出，供研究頁即時檢視。"},
    ]
    for model_id in active_models[:3]:
        payload = get_model_payload(row, model_id)
        entries.append(
            {
                "time": "本次執行",
                "title": f"{payload['name']} 已更新",
                "detail": f"目前評級為 {payload['rating']}，核心指標為 {payload['value_label']} {payload['gap_text']}。",
            }
        )
    if safe_float(row.get("imfs_intrinsic")) is None and str(row.get("imfs_model", "")) == "RULE_OF_40":
        entries.append(
            {
                "time": "IMFS 路由",
                "title": "IMFS 走品質訊號路徑",
                "detail": "此路由僅提供品質與成長訊號，不直接輸出每股內在價值。",
            }
        )
    monthly_missing_financials = data_snapshot.get("monthly_revenue_missing_financials", [])
    if data_snapshot.get("monthly_revenue_covered_count"):
        entries.append(
            {
                "time": "資料覆蓋",
                "title": "官方月營收覆蓋已核對",
                "detail": (
                    f"目前覆蓋 {data_snapshot.get('monthly_revenue_covered_count')} / {data_snapshot.get('top100_count', 0)}，"
                    f"缺口集中在 {'、'.join(monthly_missing_financials) if monthly_missing_financials else '少數標的'}。"
                ),
            }
        )
    elif int(summary.get("monthly_revenue_rows", 0) or 0) == 0:
        entries.append(
            {
                "time": "資料警示",
                "title": "月營收資料缺口已降級處理",
                "detail": "TW Buffett Quant 可執行，但與月營收相關的判讀目前屬降級模式。",
            }
        )
    return entries[:5]


def build_research_ledger(row: pd.Series, updated_at: str) -> list[dict[str, str]]:
    updates = [
        {
            "date": updated_at.split(" ")[0] if updated_at else "2025/05/19",
            "title": "巴菲特 TW 估值快照",
            "detail": (
                f"目前評級為 {classify_value(normalize_pct(row.get('buffett_v1_mos')))}，"
                f"內在價值為 {fmt_currency(row.get('buffett_v1_intrinsic'))}。"
            ),
        },
        {
            "date": "2025/05/12",
            "title": "內在價值調整",
            "detail": f"巴菲特 2.0 更新每股合理價至 {fmt_currency(row.get('buffett_v2_intrinsic'))}。",
        },
        {
            "date": "2025/05/01",
            "title": "新增風險備註",
            "detail": "納入需求循環與財報期間欄位缺口，提醒模型輸入有降級情形。",
        },
    ]
    if safe_float(row.get("hybrid_target")) is not None:
        updates.append(
            {
                "date": "2025/04/20",
                "title": "混合模型目標價更新",
                "detail": f"Hybrid 目前目標價 {fmt_currency(row.get('hybrid_target'))}，作為中期報酬參考。",
            }
        )
    return updates[:4]


def build_report(
    row: pd.Series,
    selected_models: list[str],
    dataset_summary: dict[str, object],
    updated_at: str,
    diagnostics: dict[str, object] | None = None,
    data_snapshot: dict[str, object] | None = None,
) -> str:
    diagnostics = diagnostics or {}
    data_snapshot = data_snapshot or {}
    ticker = str(row.get("ticker", ""))
    buffett3_payload = load_buffett3_payload(ticker)
    manifest_summary = summarize_manifest_for_ticker(diagnostics.get("buffett3_manifest", {}), ticker)
    export_notes = build_buffett3_export_notes(buffett3_payload)
    payload = {
        "ticker": ticker,
        "name": row.get("name"),
        "industry": row.get("industry"),
        "generated_at": updated_at,
        "selected_models": selected_models,
        "ratings": {model_id: get_model_payload(row, model_id)["rating"] for model_id in selected_models},
        "model_payloads": {model_id: get_model_payload(row, model_id) for model_id in selected_models},
        "row_data": row.to_dict(),
        "dataset_summary": dataset_summary,
        "data_provenance": {
            "ticker_snapshot": data_snapshot,
            "buffett3_manifest_generated_at": diagnostics.get("buffett3_manifest", {}).get("generated_at"),
            "validation_warning_tables": data_snapshot.get("validation_warning_tables", []),
            "normalization_warning_tables": data_snapshot.get("normalization_warning_tables", []),
            "manifest_ticker_coverage": manifest_summary,
        },
        "buffett3_detail": {
            "classification": buffett3_payload.get("classification"),
            "classification_reason": buffett3_payload.get("classification_reason"),
            "company_type": buffett3_payload.get("company_type"),
            "blended_fair_value": buffett3_payload.get("blended_fair_value"),
            "final_fair_value": buffett3_payload.get("final_fair_value"),
            "rating": buffett3_payload.get("rating"),
            "cyclical_ev_ebitda_blockers": (
                buffett3_payload.get("normalized_inputs", {}).get("cyclical_ev_ebitda_blockers", [])
            ),
            "source_field_coverage": (
                buffett3_payload.get("normalized_inputs", {}).get("source_field_coverage", {})
            ),
            "data_quality_flags": buffett3_payload.get("data_quality_flags", []),
            "manual_review_flags": buffett3_payload.get("manual_review_flags", []),
            "reporting_notes": export_notes,
        },
        "classification_rules": {
            "value_models": VALUE_RULES,
            "quant_model": QUANT_RULES,
            "hybrid_model": HYBRID_RULES,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def run_all_models() -> None:
    build_all_model_results(PATHS)
    load_results.clear()
    get_price_frame.clear()
    get_financial_frames.clear()


init_state()
try:
    results_df, dataset, result_summary = load_results()
except Exception as exc:
    st.error("應用程式目前無法完成初始化。")
    st.markdown(
        dedent(
            f"""
            **可能原因**

            - 雲端環境尚未生成基礎資料
            - 共享資料目錄尚未建立或不可寫入
            - 若你手動覆寫來源路徑，外部模型來源設定可能不正確

            **目前錯誤**

            `{type(exc).__name__}: {escape(str(exc))}`

            **部署提示**

            - 先確認 `TVM_SHARED_DATA_ROOT`
            - repo 已內建 `_external/` 完整模型來源，正常情況不需要再設定：
              - `TVM_IMFS_SOURCE_ROOT`
              - `TVM_QUANT_SOURCE_ROOT`
              - `TVM_HYBRID_SOURCE_ROOT`
            - 若為首次部署，重新整理後讓 app 先生成基礎資料與完整模型結果
            """
        )
    )
    st.stop()
default_dataset_root = str(dataset["dataset_root"])
diagnostics = load_dataset_diagnostics(default_dataset_root)
updated_at_raw = result_summary.get("generated_at") or dataset["summary"].get("generated_at") or ""
updated_at = updated_at_raw
if updated_at:
    try:
        updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).strftime("%Y/%m/%d %H:%M")
    except Exception:
        pass
external_model_availability = {
    "IMFS": PATHS.imfs_source_root.exists(),
    "台股 Buffett Quant": PATHS.quant_source_root.exists(),
    "混合模型": PATHS.hybrid_source_root.exists(),
}
demo_unavailable_models = [name for name, available in external_model_availability.items() if not available]

results_df = results_df.sort_values("market_cap", ascending=False).reset_index(drop=True)
ticker_labels = {
    row["ticker"]: f"{row['ticker']}  {row['name']}"
    for _, row in results_df[["ticker", "name"]].drop_duplicates().iterrows()
}

with st.sidebar:
    st.markdown('<div class="left-rail-title">研究控制台</div>', unsafe_allow_html=True)
    st.markdown(
        dedent("""
        <div class="sidebar-note-card">
            <div class="sidebar-note-title">操作流程</div>
            <div class="sidebar-note-copy">
                先縮小標的範圍，再確認要納入的模型，最後執行重算或直接閱讀下方儀表板輸出。
            </div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )

    st.markdown("### 標的設定")
    ticker_keyword = st.text_input("快速搜尋", value="", placeholder="輸入代號或公司名稱")
    if ticker_keyword.strip():
        keyword = ticker_keyword.strip().lower()
        filtered_df = results_df[
            results_df["ticker"].astype(str).str.lower().str.contains(keyword)
            | results_df["name"].astype(str).str.lower().str.contains(keyword)
        ].copy()
    else:
        filtered_df = results_df
    ticker_options = filtered_df["ticker"].tolist() or results_df["ticker"].tolist()
    preferred_ticker = normalize_ticker(st.session_state.get("selected_ticker"))
    if preferred_ticker not in ticker_options:
        preferred_ticker = ticker_options[0]
    ticker_selected = st.selectbox(
        "股票代號",
        ticker_options,
        index=ticker_options.index(preferred_ticker),
        format_func=lambda value: ticker_labels.get(value, value),
    )
    st.session_state.selected_ticker = ticker_selected
    if demo_unavailable_models:
        st.warning(
            "公開 demo 模式：目前缺少外部模型來源，以下模型暫時不可用："
            + "、".join(demo_unavailable_models)
        )
    selected_row = results_df[results_df["ticker"] == ticker_selected].iloc[0]
    st.caption(f"{selected_row['name']}｜目前候選 {len(ticker_options)} 檔")

    st.markdown("### 任意 ticker")
    manual_ticker = st.text_input(
        "輸入任意代號",
        value=str(st.session_state.get("manual_ticker_input", "")),
        placeholder="例如 2308、2454、AAPL",
    )
    st.session_state.manual_ticker_input = manual_ticker
    if st.button("下載最新資料並生成全部模型", width="stretch"):
        custom_ticker = normalize_ticker(manual_ticker)
        if not custom_ticker:
            st.warning("請先輸入有效的 ticker。")
        else:
            with st.spinner(f"正在為 {custom_ticker} 下載最新資料並生成全部模型..."):
                refresh_selected_ticker_for_final_ai(custom_ticker)
            st.session_state.selected_ticker = custom_ticker
            st.cache_data.clear()
            st.rerun()

    st.markdown("### 資料批次")
    st.markdown(
        dedent(f"""
        <div class="sidebar-note-card">
            <div class="sidebar-note-title">目前資料時間</div>
            <div class="sidebar-note-copy">
                {updated_at or '未提供'}<br>
                來源包含公開市場資料、共享 fundamentals 與整合模型輸出。
            </div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )

    st.markdown("### 頁面模式")
    st.session_state.page_mode = st.radio(
        "頁面模式",
        ["主頁總覽", "Final AI 專區", "研究參考與附錄"],
        index=["主頁總覽", "Final AI 專區", "研究參考與附錄"].index(st.session_state.page_mode)
        if st.session_state.page_mode in {"主頁總覽", "Final AI 專區", "研究參考與附錄"}
        else 0,
        label_visibility="collapsed",
    )

    st.markdown("### 啟用模型")
    chosen_models: list[str] = []
    for model_id in MODEL_ORDER:
        checked = st.checkbox(
            MODEL_META[model_id]["label"],
            value=model_id in st.session_state.active_models,
            key=f"sidebar_model_{model_id}",
        )
        if checked:
            chosen_models.append(model_id)
    st.session_state.active_models = chosen_models or MODEL_ORDER.copy()
    st.caption(f"目前啟用 {len(st.session_state.active_models)} / {len(MODEL_ORDER)} 個模型")

    st.markdown("### 執行控制")
    run_mode = st.radio("模式", ["執行全部模型", "僅執行選定模型"], label_visibility="collapsed")
    st.markdown('<div class="strong-button">', unsafe_allow_html=True)
    if st.button("▶ 執行全部模型", width="stretch"):
        with st.spinner("正在重算所有模型結果..."):
            run_all_models()
        st.success("全部模型已完成重算。")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="secondary-button">', unsafe_allow_html=True)
    if st.button("⇄ 僅執行選定模型", width="stretch"):
        st.info(f"目前為展示版控制流程，已套用 {run_mode} 檢視邏輯。")
    st.markdown("</div>", unsafe_allow_html=True)

    completeness = 92 if dataset["summary"]["summary"].get("monthly_revenue_rows", 0) == 0 else 100
    st.markdown("### 研究狀態")
    st.markdown(f"目前共用資料可用程度：**{completeness}%**")
    st.progress(completeness / 100)
    st.caption(f"同步時間：{updated_at or '未提供'}")
    st.caption("同步狀態：正常")


if should_refresh_final_ai(
    st.session_state.get("page_mode"),
    st.session_state.get("previous_page_mode"),
):
    with st.spinner(f"正在更新 {ticker_selected} 的全部模型與 Final AI 專區資料..."):
        refresh_selected_ticker_for_final_ai(ticker_selected)
    st.session_state.previous_page_mode = st.session_state.page_mode
    st.cache_data.clear()
    st.rerun()

st.session_state.previous_page_mode = st.session_state.page_mode


selected_row = results_df[results_df["ticker"] == ticker_selected].iloc[0]
selected_dataset_root = str(selected_row.get("dataset_root") or default_dataset_root)
diagnostics = load_dataset_diagnostics(selected_dataset_root)
active_models = [model_id for model_id in MODEL_ORDER if model_id in st.session_state.active_models]
price_df = get_price_frame(selected_dataset_root, ticker_selected)
preview_model = choose_focus_model(active_models, st.session_state.get("focus_model"))
if st.session_state.get("focus_model") != preview_model:
    st.session_state.focus_model = preview_model
preview_payload = get_model_payload(selected_row, preview_model)
dashboard_snapshot = build_dashboard_snapshot(
    selected_row,
    active_models,
    dataset,
    dataset["summary"],
    updated_at,
    diagnostics,
    ticker_selected,
)
data_diagnostic_snapshot = dashboard_snapshot.get("data_diagnostic_snapshot", {})
activity_log = build_activity_log(
    selected_row,
    active_models,
    dataset["summary"],
    updated_at,
    data_diagnostic_snapshot,
)
research_ledger = build_research_ledger(selected_row, updated_at)

header_left, header_right = st.columns([4.4, 1.6], gap="large")
with header_left:
    st.markdown(
        f"""
        <div class="hero-surface">
            <div class="title-row">
                <div>
                    <div class="title-kicker">Taiwan Equity Valuation Desk</div>
                    <h1 class="title-main">台股多模型估值平台</h1>
                    <div class="hero-subcopy">
                        將巴菲特系、Buffett 3.0、IMFS、Quant 與混合模型整合到同一個研究畫面，
                        讓估值、評級、資料健康度與模型差異可以在同一次檢視中完成判讀。
                    </div>
                </div>
                <div class="title-meta">
                    <strong>資料更新</strong>：{updated_at or '未提供'}<br>
                    <strong>研究標的</strong>：{ticker_selected}<br>
                    <strong>目前聚焦</strong>：{preview_payload['name']}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_dashboard_band(dashboard_snapshot, active_models, preview_payload["current_price_text"])

with header_right:
    st.markdown(
        dedent(f"""
        <div class="side-surface">
            <h2 style="margin-top:0;">投資判讀摘要</h2>
            <div class="detail-chip">{MODEL_META[preview_model]['symbol']} {preview_payload['name']}</div>
            <div class="rail-copy" style="margin-top:0.8rem;">
                目前聚焦模型為「{preview_payload['name']}」，評級落在 <strong>{preview_payload['rating']}</strong>，
                主要判讀依據是 {preview_payload['value_label']} {preview_payload['gap_text']}。
            </div>
            <div class="health-pill">{'月營收資料已接入' if dashboard_snapshot['monthly_revenue_rows'] > 0 else '月營收資料仍有缺口'}</div>
            <div class="side-list">
                <div class="side-list-row"><span>最強訊號</span><span>{escape(str(dashboard_snapshot['best_payload']['short_name']))}</span></div>
                <div class="side-list-row"><span>偏多模型</span><span>{dashboard_snapshot['good_count']}</span></div>
                <div class="side-list-row"><span>風險模型</span><span>{dashboard_snapshot['risk_count']}</span></div>
                <div class="side-list-row"><span>資料警示</span><span>{dashboard_snapshot['warning_count']}</span></div>
            </div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )

st.markdown('<div class="toolbar-surface">', unsafe_allow_html=True)
toolbar_chip_cols = st.columns(6, gap="small")
for idx, model_id in enumerate(MODEL_ORDER):
    state_text = "已啟用" if model_id in active_models else "未啟用"
    with toolbar_chip_cols[idx]:
        st.markdown(
            f"""
            <div class="toolbar-chip">
                <div class="toolbar-chip-name">{MODEL_META[model_id]['symbol']} {MODEL_META[model_id]['short_label']}</div>
                <div class="toolbar-chip-state">{state_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
control_cols = st.columns([1.0, 1.35], gap="medium")
with control_cols[0]:
    st.markdown('<div class="strong-button">', unsafe_allow_html=True)
    if st.button("▶ 執行全部模型", width="stretch", key="top_run_all_new"):
        with st.spinner("正在重算所有模型結果..."):
            run_all_models()
        st.success("全部模型已完成重算。")
    st.markdown("</div>", unsafe_allow_html=True)
with control_cols[1]:
    st.session_state.page_mode = st.radio(
        "工作頁面",
        ["主頁總覽", "Final AI 專區", "研究參考與附錄"],
        index=["主頁總覽", "Final AI 專區", "研究參考與附錄"].index(st.session_state.page_mode)
        if st.session_state.page_mode in {"主頁總覽", "Final AI 專區", "研究參考與附錄"}
        else 0,
        horizontal=True,
        label_visibility="collapsed",
    )
st.markdown("</div>", unsafe_allow_html=True)

triage_cols = st.columns(3, gap="medium")
with triage_cols[0]:
    render_consensus_panel(dashboard_snapshot)
with triage_cols[1]:
    render_data_health_panel(dashboard_snapshot, ticker_keyword)
with triage_cols[2]:
    render_model_snapshot_panel(selected_row, active_models)

focus_model = st.radio(
    "單模型詳情",
    options=active_models,
    format_func=lambda value: MODEL_META[value]["label"],
    horizontal=True,
    key="focus_model",
)
focus_payload = get_model_payload(selected_row, focus_model)
focus_reference = focus_payload["fair_value"] if focus_model != "quant" else None
buffett3_detail_payload: dict[str, object] = {}

if st.session_state.page_mode == "主頁總覽":
    overview_models = active_models
    title_cols = st.columns([4.8, 1.2], gap="small")
    with title_cols[0]:
        st.markdown("## 模型總覽")
        st.caption("單位：新台幣（元）｜依照模型家族與評級順序進行橫向比較")
    with title_cols[1]:
        st.session_state.view_mode = st.radio(
            "檢視模式",
            ["卡片", "列表"],
            index=0 if st.session_state.view_mode == "卡片" else 1,
            horizontal=True,
            label_visibility="collapsed",
        )

    if st.session_state.view_mode == "列表":
        table_rows = []
        for model_id in overview_models:
            payload = get_model_payload(selected_row, model_id)
            table_rows.append(
                {
                    "模型": payload["name"],
                    "評級": payload["rating"],
                    "指標": payload["value_label"],
                    "數值": payload["gap_text"],
                    "目前股價": payload["current_price_text"],
                    "內在價值 / 動作": payload["fair_value_text"],
                }
            )
        st.dataframe(pd.DataFrame(table_rows).astype(str), width="stretch", hide_index=True)
    else:
        spark_source = price_df["Close"].tail(40)
        models_per_row = 3 if len(overview_models) >= 5 else max(1, len(overview_models))
        for row_models in chunked(overview_models, models_per_row):
            st.markdown('<div class="overview-row">', unsafe_allow_html=True)
            card_cols = st.columns(len(row_models), gap="medium")
            for idx, model_id in enumerate(row_models):
                payload = get_model_payload(selected_row, model_id)
                sparkline_html = render_sparkline(spark_source, payload["color"])
                with card_cols[idx]:
                    st.markdown(
                        f"""
                        <div class="card-surface">
                            <div class="card-top">
                                <div>
                                    <div class="section-note">{payload['symbol']}</div>
                                    <div class="card-title">{payload['name']}</div>
                                </div>
                                <span class="badge {badge_class(payload['rating'])}">{payload['rating']}</span>
                            </div>
                            <div class="metric-label">{payload['value_label']}</div>
                            <div class="metric-value">{payload['gap_text']}</div>
                            {sparkline_html}
                            <div class="card-stats">
                                <div class="card-stat-row"><div class="card-stat-label">目前股價</div><div class="card-stat-value">{payload['current_price_text']}</div></div>
                                <div class="card-stat-row"><div class="card-stat-label">{payload['fair_label']}</div><div class="card-stat-value">{payload['fair_value_text']}</div></div>
                                <div class="card-stat-row"><div class="card-stat-label">信心度</div><div class="card-stat-value">{payload['confidence']}%</div></div>
                                <div class="confidence-track"><div class="confidence-fill" style="width:{payload['confidence']}%;"></div></div>
                            </div>
                            <div class="card-comment">{payload['summary']}</div>
                            <div class="card-comment">{payload['basis']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)

    header_cols = st.columns([1.1, 4.3, 1.0], gap="small")
    with header_cols[0]:
        st.markdown("## 單模型詳情")
    with header_cols[1]:
        st.markdown(
            dedent(f"""
            <div class="detail-headline">
                <div>
                    <div class="detail-chip">{MODEL_META[focus_model]['symbol']} {focus_payload['name']}</div>
                    <div class="detail-submeta">
                        {ticker_selected}　{selected_row['name']}　|　評級 {focus_payload['rating']}　|　目前股價 {focus_payload['current_price_text']}
                    </div>
                </div>
            </div>
            """).strip(),
            unsafe_allow_html=True,
        )
    with header_cols[2]:
        st.download_button(
            "下載估值摘要",
            data=build_report(
                selected_row,
                active_models,
                dataset["summary"],
                updated_at,
                diagnostics,
                data_diagnostic_snapshot,
            ),
            file_name=f"{ticker_selected}_valuation_report.json",
            mime="application/json",
            width="stretch",
        )

    detail_tabs = st.tabs(["總覽", "估值輸入", "模型解釋", "風險提示", "Final AI"])
    st.caption("主頁集中顯示估值結果、主要輸入、模型判讀與風險提示；研究參考與附錄請切到第二頁。")

    with detail_tabs[0]:
        overview_cols = st.columns([0.95, 2.45, 1.1], gap="small")
        with overview_cols[0]:
            st.markdown(
                dedent(f"""
                <div class="metric-shell">
                    <h3>估值結果</h3>
                    <div class="metric-label">{focus_payload['value_label']}</div>
                    <div class="metric-value">{focus_payload['gap_text']}</div>
                    <span class="badge {badge_class(focus_payload['rating'])}">{focus_payload['rating']}</span>
                    <div class="detail-stat"><span>{focus_payload['fair_label']}</span><strong>{focus_payload['fair_value_text']}</strong></div>
                    <div class="detail-stat"><span>目前股價</span><strong>{focus_payload['current_price_text']}</strong></div>
                    <div class="detail-stat"><span>信心度</span><strong>{focus_payload['confidence']}%</strong></div>
                    <div class="confidence-track"><div class="confidence-fill" style="width:{focus_payload['confidence']}%;"></div></div>
                </div>
                """).strip(),
                unsafe_allow_html=True,
            )
        with overview_cols[1]:
            render_detail_chart(price_df, focus_reference, focus_payload["color"])
        with overview_cols[2]:
            render_key_metrics_panel(build_key_metrics(selected_dataset_root, ticker_selected).astype(str))
        st.markdown(
            dedent(f"""
            <div class="model-summary-strip">
                <strong>模型摘要</strong>　{focus_payload['summary']} {focus_payload['basis']}
            </div>
            """).strip(),
            unsafe_allow_html=True,
        )

    with detail_tabs[1]:
        input_rows = [
            {"欄位": "目前股價", "內容": focus_payload["current_price_text"], "說明": "由 TOP100 價格資料集讀取最新收盤價。"},
            {"欄位": focus_payload["value_label"], "內容": focus_payload["gap_text"], "說明": focus_payload["basis"]},
            {"欄位": "內在價值 / 動作", "內容": focus_payload["fair_value_text"], "說明": "價值型模型顯示內在價值；Quant 顯示建議動作。"},
            {"欄位": "評級標籤", "內容": focus_payload["rating"], "說明": "依透明門檻自動映射，不使用模糊主觀文案。"},
        ]
        if focus_model == "buffett3":
            buffett3_detail_payload = load_buffett3_payload(ticker_selected)
            input_snapshot = buffett3_detail_payload.get("input_snapshot", {})
            normalized_inputs = buffett3_detail_payload.get("normalized_inputs", {})
            scenario_weights = buffett3_detail_payload.get("scenario_weights", {})
            source_field_coverage = normalized_inputs.get("source_field_coverage", {})
            cyclical_ev_blockers = normalized_inputs.get("cyclical_ev_ebitda_blockers", [])
            ready_legs = [
                format_buffett3_label(leg.get("name"))
                for leg in buffett3_detail_payload.get("valuation_legs", [])
                if str(leg.get("status", "")).lower() == "ready"
            ]
            pending_legs = [
                format_buffett3_label(leg.get("name"))
                for leg in buffett3_detail_payload.get("valuation_legs", [])
                if str(leg.get("status", "")).lower() != "ready"
            ]
            modifiers = buffett3_detail_payload.get("modifiers", {})
            input_rows.extend(
                [
                    {"欄位": "企業分類", "內容": format_buffett3_type(selected_row.get("buffett3_type")), "說明": format_buffett3_label(buffett3_detail_payload.get("classification_reason"))},
                    {"欄位": "財報資料路由", "內容": "金融路由" if data_diagnostic_snapshot.get("ticker_statement_route") == "financial" else "一般路由", "說明": "依公司類型切換官方財報抓取路徑；若官方欄位不足，會由 fallback 資料補齊。"},
                    {"欄位": "本檔官方月營收", "內容": "有" if data_diagnostic_snapshot.get("ticker_has_monthly_revenue") else "缺", "說明": "此欄直接比對本機月營收資料表與來源清單，不以推測補值。"},
                    {"欄位": "本檔年報 / 季報覆蓋", "內容": f"{'有' if data_diagnostic_snapshot.get('ticker_has_annual_statement') else '缺'} / {'有' if data_diagnostic_snapshot.get('ticker_has_quarterly_statement') else '缺'}", "說明": "確認當前標的在 Buffett 3.0 官方/回退財報資料表中的覆蓋狀態。"},
                    {"欄位": "情境權重", "內容": f"保守 {fmt_pct_plain(scenario_weights.get('conservative'))} / 基本 {fmt_pct_plain(scenario_weights.get('base'))} / 樂觀 {fmt_pct_plain(scenario_weights.get('bull'))}", "說明": "Buffett 3.0 先做三情境估值，再依公司類型套用預設權重。"},
                    {"欄位": "標準化 EPS", "內容": fmt_currency(normalized_inputs.get("normalized_eps", input_snapshot.get("normalized_eps"))), "說明": "Buffett 3.0 以標準化獲利作為多數估值支線的共同基底。"},
                    {"欄位": "標準化每股自由現金流", "內容": fmt_currency(normalized_inputs.get("normalized_fcf_per_share", input_snapshot.get("normalized_fcf_per_share"))), "說明": "自由現金流殖利率支線使用的每股現金創造能力。"},
                    {"欄位": "每股淨值", "內容": fmt_currency(normalized_inputs.get("normalized_bvps", input_snapshot.get("bvps"))), "說明": "金融股與剩餘收益支線共用的資本基底。"},
                    {"欄位": "支線加權基準值", "內容": fmt_currency(buffett3_detail_payload.get("blended_fair_value")), "說明": "先只用已就緒支線加權後得到的基準值，尚未套用總體、台灣風險與現實驗證修正。"},
                    {"欄位": "已啟用支線", "內容": "、".join(ready_legs) if ready_legs else "無", "說明": "目前已具備必要輸入並真正參與 blended fair value 的估值支線。"},
                    {"欄位": "待補支線", "內容": "、".join(pending_legs) if pending_legs else "無", "說明": "目前仍缺資料或 V1 尚未完全實作，因此先不納入 blended fair value。"},
                    {
                        "欄位": "EV/EBITDA 支線阻塞",
                        "內容": join_buffett3_labels(cyclical_ev_blockers),
                        "說明": (
                            f"年報 debt/cash = {source_field_coverage.get('annual_total_debt_non_null_rows', 0)} / "
                            f"{source_field_coverage.get('annual_cash_and_equivalents_non_null_rows', 0)}；"
                            f"季報 debt/cash = {source_field_coverage.get('quarterly_total_debt_non_null_rows', 0)} / "
                            f"{source_field_coverage.get('quarterly_cash_and_equivalents_non_null_rows', 0)}。"
                        ),
                    },
                    {"欄位": "總體環境修正", "內容": format_buffett3_modifier(modifiers.get("macro_regime_modifier", {}).get("modifier_value")), "說明": join_buffett3_labels(modifiers.get("macro_regime_modifier", {}).get("reason"))},
                    {"欄位": "台灣風險修正", "內容": format_buffett3_modifier(modifiers.get("taiwan_risk_modifier", {}).get("modifier_value")), "說明": join_buffett3_labels(modifiers.get("taiwan_risk_modifier", {}).get("reason"))},
                    {"欄位": "現實驗證修正", "內容": format_buffett3_modifier(modifiers.get("reality_validation_modifier", {}).get("modifier_value")), "說明": join_buffett3_labels(modifiers.get("reality_validation_modifier", {}).get("reason"))},
                    {"欄位": "資料品質旗標", "內容": join_buffett3_labels(buffett3_detail_payload.get("data_quality_flags")), "說明": "提示哪些估值輸入是完整、降級或需要保守解讀。"},
                    {"欄位": "人工覆核旗標", "內容": join_buffett3_labels(buffett3_detail_payload.get("manual_review_flags")), "說明": "提醒哪些估值支線或假設仍值得人工再確認。"},
                ]
            )
        if focus_model == "imfs" and str(selected_row.get("imfs_model", "")) == "RULE_OF_40" and str(selected_row.get("imfs_route", "")) == "B":
            premium_text = "可享溢價" if str(selected_row.get("imfs_premium_eligible", "")).lower() == "true" else "未達溢價"
            input_rows.extend(
                [
                    {"欄位": "預估營收成長", "內容": fmt_pct_plain(selected_row.get("imfs_est_revenue_growth_pct")), "說明": "以近八季 TTM 與近年營收趨勢估算的下一期營收成長率。"},
                    {"欄位": "預估利潤率", "內容": fmt_pct_plain(selected_row.get("imfs_est_profit_margin_pct")), "說明": "優先採用 TTM 淨利率，不足時退回營業利潤率或快照利潤率。"},
                    {"欄位": "品質分數", "內容": fmt_score(selected_row.get("imfs_quality_score")), "說明": "Rule of 40 = 預估營收成長率 + 預估利潤率，用來判斷經營品質。"},
                    {"欄位": "溢價資格", "內容": premium_text, "說明": "品質分數達到門檻時，可使用較高的 justified P/E 估出每股合理價。"},
                ]
            )
        st.dataframe(pd.DataFrame(input_rows).astype(str), width="stretch", hide_index=True)

    with detail_tabs[2]:
        st.markdown("#### 模型判讀")
        st.caption("先讀模型如何描述當前評級，再看規則表與支線細節，理解這個結論是怎麼形成的。")
        st.write(focus_payload["summary"])
        st.write(focus_payload["basis"])
        if focus_model == "buffett3":
            buffett3_explain_payload = buffett3_detail_payload or load_buffett3_payload(ticker_selected)
            leg_rows = []
            for leg in buffett3_explain_payload.get("valuation_legs", []):
                leg_rows.append(
                    {
                        "估值支線": format_buffett3_label(leg.get("name")),
                        "狀態": "已啟用" if str(leg.get("status", "")).lower() == "ready" else "待補強",
                        "權重": fmt_pct_plain(leg.get("weight")),
                        "基準值": fmt_currency(leg.get("blended_value")),
                        "備註": join_buffett3_labels(leg.get("notes")),
                    }
                )
            if leg_rows:
                st.markdown("#### Buffett 3.0 估值支線")
                st.dataframe(pd.DataFrame(leg_rows).astype(str), width="stretch", hide_index=True)
            modifier_rows = []
            for key, modifier in buffett3_explain_payload.get("modifiers", {}).items():
                modifier_rows.append(
                    {
                        "修正模組": format_buffett3_label(key),
                        "係數": format_buffett3_modifier(modifier.get("modifier_value")),
                        "判定": format_buffett3_label(modifier.get("selected_bucket")),
                        "依據": format_buffett3_label(modifier.get("reason")),
                    }
                )
            if modifier_rows:
                st.markdown("#### Buffett 3.0 修正模組")
                st.dataframe(pd.DataFrame(modifier_rows).astype(str), width="stretch", hide_index=True)
        if focus_model in {"buffett_v1", "buffett_v2", "buffett3", "imfs"}:
            render_rules_table("價值型模型分級規則", VALUE_RULES)
        elif focus_model == "quant":
            render_rules_table("Quant 模型分級規則", QUANT_RULES)
        else:
            render_rules_table("混合模型分級規則", HYBRID_RULES)

    with detail_tabs[3]:
        warnings_text = str(selected_row.get("data_warnings", "{}"))
        try:
            warnings_payload = json.loads(warnings_text)
            render_warning_panel(warnings_payload, active_models)
        except Exception:
            st.write(warnings_text)

    with detail_tabs[4]:
        render_final_module_panel(ticker_selected)

    lower_cols = st.columns([1.4, 1.0], gap="large")
    with lower_cols[0]:
        render_feed_panel("模型動態", "記錄本次載入中最值得先注意的模型更新、路由差異與資料降級訊號。", activity_log, "time")
    with lower_cols[1]:
        render_insight_panel()


if st.session_state.page_mode == "Final AI 專區":
    final_cols = st.columns([3.15, 1.35], gap="large")
    with final_cols[0]:
        st.markdown("## Final AI 專區")
        st.caption("把獨立 AI 估值、內部模型比較、新聞摘要與法人 / 公眾觀點集中到同一頁，直接給出最後判讀。")
        render_final_module_panel(ticker_selected)
    with final_cols[1]:
        render_model_snapshot_panel(selected_row, active_models)
        render_related_files_panel(ticker_selected, updated_at, active_models, diagnostics)
        render_feed_panel("模型動態", "記錄本次載入中最值得先注意的模型更新、路由差異與資料降級訊號。", activity_log, "time")
elif st.session_state.page_mode == "研究參考與附錄":
    appendix_cols = st.columns([3.1, 1.45], gap="large")
    with appendix_cols[0]:
        st.markdown("## 研究參考與附錄")
        st.caption("把跨模型說明、分級門檻、檔案與研究紀錄集中到第二頁，讓主頁保留給判讀與比較。")
        render_reference_tab(diagnostics, dashboard_snapshot.get("data_diagnostic_snapshot", {}))
        render_rating_thresholds()
    with appendix_cols[1]:
        render_related_files_panel(ticker_selected, updated_at, active_models, diagnostics)
        render_action_panel()
        render_model_snapshot_panel(selected_row, active_models)
        render_feed_panel("模型動態", "記錄本次載入中最值得先注意的模型更新、路由差異與資料降級訊號。", activity_log, "time")
        render_feed_panel("研究紀要", "整理近期估值調整、風險備註與研究脈絡，讓下一次回看同一檔標的時更快進入狀況。", research_ledger, "date")



st.markdown(
    """
    <div class="warning-surface">
        <strong>警示</strong>　本估值結果基於歷史資料與既有模型假設，不保證未來表現。若月營收、財報期間欄位或估值歷史序列仍不完整，部分模型將以降級資料狀態執行，請搭配風險管理與研究判斷使用。
    </div>
    """,
    unsafe_allow_html=True,
)
