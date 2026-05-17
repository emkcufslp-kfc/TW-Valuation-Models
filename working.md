# Working Notes - TW Valuation Models Integration

## START HERE FOR NEW SESSION

### Current State
The project is runnable and currently focused on final production polish for the Streamlit dashboard.

Workspace:
- `D:\Codex projects\TW Valuation models`

Main app:
- `D:\Codex projects\TW Valuation models\app.py`

Run command:
```powershell
python -m streamlit run "D:\Codex projects\TW Valuation models\app.py"
```

Full data/model rebuild command:
```powershell
cd "D:\Codex projects\TW Valuation models"
python -m tw_valuation_models run-all
```

### User Requirement To Preserve
The user requires professional production quality, not an approximate draft.

Hard requirements:
- UI must continue moving toward the approved dark forest / emerald / gold professional dashboard mockup.
- All user-facing app text should be Traditional Chinese except unavoidable model names.
- All valuation models must use original project formulas and logic unless the original logic has a confirmed bug.
- Do not change model formulas while doing UI work.
- After each module, think through the work twice and update this `working.md`.
- Use `working.md` as the handoff source before making new changes.

### Current Model Logic Status
- Buffett v1 / v2: integrated Python port aligned to original `buffett-stock-tw` DCF constants and formula behavior.
- IMFS: direct original route classifier and valuation engine from `D:\Claude projects\IMFS_TW_Stock`.
- TW Buffett Quant: direct original strict-mode engine from `D:\Claude projects\TWSE aihedge\tw-buffett-quant-app`.
- TW Hybrid: direct original `strategy.py` core functions/classes from `D:\Claude projects\TW hybrid model\台股法說會估值\Taiwwan-stock-hybrid-model`.

Important IMFS note:
- `資料不足` / no intrinsic value can be valid for some IMFS routes, especially Rule of 40 / quality-signal paths. It should be explained as quality-signal routing, not a crash.

### Current UI Status
Recent fixes already applied:
- Raw `<div ...>` HTML rendering bugs fixed.
- Fragile half-open Streamlit HTML wrappers removed.
- Sidebar/select/date/button/download controls themed away from white default boxes.
- Detail chart upgraded from simple line chart to mockup-style dark OHLC chart with red/green candle-like price action, volume panel, 20-day line, volatility band, target/intrinsic line, and safety-margin lines.
- Chart is not live streaming. It redraws from latest loaded price history on app rerun, stock/model change, or data rebuild.
- Right rail includes useful product panels: rating explanation, related files, quick actions, Log, Ledger, model summary.
- Added a searchable ticker/company filter in the left rail to reduce scrolling through the TOP100 universe.
- Added a top summary ribbon under the hero area for current price, active model count, best rating, average confidence, and data status.
- Added data-health and consensus cards so users can judge coverage and model agreement before drilling into a single valuation card.
- Replaced remaining `use_container_width` usage touched in the UI path with `width="stretch"` to avoid those deprecation warnings.
- Rebalanced the layout so the top-right investment card is compact and the single-model detail section appears much higher on the page.
- Moved supporting right-rail panels (`研究觀點`, `相關檔案`, `快速操作`) lower so the first screen prioritizes mockup-like hero, status, model overview, and detail flow.
- Added stronger CSS hiding for the Streamlit Deploy control that was still surfacing in the top-right corner.

### Latest Verification
Last verified commands:
```powershell
python -m compileall app.py tw_valuation_models
$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"
```

Expected warnings during bare Python runtime check:
- Streamlit `missing ScriptRunContext` warnings are normal in bare mode.
- Streamlit may still emit normal bare-runtime warnings, but the touched UI path no longer emits `use_container_width` deprecation warnings.

### Known Data Gaps
These are real gaps and should be disclosed, not hidden:
- `monthly_revenue_history.csv` is still empty because MOPS blocks requests/POST in this environment.
- TW Buffett Quant runs, but monthly-revenue-related judgment is degraded.
- `valuation.csv` is still a snapshot, not a true historical valuation series.
- `yfinance_fundamentals.csv` is still a snapshot, not point-in-time financial history.

### Buffett 3.0 Core Calculation Planning Status
User direction as of `2026-05-15`:
- Do not start UI work for Buffett 3.0 until the user confirms the core model design.
- Stick to the Buffett 3.0 document formula and calculation discipline.
- First deliver:
  - core calculation spec
  - sample application to `2330`, `2881`, `2603`, `2412`
  - review of which current loaders/data resources can be reused
  - gaps and data-acquisition plan

Primary reference document:
- `C:\Users\user\Downloads\Taiwan_Buffett_3_0_Institutional_Valuation_Model_All_in_One.md`

Buffett 3.0 non-negotiable master formula from the reference document:
```text
Fair Value per Share
=
Blended Normalized Valuation
× Macro Regime Modifier
× Taiwan Risk Modifier
× Reality Validation Modifier
```

Preferred implementation order from the document:
```text
Step 1: Estimate valuation by model before macro/risk/reality adjustment
Step 2: Apply macro modifier
Step 3: Apply Taiwan risk modifier
Step 4: Apply reality validation modifier
```

### Buffett 3.0 V1 Scope
This V1 is core-calculation-only. No UI work should start before user confirmation.

V1 should cover:
1. rule-based company classification
2. normalized economics by company type
3. sector-appropriate valuation legs
4. conservative / base / bull cases
5. probability-weighted blended fair value
6. macro / Taiwan risk / reality modifiers
7. auditable output payload

V1 should not promise yet:
- full institutional report rendering
- monthly-revenue-driven modifier automation
- historical valuation regime engine from clean time-series multiples
- full EV/EBITDA implementation with net debt and depreciation detail

### Buffett 3.0 Classification And Formula Map
Use the document's Step 4 and Step 11 definitions.

1. `High Quality Compounder`
- examples in document: `TSMC`, `Delta`, `MediaTek`, `Quanta`
- valuation legs and weights:
  - `Normalized PE`: `35%`
  - `FCF Yield`: `25%`
  - `Residual Earnings`: `25%`
  - `Dividend Yield / DDM`: `15%`
- key formulas:
  - `Normalized PE Value = Normalized EPS × Fair PE`
  - `FCF Yield Value = Normalized FCF per Share / Required FCF Yield`
  - `Residual Earnings Value = BVPS + [Residual EPS × Persistence Factor] / (Cost of Equity - Growth)`

2. `Financial`
- use for banks, insurers, and financial holding companies
- valuation legs and weights:
  - `ROE-adjusted PB`: `40%`
  - `DDM`: `35%`
  - `Normalized PE`: `15%`
  - `Residual Income`: `10%`
- key formulas:
  - `Sustainable EPS = BVPS × Sustainable ROE`
  - `Fair PB = (ROE - Growth) / (Cost of Equity - Growth)`
  - `PB Value = BVPS × Fair PB`
  - `DDM Value = DPS next year / (Cost of Equity - Long-Term Dividend Growth)`

3. `Cyclical`
- use for shipping, steel, DRAM, panel, commodity-linked stocks
- valuation legs and weights:
  - `Mid-cycle EPS`: `30%`
  - `Normalized EV/EBITDA`: `30%`
  - `Replacement / Asset Value`: `20%`
  - `Trough PB / Downside Value`: `20%`
- key formulas:
  - `Mid-cycle PE Value = 10-year normalized EPS × Mid-cycle PE`
  - `EV/EBITDA Value per Share = ((Normalized EBITDA × Fair EV/EBITDA) - Net Debt) / Shares Outstanding`
- mandatory rule:
  - never value cyclicals using peak EPS

4. `Defensive / Dividend`
- use for telecom, utilities, food, and stable defensive businesses
- valuation legs and weights:
  - `Dividend Yield Band`: `35%`
  - `DDM`: `30%`
  - `Normalized PE`: `25%`
  - `FCF Yield`: `10%`
- key formulas:
  - `Dividend Yield Value = Normalized DPS / Fair Dividend Yield`
  - `DDM Value = DPS next year / (Cost of Equity - Long-Term Growth)`

Scenario weighting from the document:
- default: `30% conservative + 50% base + 20% bull`
- high-quality compounder: `25% conservative + 50% base + 25% bull`
- high uncertainty: `40% conservative + 45% base + 15% bull`

### Current Reusable Loaders And Data Assets
Existing code/data that Buffett 3.0 V1 can reuse directly:

Dataset builder:
- `D:\Codex projects\TW Valuation models\tw_valuation_models\dataset.py`

Shared-data normalization:
- `D:\Codex projects\TW Valuation models\tw_valuation_models\shared_data.py`

Current top100 dataset root:
- `D:\Codex projects\TW Valuation models\artifacts\datasets\top100`

Reusable files:
1. `top100_universe.csv`
- company name
- industry
- market
- market cap

2. `top100_valuation_snapshot.csv`
- `pe_ratio`
- `pb_ratio`
- `dividend_yield`
- note: snapshot only, no historical regime series

3. `fundamentals/<ticker>_annual.csv`
- `revenue`
- `net_income`
- `operating_income`
- `operating_cash_flow`
- `capital_expenditure`
- `free_cash_flow`
- `equity`
- `total_assets`
- `total_liabilities`
- `current_assets`
- `current_liabilities`
- `shares_outstanding`
- `eps`
- `book_value_per_share`
- `roe`

4. `fundamentals/<ticker>_quarterly.csv`
- same fields as annual
- useful for run-rate checks and latest trend checks

5. `fundamentals/<ticker>_profile.json`
- `currentPrice`
- `trailingPE`
- `trailingEps`
- `priceToBook`
- `dividendYield`
- `currentRatio`
- `debtToEquity`
- `sector`
- `industry`

6. `prices/<ticker>.csv`
- strongest current time-series domain
- can support market-price as-of valuation date
- can support future regime-table build later

7. `TAIEX.csv`
- usable for macro context and benchmark overlays later

### Current Data Gaps Specific To Buffett 3.0
Current loader/data is good enough for a V1 core engine, but not enough for every institutional audit layer in the reference document.

Known gaps:
1. `monthly_revenue_history.csv` currently has `0` rows
- `dataset.py` does attempt to fetch MOPS monthly revenue
- in this environment the fetch currently degrades to empty output
- Buffett 3.0 Step 8 monthly-revenue validation therefore cannot be automated yet

2. no true historical valuation regime tables yet
- no dated `PE / PB / FCF yield / dividend yield` time series
- only snapshot multiples are currently normalized

3. no direct `ROIC` field
- document asks for ROIC where available
- current loader does not provide it

4. no direct `cash and equivalents` field
- document asks for `Net Cash / Net Debt`
- current top100 financial extracts provide `total_liabilities`, but not clean cash for direct net-cash computation

5. no direct `gross margin`
- operating margin and net margin can be derived
- gross margin is not currently in the annual/quarterly extracts

6. no direct `dividend per share` history table
- only current dividend yield snapshot is available
- DDM and dividend-yield methods will need a dividend history source or an explicit assumption layer

### Required Data Acquisition Plan For Buffett 3.0
Priority order for missing inputs:

1. `Monthly revenue trend`
- desired source: TWSE/MOPS monthly revenue disclosures
- current status: fetch logic exists in `dataset.py`, but returns empty in this environment
- action:
  - inspect whether MOPS HTML endpoint changed
  - consider alternate TWSE or cached raw CSV source
  - until fixed, keep monthly revenue as optional validation only

2. `Historical multiple regime tables`
- desired outputs:
  - historical PE range
  - historical PB range
  - historical dividend yield range
  - historical FCF yield range
- likely build path:
  - use `prices/<ticker>.csv`
  - combine with dated EPS/BVPS/FCF-per-share series from annual and quarterly statements
  - create approximate time-aligned regime tables by report period first, then refine later

3. `Dividend per share history`
- desired use:
  - `Dividend Yield Value`
  - `DDM Value`
- acquisition options:
  - extend profile/history loader to persist cash-dividend history from a reliable source
  - or add a local normalized dividend history table under `artifacts/normalized`

4. `Net cash / net debt`
- desired use:
  - cyclical EV/EBITDA implementation
- acquisition options:
  - extend loader to include cash and short-term investments from source fundamentals
  - until then, cyclical V1 should degrade away from full EV/EBITDA and rely more on mid-cycle EPS and PB-style downside anchors

5. `ROIC` and `gross margin`
- useful for business-quality scoring and compounder quality review
- acquisition options:
  - derive when source columns become available
  - or add additional source extraction

### Sample Application Plan By Ticker
The first four Buffett 3.0 validation names should be:
1. `2330`
2. `2881`
3. `2603`
4. `2412`

#### 2330
- company: `台灣積體電路製造股份有限公司`
- classification from the document:
  - `High Quality Compounder with semiconductor cycle exposure`
- current reusable fields:
  - price from `2330_profile.json`
  - EPS / FCF / BVPS / ROE from `2330_annual.csv`
  - latest quarterly trend from `2330_quarterly.csv`
  - PE / PB / dividend yield snapshot from `top100_valuation_snapshot.csv` and profile
- Buffett 3.0 calculation path:
  - build normalized EPS using the document's `2330` discipline
  - run `Normalized PE`
  - run `FCF Yield`
  - run `Residual Earnings`
  - run `Dividend Yield / DDM`
  - apply compounder scenario weighting: `25 / 50 / 25`
  - apply macro / Taiwan risk / reality modifiers
- current practical note:
  - this is the strongest Buffett 3.0 golden case because the reference document includes a dedicated `2330` example section

#### 2881
- company: `富邦金融控股股份有限公司`
- classification:
  - `Financial`
- current reusable fields:
  - price from `2881_profile.json`
  - BVPS / EPS / ROE from `2881_annual.csv`
  - latest quarterly earnings trend from `2881_quarterly.csv`
  - PB / PE / dividend yield snapshot from `top100_valuation_snapshot.csv` and profile
- Buffett 3.0 calculation path:
  - estimate `Sustainable ROE`
  - compute `Sustainable EPS = BVPS × Sustainable ROE`
  - run `ROE-adjusted PB`
  - run `DDM`
  - run `Normalized PE`
  - run `Residual Income`
  - apply default scenario weighting unless uncertainty requires stricter weighting
  - apply macro / Taiwan risk / reality modifiers
- current practical note:
  - this ticker is useful to prove the engine does not incorrectly reuse compounder logic for financials

#### 2603
- company: `長榮海運股份有限公司`
- classification:
  - `Cyclical`
- current reusable fields:
  - price from `2603_profile.json`
  - multi-year EPS / FCF / BVPS from `2603_annual.csv`
  - quarterly cyclicality pattern from `2603_quarterly.csv`
  - PE / PB / dividend yield snapshot from `top100_valuation_snapshot.csv` and profile
- Buffett 3.0 calculation path:
  - build `10-year normalized EPS` or longest available mid-cycle EPS proxy
  - do not use current or peak-year EPS directly
  - run `Mid-cycle EPS`
  - attempt `Normalized EV/EBITDA` only when cash / debt detail is available
  - otherwise flag `Data unavailable. Assumption required.`
  - run `Replacement / Asset Value` or interim balance-sheet proxy
  - run `Trough PB / Downside Value`
  - use `high uncertainty` scenario weighting if cyclicality is severe
  - apply macro / Taiwan risk / reality modifiers
- current practical note:
  - this is the best V1 test for the document's rule: never value cyclicals using peak EPS

#### 2412
- company: `中華電信股份有限公司`
- classification:
  - `Defensive / Dividend`
- current reusable fields:
  - price from `2412_profile.json`
  - EPS / FCF / BVPS / ROE from `2412_annual.csv`
  - quarterly stability pattern from `2412_quarterly.csv`
  - PE / PB / dividend yield snapshot from `top100_valuation_snapshot.csv` and profile
- Buffett 3.0 calculation path:
  - build normalized EPS from stable multi-year average
  - build normalized dividend capacity
  - run `Dividend Yield Band`
  - run `DDM`
  - run `Normalized PE`
  - run `FCF Yield`
  - apply default scenario weighting
  - apply macro / Taiwan risk / reality modifiers
- current practical note:
  - this is the best V1 test for defensive/yield logic and a dividend-first valuation path

### Immediate Buffett 3.0 Working Sequence
Do not code before reconfirming the user accepts this sequence:
1. finalize the core calculation spec exactly against the Buffett 3.0 document
2. define required output schema for all four company types
3. document per-ticker input mapping for `2330 / 2881 / 2603 / 2412`
4. decide which missing inputs remain optional vs blocking
5. only then begin model-engine implementation

### Next Best Tasks
Priority order for next session:
1. Launch the app in browser and visually compare the new search/ribbon/right-rail layout against the approved mockup screenshot.
2. Tighten any remaining spacing, card density, and cross-column rhythm after a visual pass in the actual rendered app.
3. Replace or supplement blocked MOPS monthly revenue source.
4. Add historical valuation series ingestion so valuation bands can become more meaningful.
5. Consider a second-pass interaction polish for focus-model switching and report/download affordances once browser validation is done.

### Important Caution
This folder may not be a git repository. Do not rely on git history for rollback unless confirmed.

Do not use destructive commands. Do not revert user changes.

## Current Goal
Build one runnable Taiwan stock valuation workspace that:
- keeps each model logically separate
- uses one shared data root
- can download or reuse the required TOP100 Taiwan stock inputs
- can generate integrated model outputs
- can be launched through a Streamlit app
- aligns the app UI to the approved dashboard mockup as closely as possible
- makes every valuation label explainable to end users

## Workspace
- Workspace root: `D:\Codex projects\TW Valuation models`
- Shared data root: `D:\Claude projects\主觀看盤\data`
- Reference date during this build: `2026-05-15` (Asia/Taipei)

## Selected Models
The integrated app currently wires these model families:
1. `buffett-stock-tw`
2. `buffett-stock-tw-2.0`
3. `IMFS_TW_Stock`
4. `tw-buffett-quant-app`
5. `Taiwwan-stock-hybrid-model`

## Planning Documents In Workspace
- `APP_ARCHITECTURE_PLAN.md`
- `UI_CONTENT_PLAN_ZH_TW.md`
- `DATA_DOWNLOADER_BLUEPRINT.md`
- `DATA_FIELD_MAPPING.md`
- `DATA_GAP_AUDIT_TEMPLATE.md`
- `DATA_GAP_AUDIT_FIRST_PASS.md`
- `MODEL_ADAPTER_PLAN.md`
- `IMPLEMENTATION_ROADMAP.md`

## Implementation Status

### Module 1 Completed: Shared Data Layer
Implemented package and CLI under `tw_valuation_models/` with working commands:
- `python -m tw_valuation_models discover`
- `python -m tw_valuation_models normalize`
- `python -m tw_valuation_models validate`

Normalized outputs:
- `artifacts/normalized/universe_snapshot.csv`
- `artifacts/normalized/valuation_snapshot.csv`
- `artifacts/normalized/fundamentals_snapshot.csv`
- `artifacts/normalized/price_daily.csv`
- `artifacts/normalized/benchmark_daily.csv`
- `artifacts/normalized/normalization_summary.json`

Latest verified normalization counts:
- universe rows: `1973`
- valuation snapshot rows: `1960`
- fundamentals snapshot rows: `222`
- price daily rows: `623006`
- price daily tickers: `241`
- benchmark daily rows: `2765`

### Module 2 Completed: Validation Layer
Validation output:
- `artifacts/validation/validation_summary.json`

Latest verified validation findings:
1. `listing_date_missing = 1086`
2. valuation snapshot still has no historical date column
3. fundamentals snapshot still has no `report_date` or `fiscal_period`
4. current raw price domain has no `adjusted_close`

### Module 3 Completed: TW Hybrid Adapter Proof
Working commands:
- `python -m tw_valuation_models check-tw-hybrid-runtime`
- `python -m tw_valuation_models prepare-tw-hybrid --ticker 2330`
- `python -m tw_valuation_models probe-tw-hybrid --ticker 2330`

Verified result:
- original `strategy.py` imports successfully
- source feature engineering runs successfully on prepared shared-data bundle

### Module 4 Completed: TOP100 Dataset Builder
Working command:
- `python -m tw_valuation_models build-top100`

Generated dataset root:
- `artifacts/datasets/top100`

Generated files include:
- `top100_universe.csv`
- `top100_valuation_snapshot.csv`
- `top100_fundamentals_snapshot.csv`
- `prices/<ticker>.csv`
- `TAIEX.csv`
- `fundamentals/<ticker>_annual.csv`
- `fundamentals/<ticker>_quarterly.csv`
- `fundamentals/<ticker>_profile.json`
- `annual_financials_index.csv`
- `quarterly_financials_index.csv`
- `monthly_revenue_history.csv`
- `dataset_summary.json`

Latest verified dataset result:
- top100 count: `100`
- reused shared/raw price files: `100`
- downloaded missing price files: `0`
- reused local fundamental profiles on rerun: `100`
- monthly revenue rows: `0`

Confirmed TOP100 selection rule:
- rank `artifacts/normalized/fundamentals_snapshot.csv` by `market_cap`
- take the largest `100` tickers

### Module 5 Completed: Integrated Model Results
Working command:
- `python -m tw_valuation_models build-results`

Generated result files:
- `artifacts/results/top100_model_results.csv`
- `artifacts/results/top100_model_results_summary.json`

Latest verified result:
- result count: `100`

Integrated output columns include:
- Buffett v1 intrinsic value / margin of safety / signal
- Buffett v2 intrinsic value / margin of safety / signal
- IMFS route / model / intrinsic value / gap / signal
- TW Buffett Quant score / action / signal
- TW Hybrid target price / expected return / signal
- per-model warning payloads

### Module 6 Completed: End-to-End Run Command
Working command:
- `python -m tw_valuation_models run-all`

Latest verified run-all result:
- normalize: success
- validate: success
- build-top100: success
- build-results: success

### Module 7 Rebuilt: Streamlit App And Mockup Alignment
App entry file:
- `app.py`

This module was rebuilt from scratch after the prior draft became visually inconsistent with the approved mockup and accumulated broken display logic.

Current verified app structure:
1. top header bar with title and update metadata
2. left control rail with stock selection, date block, model selection, execution options, and completeness block
3. top model toolbar with five model status chips and execution button
4. `模型總覽` card section with one card per active model
5. `單模型詳情` section with three-column overview layout
   - left valuation result block
   - center historical price / intrinsic value chart
   - right key-indicator block
6. detail tabs:
   - `總覽`
   - `估值輸入`
   - `模型解釋`
   - `風險提示`
7. `下載報告` action
8. bottom warning banner
9. right-side panels for design guidance and valuation-rule transparency

What was fixed in this rebuild:
1. removed the corrupted HTML rendering path that caused raw `<div ...>` fragments to appear in cards
2. replaced the previous `st.line_chart(...)` detail chart path that was throwing the `unexpected keyword argument 'closed'` error
3. rebuilt all user-facing labels in Traditional Chinese
4. made valuation tags explainable instead of opaque
5. restored the app goal of following the approved dashboard layout rather than treating the mockup as a loose reference
6. changed the left rail title from a ribbon shape to a full capsule block to match the approved layout more closely
7. merged the top-right guidance area back into a single design-spec card with internal sections instead of multiple unrelated cards
8. rebuilt the model-card bottom stat rows so `目前股價 / 內在價值或目標價或建議動作 / 信心度` read as explicit rows rather than loose text
9. replaced deprecated Streamlit `use_container_width` calls with `width="stretch"` so the app runs without those legacy UI warnings

### Module 8 Added: Transparent Valuation Criteria
The app now exposes six user-facing rating bands:
1. `低估`
2. `合理偏低`
3. `合理`
4. `合理偏高`
5. `昂貴`
6. `非常昂貴`

Current visible rules in the UI:

For value models (`buffett_v1`, `buffett_v2`, `imfs`):
- formula: `(內在價值 - 目前股價) / 內在價值`
- `低估`: `>= 25%`
- `合理偏低`: `10% 至 25%`
- `合理`: `-5% 至 10%`
- `合理偏高`: `-20% 至 -5%`
- `昂貴`: `-50% 至 -20%`
- `非常昂貴`: `<= -50%`

For Quant:
- based on `quant_score`
- `低估`: `>= 80`
- `合理偏低`: `65 至 79.9`
- `合理`: `50 至 64.9`
- `合理偏高`: `40 至 49.9`
- `昂貴`: `25 至 39.9`
- `非常昂貴`: `< 25`

For Hybrid:
- based on `hybrid_return_pct`
- `低估`: `>= 20%`
- `合理偏低`: `8% 至 19.9%`
- `合理`: `-3% 至 7.9%`
- `合理偏高`: `-10% 至 -3.1%`
- `昂貴`: `-20% 至 -10.1%`
- `非常昂貴`: `<= -20%`

### Module 9 Clarified: Original Logic Alignment Status
Current integration status after code review:

1. `IMFS`
- uses original route classifier and valuation engine from `D:\Claude projects\IMFS_TW_Stock`
- `Route B / RULE_OF_40` does not produce intrinsic value by design
- UI should label this as a quality signal path, not generic missing data

2. `TW Buffett Quant`
- uses original strict-mode evaluation engine from `D:\Claude projects\TWSE aihedge\tw-buffett-quant-app`
- still depends on integrated input tables built inside this workspace
- monthly revenue remains a known upstream gap

3. `TW Hybrid`
- feature engineering and training skeleton match the original project structure closely
- signal threshold was corrected toward the original app default (`BUY > +5%`, `SELL < -5%`, else `HOLD`)
- still not yet a fully direct source-runner integration

4. `Buffett v1 / v2`
- still run through the integrated workspace implementation in `tw_valuation_models/models/buffett_dcf.py`
- not yet proven to be a direct source-equivalent runner

Implication:
- the workspace is runnable
- IMFS and Quant are closer to original source behavior
- Hybrid is partially aligned
- Buffett models still need direct-source equivalence work if the requirement is strict formula parity

## Current Runnable Commands

### One-shot
```powershell
python -m tw_valuation_models run-all
```

### Step-by-step
```powershell
python -m tw_valuation_models normalize
python -m tw_valuation_models validate
python -m tw_valuation_models build-top100
python -m tw_valuation_models build-results
python -m streamlit run app.py
```

## Verification Performed
1. `python -m compileall app.py`
2. imported `app.py` successfully in bare mode after bootstrapping local `.deps`

### Module 10 Added: Dark Production Dashboard Pass
This pass moved the app from the earlier light mockup drift back toward the approved dark forest research-terminal direction.

What changed:
1. replaced the global light ivory theme with a dark forest / charcoal / gold palette in `app.py`
2. removed the right-side `設計規格指南` presentation panel
3. rebuilt the right rail into product-useful panels:
   - `投資判讀`
   - `評級說明`
   - `相關檔案`
   - `快速操作`
   - `Log`
   - `Ledger`
4. kept the card area high-density instead of reverting to a sparse marketing layout
5. upgraded the detail chart toward a darker research-terminal style with valuation bands and reference lines
6. added sidebar system status copy under the completeness block

Implementation notes:
- `Log` currently derives from model outputs, IMFS route state, monthly revenue gap status, and latest run metadata
- `Ledger` currently acts as a research timeline scaffold seeded from the selected row and latest intrinsic values
- this pass focused on production layout and dashboard usefulness, not yet strict 1:1 parity for every micro-spacing detail

Verification for this pass:
1. `python -m compileall app.py`
2. `PYTHONPATH=.deps python -c "import app"` equivalent bare import check completed successfully

Remaining next:
1. visually verify the new dark layout in an actual Streamlit browser session
2. continue tightening card spacing, toolbar density, and right-rail hierarchy against the approved mockup
3. continue direct-source parity work for Buffett v1 / v2 if strict formula equivalence remains required

### Module 10 Follow-up: Theme Consistency Fix
User screenshot showed two production issues:
1. the Streamlit native sidebar still appeared light grey even though the central dashboard was dark
2. the right rail `相關檔案 / 快速操作` HTML rendered as a white code block

Fixes applied:
- added stronger Streamlit sidebar/header CSS selectors for dark theme consistency
- hid the default Streamlit deploy/header strip background
- wrapped the affected right-rail HTML blocks with `textwrap.dedent(...).strip()` so Markdown no longer treats indented HTML as code

Verification:
- `python -m compileall app.py`
- `.deps` bare import check completed successfully

### Module 10 Follow-up: Mockup Content Gap Fix
User screenshot showed the dark theme was closer, but the content density still missed important mockup details:
1. detail summary block was too thin and did not show confidence / value rows like the mockup
2. key metrics were rendered as a native Streamlit dataframe instead of a dark product panel
3. detail chart lacked a surrounding research-panel treatment and caption
4. right rail rating explanation was too generic and needed explicit threshold lines
5. related files and quick actions needed to feel like real product cards, not loose helper text

Fixes applied:
- added custom detail summary stat rows for fair value / current price / confidence
- added custom `render_key_metrics_panel(...)` to replace the native dataframe in the visible overview
- added a chart shell and model-summary strip under the detail chart
- changed right rail rating explanation into explicit threshold rows
- tightened related-file and quick-action cards

Verification:
- `python -m compileall app.py`
- `.deps` bare import check completed successfully
3. launched Streamlit successfully in headless mode through the bootstrapped local environment
4. confirmed local serving startup on `http://localhost:8519`

## Important Files Added Or Updated
- `app.py`
- `requirements.txt`
- `tests/test_shared_data.py`
- `tw_valuation_models/__init__.py`
- `tw_valuation_models/__main__.py`
- `tw_valuation_models/config.py`
- `tw_valuation_models/csv_utils.py`
- `tw_valuation_models/deps.py`
- `tw_valuation_models/shared_data.py`
- `tw_valuation_models/dataset.py`
- `tw_valuation_models/portfolio_builder.py`
- `tw_valuation_models/source_bridge.py`
- `tw_valuation_models/cli.py`
- `tw_valuation_models/models/__init__.py`
- `tw_valuation_models/models/buffett_dcf.py`
- `tw_valuation_models/adapters/__init__.py`
- `tw_valuation_models/adapters/base.py`
- `tw_valuation_models/adapters/tw_hybrid.py`

## Known Gaps That Remain
These do not block the app from running, but they are real data-quality or fidelity gaps and should not be forgotten.

1. `valuation.csv` is still a snapshot table, not a historical valuation series.
2. `yfinance_fundamentals.csv` is still a snapshot table, not a point-in-time financial history table.
3. `monthly_revenue_history.csv` is currently empty because MOPS access is blocked by the site security page in this environment.
4. TW Buffett Quant therefore runs with incomplete monthly-revenue context.
5. IMFS can legitimately return no intrinsic value for some routes because of model logic, not because the pipeline crashed.
6. the current app is structurally much closer to the approved mockup, but iconography, exact spacing, and some decorative details can still be tightened for stricter 1:1 fidelity.

## Important Observations
1. The TOP100 pipeline depends on ticker normalization. `pandas` reading tickers as integers caused an empty universe once; that bug has already been fixed.
2. The TW Hybrid integrated runner completes on all 100 names after filtering `NaN` and `inf` rows before training.
3. Shared data reuse is working. Re-runs are much faster because price files and downloaded per-ticker fundamentals are reused.
4. The dashboard now shows the valuation criteria to end users instead of hiding them behind internal logic.

## Recommended Next Follow-up
If a future session continues from here, the highest-value next improvement is:
1. replace the blocked MOPS monthly revenue source with a reliable alternative
2. add historical valuation series ingestion
3. add richer fundamentals period metadata
4. continue tightening spacing, iconography, and small decorative chart styling for stricter 1:1 visual fidelity

### Module 11 Added: Original Formula And Logic Alignment
User explicitly accepted the rule:
- all models must follow the original project formula and logic unless the original logic has a bug

Changes applied:
1. Buffett v1 / v2 DCF constants in `tw_valuation_models/models/buffett_dcf.py` were aligned to original `buffett-stock-tw/src/constants.ts`
   - sector exit multiples now match the original source
   - FCF conversion threshold changed to `0.6`
   - FCF minimum factor changed to `0.4`
   - signal labels now match original `dcf-engine.ts` wording: `低估 / 合理價位 / 高估`
2. Hybrid integration now imports and uses original source core logic from:
   - `D:\Claude projects\TW hybrid model\台股法說會估值\Taiwwan-stock-hybrid-model\strategy.py`
   - direct usage: `compute_technical_features`
   - direct usage: `FEATURE_COLS`
   - direct usage: `EnsembleValuationModel`
3. Result summary now records `model_logic_sources` so downstream UI/reporting can disclose logic provenance.
4. Dashboard right rail now includes a visible `模型邏輯` note explaining original-logic priority.

Current model logic status:
- Buffett v1 / v2: formula port aligned to original TS DCF engine and hook logic
- IMFS: direct original route classifier and valuation engine
- TW Buffett Quant: direct original strict mode engine with integrated input tables
- TW Hybrid: direct original strategy core functions/classes

Verification:
- `python -m compileall tw_valuation_models`
- original Hybrid strategy import check
- `PYTHONPATH=.deps python -m tw_valuation_models build-results`
- latest build-results completed for `100` tickers and wrote `artifacts/results/top100_model_results.csv`

## Handoff Reminder
Before changing architecture, read this file first and check:
- `artifacts/datasets/top100/dataset_summary.json`
- `artifacts/results/top100_model_results_summary.json`
- `artifacts/validation/validation_summary.json`

### Module 12 Added: Streamlit HTML Rendering Fixes
Issue explained and fixed:
- Some dashboard panels rendered raw `<div ...>` text because Streamlit/Markdown treated indented multi-line HTML as code blocks.
- The single-model chart had an empty box above the real chart because a custom `<div class="chart-shell">` was opened with `st.markdown`, then a Streamlit chart component was rendered outside that HTML container. Streamlit does not reliably nest later components inside previous raw HTML wrappers.

Changes applied:
1. `render_key_metrics_panel()` now emits one complete quoted HTML block and no longer breaks Python syntax.
2. The detail chart now remains a self-contained base64 image inside one complete `chart-shell` HTML block.
3. Removed the half-open `detail-section` wrapper around Streamlit tabs/columns.
4. Right-rail `模型摘要`, `Log`, and `Ledger` now render as complete HTML strings instead of fragmented open/loop/close markdown blocks.
5. User-facing model formulas and calculation logic were not changed in this module.

Verification:
- `python -m compileall app.py tw_valuation_models`
- `PYTHONPATH=.deps python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

### Module 13 Added: Native Widget Theme And Chart Readability
Issue explained and fixed:
- White boxes came from native Streamlit controls (`selectbox`, `date_input`, buttons, download buttons) using default light styling inside the dark dashboard.
- The chart was present, but it was too dim/small and the UI did not explain whether it was live.

Changes applied:
1. Added dark-theme CSS overrides for Streamlit sidebar select/date controls, checkbox/radio labels, primary/secondary buttons, download buttons, hover states, and disabled states.
2. Enlarged and brightened the single-model detail chart.
3. Updated the chart caption to state clearly that it is not real-time streaming; it redraws from the latest loaded price history whenever the app reruns or the stock/model changes.

Verification:
- `python -m compileall app.py tw_valuation_models`
- `PYTHONPATH=.deps python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

### Module 14 Added: Mockup-Style Detail Chart Upgrade
Issue explained and fixed:
- The previous chart was visible but still closer to a simple line chart than the approved mockup.
- The mockup detail area expects a denser professional chart: price action, shaded valuation/volatility band, reference lines, volume, and dark terminal styling.

Changes applied:
1. Detail chart now uses OHLC data to draw compact red/green candle-style price action.
2. Added a lower volume panel with matching up/down colors.
3. Kept the valuation/target reference line and safety-margin upper/lower lines when a reference value exists.
4. Added 20-day moving line and volatility band.
5. Enlarged chart shell height and plot dimensions for better readability.

Verification:
- `python -m compileall app.py tw_valuation_models`
- `PYTHONPATH=.deps python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

### Module 15 Added: IMFS Route B Valuation Bridge And Tighter Card Layout
Issue explained and fixed:
- The original IMFS Rule of 40 Route B only surfaced quality scoring and premium eligibility, so the dashboard could not show a per-share fair value for that route.
- The model overview cards still had too much empty vertical space around the sparkline area, which drifted away from the target mockup.

Changes applied:
1. `tw_valuation_models/portfolio_builder.py` now builds an IMFS Route B bridge using estimated revenue growth, estimated profit margin, projected EPS, and a justified P/E derived from the quality score.
2. Route B rows now write `imfs_est_revenue_growth_pct`, `imfs_est_profit_margin_pct`, `imfs_quality_score`, `imfs_premium_eligible`, `imfs_justified_pe`, and `imfs_projected_eps` into `top100_model_results.csv`.
3. `app.py` now presents IMFS Route B as:
   - card metric: `品質分數`
   - fair value label: `每股合理價`
   - summary copy: estimated growth, estimated margin, and premium eligibility
4. The single-model `估值輸入` tab now includes `預估營收成長`, `預估利潤率`, `品質分數`, and `溢價資格` for IMFS Route B.
5. Sparkline rendering was tightened by adding explicit vertical bounds/padding in matplotlib and reducing card/sparkline height to remove the large empty gap above the line.

Verification:
- `python -m compileall app.py tw_valuation_models`
- `PYTHONPATH=.deps python -m tw_valuation_models build-results`
- Restarted Streamlit on `http://127.0.0.1:8501`

### Module 16 Added: Buffett 3.0 V1 Core Spec Draft
Purpose:
- convert Buffett 3.0 planning notes into one concrete implementation spec before any Buffett 3.0 UI work

What was added:
1. new document `BUFFETT_3_0_V1_SPEC.md`
2. documented the approved master formula and mandatory modifier order
3. defined a V1 engine shape:
   - classifier
   - normalization layer
   - valuation-leg layer
   - scenario layer
   - modifier layer
   - auditable payload layer
4. documented normalization rules for:
   - `high_quality_compounder`
   - `financial`
   - `cyclical`
   - `defensive_dividend`
5. documented approved valuation legs and weights by company type
6. documented required output schema and missing-data policy
7. mapped current local reusable sample inputs for:
   - `2330`
   - `2881`
   - `2603`
   - `2412`

Important current conclusion:
- Buffett 3.0 V1 can start with the current dataset for classification, normalized EPS/BVPS/ROE/FCF work, and price comparison.
- Full DDM/dividend-yield rigor and cyclical EV/EBITDA still need additional source data or explicit temporary assumption rules.

Still blocked pending confirmation before engine coding:
1. parameter tables for fair PE / required FCF yield / persistence factor / cost of equity / long-term growth
2. modifier bucket values for macro / Taiwan risk / reality validation
3. whether missing legs may be emitted as `not_ready` in V1
4. whether dividend methods may use explicit assumption inputs until dividend-history sourcing is added

Verification:
1. extracted current sample inputs from local dataset files for `2330 / 2881 / 2603 / 2412`
2. confirmed the spec stays within the Buffett 3.0 planning constraints already recorded in this file
- Visual browser check confirmed for ticker `2330`:
  - `IMFS 品質分數 76.6`
  - `每股合理價 2,528.68`
  - `預估營收成長 31.6%`
  - `預估利潤率 45.0%`
  - `溢價資格：可享溢價`
### Module 17 Added: Buffett 3.0 Official Data Loader Implementation Plan
Purpose:
- convert the Buffett 3.0 web-research result into a concrete downloader implementation sequence before engine coding

What was decided:
1. Buffett 3.0 should move to an official-source-first loader path
2. TWSE OpenAPI is now the primary source family for Buffett 3.0 V1 data acquisition
3. company IR / annual reports remain audit cross-check sources, not the default automated loader path
4. the current `dataset.py` flow is not yet sufficient because it still leans on:
   - legacy MOPS monthly revenue HTML scraping
   - local snapshot reuse
   - `yfinance`-style fundamentals snapshots

Confirmed official source mapping:
1. valuation snapshot:
   - `exchangeReport/BWIBBU_ALL`
2. dividend history:
   - `opendata/t187ap45_L`
3. monthly revenue:
   - `opendata/t187ap05_L`
4. non-financial income statement / balance sheet:
   - `opendata/t187ap06_L_ci`
   - `opendata/t187ap07_L_ci`
5. financial income statement / balance sheet:
   - `opendata/t187ap06_L_basi`
   - `opendata/t187ap07_L_basi`

Implementation decision for the loader:
1. keep the existing shared-data normalization path for current integrated models
2. add Buffett 3.0-specific official data download support instead of forcing Buffett 3.0 to depend on old snapshot assumptions
3. route financial holdings like `2881` through the financial statement endpoints
4. route names like `2330`, `2603`, and `2412` through the general-company statement endpoints
5. persist the new official-source outputs into reusable artifacts rather than ad hoc research notes

Planned Buffett 3.0 output tables:
1. `buffett3_valuation_snapshot.csv`
2. `buffett3_dividend_history.csv`
3. `buffett3_monthly_revenue_history.csv`
4. `buffett3_annual_fundamentals.csv`
5. `buffett3_quarterly_fundamentals.csv`
6. `buffett3_source_manifest.json`

Immediate to-do sequence now recorded:
1. replace `fetch_monthly_revenue_history()` with TWSE OpenAPI monthly revenue ingestion
2. add official valuation snapshot download
3. add official dividend-history download
4. add official annual/quarterly statement ingestion with financial vs non-financial routing
5. add validation and manifest coverage for the new domains
6. re-run `2330 / 2881 / 2603 / 2412` as the mandatory loader regression set

Important current conclusion:
- the Buffett 3.0 blocker has shifted from formula design to data-loader execution
- the next highest-value coding step is downloader work, not UI work
- once the loader is in place, Buffett 3.0 can be recalculated from mostly official TWSE data instead of mixed local assumptions

Files updated for this checkpoint:
1. [IMPLEMENTATION_ROADMAP.md](/D:/Codex%20projects/TW%20Valuation%20models/IMPLEMENTATION_ROADMAP.md)
2. [TODO.md](/D:/Codex%20projects/TW%20Valuation%20models/TODO.md)
3. [working.md](/D:/Codex%20projects/TW%20Valuation%20models/working.md)
### Module 18 Added: Buffett 3.0 Official Loader First Implementation
Purpose:
- implement the first real Buffett 3.0 data-loader upgrade after the planning-only pass

Code changes completed:
1. updated [tw_valuation_models/dataset.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/dataset.py)
2. added [tests/test_dataset.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_dataset.py)
3. kept existing `build_top100_dataset()` behavior, but added an official Buffett 3.0 sidecar download set

What the loader now does:
1. monthly revenue now tries official TWSE OpenAPI first and only falls back to the old MOPS HTML scraper if needed
2. `build_top100_dataset()` now also writes Buffett 3.0-specific official-source artifacts:
   - `buffett3_valuation_snapshot.csv`
   - `buffett3_dividend_history.csv`
   - `buffett3_monthly_revenue_history.csv`
   - `buffett3_annual_fundamentals.csv`
   - `buffett3_quarterly_fundamentals.csv`
   - `buffett3_source_manifest.json`
3. added official TWSE endpoint support for:
   - `exchangeReport/BWIBBU_ALL`
   - `opendata/t187ap45_L`
   - `opendata/t187ap05_L`
   - `opendata/t187ap06_L_ci`
   - `opendata/t187ap07_L_ci`
   - `opendata/t187ap06_L_basi`
   - `opendata/t187ap07_L_basi`
4. added financial-company routing logic, with an industry-text rule plus a conservative `28xx` fallback for financial holdings
5. added source-manifest output so Buffett 3.0 official files are auditable

Verification completed:
1. `python -m compileall tw_valuation_models tests`
2. `python -m unittest tests.test_shared_data tests.test_dataset`
3. live TWSE endpoint check against `2330 / 2881 / 2603 / 2412`

Live-check result from the new loader:
1. valuation snapshot rows: `4`
2. dividend history rows: `5`
3. monthly revenue rows: `3`
4. annual official fundamentals rows: `0`
5. quarterly official fundamentals rows: `2`

Important current conclusion:
- the official loader path is now real, not just planned
- Buffett 3.0 can already pull current official valuation, dividend, and monthly revenue data into reusable artifacts
- statement ingestion is only partially complete in practice so far; quarterly rows are coming through, but annual coverage is not yet there in the live check

Remaining known gaps after Module 18:
1. dividend parsing for some financial names, especially `2881`, still needs business-rule review against company IR because the TWSE dividend table may not line up 1:1 with the total cash-dividend figure we want for Buffett 3.0
2. annual official statement coverage is still thin in the current live check
3. statement field mapping is intentionally conservative and should be expanded after inspecting more raw endpoint rows
4. merged statement output still emits a pandas `FutureWarning` from the coalescing helper; it is non-blocking but worth cleaning up later

Best next coding step:
1. inspect raw financial-statement payloads for `2881` and one non-financial name in more detail
2. improve annual vs quarterly statement period detection
3. lock the dividend-per-share rule for financial holdings
4. then wire Buffett 3.0 calculations to these new official-source tables
### Module 19 Added: Buffett 3.0 Coverage-Aware Official Loader
Purpose:
- harden the first Buffett 3.0 official loader so missing TWSE coverage does not create false matches or empty statement tables

What was improved after Module 18:
1. statement routing is now coverage-aware, not just category-aware
2. false-positive ticker extraction risk was reduced by tightening code-field matching
3. official statement gaps now fall back to the existing per-ticker fundamentals files already downloaded into the top100 dataset
4. source manifests now record requested tickers, covered tickers, and missing tickers for each Buffett 3.0 data domain

Important discovery from live TWSE endpoint inspection:
1. `t187ap06_L_ci` and `t187ap07_L_ci` currently provide usable rows for `2412` and `2603`
2. `2330` was not present in the current official statement slice tested here
3. `2881` was not present in the current official statement slice tested here
4. `t187ap06_L_basi` currently exposes only a narrow financial subset in this environment
5. `t187ap07_L_basi` looked effectively unusable in this environment for the tested flow

Implementation outcome:
1. official statement rows are still preferred wherever they exist
2. when official statement rows are missing, Buffett 3.0 annual/quarterly tables now fall back to:
   - `fundamentals/<ticker>_annual.csv`
   - `fundamentals/<ticker>_quarterly.csv`
3. output tables stay reusable and auditable because every row keeps a `source_name`
4. manifest files now make incomplete official coverage visible instead of hiding it

Verification completed:
1. `python -m unittest tests.test_shared_data tests.test_dataset`
2. `python -m compileall tw_valuation_models tests`
3. live rebuild against the real [artifacts/datasets/top100](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/datasets/top100) folder

Latest live result for `2330 / 2881 / 2603 / 2412` on `2026-05-15`:
1. valuation rows: `4`
2. dividend rows: `5`
3. monthly revenue rows: `3`
4. annual rows: `9`
5. quarterly rows: `15`
6. official statement tickers actually covered by TWSE in this run: `2412`, `2603`

Important current conclusion:
- Buffett 3.0 data loading is now usable for implementation work even when official TWSE statement coverage is partial
- the loader is honest about where official data exists and where fallback data is being used
- the next meaningful step is to wire the Buffett 3.0 calculation engine to these new `buffett3_*` tables

Remaining known gaps:
1. `2330` and `2881` still need stronger official statement coverage if we want a fully official-only Buffett 3.0 path
2. financial-holding dividend interpretation should still be checked against company IR before finalizing the valuation engine defaults
3. if needed later, a second source family can be added for official-statement backfill, but that is no longer blocking V1 engine work
### Module 20 Added: Buffett 3.0 Engine, Results Pipeline, And App Integration
Purpose:
- turn the Buffett 3.0 planning work and official-source loader outputs into a runnable model inside the shared valuation system

Code changes completed:
1. added [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py)
2. updated [tw_valuation_models/portfolio_builder.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/portfolio_builder.py)
3. refined [tw_valuation_models/dataset.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/dataset.py) fallback behavior for annual vs quarterly statement coverage
4. added [tests/test_buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_buffett_three.py)
5. expanded [tests/test_dataset.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_dataset.py)
6. integrated Buffett 3.0 into [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)

What is now implemented:
1. Buffett 3.0 now classifies stocks into four V1 model families:
   - `high_quality_compounder`
   - `financial`
   - `cyclical`
   - `defensive_dividend`
2. the model consumes the new official-loader artifacts:
   - `buffett3_valuation_snapshot.csv`
   - `buffett3_dividend_history.csv`
   - `buffett3_monthly_revenue_history.csv`
   - `buffett3_annual_fundamentals.csv`
   - `buffett3_quarterly_fundamentals.csv`
3. the engine produces per-ticker intrinsic value, margin-of-safety, signal, type, quality flags, manual-review flags, and leg-by-leg valuation payloads
4. results generation now writes Buffett 3.0 payload JSON files under [artifacts/results/buffett3_payloads](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/buffett3_payloads)
5. top-level model results now include:
   - `buffett3_intrinsic`
   - `buffett3_mos`
   - `buffett3_signal`
   - `buffett3_type`
   - `buffett3_quality_flags`
6. the Streamlit app now recognizes Buffett 3.0 as a first-class model in the shared comparison flow

Important implementation details:
1. cyclical names intentionally expose the EV or EBITDA path as `not_ready` when required debt or EBITDA inputs are still incomplete; the remaining usable legs are reweighted rather than silently fabricating a number
2. annual and quarterly fallback coverage are now handled separately, which fixed the earlier missing-normalization issue for names like `2603`
3. official TWSE statement rows are still preferred, but fallback fundamentals remain available when official statement coverage is partial

Verification completed:
1. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
2. `python -m compileall tw_valuation_models tests app.py`
3. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -m tw_valuation_models build-top100 --top-n 100`
4. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -m tw_valuation_models build-results --top-n 100`
5. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

Latest live dataset/result status on `2026-05-15`:
1. Buffett 3.0 official loader output from the rebuilt top100 dataset:
   - valuation rows: `100`
   - dividend rows: `104`
   - monthly revenue rows: `95`
   - annual rows: `477`
   - quarterly rows: `185`
2. official statement coverage is still partial in practice; names such as `2330` and `2881` continue to rely on fallback fundamentals for some statement history
3. the full model-results build now completes for the top 100 universe and writes Buffett 3.0 values into the shared comparison table

Validation snapshot for the four required Buffett 3.0 reference names:
1. `2330`
   - type: `high_quality_compounder`
   - intrinsic value: `799.566`
   - margin of safety: `-64.7768%`
   - signal: `避開`
2. `2881`
   - type: `financial`
   - intrinsic value: `71.153`
   - margin of safety: `-24.7854%`
   - signal: `避開`
3. `2603`
   - type: `cyclical`
   - intrinsic value: `209.119`
   - margin of safety: `-1.1258%`
   - signal: `持有`
4. `2412`
   - type: `defensive_dividend`
   - intrinsic value: `96.773`
   - margin of safety: `-29.6196%`
   - signal: `避開`

Important current conclusion:
1. Buffett 3.0 is now implemented end to end across loader, engine, results build, and app integration
2. the current blocker is no longer model plumbing; it is assumption refinement and official-data coverage quality for a few edge cases
3. the system can now compare Buffett 3.0 against the older Taiwan Buffett Quant output on the same universe without manual recalculation

Remaining known gaps after Module 20:
1. `2881` dividend interpretation should still be confirmed against company IR if we want institution-grade handling for financial holdings
2. `2330` and `2881` still lack a fully official-only statement path in the current TWSE endpoint coverage
3. [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py) contains older mojibake text outside the Buffett 3.0 core logic; the file now compiles and bare-runs, but text cleanup is still worthwhile
4. cyclical EV or EBITDA support is intentionally visible as incomplete rather than guessed; if we later add reliable debt and EBITDA history, the cyclical branch can be upgraded

Best next coding step:
1. clean up Buffett 3.0 presentation details in the app so the new model renders with polished Traditional Chinese labels and summaries
2. tighten dividend/business-rule handling for financial holdings
3. optionally add a second statement-source backfill path if fully official-only coverage becomes a hard requirement
### Module 21 Added: Buffett 3.0 App Presentation Polish
Purpose:
- improve Buffett 3.0 readability in the Streamlit UI without reopening the wider legacy-text cleanup problem

Code changes completed:
1. updated the Buffett 3.0 `value_label` in [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. added a `format_buffett3_type()` helper for readable company-type labels
3. replaced the Buffett 3.0 summary and basis copy with clearer Traditional Chinese text
4. set the Buffett 3.0 fair-value label to `合理價`

Verification completed:
1. `python -m compileall app.py`
2. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

Important current conclusion:
1. Buffett 3.0 now presents a readable metric label, valuation summary, basis description, and company-type mapping in the app path we just added
2. the app still starts successfully in bare mode after the text cleanup
3. broader mojibake remains in older app copy, but the Buffett 3.0 path itself is now in better shape for comparison use

Remaining known gaps after Module 21:
1. terminal output still renders some Traditional Chinese strings poorly because of existing encoding/display issues, so browser-side verification is still the better final UI check
2. the rest of [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py) still contains legacy garbled labels outside the Buffett 3.0 slice
3. a full app text cleanup should be handled as a separate pass to avoid mixing UI copy repair with valuation logic work

### Module 22 Added: Buffett 3.0 Detail Explainability Pass
Purpose:
- continue the Buffett 3.0 app-polish work by making the detail tabs reflect the live payload contents instead of only the top-line intrinsic value

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. added a cached loader for [artifacts/results/buffett3_payloads](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/buffett3_payloads)
3. added Buffett 3.0 label-formatting helpers for valuation legs, modifiers, flags, and classification reasons
4. extended the Buffett 3.0 `估值輸入` tab with:
   - company classification
   - scenario weights
   - ready vs pending valuation legs
   - three-stage modifiers
   - input coverage counts
   - data-quality flags
   - manual-review flags
5. extended the Buffett 3.0 `模型解釋` tab with:
   - valuation-leg table
   - modifier table

What this improves:
1. the app now explains why Buffett 3.0 produced a result, not just what number it produced
2. users can now see when a cyclical name is using a partial leg set, instead of only inferring that from the final rating
3. live payload details for names like `2330`, `2881`, `2603`, and `2412` are now surfaced directly in the UI path that matters most

Verification completed:
1. `python -m compileall app.py tw_valuation_models tests`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

Important current conclusion:
1. Buffett 3.0 is now much closer to a production-readable model card in the app
2. no valuation formulas were changed; this pass only exposed existing payload detail more clearly
3. the next best verification step is browser-side UI review, because bare Streamlit execution only confirms the code path and not the rendered layout

Remaining known gaps after Module 22:
1. broader legacy mojibake outside the Buffett 3.0 path still remains in older app copy
2. terminal and raw command output can still display Traditional Chinese poorly depending on shell encoding, even though the source file itself is UTF-8
3. Buffett 3.0 still needs business-rule follow-up for financial-holding dividends and optional future EV or EBITDA completion for cyclical names

### Module 23 Added: Model Overview Layout Realignment
Purpose:
- place Buffett 3.0 cleanly between `巴菲特 2.0` and `IMFS` in the dashboard overview, while fixing the card-layout compression that made the model strip feel misaligned

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. added a small `chunked()` helper so model cards can render in balanced rows instead of one overcompressed strip
3. changed the overview-card layout rule so:
   - `5+` active models render as `3` cards per row
   - smaller selections still render in a single clean row
4. increased model-card minimum height slightly for more stable alignment across mixed copy lengths
5. added `overview_models` so the visible overview always follows canonical `MODEL_ORDER`, even if session state ever drifts
6. widened the title/toggle split slightly so the `模型總覽` header and `卡片 / 列表` control align more cleanly

Implementation outcome:
1. the overview sequence is now explicitly preserved as:
   - `巴菲特 TW`
   - `巴菲特 2.0`
   - `Buffett 3.0`
   - `IMFS`
   - `台股 Buffett Quant`
   - `混合模型`
2. Buffett 3.0 no longer depends on a single overpacked six-column row to appear in the right visual position
3. the top comparison area is more resilient when all six models are enabled at once

Verification completed:
1. `python -m compileall app.py`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`
4. local app reachable at `http://127.0.0.1:8501` via `Invoke-WebRequest`

Important current conclusion:
1. the dashboard overview structure is now materially better aligned for the six-model state the user wants
2. this turn focused on the live comparison strip and did not change any valuation formulas
3. the next strongest UI step is still true browser-side visual QA, but that could not be completed here because the available Node browser runtime does not currently have Playwright installed

Remaining known gaps after Module 23:
1. broader app-wide mojibake cleanup still remains outside the Buffett 3.0 and directly touched overview path
2. browser screenshot verification is still pending even though the app is running locally, because the current tool stack in this session cannot render a page screenshot
3. further production polish should next focus on full-dashboard copy cleanup and right-rail alignment after the overview-strip fix

### Module 24 Added: Right-Rail Narrative And Ordering Polish
Purpose:
- continue the dashboard-production pass by cleaning up the panels immediately adjacent to the overview and detail area, without touching model formulas

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. normalized `active_models` at the page level so downstream dashboard sections always follow canonical `MODEL_ORDER`
3. renamed the top-right hero-side panel from `投資判讀` to `投資判讀摘要`
4. upgraded the lower right-rail support panels from internal-tool labels to more product-ready labels:
   - `模型快照`
   - `模型動態`
   - `研究紀要`
5. added short explanatory copy to those support panels so the rail reads like a guided research workflow rather than a raw diagnostics dump
6. kept the overview card and summary ordering aligned with the same canonical model sequence

Implementation outcome:
1. the right rail now reads more coherently from top to bottom:
   - quick interpretation
   - data health
   - consensus
   - research context
   - file/action utilities
   - compact model snapshot
   - recent model events
   - research notes
2. active-model ordering is now less fragile because it no longer depends on raw session-state order in the touched dashboard sections
3. the dashboard feels less like an internal prototype and more like a user-facing research interface

Verification completed:
1. `python -m compileall app.py`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

Important current conclusion:
1. this pass improved readability and section hierarchy around the dashboard core without changing any model outputs
2. the main remaining UI debt is broader app-wide copy cleanup and visual QA in a real browser
3. `working.md` remains the correct restart point for a fresh session

Remaining known gaps after Module 24:
1. broader mojibake cleanup still remains in older app areas outside the directly touched dashboard flow
2. browser-side screenshot inspection is still pending because the current tool stack in this session cannot render a page screenshot
3. the next production-polish step should likely target full-page text cleanup plus final spacing/visual balance after real browser review

### Module 25 Added: Mockup-Driven Hero And Detail Presentation Pass
Purpose:
- continue aligning the live dashboard with the approved mockup direction by strengthening the hero area and the single-model detail presentation

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. added presentation classes for:
   - `title-kicker`
   - `hero-subcopy`
   - `detail-submeta`
3. rewrote the main hero block so it now includes:
   - an English desk-style kicker
   - a clearer explanatory subtitle
   - cleaner right-side metadata for update time, active ticker, and current focus model
4. refined the top stat-band copy so the enabled-model card reads more like a dashboard action summary
5. updated the `模型總覽` caption to make the comparison intent more explicit
6. improved the `單模型詳情` header so it now surfaces ticker, company, rating, and current price in one tighter presentation row
7. renamed the export control text from `下載報告` to `下載估值摘要`
8. tightened the detail-section caption so it reads more like a guided workflow

Implementation outcome:
1. the top of the page now better matches the “institutional research dashboard” direction instead of a generic app shell
2. the detail area now feels more connected to the selected security and current model context
3. no model formulas, payload structures, or scoring logic were changed in this pass

Verification completed:
1. `python -m compileall app.py`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

Important current conclusion:
1. the live app is moving closer to the approved mockup in tone and hierarchy, not just raw functionality
2. the remaining polish gap is now mostly visual QA and untouched legacy copy elsewhere in the app
3. `working.md` remains current and suitable as the next-session restart source

Remaining known gaps after Module 25:
1. broader app-wide text cleanup is still pending outside the touched hero, overview, right-rail, and detail sections
2. browser screenshot verification is still pending because the current session tools cannot capture the running page visually
3. the next likely UI pass should focus on final tab-area polish and any residual copy inconsistencies after visual review

### Module 26 Added: Detail Tabs Presentation Cleanup
Purpose:
- finish a cleaner presentation pass inside the single-model workspace so the lower half of the page matches the production tone of the hero and overview areas

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. added warning-panel styles:
   - `warning-grid`
   - `warning-card`
   - `warning-card-title`
   - `warning-card-copy`
3. upgraded `render_rules_table()` with a short caption so grading rules feel like part of the guided workflow
4. refined `render_reference_tab()` caption wording to better match the research-desk tone
5. added a new `render_warning_panel()` helper so the `風險提示` tab no longer defaults to raw JSON rendering when structured warning payloads are available
6. added explanatory headers/captions inside:
   - `模型解釋`
   - `風險提示`
   - `參考說明`

Implementation outcome:
1. the detail tabs now read more like a guided analysis surface and less like a debug area
2. warning content is easier to scan by model because it is grouped into styled cards instead of a raw JSON blob
3. the lower section of the dashboard is now more consistent with the top-level mockup direction

Verification completed:
1. `python -m compileall app.py`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

Important current conclusion:
1. the live app now has a much more coherent end-to-end narrative from hero to overview to detail tabs
2. this pass still did not change valuation logic, only presentation and explanation flow
3. the biggest remaining UI risk is still the lack of true browser-side visual QA in this session

Remaining known gaps after Module 26:
1. broader app-wide copy cleanup is still pending outside the areas already polished
2. browser screenshot verification is still pending because the current tool stack in this session cannot capture the running page visually
3. the next best step is likely final full-page text cleanup plus real rendered-layout review once screenshot/browser tooling is available

### Module 27 Added: Sidebar Control Deck Polish
Purpose:
- bring the left sidebar up to the same product quality level as the hero, overview, right rail, and detail tabs

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. added sidebar presentation classes:
   - `sidebar-note-card`
   - `sidebar-note-title`
   - `sidebar-note-copy`
3. renamed the left rail title from `左側控制區` to `研究控制台`
4. added a short workflow card at the top of the sidebar so the control sequence is clearer
5. renamed and refined sidebar sections:
   - `股票設定` -> `標的設定`
   - `日期選擇` -> `資料批次`
   - `模型選擇` -> `啟用模型`
   - `執行選項` -> `執行控制`
   - `資料完整度` -> `研究狀態`
6. removed the awkward disabled date picker and replaced it with a clearer status card showing the current data timestamp and source context
7. improved nearby captions so the sidebar now communicates:
   - current candidate count after filtering
   - currently enabled model count
   - sync status in more product-friendly language

Implementation outcome:
1. the sidebar now feels much more like a professional operator panel instead of a default form stack
2. the control flow is easier to understand at a glance
3. no valuation logic or model selection behavior was changed beyond presentation and clearer status wording

Verification completed:
1. `python -m compileall app.py`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

Important current conclusion:
1. the primary dashboard surfaces are now much more aligned with the approved mockup direction across left rail, hero, overview, right rail, and detail tabs
2. the biggest remaining work is now mostly final copy cleanup and real browser-side visual balancing
3. `working.md` remains current enough to restart from a fresh session without re-auditing this work

Remaining known gaps after Module 27:
1. broader app-wide text cleanup is still pending in untouched areas
2. browser screenshot verification is still pending because the current tool stack in this session cannot capture the running page visually
3. the next likely pass should focus on final consistency cleanup and any residual spacing issues after real browser review

### Module 28 Added: Model Payload Copy Cleanup
Purpose:
- continue the production-polish pass by cleaning up remaining corrupted or placeholder user-facing copy in the model payload summary/basis layer, without changing any valuation formulas

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. replaced the remaining corrupted summary strings in `build_model_summary()` for:
   - `Buffett TW`
   - `Buffett 2.0`
   - `IMFS`
   - `台股 Buffett Quant`
   - `混合模型`
3. split `build_model_basis()` into model-specific Traditional Chinese explanations so each card now describes its own valuation language instead of falling back to corrupted placeholder text
4. normalized default output labels in `get_model_payload()`:
   - default fair-value label now reads `內在價值`
   - `台股 Buffett Quant` now uses `操作建議`
   - `混合模型` now uses `目標價`
5. improved the IMFS Route B / Rule of 40 quality-signal branch so the UI text now clearly explains that:
   - no intrinsic value can be a valid route outcome
   - the branch may intentionally output quality-score-oriented interpretation instead of a single target price
6. kept all calculation logic, thresholds, and model formulas unchanged

Implementation outcome:
1. the overview cards, detail hero, and downstream single-model narrative now have materially cleaner Traditional Chinese copy in the remaining payload-driven surfaces
2. the IMFS no-intrinsic-value case is now described as a valid quality-signal route outcome instead of reading like a broken or missing result
3. the app moved another step away from prototype/debug language and closer to the production research tone required by the user

Verification completed:
1. `python -m compileall app.py tw_valuation_models tests`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

Important current conclusion:
1. the highest-value remaining work is now more about rendered visual QA and any untouched legacy copy than about the central dashboard narrative path
2. this pass did not change any valuation outputs; it only cleaned presentation copy and output labeling
3. `working.md` remains the correct handoff source for the next session

Remaining known gaps after Module 28:
1. broader app-wide copy cleanup may still remain in untouched legacy areas outside the payload-summary path
2. browser-side screenshot inspection is still pending because this session has no working page-capture path
3. the next best pass should likely focus on rendered spacing balance and any last visual inconsistencies after true browser review

### Module 29 Added: Live DOM QA And Consistency Cleanup
Purpose:
- continue from Module 28 by validating the rendered app against the live local page and fixing the next set of copy/consistency issues revealed by browser-side inspection

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. changed `台股 Buffett Quant` overview/detail metric formatting from percentage-style display to raw score display:
   - `48.0%` -> `48.0`
3. fixed the right-rail `研究觀點` narrative to reflect the actual six-model dashboard state:
   - `五模型` -> `六模型`
4. replaced the stale hard-coded research-ledger headline `評級更新為合理偏低` with a neutral live-data-driven entry:
   - title now `巴菲特 TW 估值快照`
   - detail now reflects the current live rating and current intrinsic value instead of a potentially contradictory static phrase
5. kept formulas, ratings thresholds, and all model logic unchanged

Live verification completed:
1. confirmed local app reachable at `http://127.0.0.1:8501`
2. inspected the rendered page through live browser DOM snapshot
3. verified post-fix live DOM results:
   - `台股 Buffett Quant` now shows `綜合分數 48.0`
   - `研究觀點` now says `六模型`
   - `研究紀要` now shows `巴菲特 TW 估值快照`
   - stale `評級更新為合理偏低` text no longer appears

Code verification completed:
1. `python -m compileall app.py`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`

Important current conclusion:
1. the central dashboard copy path is now materially cleaner both in source and in the live rendered DOM
2. the next remaining polish work is increasingly visual/layout-oriented rather than text-corruption-oriented
3. true screenshot-based visual QA is still blocked here because browser image capture timed out even though DOM inspection worked

Remaining known gaps after Module 29:
1. broader untouched legacy copy may still remain outside the currently inspected live path
2. screenshot-style browser verification is still pending because current page capture in this environment timed out
3. the next best pass should focus on spacing, density, and cross-column rhythm once a reliable screenshot/browser visual path is available

### Module 30 Added: Main Workspace / Appendix Page Restructure
Purpose:
- move the app closer to the broader project-complete target by restructuring the dashboard into a more production-like workspace:
  - first page for decision-making and model reading
  - second page for references, appendices, and supporting material
- reduce visible empty space by using the main page width more efficiently and removing the old always-on support rail from the primary workflow

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. added `page_mode` session state so the app now supports two top-level workspaces:
   - `主頁總覽`
   - `研究參考與附錄`
3. rebuilt the active runtime path so the new layout renders first and stops before the legacy layout block
4. reorganized the primary page to keep the highest-value surfaces together:
   - hero + investment summary
   - compact model-status control deck
   - consensus / data health / research-view triage row
   - full-width model overview
   - full-width single-model detail tabs
   - lower section with model dynamic + model snapshot
5. reduced detail-tab clutter on the main page by removing the old inline `參考說明` tab from the active path
6. moved reference-heavy and support-heavy content to the second page:
   - model reference overview
   - IMFS route mapping
   - integration principles
   - rating thresholds
   - related files
   - quick actions
   - model snapshot
   - model dynamic
   - research ledger
7. made related-file summary text dynamic to match the number of currently enabled models instead of hard-coding an outdated model count

Implementation outcome:
1. the main page is now much closer to an operator-style research workspace instead of a mixed workspace + archive
2. wide-screen space is used more efficiently because the main decision surfaces are no longer competing with a tall secondary right rail
3. the app now has a clearer information hierarchy:
   - page one = compare, decide, inspect, evaluate risk
   - page two = reference, appendix, file context, research notes

Verification completed:
1. `python -m compileall app.py tw_valuation_models tests`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`

Important current conclusion:
1. the project has moved another meaningful step toward the broader target-2 completion state because the app structure now better matches a final production workflow
2. the main remaining risk is now visual polish and rendered spacing judgment rather than major information-architecture debt
3. live browser verification for this new layout could not be completed here because the in-app browser rejected `http://127.0.0.1:8501` due to policy, so no workaround was attempted

Remaining known gaps after Module 30:
1. the legacy layout block still exists below the new path and should be safely removed in a cleanup pass after visual confirmation
2. final rendered spacing, density, and cross-column rhythm still need human/browser review on the new main-page structure
3. broader target-2 completion still requires more work beyond UI structure:
   - deeper Buffett 3.0 validation and refinement
   - data-source maturity follow-up
   - additional end-to-end production QA

### Module 31 Added: Buffett 3.0 Detail Payload Audit / Compatibility Repair
Purpose:
- continue the target-2 completion path by auditing a real Buffett 3.0 data inconsistency instead of assuming the UI issue was only visual
- verify whether the engine, the exported payloads, or the app detail-reader was responsible for missing Buffett 3.0 detail fields

Audit steps completed:
1. inspected the active app runtime path and confirmed the new two-page layout still short-circuits before the legacy block:
   - `st.stop()` remains in place before the old dashboard path
   - the old layout is still dead code, not currently executing
2. validated real local Buffett 3.0 artifacts for representative tickers:
   - `2330`
   - `2881`
   - `2603`
   - `2412`
3. confirmed the main results table was already carrying real Buffett 3.0 outputs correctly:
   - `buffett3_intrinsic`
   - `buffett3_mos`
   - `buffett3_signal`
   - `buffett3_type`
4. traced the payload schema from `tw_valuation_models/models/buffett_three.py` into `artifacts/results/buffett3_payloads/*.json`

Exact findings from the audit:
1. the Buffett 3.0 engine was already producing real top-level outputs:
   - `classification`
   - `blended_normalized_valuation`
   - `final_fair_value_per_share`
2. older saved payloads did not include compatibility aliases that some downstream readers would naturally expect:
   - `company_type`
   - `blended_fair_value`
   - `final_fair_value`
3. more importantly, the app detail tab was reading normalized valuation inputs from the wrong branch:
   - the engine stores them in `normalized_inputs`
   - the app was trying to read them from `input_snapshot`
4. this means the Buffett 3.0 detail area could show `資料不足` for real values that were already present in the saved JSON

Code changes completed:
1. updated [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py)
2. added compatibility aliases directly in the Buffett 3.0 engine output:
   - `company_type = classification`
   - `blended_fair_value = blended_normalized_valuation`
   - `final_fair_value = final_fair_value_per_share`
3. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
4. hardened `load_buffett3_payload()` so existing saved payloads are normalized on read:
   - merges `normalized_inputs` into the app-facing snapshot fields used by the detail table
   - backfills legacy alias keys when they are absent
5. corrected the Buffett 3.0 detail tab to read normalized values from `normalized_inputs` first instead of relying on the wrong payload branch
6. added a new detail row for the pre-modifier Buffett 3.0 blended baseline:
   - `支線加權基準值`
7. updated [tests/test_buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_buffett_three.py) so the compatibility fields are now part of the verified result schema

Real validation completed:
1. `python -m compileall app.py tw_valuation_models tests`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. bare runtime check:
   - `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`
4. direct loader verification against a real saved payload (`2330`) confirmed the app now resolves:
   - `company_type = high_quality_compounder`
   - `blended_fair_value = 793.3343`
   - `final_fair_value = 799.566`
   - `normalized_eps = 47.658681409797715`
   - `normalized_fcf_per_share = 27.50909549544407`
   - `bvps = 206.4989351755369`

Important current conclusion:
1. this was a real production-facing data-contract fix, not just copy cleanup
2. the Buffett 3.0 detail experience is now materially more trustworthy because real saved payload data is no longer silently dropped by the UI
3. the broader target-2 path still remains incomplete, but the current Buffett 3.0 detail-view inconsistency has been narrowed and repaired with local verifiable evidence

Remaining known gaps after Module 31:
1. the legacy layout block still exists below `st.stop()` and should be removed once the new layout has visual confirmation
2. full rendered visual QA is still pending because the in-app browser path to `http://127.0.0.1:8501` is currently blocked by policy in this session, so no workaround was attempted
3. the main-page space-efficiency work has improved structurally, but final spacing, density, and hierarchy still need real browser-side judgment
4. broader target-2 completion still requires follow-up in three areas:
   - deeper Buffett 3.0 model/readout refinement beyond schema compatibility
   - data-source maturity and historical-input completeness
   - final production-style end-to-end QA

### Module 32 Added: Legacy Layout Block Removal / Active Path Simplification
Purpose:
- continue the target-2 production-hardening path by removing the now-confirmed unreachable legacy dashboard code instead of leaving duplicate UI logic in `app.py`
- reduce maintenance risk so future edits only touch the real active two-page layout path

Audit before removal:
1. re-verified that the active app path already finished the new two-page layout and then fell into a top-level `st.stop()`
2. confirmed the old single-page dashboard still existed physically below that stop point
3. mapped the exact dead-code span:
   - start: former `st.stop()`
   - end: just before the shared warning footer

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. removed the entire unreachable legacy dashboard block that previously lived below the active appendix page
3. preserved the shared warning footer and the current live two-page layout path
4. confirmed the source now falls directly from the active appendix-page content into the shared warning footer without any hidden duplicate runtime branch

Post-change validation completed:
1. `python -m compileall app.py tw_valuation_models tests`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. bare runtime check:
   - `$env:PYTHONPATH='D:\Codex projects\TW Valuation models\.deps'; python -c "import runpy; runpy.run_path('app.py', run_name='__main__')"`
4. direct source audit confirmed the old markers are gone:
   - `st.stop()` count = `0`
   - old `header_left, header_right = st.columns([4.0, 1.35], gap="large")` legacy branch count = `0`
   - old five-tab legacy detail path count = `0`

Important current conclusion:
1. the app source is materially cleaner now because there is only one dashboard runtime path left in `app.py`
2. future layout or model-detail work is less likely to accidentally patch the wrong branch
3. this was a safe cleanup step with regression checks, not a formula or data-logic change

Remaining known gaps after Module 32:
1. full rendered visual QA is still pending because the in-app browser path to `http://127.0.0.1:8501` is currently blocked by policy in this session, so no workaround was attempted
2. the main-page information hierarchy is structurally better, but final spacing, density, and first-page efficiency still need real browser-side judgment
3. broader target-2 completion still requires follow-up in three areas:
   - deeper Buffett 3.0 model/readout refinement beyond schema compatibility
   - data-source maturity and historical-input completeness
   - final production-style end-to-end QA

### Module 33 Added: Provenance / Coverage Diagnostics Surfaced In App
Purpose:
- close more of the target-2 trust gap by showing real local source coverage and validation limits directly inside the app instead of relying on broad narrative warnings
- make the UI reflect what the dataset and Buffett 3.0 manifests actually say on disk

Audit findings used for this pass:
1. `artifacts/datasets/top100/dataset_summary.json` and `buffett3_source_manifest.json` already contain real coverage evidence
2. the current local top100 dataset is stronger than the older coarse warning suggested:
   - official valuation snapshot coverage: `100 / 100`
   - official dividend-history coverage: `100 / 100`
   - official monthly-revenue coverage: `95 / 100`
   - monthly revenue missing tickers are exactly the five financial holdings:
     - `2881`
     - `2882`
     - `2885`
     - `2887`
     - `2891`
3. annual / quarterly Buffett 3.0 financial tables are complete after official-plus-fallback assembly for the top100 validation set
4. `artifacts/validation/validation_summary.json` still shows the real shared-data limits:
   - `universe_snapshot`
   - `valuation_snapshot`
   - `fundamentals_snapshot`
5. `artifacts/normalized/normalization_summary.json` still shows snapshot warnings for:
   - `valuation_snapshot`
   - `fundamentals_snapshot`

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. added cached loaders for:
   - optional JSON diagnostics
   - dataset diagnostics bundle
   - Buffett 3.0 manifest-entry extraction
   - per-ticker data diagnostic snapshot assembly
3. upgraded the main-page summary/data-health path so it now reflects manifest-backed coverage instead of only a coarse monthly-revenue row count
4. upgraded the appendix reference page so it now shows:
   - source coverage table from `buffett3_source_manifest.json`
   - normalization / validation summary table from the local JSON audit files
5. upgraded the related-files panel so it now explicitly references:
   - `buffett3_source_manifest.json`
   - `validation_summary.json`
   - `normalization_summary.json`
6. upgraded the Buffett 3.0 detail-input table on page one so it now exposes current-ticker provenance facts directly:
   - financial vs general statement route
   - whether this ticker actually has official monthly-revenue rows
   - annual / quarterly statement coverage status

Real validation completed:
1. `python -m compileall app.py tw_valuation_models tests`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. direct diagnostic spot checks from live local artifacts:
   - `2330`
     - `ticker_statement_route = general`
     - `ticker_has_monthly_revenue = True`
     - `ticker_has_annual_statement = True`
     - `ticker_has_quarterly_statement = True`
   - `2881`
     - `ticker_statement_route = financial`
     - `ticker_has_monthly_revenue = False`
     - `ticker_has_annual_statement = True`
     - `ticker_has_quarterly_statement = True`

Important current conclusion:
1. the app now communicates a much more truthful data story:
   - not “monthly revenue is empty”
   - but “monthly revenue covers 95 / 100 and the missing names are the five financial holdings”
2. this materially reduces hallucination risk for later review because the product now points back to real local manifests and audit summaries
3. the remaining unfinished work is now disproportionately visual/browser-side rather than hidden source-contract ambiguity

Remaining known gaps after Module 33:
1. full rendered visual QA is still pending because the in-app browser path to `http://127.0.0.1:8501` is currently blocked by policy in this session, so no workaround was attempted
2. first-page spacing, density, and exact visual rhythm still need browser-side judgment before calling the UI truly final
3. broader target-2 work is now narrower but not zero:
   - deeper Buffett 3.0 weighting / cyclical-path refinement
   - improved historical data maturity beyond current snapshot limitations
   - final production-style interactive QA

### Module 34 Added: Export / Activity Feed Provenance Alignment
Purpose:
- finish the current source-side production hardening loop by making the downloadable JSON report and the activity feed tell the same manifest-backed story as the UI
- avoid a situation where page content is truthful but exported artifacts fall back to older coarse wording

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. upgraded `build_activity_log()` so the feed now prefers real source-coverage messaging when manifest diagnostics are available:
   - reports official monthly-revenue coverage as `95 / 100`
   - names the actual missing financial holdings instead of implying a generic empty dataset
3. upgraded `build_report()` so exported JSON now includes:
   - per-model UI payload snapshots
   - ticker-level provenance snapshot
   - manifest generation timestamp
   - validation / normalization warning table names
   - condensed Buffett 3.0 detail fields such as classification, blended fair value, final fair value, and review flags
4. updated the active download button call so the exported valuation report receives the same diagnostics bundle used by the UI

Real validation completed:
1. `python -m compileall app.py tw_valuation_models tests`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. direct report-generation check for `2881` confirmed the exported JSON now contains:
   - `data_provenance.ticker_snapshot`
   - `buffett3_manifest_generated_at`
   - `validation_warning_tables`
   - `normalization_warning_tables`
   - `buffett3_detail.classification = financial`
   - `buffett3_detail.blended_fair_value = 73.49`
   - `buffett3_detail.final_fair_value = 71.153`

Important current conclusion:
1. the app, appendix, activity feed, and downloaded JSON report are now materially more aligned with each other
2. the remaining open work is no longer about hidden dataset ambiguity in the active product surfaces
3. the honest blocker to calling the project fully final in this session is still rendered browser-side QA, not missing source-side provenance or reportability

Remaining known gaps after Module 34:
1. full rendered visual QA is still pending because the in-app browser path to `http://127.0.0.1:8501` is currently blocked by policy in this session, so no workaround was attempted
2. first-page spacing, density, and exact visual rhythm still need browser-side judgment before calling the UI truly final
3. broader target-2 follow-up now mainly means:
   - deeper Buffett 3.0 weighting / cyclical-path refinement
   - improved historical data maturity beyond current snapshot limitations
   - final production-style interactive QA

### Module 35 Added: Provenance / Export Regression Tests
Purpose:
- protect the new target-2 provenance work with automated tests so future edits do not silently regress the diagnostics snapshot or exported report structure

Code changes completed:
1. added [tests/test_app_reporting.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_app_reporting.py)
2. covered two production-facing behaviors:
   - `build_data_diagnostic_snapshot()` respects manifest truth for general vs financial names
   - `build_report()` includes provenance payloads and condensed Buffett 3.0 detail fields

Real validation completed:
1. `python -m unittest tests.test_app_reporting tests.test_shared_data tests.test_dataset tests.test_buffett_three`
2. `python -m compileall app.py tw_valuation_models tests`
3. result:
   - `Ran 14 tests ... OK`

Important current conclusion:
1. the new diagnostics/reporting path is no longer only manually spot-checked; it is now covered by regression tests
2. this reduces the remaining target-2 risk further because future UI/report changes are less likely to drift away from manifest-backed truth

Remaining known gaps after Module 35:
1. full rendered visual QA is still pending because the in-app browser path to `http://127.0.0.1:8501` is currently blocked by policy in this session, so no workaround was attempted
2. first-page spacing, density, and exact visual rhythm still need browser-side judgment before calling the UI truly final
3. broader target-2 follow-up now mainly means:
   - deeper Buffett 3.0 weighting / cyclical-path refinement
   - improved historical data maturity beyond current snapshot limitations
   - final production-style interactive QA

### Module 36 Added: Live Browser QA Fixes And Default Main-Page Density Pass
Purpose:
- use the newly authorized in-app local browser to close the remaining real product bugs found only in rendered QA
- finish a first truthful layout-density pass on page one instead of guessing from source alone

Live browser findings before code edits:
1. the live `2330` page showed `本檔月營收 = 缺` even though local source data and manifest truth already showed `2330` is covered
2. the live Buffett 3.0 overview card for `2330` showed a false degraded state:
   - `評級 = 資料不足`
   - `合理價 = 資料不足`
   - company type summary rendered as `未分類`
3. the first-page workspace still felt cramped because the Streamlit sidebar opened expanded by default, reducing the useful width of the main dashboard

Root causes verified:
1. [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py) `load_buffett3_payload()` only used `setdefault()` for compatibility aliases, so older payloads with explicit `null` alias keys were not actually repaired
2. `get_model_payload(..., "buffett3")` still depended primarily on flattened result-row columns instead of falling back to the richer saved Buffett 3.0 payload when those row fields were incomplete
3. `build_data_diagnostic_snapshot()` determined ticker monthly-revenue presence from the loaded dataframe row count alone, even when the manifest already contained a stronger explicit covered/missing-ticker truth source

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. repaired `load_buffett3_payload()` so it now backfills compatibility aliases when the saved key exists but is `null`:
   - `company_type`
   - `blended_fair_value`
   - `final_fair_value`
3. added a Buffett 3.0 payload-side rating fallback so saved payloads can still classify value when the flattened row is incomplete
4. upgraded `get_model_payload()` for `buffett3` so overview/detail cards now fall back to the verified saved payload for:
   - final fair value
   - derived gap percentage when row MOS is missing
   - company type / classification text
5. upgraded `build_data_diagnostic_snapshot()` so ticker monthly-revenue truth now prefers the manifest coverage list when available, instead of relying only on the loaded dataframe row count
6. changed `st.set_page_config(... initial_sidebar_state=...)` from `expanded` to `collapsed` so the main dashboard opens in a denser first-page layout by default while still keeping sidebar controls available on demand
7. extended [tests/test_app_reporting.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_app_reporting.py) with regression coverage for:
   - manifest-preferred ticker monthly-revenue truth
   - Buffett 3.0 payload fallback when row-level fields are absent

Real validation completed:
1. `python -m compileall app.py tw_valuation_models tests`
2. `python -m unittest tests.test_app_reporting tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. live browser DOM verification against `http://127.0.0.1:8501` confirmed the two real product bugs are fixed:
   - `本檔月營收 = 有`
   - Buffett 3.0 now renders:
     - `評級 = 非常昂貴`
     - `價值差距 = -64.8%`
     - `合理價 = 799.57`
     - `高品質複利股`
4. live browser screenshot verification confirmed the default first screen now opens with the sidebar collapsed, giving the hero, KPI strip, model chips, and workspace controls materially more effective space on page one

Important current conclusion:
1. the remaining target-2 UI risk is no longer hidden inside false data-state rendering for `2330`; the live app now matches real local evidence for both data coverage and Buffett 3.0 card output
2. browser-side QA is now genuinely working in this session, so the earlier browser-blocked caveat is no longer true
3. the first-page density issue improved materially with the collapsed-default sidebar, without removing any controls or inventing non-verifiable UI changes

Remaining known gaps after Module 36:
1. broader target-2 completion is now mostly model/data maturity work rather than active dashboard truthfulness:
   - deeper Buffett 3.0 weighting / cyclical-path refinement
   - improved historical data maturity beyond current snapshot limitations
2. more cross-ticker browser QA is still worthwhile for additional representative names such as `2881`, `2603`, and `2412`
3. if a future pass wants more aggressive page-one compaction, it should be done from fresh browser evidence rather than source-only intuition

### Module 37 Added: Full Buffett 3.0 Artifact Consistency Audit
Purpose:
- turn the recent `2330` browser-discovered Buffett 3.0 mismatch into a broader regression guard across the whole saved top100 artifact set
- confirm that the loader/payload fallback fix is not only correct for one ticker, but stable across all locally saved Buffett 3.0 outputs

Audit findings used for this pass:
1. a direct local artifact audit over `artifacts/results/top100_model_results.csv` and all `artifacts/results/buffett3_payloads/*.json` found:
   - `100 / 100` result rows have matching saved Buffett 3.0 payload files
   - `0` fair-value mismatches between flattened result rows and payload `final_fair_value_per_share`
   - `0` classification mismatches between flattened result rows and payload `classification`
2. representative real rows remain coherent after the earlier app-layer fix:
   - `2881` -> `financial`, `71.153`, `避開`
   - `2603` -> `cyclical`, `209.119`, `持有`
   - `2412` -> `defensive_dividend`, `96.773`, `避開`
3. older payload JSON files still physically store some compatibility aliases as `null`, so loader-side backfill remains necessary even though the underlying core values are present

Code changes completed:
1. added [tests/test_artifact_consistency.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_artifact_consistency.py)
2. the new regression file verifies two high-value target-2 invariants against the real saved artifacts:
   - every top100 flattened Buffett 3.0 result row matches its saved payload on fair value and classification
   - `load_buffett3_payload()` exposes usable compatibility fields for all 100 saved payloads:
     - `company_type`
     - `blended_fair_value`
     - `final_fair_value`
     - derived `rating`

Real validation completed:
1. `python -m unittest tests.test_artifact_consistency tests.test_app_reporting tests.test_shared_data tests.test_dataset tests.test_buffett_three`
2. `python -m compileall app.py tw_valuation_models tests`
3. result:
   - `Ran 18 tests ... OK`

Important current conclusion:
1. the earlier `2330` Buffett 3.0 rendering issue is now surrounded by stronger protection at three levels:
   - live browser verification
   - app-path regression tests
   - full-artifact consistency audit tests over all 100 saved payloads
2. the current local Buffett 3.0 artifact set is internally coherent; the remaining target-2 work is no longer about hidden drift between saved payloads and the flattened result table
3. cross-ticker browser-side QA is still desirable, but I am not claiming it here because the Streamlit ticker-switch interaction path was not yet reliable enough in the in-app browser to validate those names visually without ambiguity

Remaining known gaps after Module 37:
1. broader target-2 completion is still mainly model/data maturity work:
   - deeper Buffett 3.0 weighting / cyclical-path refinement
   - improved historical data maturity beyond current snapshot limitations
2. browser-side representative-ticker QA for `2881`, `2603`, and `2412` is still worth doing once the in-app ticker-switch path is more controllable
3. if future work pushes Buffett 3.0 logic further, the saved artifacts should be regenerated and this new full-artifact audit should remain green before calling the model path production-final

### Module 38 Added: Buffett 3.0 Source-Contract Finalization And Artifact Refresh
Purpose:
- move Buffett 3.0 one step closer to production-final by making the saved model payload self-contained at the model-engine layer, not only reparable in the app
- regenerate the local top100 result artifacts so the saved payload files themselves reflect the stronger contract

Code changes completed:
1. updated [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py)
2. added native Buffett 3.0 `rating` emission at model-generation time using the same value-bucket thresholds already used in the app:
   - `低估`
   - `合理偏低`
   - `合理`
   - `合理偏高`
   - `昂貴`
   - `非常昂貴`
3. updated [tests/test_buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_buffett_three.py) so the engine contract now explicitly expects `rating` in the produced result

Artifact refresh completed:
1. rebuilt the full local top100 model-result bundle with:
   - `build_all_model_results(WorkspacePaths(...), top_n=100)`
2. refreshed files now include:
   - [artifacts/results/top100_model_results.csv](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results.csv)
   - [artifacts/results/top100_model_results_summary.json](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results_summary.json)
   - all `artifacts/results/buffett3_payloads/*.json`
3. refreshed summary timestamp:
   - `2026-05-16T10:43:48+00:00`

Real validation completed:
1. `python -m compileall app.py tw_valuation_models tests`
2. `python -m unittest tests.test_artifact_consistency tests.test_app_reporting tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. result:
   - `Ran 18 tests ... OK`
4. direct refreshed-payload spot checks confirmed the saved files now natively contain non-null compatibility fields plus `rating`:
   - `2330`
     - `company_type = high_quality_compounder`
     - `blended_fair_value = 793.3343`
     - `final_fair_value = 799.566`
     - `rating = 非常昂貴`
   - `2881`
     - `company_type = financial`
     - `blended_fair_value = 73.49`
     - `final_fair_value = 71.153`
     - `rating = 昂貴`
   - `2603`
     - `company_type = cyclical`
     - `blended_fair_value = 220.6827`
     - `final_fair_value = 209.119`
     - `rating = 合理`
   - `2412`
     - `company_type = defensive_dividend`
     - `blended_fair_value = 95.0186`
     - `final_fair_value = 96.773`
     - `rating = 昂貴`
5. live browser DOM sanity check after the artifact refresh confirmed `2330` still renders correctly:
   - `本檔月營收 = 有`
   - Buffett 3.0 shows `高品質複利股`
   - `合理價 = 799.57`
   - `評級 = 非常昂貴`

Important current conclusion:
1. Buffett 3.0 no longer relies on app-side derivation to obtain a usable saved `rating`; the source model now emits it directly
2. the regenerated local artifacts are cleaner production inputs than the earlier mixed old/new payload set
3. the remaining target-2 work is now even more clearly outside this payload-contract layer

Remaining known gaps after Module 38:
1. broader target-2 completion is still mainly model/data maturity work:
   - deeper Buffett 3.0 weighting / cyclical-path refinement
   - improved historical data maturity beyond current snapshot limitations
2. browser-side representative-ticker QA for `2881`, `2603`, and `2412` is still worth doing once the in-app ticker-switch path is more controllable
3. if future work changes Buffett 3.0 thresholds or weighting logic, the top100 artifacts should be regenerated again and the full artifact-consistency suite should remain green before calling the model path final

### Module 39 Added: Cyclical EV/EBITDA Blocker Diagnostics
Purpose:
- improve Buffett 3.0 target-2 transparency for cyclical names by making the `EV/EBITDA` blocker auditable from the payload itself
- avoid vague `not_ready` messaging when the real blocker is missing debt/cash coverage plus lack of a clean EBITDA series in the current dataset

Audit findings used for this pass:
1. the current local top100 cyclical set is:
   - `2603`
   - `2002`
   - `1326`
   - `1717`
   - `1795`
2. across all five cyclical names, the current Buffett 3.0 source tables show:
   - annual `total_debt` non-null rows: `0`
   - annual `cash_and_equivalents` non-null rows: `0`
   - quarterly `total_debt` non-null rows: `0`
   - quarterly `cash_and_equivalents` non-null rows: `0`
3. operating-income rows do exist for those names, but a clean EBITDA series still is not present in the current dataset contract, so enabling `EV/EBITDA` from these sources would require inference rather than direct verified data

Code changes completed:
1. updated [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py)
2. Buffett 3.0 normalized inputs now carry real source-field coverage counts:
   - annual / quarterly `total_debt`
   - annual / quarterly `cash_and_equivalents`
   - annual / quarterly `operating_income`
3. cyclical Buffett 3.0 payloads now emit explicit `cyclical_ev_ebitda_blockers`, including:
   - `total_debt_missing_in_source_tables`
   - `cash_and_equivalents_missing_in_source_tables`
   - `clean_ebitda_series_not_available_in_current_dataset`
4. the cyclical `normalized_ev_ebitda` leg now includes those blocker reasons in its own `notes` and carries the same source-field coverage inside `inputs`
5. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py) so the Buffett 3.0 detail table can render:
   - translated blocker labels
   - real annual/quarterly debt/cash coverage counts for the current ticker

Artifact refresh completed:
1. rebuilt the full local top100 model-result bundle after the payload-contract change
2. refreshed summary timestamp:
   - `2026-05-16T11:15:36+00:00`

Real validation completed:
1. `python -m compileall app.py tw_valuation_models tests`
2. `python -m unittest tests.test_artifact_consistency tests.test_app_reporting tests.test_shared_data tests.test_dataset tests.test_buffett_three`
3. result:
   - `Ran 18 tests ... OK`
4. direct refreshed-payload checks for real cyclical names confirmed the new blocker contract:
   - `2603`
     - blockers:
       - `total_debt_missing_in_source_tables`
       - `cash_and_equivalents_missing_in_source_tables`
       - `clean_ebitda_series_not_available_in_current_dataset`
     - annual/quarterly source coverage:
       - debt rows `0 / 0`
       - cash rows `0 / 0`
       - operating-income rows `4 / 1`
   - `2002`
     - same blocker set and same debt/cash coverage pattern

Important current conclusion:
1. the cyclical Buffett 3.0 path is still intentionally incomplete, but it is now incomplete in a much more auditable way
2. this is a real target-2 improvement because the product can now distinguish:
   - formula not enabled by design
   - source fields actually absent in the current local dataset
3. I did not enable `EV/EBITDA` because the local data does not yet justify it without inference

Remaining known gaps after Module 39:
1. broader target-2 completion is still mainly model/data maturity work:
   - real debt/cash coverage ingestion for cyclical names if an official or otherwise verifiable source becomes available
   - improved historical data maturity beyond current snapshot limitations
2. browser-side representative-ticker QA for `2881`, `2603`, and `2412` is still worth doing once the in-app ticker-switch path is more controllable
3. if future data ingestion adds verified debt/cash or EBITDA fields, the cyclical `EV/EBITDA` leg should be revisited from that new evidence rather than by relaxing the current blocker rules

### Module 40 Added: Cyclical Blocker Export And Regression Protection
Purpose:
- make sure the new cyclical `EV/EBITDA` blocker truth survives outside the UI
- protect the refreshed cyclical transparency path against future regressions in both exports and saved artifacts

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. expanded `build_report()` so exported `buffett3_detail` now includes:
   - `rating`
   - `cyclical_ev_ebitda_blockers`
   - `source_field_coverage`
3. updated [tests/test_app_reporting.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_app_reporting.py) so exported Buffett 3.0 detail is now required to carry the richer blocker/coverage fields
4. updated [tests/test_artifact_consistency.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_artifact_consistency.py) with a dedicated real-artifact check for cyclical names:
   - every cyclical saved payload must publish the blocker list
   - the blocker list must include debt/cash/clean-EBITDA reasons
   - annual/quarterly debt and cash coverage counts must stay at the observed `0` values until a real source changes that fact
   - the `normalized_ev_ebitda` leg notes must include the same blocker reasons

Real validation completed:
1. `python -m unittest tests.test_artifact_consistency tests.test_app_reporting tests.test_shared_data tests.test_dataset tests.test_buffett_three`
2. `python -m compileall app.py tw_valuation_models tests`
3. result:
   - `Ran 19 tests ... OK`

Important current conclusion:
1. cyclical Buffett 3.0 blocker transparency is now protected at three layers:
   - live UI detail view
   - exported `valuation_report.json`
   - full real-artifact regression tests
2. the remaining target-2 work is no longer about whether the product can explain the cyclical gap truthfully; it is about whether we can later source better real data to shrink that gap

Remaining known gaps after Module 40:
1. broader target-2 completion is still mainly model/data maturity work:
   - real debt/cash coverage ingestion for cyclical names if an official or otherwise verifiable source becomes available
   - improved historical data maturity beyond current snapshot limitations
2. browser-side representative-ticker QA for `2881`, `2603`, and `2412` is still worth doing once the in-app ticker-switch path is more controllable
3. if future data ingestion adds verified debt/cash or EBITDA fields, the cyclical `EV/EBITDA` leg and these blocker expectations should be revisited from that new evidence

### Module 41 Added: Buffett 3.0 Taiwan Sector Classification Tightening
Purpose:
- reduce the obviously over-broad Buffett 3.0 fallback into `high_quality_compounder`
- make the live top100 classification mix better reflect common Taiwan sector labels before touching any valuation weights or formulas

Root cause identified:
1. the old classifier defaulted every unmatched name to `high_quality_compounder`
2. the existing keyword buckets were too narrow for several common Taiwan sectors, especially:
   - plastics
   - cement
   - glass / ceramics
   - textiles
   - some panel / optoelectronics names

Code changes completed:
1. updated [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py)
2. expanded Taiwan-friendly keyword coverage:
   - compounder now also recognizes broader computer / network / commerce wording
   - cyclical now also recognizes `光電`, `塑膠`, `水泥`, `玻璃`, `陶瓷`, `紡織`, `汽車`
3. updated [tests/test_buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_buffett_three.py)
4. added explicit classifier regression cases for:
   - `1101` / `水泥工業`
   - `1301` / `塑膠工業`
   - `2409` / `友達光電`

Artifact refresh completed:
1. rebuilt the local top100 Buffett 3.0 result bundle after the classifier change
2. refreshed outputs include:
   - [artifacts/results/top100_model_results.csv](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results.csv)
   - [artifacts/results/top100_model_results_summary.json](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results_summary.json)
   - `artifacts/results/buffett3_payloads/*.json`

Real validation completed:
1. `python -m compileall tw_valuation_models tests app.py`
2. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three tests.test_app_reporting tests.test_artifact_consistency`
3. result:
   - `Ran 19 tests ... OK`

Live distribution improvement after refresh:
1. Buffett 3.0 classification mix changed from:
   - `high_quality_compounder: 86`
   - `financial: 5`
   - `cyclical: 5`
   - `defensive_dividend: 4`
2. to:
   - `high_quality_compounder: 73`
   - `cyclical: 18`
   - `financial: 5`
   - `defensive_dividend: 4`

Important current conclusion:
1. this pass improved classification realism without changing Buffett 3.0 valuation formulas
2. the classifier is still heuristic and not yet fully institution-grade, but it is no longer pushing nearly the entire universe into the compounder bucket
3. the next high-value Buffett 3.0 work should likely be targeted review of the newly cyclical names rather than more blind keyword expansion

Remaining known gaps after Module 41:
1. `high_quality_compounder` is still the dominant class at `73 / 100`, so classification is better but not final
2. some source `industry` labels in the current dataset are still noisy or suspicious, which limits how precise keyword routing can be
3. cross-checking the 18 cyclical names for obvious false positives is now the most useful next audit step before touching weighting logic

### Module 42 Added: Buffett 3.0 False-Positive Cyclical Cleanup
Purpose:
- audit the newly expanded cyclical bucket from Module 41
- reduce obvious false positives caused by broad company-name substring matching rather than reliable Taiwan sector routing

Audit findings used for this pass:
1. the first Module 41 expansion pushed several names into cyclical for weak reasons:
   - `3008` 大立光電
   - `3450` 聯鈞光電
   - `1795` 美時化學製藥
   - `1717` 長興材料
2. the bad matches came mainly from overly broad cyclical keywords:
   - `光電`
   - `化學`
3. exact sector routing is more trustworthy than company-name substring routing for:
   - `塑膠工業`
   - `水泥工業`
   - `鋼鐵工業`
   - `玻璃陶瓷`
   - `紡織纖維`
   - `汽車工業`
   - `航運業`

Code changes completed:
1. updated [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py)
2. introduced explicit exact-industry buckets before fallback keyword matching:
   - `FINANCIAL_INDUSTRIES`
   - `CYCLICAL_INDUSTRIES`
   - `DEFENSIVE_INDUSTRIES`
3. removed the too-broad cyclical fallback keywords:
   - `光電`
   - `化學`
4. kept finance routing tied to:
   - real `金融保險` industry
   - `28xx` tickers
   - financial keywords
5. updated [tests/test_buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_buffett_three.py)
6. added safer classifier expectations for:
   - `3008` should not be auto-routed to cyclical from a noisy industry label
   - `1795` should not be auto-routed to cyclical just because the company name contains `化學`

Intermediate audit mistake caught and fixed:
1. an initial exact-industry shortcut incorrectly treated raw industry code `28` as financial
2. that briefly inflated the financial bucket to `22`
3. the shortcut was removed so only `金融保險` and `28xx` ticker logic remain for finance routing

Artifact refresh completed:
1. rebuilt the local top100 Buffett 3.0 bundle after the classifier cleanup
2. refreshed outputs include:
   - [artifacts/results/top100_model_results.csv](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results.csv)
   - [artifacts/results/top100_model_results_summary.json](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results_summary.json)
   - `artifacts/results/buffett3_payloads/*.json`

Real validation completed:
1. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three tests.test_app_reporting tests.test_artifact_consistency`
2. `python -m compileall tw_valuation_models tests app.py`
3. result:
   - `Ran 19 tests ... OK`

Live distribution after final Module 42 refresh:
1. `high_quality_compounder: 80`
2. `cyclical: 11`
3. `financial: 5`
4. `defensive_dividend: 4`

Current cyclical bucket after cleanup:
1. `1303` 南亞塑膠
2. `2603` 長榮海運
3. `1301` 台塑
4. `2002` 中鋼
5. `1326` 台化
6. `2207` 和泰車
7. `1802` 台玻
8. `1101` 台泥
9. `1402` 遠東新世紀
10. `1102` 亞泥
11. `1476` 儒鴻

Important current conclusion:
1. the cyclical bucket is now smaller and more defensible than the earlier 18-name version
2. the remaining cyclical set still includes a few debatable names, especially around textiles and autos, but the clearly bad optoelectronics / pharmaceutical false positives were removed
3. classification is now more stable for further Buffett 3.0 review, even though it is still heuristic rather than fully institution-grade

Remaining known gaps after Module 42:
1. `high_quality_compounder` is still dominant at `80 / 100`, so classification still needs judgment rather than blind trust
2. `紡織纖維` and `汽車工業` may deserve a later policy decision on whether they should stay cyclical or move to another bucket
3. some dataset `industry` labels remain noisy, so a future sector-mapping layer may be better than more ad hoc keyword expansion

### Module 43 Added: Textile And Auto De-Risking In Buffett 3.0 Classification
Purpose:
- continue the classifier cleanup after Module 42 by deciding whether `紡織纖維` and `汽車工業` should really be forced into the cyclical bucket
- avoid sending likely steady operators into the cyclical partial-leg path by default

Audit findings used for this pass:
1. after Module 42, these names were still cyclical only because of textile / auto routing:
   - `1402` 遠東新世紀
   - `1476` 儒鴻
   - `2207` 和泰車
2. those names were entering the cyclical path with:
   - `cyclical_ev_ebitda_not_ready_without_clean_ebitda`
   - `cyclical_model_uses_partial_leg_set`
   - `some_valuation_legs_not_ready`
3. that is a poor default unless we have stronger evidence than just sector wording that they should be treated like classic shipping / steel / cement / plastics names

Code changes completed:
1. updated [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py)
2. removed `紡織纖維` and `汽車工業` from `CYCLICAL_INDUSTRIES`
3. removed the fallback cyclical keywords:
   - `紡織`
   - `汽車`
4. rebuilt [tests/test_buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_buffett_three.py) into a clean UTF-8 version with readable sample names and clearer classifier assertions
5. added explicit classifier expectations that:
   - `1476` / `紡織纖維` should not auto-route to cyclical
   - `2207` / `汽車工業` should not auto-route to cyclical

Artifact refresh completed:
1. rebuilt the full top100 Buffett 3.0 bundle after the routing change
2. refreshed outputs include:
   - [artifacts/results/top100_model_results.csv](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results.csv)
   - [artifacts/results/top100_model_results_summary.json](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results_summary.json)
   - `artifacts/results/buffett3_payloads/*.json`

Real validation completed:
1. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three tests.test_app_reporting tests.test_artifact_consistency`
2. `python -m compileall tw_valuation_models tests app.py`
3. result:
   - `Ran 19 tests ... OK`

Live distribution after Module 43 refresh:
1. `high_quality_compounder: 83`
2. `cyclical: 8`
3. `financial: 5`
4. `defensive_dividend: 4`

Current cyclical bucket after cleanup:
1. `1303` 南亞塑膠
2. `2603` 長榮海運
3. `1301` 台塑
4. `2002` 中鋼
5. `1326` 台化
6. `1802` 台玻
7. `1101` 台泥
8. `1102` 亞泥

Important current conclusion:
1. the cyclical set is now much closer to a classic heavy-sector bucket
2. the classifier still uses heuristics, but the remaining cyclical names are materially more defensible than the earlier textile / auto / optoelectronics mix
3. the next best Buffett 3.0 step is probably no longer classifier cleanup; it is either:
   - targeted review of the still-dominant compounder bucket
   - or model-weight / normalization review for representative names

Remaining known gaps after Module 43:
1. `high_quality_compounder` is now `83 / 100`, so the classifier is cleaner but still broad
2. some names now fall back to compounder because the current taxonomy has no intermediate stable-industrial bucket
3. if we want finer Buffett 3.0 classification quality, a small explicit sector-policy map is likely better than more keyword tweaking

### Module 44 Added: Targeted Panel And Memory Cyclical Overrides
Purpose:
- recover a few genuinely cyclical panel / memory names after the broader `光電` cleanup from Modules 42-43
- avoid reintroducing noisy global keywords while still routing obvious cyclical semiconductor-memory / panel names away from the default compounder path

Audit findings used for this pass:
1. after Module 43, several likely cyclical names were sitting in `high_quality_compounder` only because:
   - the source `industry` labels were noisy
   - global `光電` matching had been removed intentionally
2. the strongest candidates were:
   - `2409` 友達光電
   - `3481` 群創光電
   - `2408` 南亞科技
   - `2337` 旺宏
   - `6770` 力積電
3. these names were not being reclassified for good reasons:
   - `2409` and `3481` were falling through with noisy `農業科技` labels
   - `2408`, `2337`, and `6770` were being caught by generic electronics compounder wording instead of a cyclical override

Code changes completed:
1. updated [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py)
2. added `CYCLICAL_TICKER_OVERRIDES` for:
   - `2409`
   - `3481`
   - `2408`
   - `2337`
   - `6770`
3. wired the classifier to emit:
   - `classification = cyclical`
   - `classification_reason = ticker_matches_cyclical_override`
   - `classification_confidence = high`
4. updated [tests/test_buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_buffett_three.py)
5. added explicit classifier assertions that:
   - `2409` / `友達光電` routes to cyclical despite noisy industry text
   - `2408` / `南亞科技` routes to cyclical despite generic electronics wording

Artifact refresh completed:
1. rebuilt the full top100 Buffett 3.0 bundle after the override change
2. refreshed outputs include:
   - [artifacts/results/top100_model_results.csv](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results.csv)
   - [artifacts/results/top100_model_results_summary.json](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results_summary.json)
   - `artifacts/results/buffett3_payloads/*.json`

Real validation completed:
1. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three tests.test_app_reporting tests.test_artifact_consistency`
2. `python -m compileall tw_valuation_models tests app.py`
3. result:
   - `Ran 19 tests ... OK`

Live distribution after Module 44 refresh:
1. `high_quality_compounder: 78`
2. `cyclical: 13`
3. `financial: 5`
4. `defensive_dividend: 4`

Current cyclical bucket after Module 44:
1. `1101` 台泥
2. `1102` 亞泥
3. `1301` 台塑
4. `1303` 南亞塑膠
5. `1326` 台化
6. `1802` 台玻
7. `2002` 中鋼
8. `2337` 旺宏
9. `2408` 南亞科技
10. `2409` 友達
11. `2603` 長榮海運
12. `3481` 群創
13. `6770` 力積電

Important current conclusion:
1. this pass preserved the safer removal of broad `光電` matching while still recovering the most obvious panel / memory cyclicals
2. the classifier is now more intentional:
   - heavy-sector cyclicals via exact industry buckets
   - panel / memory cyclicals via narrow ticker overrides
   - stable non-cyclicals no longer swept in by raw word matching
3. the next best Buffett 3.0 work is likely no longer classification cleanup; it is review of valuation behavior and weighting for representative names under the now-cleaner taxonomy

Remaining known gaps after Module 44:
1. `high_quality_compounder` is still large at `78 / 100`
2. ticker overrides solve real cases but are not a full substitute for a richer sector-policy layer
3. if further classification work is desired, the next step should probably be an explicit curated sector map rather than more heuristic keyword additions

### Module 45 Added: Buffett 3.0 Compounder Dividend Leg Activation
Purpose:
- validate Buffett 3.0 valuation behavior on representative names under the cleaner taxonomy
- fix any real valuation-leg implementation gaps before touching scenario weights or broader normalization rules

Audit findings used for this pass:
1. representative payload review covered:
   - `2330`
   - `2881`
   - `2603`
   - `2412`
   - `2409`
   - `2408`
2. `2330` surfaced a real Buffett 3.0 issue:
   - classification was correct as `high_quality_compounder`
   - normalized dividend capacity was present
   - but the `dividend_yield_or_ddm` leg still showed `not_ready`
   - manual review flags included the equivalent of incomplete valuation-leg readiness
3. inspection of [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py) confirmed the cause:
   - `_compute_leg_value()` had no implementation branch for `dividend_yield_or_ddm`
   - compounder names therefore dropped that leg even when dividend history existed

Code changes completed:
1. updated [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py)
2. implemented `dividend_yield_or_ddm` valuation logic in `_compute_leg_value()`:
   - return `None` when required dividend-per-share inputs are missing
   - compute dividend-yield value as `dps / fair_dividend_yield`
   - compute DDM value as `next_year_dps / spread`
   - return a `50 / 50` blend of the two values
3. updated [tests/test_buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_buffett_three.py)
4. strengthened the compounder regression so it now asserts:
   - `dividend_yield_or_ddm` is `ready`
   - `blended_value` is populated
   - incomplete-valuation-leg review flags are absent for the representative compounder case
5. updated [tests/test_artifact_consistency.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_artifact_consistency.py)
6. added an artifact-level regression for saved `2330` Buffett 3.0 payloads so future refreshes keep the compounder dividend leg active when dividend history exists

Artifact refresh completed:
1. rebuilt the full top100 Buffett 3.0 bundle after the dividend-leg fix
2. refreshed outputs include:
   - [artifacts/results/top100_model_results.csv](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results.csv)
   - [artifacts/results/top100_model_results_summary.json](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results_summary.json)
   - `artifacts/results/buffett3_payloads/*.json`

Real validation completed:
1. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three tests.test_app_reporting tests.test_artifact_consistency`
2. `python -m compileall tw_valuation_models tests app.py`
3. result:
   - `Ran 20 tests ... OK`

Representative verification after Module 45 refresh:
1. `2330` now keeps the compounder dividend leg active:
   - classification remains `high_quality_compounder`
   - `dividend_yield_or_ddm` status is `ready`
   - manual review flags are now empty
   - refreshed final fair value is `705.198`
2. sampled peer payloads remained structurally sensible:
   - `2881` stayed `financial`
   - `2603` stayed `cyclical`
   - `2412` stayed `defensive_dividend`
   - `2409` and `2408` stayed `cyclical`

Important current conclusion:
1. the recent Buffett 3.0 work has now moved beyond classification cleanup and into real valuation-engine hardening
2. this was a true implementation bug rather than a judgment call about sector routing or weights
3. the next best step is to continue representative payload review for additional valuation anomalies before changing any Buffett 3.0 scenario weights

### Module 46 Added: Cyclical Partial-Leg Flag Cleanup
Purpose:
- keep Buffett 3.0 cyclical payloads transparent about the current EV/EBITDA limitation
- remove a noisier duplicate manual-review flag when the only missing leg is the known v1 structural EV/EBITDA placeholder

Audit findings used for this pass:
1. a full payload sweep showed a very consistent pattern across all current cyclical names:
   - `manual_review_flags` always included:
     - `cyclical_ev_ebitda_not_ready_without_clean_ebitda`
     - `cyclical_model_uses_partial_leg_set`
     - `some_valuation_legs_not_ready`
   - the only non-ready leg was always `normalized_ev_ebitda`
2. code inspection confirmed this was not a new data break:
   - [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py) intentionally keeps the cyclical EV/EBITDA leg visible but uncomputed in v1
   - the generic `some_valuation_legs_not_ready` flag was therefore duplicating a known structural limitation already described by more specific cyclical flags

Code changes completed:
1. updated [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py)
2. adjusted `_blend_valuation_legs()` so it now detects the specific case where:
   - classification is `cyclical`
   - the only missing leg is `normalized_ev_ebitda`
   - that leg is missing because v1 intentionally leaves it uncomputed
3. in that structural cyclical case:
   - keep `cyclical_ev_ebitda_not_ready_without_clean_ebitda`
   - keep `cyclical_model_uses_partial_leg_set`
   - stop adding the broader duplicate `some_valuation_legs_not_ready`
4. updated [tests/test_buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_buffett_three.py)
5. strengthened cyclical regression coverage to assert that the specific cyclical partial-leg flag remains while the generic duplicate flag is absent
6. updated [tests/test_artifact_consistency.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_artifact_consistency.py)
7. added artifact-level assertions that saved cyclical payloads retain the EV/EBITDA blockers and cyclical partial-leg flag without also publishing `some_valuation_legs_not_ready`

Artifact refresh completed:
1. rebuilt the full top100 Buffett 3.0 bundle after the cyclical-flag cleanup
2. refreshed outputs include:
   - [artifacts/results/top100_model_results.csv](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results.csv)
   - [artifacts/results/top100_model_results_summary.json](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results_summary.json)
   - `artifacts/results/buffett3_payloads/*.json`

Real validation completed:
1. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three tests.test_app_reporting tests.test_artifact_consistency`
2. `python -m compileall tw_valuation_models tests app.py`
3. result:
   - `Ran 20 tests ... OK`

Representative verification after Module 46 refresh:
1. sampled cyclical payloads checked:
   - `2603`
   - `2409`
   - `2408`
   - `1101`
2. each still correctly publishes:
   - `cyclical_ev_ebitda_not_ready_without_clean_ebitda`
   - `cyclical_model_uses_partial_leg_set`
   - `warnings = ["valuation_weights_reallocated_over_ready_legs"]`
3. each no longer publishes:
   - `some_valuation_legs_not_ready`

Important current conclusion:
1. Buffett 3.0 cyclical output is now cleaner without hiding the real v1 EV/EBITDA limitation
2. the remaining cyclical warning state is more intentional:
   - specific structural limitation flags remain
   - generic duplicate manual-review noise is reduced
3. the next best step is still representative valuation review, but now likely focused on whether the cyclical EV/EBITDA leg should stay intentionally uncomputed in v1 or gain a conservative proxy implementation in a later module

### Module 47 Added: Non-Negative Buffett 3.0 Equity Output Guardrails
Purpose:
- stop Buffett 3.0 from publishing impossible negative fair values per share on weak compounder names
- align the model more closely with the existing v1 spec while preserving the strong downside signal on distressed names

Audit findings used for this pass:
1. representative payload sweep showed several `high_quality_compounder` names with negative fair values, including:
   - `3714`
   - `4919`
   - `6451`
   - `3006`
   - `2344`
2. the failure mode was consistent:
   - negative normalized EPS or negative average FCF propagated into negative `normalized_pe`, `fcf_yield`, or `residual_earnings` leg outputs
   - blended Buffett 3.0 fair value could therefore fall below zero, which is not a sensible equity valuation output
3. spec review in [BUFFETT_3_0_V1_SPEC.md](/D:/Codex%20projects/TW%20Valuation%20models/BUFFETT_3_0_V1_SPEC.md) also confirmed an already-intended normalization rule that had not been implemented:
   - high-quality compounder `FCF/share` should use the 3-year average with a floor at zero when all sampled periods are negative

Code changes completed:
1. updated [tw_valuation_models/models/buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/models/buffett_three.py)
2. added `_normalize_fcf_per_share()` so `high_quality_compounder` names now follow the spec-aligned rule:
   - use 3-year average FCF/share normally
   - floor to `0.0` only when the trailing sampled compounder FCF/share periods are all negative
3. added a non-negative equity-output guardrail in `_build_valuation_legs()`:
   - when a computed per-share leg value is negative, floor that scenario value to `0.0`
   - add a single leg note: `negative_equity_leg_value_floored_to_zero`
4. this keeps Buffett 3.0 honest:
   - weak names can still screen as deeply unattractive
   - but the model no longer emits impossible negative per-share equity values
5. updated [tests/test_buffett_three.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_buffett_three.py)
6. added a regression covering a distressed compounder case where:
   - negative PE / FCF / residual-style outputs are floored to zero
   - final fair value remains non-negative
7. updated [tests/test_artifact_consistency.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_artifact_consistency.py)
8. added an artifact-level guard that saved Buffett 3.0 payloads must not publish negative ready-leg values or negative final fair values

Artifact refresh completed:
1. rebuilt the full top100 Buffett 3.0 bundle after the non-negative output fix
2. refreshed outputs include:
   - [artifacts/results/top100_model_results.csv](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results.csv)
   - [artifacts/results/top100_model_results_summary.json](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/top100_model_results_summary.json)
   - `artifacts/results/buffett3_payloads/*.json`

Real validation completed:
1. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three tests.test_app_reporting tests.test_artifact_consistency`
2. `python -m compileall tw_valuation_models tests app.py`
3. result:
   - `Ran 22 tests ... OK`

Representative verification after Module 47 refresh:
1. formerly negative compounder outputs were rechecked:
   - `3714`
   - `4919`
   - `6451`
   - `3006`
   - `2344`
2. those names now remain strongly unattractive, but fair values are no longer negative:
   - `3714` now `8.906`
   - `4919` now `0.0`
   - `6451` now `6.7966`
   - `3006` now `3.6524`
   - `2344` now `3.7469`
3. affected legs now carry a single explicit floor note rather than repeated scenario-note noise

Important current conclusion:
1. Buffett 3.0 hardening has now removed another unrealistic output class from the live artifacts
2. the engine is now more production-safe on distressed names:
   - no negative ready-leg values
   - no negative final fair values
3. the next best step is probably not more guardrails, but a review of whether some names still sitting in `high_quality_compounder` should really route to a different Buffett 3.0 bucket before deeper scenario-weight tuning

### Module 48 Added: Buffett 3.0 App Reporting Label Hardening
Purpose:
- make the live Streamlit reporting path display Buffett 3.0 types, reasons, and modifier flags correctly after the recent model hardening passes
- remove a real UI degradation where string-valued Buffett 3.0 reason fields could render as `無` or raw internal keys

Audit findings used for this pass:
1. the engine-side Buffett 3.0 payload has grown more expressive across Modules 41-47:
   - more classifier reasons
   - more cyclical limitation flags
   - the new `negative_equity_leg_value_floored_to_zero` safeguard note
2. app-side helper review found a mismatch in [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py):
   - `join_buffett3_labels()` only handled non-empty lists cleanly
   - several Buffett 3.0 fields can arrive as strings or comma-separated strings
3. practical consequence:
   - some live Buffett 3.0 detail sections could show `無`
   - some internal model keys could leak through untranslated instead of readable Traditional Chinese labels

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. expanded `format_buffett3_label()` coverage for newer Buffett 3.0 keys, including:
   - `negative_equity_leg_value_floored_to_zero`
   - `monthly_revenue_yoy_supportive`
   - `industry_or_ticker_matches_financial_rules`
   - `defaulted_to_compounder_rule`
   - other classifier, balance-sheet, and payload-note keys added during hardening
3. hardened `join_buffett3_labels()` so it now supports:
   - `None`
   - lists
   - single strings
   - comma-separated strings
4. adjusted Buffett 3.0 type presentation so:
   - `defensive_dividend` displays as `防禦收益股`
   - unknown / absent type falls back to `無資料`
5. updated [tests/test_app_reporting.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_app_reporting.py)
6. added app-side regression coverage proving the helper path now renders:
   - single-string flags
   - comma-separated strings
   - newly introduced hardening notes

Real validation completed:
1. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three tests.test_app_reporting tests.test_artifact_consistency`
2. `python -m compileall tw_valuation_models tests app.py`
3. localhost smoke check:
   - `Invoke-WebRequest -UseBasicParsing 'http://localhost:8501' -TimeoutSec 15 | Select-Object StatusCode, Content`
4. result:
   - `Ran 23 tests ... OK`
   - compile succeeded
   - localhost returned HTTP `200`

Important current conclusion:
1. the Buffett 3.0 engine and app reporting layers are now aligned more cleanly for production use
2. this pass removed a real presentation bug rather than adding another speculative enhancement
3. the remaining open items are now mostly optional refinement work:
   - broader browser-side visual QA
   - future taxonomy / scenario-weight tuning
   - later cyclical EV/EBITDA expansion if desired

### Module 49 Added: Buffett 3.0 Default Focus And Live Card Review
Purpose:
- finish the highest-value remaining app-side Buffett 3.0 product decisions after the production hardening pass
- close the remaining backlog items that were still about live presentation consistency rather than core model math

Audit findings used for this pass:
1. the main-page layout swap request was completed successfully:
   - `模型快照` moved into the upper three-card comparison row
   - `研究觀點` moved into the lower right rail slot
2. the app was still defaulting the detail focus to the first active model:
   - in practice this meant users landed on `buffett_v1`
   - that no longer matched the current roadmap emphasis, where Buffett 3.0 is the most actively hardened Buffett-family path
3. Buffett 3.0 artifact spot-checks were completed for representative names:
   - `2330`
   - `2881`
   - `2603`
   - `2412`
4. those spot checks confirmed the saved Buffett 3.0 payloads and `top100_model_results.csv` rows were aligned on the key outputs reviewed in this pass:
   - `2330` compounder output around `705.198`
   - `2881` financial output with `current_ratio_missing`
   - `2603` cyclical output with EV/EBITDA blockers and partial-leg warning state
   - `2412` defensive dividend output without extra manual-review noise

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. added `choose_focus_model()` so the app now:
   - preserves an explicit user-selected focus model when it remains active
   - otherwise defaults to `buffett3` when Buffett 3.0 is enabled
   - falls back to the first active model only when Buffett 3.0 is unavailable
3. this default now drives the pre-radio preview state cleanly instead of always favoring the oldest Buffett tab
4. updated [tests/test_app_reporting.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_app_reporting.py)
5. added regression coverage proving:
   - Buffett 3.0 becomes the default focus when present
   - an explicit existing user focus selection is preserved
   - non-Buffett3 active sets still fall back safely
6. updated [TODO.md](/D:/Codex%20projects/TW%20Valuation%20models/TODO.md)
7. removed the completed backlog items for:
   - live Buffett 3.0 card/comparison review
   - the default Buffett-family detail-tab decision
   - representative payload spot checks

Real validation completed:
1. `python -m unittest tests.test_app_reporting tests.test_buffett_three tests.test_artifact_consistency`
2. `python -m compileall app.py`
3. result:
   - targeted regression slice green
   - compile succeeded

Important current conclusion:
1. the app now better reflects the actual project emphasis:
   - Buffett 3.0 is surfaced by default in the detail workflow
   - older Buffett variants still remain available in parallel
2. the remaining TODO list is now mostly future data and model-expansion work rather than unfinished production cleanup

### Module 50 Added: Reporting Enhancements, Ranking Comparison, And Dividend Parser Follow-Up
Purpose:
- complete the highest-value remaining TODO items that could be finished locally without inventing new model math
- improve export/reporting utility around Buffett 3.0 provenance and ranking behavior
- tighten the official dividend ingestion path for mixed cash-plus-stock dividend rows such as `2881`

Audit findings used for this pass:
1. the remaining TODO list still contained three enhancement items that were implementable with existing local artifacts:
   - row-level manifest visibility for Buffett 3.0 report consumers
   - export-friendly Buffett 3.0 explanation fields
   - ranking-behavior comparison against `quant` and `hybrid`
2. report generation in [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py) already had the right inputs available:
   - live Buffett 3.0 payloads
   - manifest diagnostics
   - top100 result tables
3. local review of the existing dividend artifact for `2881` showed a real data-quality gap:
   - Fubon-style mixed cash-plus-stock distributions were not represented in the saved official dividend dataset
   - Buffett 3.0 was therefore correctly falling back to proxy / missing-dividend signaling on those rows

Code changes completed:
1. added [tw_valuation_models/reporting.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/reporting.py)
2. implemented three reusable helpers there:
   - `summarize_manifest_for_ticker()`
   - `build_buffett3_export_notes()`
   - `build_model_ranking_comparison()`
3. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py) so exported reports now include:
   - `data_provenance.manifest_ticker_coverage`
   - `buffett3_detail.reporting_notes`
4. added regression coverage in:
   - [tests/test_app_reporting.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_app_reporting.py)
   - [tests/test_dataset.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_dataset.py)
5. generated [artifacts/results/model_ranking_comparison.json](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/results/model_ranking_comparison.json)
6. added `_fetch_dividend_history_official_v2()` in [tw_valuation_models/dataset.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/dataset.py) and switched the dataset build to use it
7. broadened stock-dividend field recognition to cover TWSE labels like:
   - `股東配發-盈餘轉增資配股(元/股)`
   - `股東配發-法定盈餘公積轉增資配股(元/股)`
   - `股東配發-資本公積轉增資配股(元/股)`
8. updated [TODO.md](/D:/Codex%20projects/TW%20Valuation%20models/TODO.md) to remove the enhancement items that are now completed

Real validation completed:
1. targeted regression slice:
   - `python -m unittest tests.test_dataset tests.test_app_reporting tests.test_artifact_consistency`
2. full regression slice:
   - `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three tests.test_app_reporting tests.test_artifact_consistency`
3. compile check:
   - `python -m compileall tw_valuation_models tests app.py`
4. dataset and model refresh:
   - rebuilt top100 dataset and model artifacts successfully after the parser change

Important current conclusion:
1. the reporting / export backlog is now materially more complete:
   - per-ticker manifest coverage is available in the report payload
   - Buffett 3.0 detail exports now include explanation-ready notes
   - cross-model ranking comparison for the top100 universe now exists as a generated artifact
2. the dividend parser improvement is implemented and regression-covered, but the live rebuilt official dividend artifact remained empty in this environment
3. because of that, the `2881` dividend item remains correctly open in [TODO.md](/D:/Codex%20projects/TW%20Valuation%20models/TODO.md) as an external-data follow-up rather than being overstated as fully resolved

### Module 51 Added: Final-Module Pilot Data Layer And Shared-Root Raw Source Pipeline
Purpose:
- start the final AI commentary module as a completely separate data layer without touching existing valuation logic
- keep all newly downloaded source pages under the same shared data root so there is one download home for official data and final-module market-context data
- wire a first pilot path for `2330`, `2881`, `2603`, and `2412`

Design constraints preserved:
1. do not modify existing Buffett / IMFS / Quant / Hybrid valuation formulas
2. do not change current app UI yet
3. do store new raw source downloads under `paths.shared_data_root`
4. do keep final-module normalized tables and summaries isolated from the current model results

Code changes in progress for this pass:
1. extended [tw_valuation_models/config.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/config.py) with explicit final-module path helpers:
   - `final_module_shared_root`
   - `final_module_raw_root`
   - `final_module_manifest_root`
   - `final_module_artifacts_root`
   - `final_module_normalized_root`
2. added [tw_valuation_models/final_module_data.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/final_module_data.py) as a new standalone pipeline that:
   - defines a curated pilot source catalog for `2330`, `2881`, `2603`, `2412`
   - downloads raw source pages into the shared data root
   - writes per-source manifest JSON files beside the raw downloads
   - builds:
     - `institutional_consensus.csv`
     - `news_commentary.csv`
     - `public_commentary.csv`
     - `market_view_snapshot.csv`
3. updated [tw_valuation_models/cli.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/cli.py) with new commands:
   - `fetch-final-module-sources`
   - `build-final-module-snapshot`
   - `run-final-module-pilot`
4. added [tests/test_final_module_data.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_final_module_data.py) to cover:
   - raw HTML download storage under the shared data root
   - normalized-table generation and market-view snapshot output

Intended output layout after this pass:
1. shared raw downloads:
   - `shared_data_root/final_module/raw/...`
2. shared per-source manifests:
   - `shared_data_root/final_module/manifests/...`
3. workspace normalized outputs:
   - `artifacts/final_module/normalized/...`
4. workspace run summary:
   - `artifacts/final_module/summary.json`

Next verification target:
1. run the new unit tests locally
2. run compile checks
3. if green, execute the new pilot downloader against the real shared data root and save the fetched source pages there

Verification completed for this module:
1. all pilot raw source pages were downloaded into the shared data root
2. fallback updates replaced the blocked Fintel pages with Yahoo valuation pages
3. controlled SSL retry removed the remaining raw-download failures
4. final state:
   - `24/24` pilot source entries downloaded successfully
   - normalized final-module pilot tables built successfully

### Module 52 Added: Pilot Independent-AI And Final-Commentary Payload Generation
Purpose:
- move the final-module work from raw sources and normalized tables into actual user-facing payloads
- generate a first complete `independent_ai` and `final_commentary` layer for the four pilot tickers
- keep this entire layer fully separate from existing valuation outputs

Code changes completed:
1. extended [tw_valuation_models/config.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/config.py) with:
   - `final_module_payload_root`
   - `final_module_independent_ai_root`
   - `final_module_commentary_root`
2. added [tw_valuation_models/final_module_payloads.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/final_module_payloads.py)
3. the new payload builder now:
   - reads current internal model outputs
   - reads final-module normalized tables
   - applies a separate sector-specific independent valuation range for:
     - `2330`
     - `2881`
     - `2603`
     - `2412`
   - writes:
     - `artifacts/final_module/payloads/independent_ai/{ticker}.json`
     - `artifacts/final_module/payloads/final_commentary/{ticker}.json`
4. updated [tw_valuation_models/cli.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/cli.py) with:
   - `build-final-module-payloads`
5. fixed [tw_valuation_models/__main__.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/__main__.py) so local dependency bootstrap runs before importing the CLI
6. added [tests/test_final_module_payloads.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_final_module_payloads.py)

Real validation completed:
1. `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three tests.test_app_reporting tests.test_artifact_consistency tests.test_final_module_data tests.test_final_module_payloads`
2. `python -m compileall tw_valuation_models tests app.py`
3. `python -m tw_valuation_models build-final-module-payloads`

Generated payload state:
1. pilot payload count:
   - `4`
2. generated files:
   - `artifacts/final_module/payloads/independent_ai/2330.json`
   - `artifacts/final_module/payloads/independent_ai/2881.json`
   - `artifacts/final_module/payloads/independent_ai/2603.json`
   - `artifacts/final_module/payloads/independent_ai/2412.json`
   - `artifacts/final_module/payloads/final_commentary/2330.json`
   - `artifacts/final_module/payloads/final_commentary/2881.json`
   - `artifacts/final_module/payloads/final_commentary/2603.json`
   - `artifacts/final_module/payloads/final_commentary/2412.json`

Important current conclusion:
1. the final module is now no longer just a plan:
   - it has source downloads
   - normalized market-context tables
   - pilot independent-AI valuation payloads
   - pilot final commentary payloads
2. the next highest-value step is no longer data plumbing
3. the next highest-value step is one of:
   - refine payload wording / encoding polish for live presentation
   - add UI integration as a separate new page or section
   - broaden the payload builder beyond the four pilot tickers

### Module 53 Added: Final Module Main-UI Integration
Purpose:
- connect the new final-module payload layer into the existing Streamlit app without changing any existing valuation model logic
- keep the final module as a read-only interpretation layer on top of the current outputs
- make the pilot payloads reviewable directly from the main UI

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py) to add:
   - final-module payload path constants
   - `load_final_module_payload(...)`
   - `format_final_module_confidence(...)`
   - `render_final_module_panel(...)`
2. added a new detail tab in the main stock view:
   - `Final AI`
3. the new tab now reads:
   - `artifacts/final_module/payloads/independent_ai/{ticker}.json`
   - `artifacts/final_module/payloads/final_commentary/{ticker}.json`
4. the tab presents:
   - final valuation label
   - action stance
   - confidence
   - independent AI fair-value range
   - internal-model comparison table
   - news and public-vs-institution view
   - key risks and change-view conditions
5. updated [tests/test_app_reporting.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_app_reporting.py) with coverage for final-module payload loading

Verification completed for this module:
1. `python -m unittest tests.test_app_reporting tests.test_final_module_payloads tests.test_final_module_data`
2. `python -m compileall tw_valuation_models tests app.py`
3. local Streamlit smoke:
   - launched `python -m streamlit run app.py --server.headless true --server.port 8501`
   - local HTTP check returned `200`

Current state after integration:
1. final-module pilot payloads are now surfaced from the main app
2. existing valuation engines remain unchanged
3. the final module is still pilot-scoped to:
   - `2330`
   - `2881`
   - `2603`
   - `2412`

Next highest-value step:
1. remove duplicate helper definitions left behind in [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py) during the integration pass
2. do a browser-level visual inspection of the new `Final AI` tab
3. decide whether to expand the final module beyond the pilot tickers

### Module 54 Added: Auto-Refresh Final AI Page On Entry
Purpose:
- make `Final AI 專區` behave like a fresh research run instead of a static viewer
- rerun the shared top100 dataset, core valuation outputs, final-module source pipeline, and final-module payload generation when the user enters the page
- keep the behavior scoped to page transitions so repeated reruns do not trigger on every same-page interaction

Code changes completed:
1. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py) to add:
   - `should_refresh_final_ai(...)`
   - `refresh_all_outputs_for_final_ai()`
   - `previous_page_mode` session-state tracking
2. entering `Final AI 專區` from another page mode now runs:
   - `build_top100_dataset(PATHS)`
   - `build_all_model_results(PATHS)`
   - `run_final_module_pilot(PATHS, overwrite=True)`
   - `build_final_module_payloads(PATHS)`
3. after the refresh finishes, the app now:
   - clears `st.cache_data`
   - reruns the Streamlit script
   - shows the page with rebuilt outputs
4. updated [tests/test_app_reporting.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_app_reporting.py) with transition coverage for the refresh trigger

Verification completed for this module:
1. `python -m unittest tests.test_app_reporting tests.test_final_module_data tests.test_final_module_payloads`
   - `12 tests ... OK`
2. `python -m compileall tw_valuation_models tests app.py`
   - passed
3. local HTTP smoke on `http://127.0.0.1:8501`
   - returned `200`

Current state after this module:
1. `Final AI 專區` is now an update-triggered page, not just a payload viewer
2. the refresh is transition-based:
   - entering the page triggers a rerun
   - staying on the page does not keep rerunning
3. existing model formulas remain untouched

Next highest-value step:
1. visually inspect the page transition behavior in-browser to confirm the rerun experience feels acceptable
2. clean up duplicate helper definitions in [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
3. decide whether to extend final-module payload generation beyond the four pilot tickers

### Module 55 Added: Final AI UI Verification And Cleanup
Purpose:
- finish the last integration polish around the new `Final AI 專區`
- verify the page in-browser instead of relying only on unit tests
- remove duplicate helper definitions and fix the confidence label display

Code and verification completed:
1. removed the duplicate trailing copies of:
   - `format_final_module_confidence(...)`
   - `render_final_module_panel(...)`
   from [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
2. updated `format_final_module_confidence(...)` so it accepts both normalized values like:
   - `medium_high`
   and already-localized values like:
   - `中高`
3. browser-level verification confirmed that `2330` now shows:
   - `信心：中高`
   on the `Final AI 專區` page
4. regression and compile verification completed:
   - `python -m unittest tests.test_app_reporting tests.test_final_module_data tests.test_final_module_payloads`
   - `python -m compileall app.py`

Current state after this module:
1. the `Final AI 專區` page is visible from the main UI
2. entering the page refreshes the full output pipeline
3. the final-AI card now renders the confidence label correctly
4. duplicate helper shadowing in [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py) has been removed

### Module 56 Added: Arbitrary Ticker Latest-Data Generation
Purpose:
- allow the user to type any ticker and generate all model outputs on demand
- make `Final AI` work for non-top100 tickers using the latest current data
- keep the existing top100 flow intact while adding an on-demand runtime path

Code and verification completed:
1. added single-ticker runtime paths in [tw_valuation_models/config.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/config.py)
2. added `build_single_ticker_dataset(...)` in [tw_valuation_models/dataset.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/dataset.py)
3. added `build_single_ticker_model_result(...)` in [tw_valuation_models/portfolio_builder.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/portfolio_builder.py)
4. generalized [tw_valuation_models/final_module_payloads.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/final_module_payloads.py) so it can build payloads from:
   - top100 results
   - or on-demand runtime results
5. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py) so:
   - sidebar now has an arbitrary ticker input
   - pressing the new button downloads latest data and generates all models
   - custom ticker rows are merged into the main result set
   - the selected ticker uses its own dataset root for charts, metrics, diagnostics, and Final AI
   - entering `Final AI` refreshes the selected ticker instead of only relying on the old pilot flow
6. configured yfinance cache to use a writable workspace-local runtime directory in [tw_valuation_models/dataset.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/dataset.py)
7. added regression coverage for non-top100 on-demand payload fallback in [tests/test_final_module_payloads.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_final_module_payloads.py)

Live smoke test completed:
1. arbitrary ticker `2308` was generated successfully end-to-end using live network access
2. created runtime dataset under:
   - [2308 dataset](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/runtime/on_demand/datasets/2308)
3. created on-demand model result under:
   - [2308 result](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/runtime/on_demand/model_results/2308.json)
4. created final AI payloads under:
   - [2308 independent_ai](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/final_module/payloads/independent_ai/2308.json)
   - [2308 final_commentary](/D:/Codex%20projects/TW%20Valuation%20models/artifacts/final_module/payloads/final_commentary/2308.json)

Verification completed:
1. `python -m unittest tests.test_final_module_payloads tests.test_app_reporting`
2. `python -m compileall tw_valuation_models app.py tests`

Current state after this module:
1. the app can now generate latest-data outputs for arbitrary tickers, not only the top100 universe
2. Final AI payload generation is no longer limited to the four original pilot tickers
3. market/news/public context is still richest for the curated pilot set, but non-pilot tickers now have a working independent AI and final commentary path

### Module 57 Added: Streamlit Cloud Deployment Hardening Pass 1
Purpose:
- prepare the project for free public deployment on Streamlit Community Cloud
- remove hard dependency on Windows-only absolute paths
- fail with clear app messaging when external model sources are unavailable

Code and verification completed:
1. updated [tw_valuation_models/config.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/config.py)
   - workspace, shared-data, and source-model roots now support environment variables
   - defaults now fall back to repo-relative paths instead of `D:\...`
   - added repo-relative external model roots:
     - `imfs_source_root`
     - `quant_source_root`
     - `hybrid_source_root`
2. updated [tw_valuation_models/source_bridge.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/source_bridge.py)
   - external model imports now read from configurable roots
   - missing external source roots now raise clear `FileNotFoundError` messages
3. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
   - startup now catches initialization failures and shows deployment guidance in the UI
   - the app stops cleanly instead of dropping the user into a raw traceback
4. added deployment-oriented files:
   - [README.md](/D:/Codex%20projects/TW%20Valuation%20models/README.md) public deployment notes
   - [.streamlit/config.toml](/D:/Codex%20projects/TW%20Valuation%20models/.streamlit/config.toml)
5. added regression coverage:
   - [tests/test_config.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_config.py)
   - [tests/test_source_bridge.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_source_bridge.py)

Verification completed:
1. `python -m unittest tests.test_config tests.test_source_bridge tests.test_app_reporting tests.test_final_module_data tests.test_final_module_payloads`
2. `python -m compileall tw_valuation_models tests app.py`

Current state after this module:
1. the project is materially closer to Streamlit Community Cloud compatibility
2. hardcoded local Windows paths are no longer the primary blocker
3. the main remaining blocker for full public deployment is external model source availability for:
   - IMFS
   - TW Buffett Quant
   - TW Hybrid
4. if those external sources are not provided in the cloud environment, the app now fails gracefully with setup guidance instead of crashing invisibly

### Module 58 Added: Public Demo Degradation Path
Purpose:
- make a free public demo deployment realistic even when the external source-model repos are not available in the cloud
- keep the app usable with internal Buffett-family models and Final AI instead of failing the entire pipeline

Code and verification completed:
1. updated [tw_valuation_models/portfolio_builder.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/portfolio_builder.py)
   - external models are now loaded through an optional availability layer
   - missing IMFS / Quant / Hybrid sources no longer crash result generation
   - fallback outputs are generated with stable placeholder values and explicit `unavailable` signals
   - result summaries now include external model availability metadata
2. updated [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
   - sidebar now detects whether external model roots exist
   - public demo mode shows a warning when IMFS / Quant / Hybrid are unavailable
3. updated [README.md](/D:/Codex%20projects/TW%20Valuation%20models/README.md)
   - documented the public demo mode behavior
4. added regression coverage:
   - [tests/test_portfolio_builder.py](/D:/Codex%20projects/TW%20Valuation%20models/tests/test_portfolio_builder.py)

Verification completed:
1. `python -m unittest tests.test_portfolio_builder tests.test_config tests.test_source_bridge tests.test_final_module_payloads tests.test_app_reporting`
2. `python -m compileall tw_valuation_models tests app.py`

Current state after this module:
1. a free public Streamlit demo is now feasible without bundling all external source-model repos on day one
2. missing external model repos degrade to an explicit demo-mode warning instead of breaking the whole app
3. the remaining work for a real public launch is mostly deployment wiring and a cloud smoke test, not core app stabilization
### Module 59 Added: Streamlit Public Demo Entry And Deploy Docs
Purpose:
- prepare the repo for a free public Streamlit Community Cloud demo
- add a standard `streamlit_app.py` entrypoint
- provide a clean Traditional Chinese deployment README and secrets example

Changes:
- rewrote `README.md` into a clean UTF-8 deployment/user guide
- added `streamlit_app.py` as the standard Streamlit Cloud entrypoint
- added `.streamlit/secrets.toml.example` for deploy-time environment mapping
- updated `.gitignore` to exclude `.streamlit/secrets.toml`

Notes:
- public demo mode still degrades gracefully when external model repos are unavailable
- `IMFS`, `台股 Buffett Quant`, and `混合模型` remain optional in cloud demo mode
