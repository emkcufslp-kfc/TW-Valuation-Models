# TODO

## Data Quality Follow-Up
- Confirm financial-holding dividend interpretation for `2881` and similar names against company IR and AGM materials.
- Investigate whether a second official statement source is needed for `2330`, `2881`, and other names missing from the current TWSE statement coverage.

## Model Refinement
- Add a cleaner cyclical EV or EBITDA path once reliable debt and EBITDA history is available.
- Evaluate whether Buffett 3.0 should use a stricter or more flexible weighting scheme for defensive dividend names like `2412`.
- Review compounder normalization assumptions for names like `2330` after a few more validation cases.

## Verification
- Keep Buffett 3.0 app-rendering regression coverage for string and comma-separated label fields.
- Keep `python -m unittest tests.test_shared_data tests.test_dataset tests.test_buffett_three` in the regression set.
- Keep `python -m compileall tw_valuation_models tests app.py` in the regression set.

## Optional Expansion
