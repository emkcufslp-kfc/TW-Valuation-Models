# Buffett 3.0 V1 Core Calculation Spec

## Scope
This document defines the V1 core-calculation plan for Buffett 3.0 in this workspace.

V1 goal:
- implement an auditable fair-value engine before any Buffett 3.0 UI work

V1 includes:
- rule-based company classification
- normalized economics by company type
- sector-appropriate valuation legs
- conservative/base/bull scenario handling
- probability-weighted blended fair value
- macro/Taiwan/reality modifiers
- auditable output payload

V1 does not include:
- final UI panels
- full institutional report rendering
- automated monthly-revenue validation
- complete EV/EBITDA with clean net-debt support
- historical regime-table automation beyond current snapshot inputs

## Non-Negotiables
Master formula from the approved Buffett 3.0 direction:

```text
Fair Value per Share
=
Blended Normalized Valuation
x Macro Regime Modifier
x Taiwan Risk Modifier
x Reality Validation Modifier
```

Required sequence:
1. Estimate valuation by model before macro/risk/reality adjustment.
2. Apply macro modifier.
3. Apply Taiwan risk modifier.
4. Apply reality validation modifier.

## V1 Engine Shape
Recommended module split:
1. `classifier`
   - maps ticker to one of four company types
2. `normalizer`
   - computes normalized EPS, FCF/share, BVPS, ROE, and stability signals
3. `legs`
   - runs valuation legs for the chosen company type
4. `scenarios`
   - applies conservative/base/bull assumptions
5. `modifiers`
   - applies macro, Taiwan-risk, and reality-validation modifiers
6. `payload`
   - emits a fully auditable result object

## Classification Framework
V1 company types:
1. `high_quality_compounder`
2. `financial`
3. `cyclical`
4. `defensive_dividend`

V1 classification rules should remain explicit and inspectable. They should not depend on opaque scoring.

Recommended first-pass rules:
1. `financial`
   - sector or industry contains finance, bank, insurance, securities, or financial holding
2. `cyclical`
   - industry contains shipping, steel, panel, memory, DRAM, chemicals, or other commodity-linked businesses
3. `defensive_dividend`
   - industry contains telecom, utility, food, gas, or other stable yield-led businesses
4. `high_quality_compounder`
   - default for durable high-return non-financial businesses with strong reinvestment economics

The classifier should also emit:
- `classification_reason`
- `classification_confidence`
- `manual_review_flags`

## Normalized Economics Rules
The normalization layer should produce one reusable input bundle regardless of company type.

Core normalized fields:
- `normalized_eps`
- `normalized_fcf_per_share`
- `normalized_bvps`
- `normalized_roe`
- `normalized_dividend_capacity_per_share`
- `latest_price`
- `latest_pe_snapshot`
- `latest_pb_snapshot`
- `latest_dividend_yield_snapshot`
- `trend_flags`
- `data_quality_flags`

Recommended V1 normalization logic by type:

### High Quality Compounder
- EPS basis:
  - use `min(ttm_eps, average_of_last_3_full_year_eps)` when the latest year looks elevated
  - otherwise use blended `60% latest full-year EPS + 40% 3-year average EPS`
- FCF/share basis:
  - use 3-year average FCF/share with a floor at zero only if all sampled periods are negative
- BVPS basis:
  - use latest BVPS
- ROE basis:
  - use 3-year average ROE, capped if a single outlier year dominates

### Financial
- Sustainable ROE:
  - use 3-year average ROE unless the latest year is materially below trend
  - if latest year is below 75% of the 3-year average, blend `70% 3-year average + 30% latest`
- Sustainable EPS:
  - `latest_bvps x sustainable_roe`
- BVPS basis:
  - use latest BVPS
- Dividend capacity:
  - use dividend proxy only when a reliable source exists
  - otherwise mark DDM as assumption-driven

### Cyclical
- EPS basis:
  - do not use peak-year EPS directly
  - use the lowest of:
    - trailing 3-year average EPS
    - trailing 4-year average EPS
    - TTM EPS if it is below both averages
- FCF/share basis:
  - use 3-year average FCF/share only as a cross-check, not the primary anchor
- BVPS basis:
  - use latest BVPS
- Downside anchor:
  - prefer trough PB / asset-value style methods over headline PE

### Defensive / Dividend
- EPS basis:
  - use 3-year average EPS unless TTM is lower, then blend with TTM
- FCF/share basis:
  - use 3-year average FCF/share
- BVPS basis:
  - use latest BVPS
- Dividend capacity:
  - proxy from stable payout capacity until dividend history is added

## Valuation Legs And Weights
These weights are already approved in the planning notes and should be preserved.

### High Quality Compounder
- `normalized_pe`: `35%`
- `fcf_yield`: `25%`
- `residual_earnings`: `25%`
- `dividend_yield_or_ddm`: `15%`

Leg formulas:
- `normalized_pe_value = normalized_eps x fair_pe`
- `fcf_yield_value = normalized_fcf_per_share / required_fcf_yield`
- `residual_earnings_value = bvps + ((residual_eps x persistence_factor) / (cost_of_equity - growth))`

### Financial
- `roe_adjusted_pb`: `40%`
- `ddm`: `35%`
- `normalized_pe`: `15%`
- `residual_income`: `10%`

Leg formulas:
- `sustainable_eps = bvps x sustainable_roe`
- `fair_pb = (roe - growth) / (cost_of_equity - growth)`
- `pb_value = bvps x fair_pb`
- `ddm_value = dps_next_year / (cost_of_equity - long_term_dividend_growth)`

### Cyclical
- `mid_cycle_eps`: `30%`
- `normalized_ev_ebitda`: `30%`
- `replacement_asset_value`: `20%`
- `trough_pb_downside`: `20%`

Leg formulas:
- `mid_cycle_pe_value = normalized_eps x mid_cycle_pe`
- `ev_ebitda_value_per_share = ((normalized_ebitda x fair_ev_ebitda) - net_debt) / shares_outstanding`

V1 downgrade rule:
- if clean cash / debt data is unavailable, set `normalized_ev_ebitda` to `not_ready` and redistribute weight only if the user approves that simplification
- until then, keep the leg visible in output as missing rather than silently fabricating it

### Defensive / Dividend
- `dividend_yield_band`: `35%`
- `ddm`: `30%`
- `normalized_pe`: `25%`
- `fcf_yield`: `10%`

Leg formulas:
- `dividend_yield_value = normalized_dps / fair_dividend_yield`
- `ddm_value = dps_next_year / (cost_of_equity - long_term_growth)`
- `normalized_pe_value = normalized_eps x fair_pe`
- `fcf_yield_value = normalized_fcf_per_share / required_fcf_yield`

## Scenario Framework
Scenario weights:
- default: `30% conservative + 50% base + 20% bull`
- high-quality compounder: `25% conservative + 50% base + 25% bull`
- high uncertainty: `40% conservative + 45% base + 15% bull`

Each leg should return:
- `conservative_value`
- `base_value`
- `bull_value`
- `scenario_assumptions`

Then compute:

```text
leg_blended_value
=
(conservative_value x conservative_weight)
+ (base_value x base_weight)
+ (bull_value x bull_weight)
```

Then compute:

```text
blended_normalized_valuation
=
sum(leg_blended_value x leg_weight)
```

## Modifier Framework
V1 modifier handling should be explicit and configurable.

Required modifier blocks:
1. `macro_regime_modifier`
2. `taiwan_risk_modifier`
3. `reality_validation_modifier`

V1 design rule:
- the engine must support these modifiers now
- the exact numerical tables should live in a config object so they can be confirmed before production use

Suggested V1 payload for each modifier:
- `raw_score`
- `selected_bucket`
- `modifier_value`
- `reason`
- `data_source`

Examples of V1-ready signals:
- macro:
  - TAIEX trend
  - rate-sensitive regime switch placeholder
- Taiwan risk:
  - default country-risk haircut placeholder
  - business-specific export/cross-strait sensitivity flag
- reality validation:
  - quarterly trend support
  - balance-sheet stress check
  - monthly revenue validation placeholder when unavailable

## Auditable Output Schema
Each result should return a single structured payload.

Required top-level fields:
- `ticker`
- `company_name`
- `valuation_date`
- `classification`
- `classification_reason`
- `input_snapshot`
- `normalized_inputs`
- `valuation_legs`
- `scenario_weights`
- `blended_normalized_valuation`
- `modifiers`
- `final_fair_value_per_share`
- `current_price`
- `upside_downside_pct`
- `data_quality_flags`
- `manual_review_flags`
- `formula_version`

Required `valuation_legs` child fields:
- `name`
- `weight`
- `status`
- `inputs`
- `conservative_value`
- `base_value`
- `bull_value`
- `blended_value`
- `notes`

## Current Reusable Inputs In This Workspace
Reusable now:
- `top100_universe.csv`
- `top100_valuation_snapshot.csv`
- `fundamentals/<ticker>_annual.csv`
- `fundamentals/<ticker>_quarterly.csv`
- `fundamentals/<ticker>_profile.json`
- `prices/<ticker>.csv`
- `TAIEX.csv`

Existing loader and normalization code worth reusing:
- [tw_valuation_models/dataset.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/dataset.py)
- [tw_valuation_models/shared_data.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/shared_data.py)
- [tw_valuation_models/config.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/config.py)

## Known Gaps And V1 Policy
Blocking gaps:
1. no confirmed parameter table yet for:
   - fair PE
   - required FCF yield
   - persistence factor
   - cost of equity
   - long-term growth
   - macro/Taiwan/reality modifier buckets
2. no clean dividend-per-share history table
3. no clean net cash / net debt field for full EV/EBITDA

Non-blocking gaps if disclosed:
1. monthly revenue history is currently empty in this environment
2. no historical PE/PB/dividend-yield/FCF-yield regime series yet
3. no direct ROIC field
4. no direct gross-margin field

V1 implementation rule:
- missing inputs must produce visible assumptions or `not_ready` flags
- they must not be silently backfilled with invented numbers

## Sample Application To The First Four Validation Names

### 2330
- company: `台灣積體電路製造股份有限公司`
- proposed classification: `high_quality_compounder`
- current market inputs:
  - price: `2270.0`
  - trailing PE: `30.8`
  - price/book: `9.99`
  - dividend yield: `1.08%`
- current reusable normalized candidates:
  - latest EPS: `65.46`
  - 3-year average EPS: `47.66`
  - 4-year average EPS: `45.32`
  - latest BVPS: `206.50`
  - 3-year average ROE: `27.94%`
  - latest FCF/share: `38.27`
  - 3-year average FCF/share: `27.51`
  - TTM EPS from quarterly series: `65.46`
- V1 interpretation:
  - this is the cleanest compounder test case
  - the latest year is materially above the 3-year average, so the normalizer should avoid simply using peak latest EPS
  - DDM can only run with an explicit dividend assumption until dividend history is added

### 2881
- company: `富邦金融控股股份有限公司`
- proposed classification: `financial`
- current market inputs:
  - price: `94.6`
  - trailing PE: `11.3`
  - price/book: `1.37`
  - dividend yield: `4.38%`
- current reusable normalized candidates:
  - latest EPS: `8.85`
  - 3-year average EPS: `8.11`
  - 4-year average EPS: `6.92`
  - latest BVPS: `71.90`
  - 3-year average ROE: `12.13%`
  - TTM EPS from quarterly series: `8.69`
- V1 interpretation:
  - this case should validate the ROE-adjusted PB route
  - FCF is not a reliable primary anchor for this financial name and should not drive valuation
  - DDM remains assumption-driven until dividend history is added

### 2603
- company: `長榮海運股份有限公司`
- proposed classification: `cyclical`
- current market inputs:
  - price: `211.5`
  - trailing PE: `6.68`
  - price/book: `0.81`
  - dividend yield: `15.48%`
- current reusable normalized candidates:
  - latest EPS: `31.68`
  - 3-year average EPS: `37.59`
  - 4-year average EPS: `67.67`
  - latest BVPS: `260.42`
  - 3-year average ROE: `14.74%`
  - latest FCF/share: `36.58`
  - 3-year average FCF/share: `34.22`
  - TTM EPS from quarterly series: `31.68`
- V1 interpretation:
  - this is the key proof that the engine will not use a peak cyclical year as normalized value
  - the 2022 outlier makes the 4-year EPS average too aggressive for V1
  - the 3-year average or TTM is the safer normalization anchor
  - EV/EBITDA should stay flagged as incomplete until net-debt support exists

### 2412
- company: `中華電信股份有限公司`
- proposed classification: `defensive_dividend`
- current market inputs:
  - price: `137.5`
  - trailing PE: `27.39`
  - price/book: `2.69`
  - dividend yield: `3.64%`
- current reusable normalized candidates:
  - latest EPS: `4.99`
  - 3-year average EPS: `4.85`
  - 4-year average EPS: `4.81`
  - latest BVPS: `49.52`
  - 3-year average ROE: `9.84%`
  - latest FCF/share: `6.39`
  - 3-year average FCF/share: `6.16`
  - TTM EPS from quarterly series: `4.99`
- V1 interpretation:
  - this is the cleanest defensive/dividend case
  - normalization can stay close to the recent multi-year average because earnings are stable
  - dividend-yield-band and DDM both need a dividend assumption layer until history is sourced

## Recommended Build Order
1. create Buffett 3.0 config tables for all required parameter ranges
2. implement classifier output schema
3. implement shared normalization bundle
4. implement company-type valuation legs
5. wire scenario blending
6. wire modifiers
7. emit auditable payload
8. validate against `2330`, `2881`, `2603`, and `2412`
9. only then start any Buffett 3.0 UI work

## Immediate Decision Still Needed
Before coding the engine, the remaining user-confirmation items are:
1. parameter tables for each valuation leg and modifier
2. whether V1 may temporarily mark missing legs as `not_ready`
3. whether DDM/dividend-yield methods may use explicit assumption inputs until dividend history is added
