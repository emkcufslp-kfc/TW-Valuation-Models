"""TWSE OpenAPI loader for typed IMFS records."""

from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Iterable
from urllib.request import Request, urlopen

from imfs.data.models import Currency, FinancialSnapshot, Market, PriceRecord, SecurityProfile, SourceMeta


BASE_URL = "https://openapi.twse.com.tw/v1"

COMPANY_BASICS = "/opendata/t187ap03_L"
STOCK_DAY_ALL = "/exchangeReport/STOCK_DAY_ALL"
BWIBBU_ALL = "/exchangeReport/BWIBBU_ALL"
MONTHLY_REVENUE = "/opendata/t187ap05_L"
INCOME_STATEMENT = "/opendata/t187ap06_L_ci"
BALANCE_SHEET = "/opendata/t187ap07_L_ci"

FetchRows = Callable[[str], list[dict[str, Any]]]


@dataclass(frozen=True)
class TwseBundle:
    securities: list[SecurityProfile]
    prices: list[PriceRecord]
    financials: list[FinancialSnapshot]


class TwseLoader:
    def __init__(self, fetch_rows: FetchRows | None = None, retrieved_at: datetime | None = None) -> None:
        self.fetch_rows = fetch_rows or request_twse_rows
        self.retrieved_at = retrieved_at or datetime.now()

    def load(self, codes: Iterable[str]) -> TwseBundle:
        normalized_codes = {_normalize_code(code) for code in codes}
        basics = _index_latest(self.fetch_rows(COMPANY_BASICS))
        day = _index_latest(self.fetch_rows(STOCK_DAY_ALL))
        bwi = _index_latest(self.fetch_rows(BWIBBU_ALL))
        revenue = _index_latest(self.fetch_rows(MONTHLY_REVENUE))
        income = _index_latest(self.fetch_rows(INCOME_STATEMENT))
        balance = _index_latest(self.fetch_rows(BALANCE_SHEET))

        securities: list[SecurityProfile] = []
        prices: list[PriceRecord] = []
        financials: list[FinancialSnapshot] = []

        for code in sorted(normalized_codes):
            security = self._security_profile(code, basics.get(code, {}))
            if security is not None:
                securities.append(security)
            price = self._price_record(code, day.get(code, {}))
            if price is not None:
                prices.append(price)
            snapshot = self._financial_snapshot(
                code,
                basics.get(code, {}),
                bwi.get(code, {}),
                revenue.get(code, {}),
                income.get(code, {}),
                balance.get(code, {}),
                day.get(code, {}),
            )
            if snapshot is not None:
                financials.append(snapshot)

        return TwseBundle(securities=securities, prices=prices, financials=financials)

    def _security_profile(self, code: str, basics: dict[str, Any]) -> SecurityProfile | None:
        if not basics:
            return None
        name = _clean_text(_pick(basics, "公司簡稱", "公司名稱", "Name"))
        industry = _clean_text(_pick(basics, "產業別", "Industry"))
        return SecurityProfile(
            ticker=f"{code}.TW",
            name=name or code,
            market=Market.TW,
            currency=Currency.TWD,
            sector=_tw_sector(industry),
            industry=industry,
            is_financial="金融" in industry or "銀行" in industry,
            is_cyclical=any(term in industry for term in ("半導體", "鋼", "化學", "塑膠")),
            metadata={"source": "twse_openapi", "raw_code": code},
        )

    def _price_record(self, code: str, day: dict[str, Any]) -> PriceRecord | None:
        price = _clean_float(_pick(day, "ClosingPrice", "收盤價", "收盤價(元)"))
        trade_date = _parse_date(_pick(day, "Date", "日期"))
        if price is None or price <= 0 or trade_date is None:
            return None
        return PriceRecord(
            ticker=f"{code}.TW",
            market=Market.TW,
            currency=Currency.TWD,
            close=price,
            adjusted_close=price,
            trade_date=trade_date,
            source=self._source(trade_date, notes=STOCK_DAY_ALL),
        )

    def _financial_snapshot(
        self,
        code: str,
        basics: dict[str, Any],
        bwi: dict[str, Any],
        revenue: dict[str, Any],
        income: dict[str, Any],
        balance: dict[str, Any],
        day: dict[str, Any],
    ) -> FinancialSnapshot | None:
        if not any((basics, bwi, revenue, income, balance)):
            return None

        fiscal_period_end = _report_period_end(income) or _report_period_end(balance)
        if fiscal_period_end is None:
            fiscal_period_end = _parse_date(_pick(day, "Date", "日期")) or date.today()

        shares = _clean_float(_pick(basics, "已發行普通股數或TDR原股發行股數", "SharesOutstanding"))
        price = _clean_float(_pick(day, "ClosingPrice", "收盤價", "收盤價(元)"))
        pe = _clean_float(_pick(bwi, "PEratio", "本益比"))
        pb = _clean_float(_pick(bwi, "PBratio", "股價淨值比"))
        revenue_growth = _clean_float(_pick(revenue, "營業收入-去年同月增減(%)", "RevenueYoY"))
        revenue_total = _clean_float(_pick(income, "營業收入", "Revenue"))
        operating_income = _clean_float(_pick(income, "營業利益", "OperatingIncome"))
        net_income = _clean_float(_pick(income, "本期淨利（淨損）", "NetIncome"))
        eps = _clean_float(_pick_contains(income, "基本每股盈餘")) or (
            price / pe if price and pe and pe > 0 else None
        )
        total_assets = _clean_float(_pick(balance, "資產總額", "TotalAssets"))
        total_liabilities = _clean_float(_pick(balance, "負債總額", "TotalLiabilities"))
        total_equity = _clean_float(_pick(balance, "權益總額", "Equity"))
        current_assets = _clean_float(_pick(balance, "流動資產", "CurrentAssets"))
        current_liabilities = _clean_float(_pick(balance, "流動負債", "CurrentLiabilities"))
        book_value_per_share = _clean_float(_pick(balance, "每股參考淨值", "BookValuePerShare"))

        return FinancialSnapshot(
            ticker=f"{code}.TW",
            market=Market.TW,
            currency=Currency.TWD,
            fiscal_period_end=fiscal_period_end,
            source=self._source(fiscal_period_end, notes=";".join([INCOME_STATEMENT, BALANCE_SHEET, BWIBBU_ALL])),
            revenue=revenue_total,
            revenue_growth=revenue_growth / 100.0 if revenue_growth is not None else None,
            operating_income=operating_income,
            net_income=net_income,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
            current_assets=current_assets,
            current_liabilities=current_liabilities,
            shares_outstanding=shares,
            eps=eps,
            normalized_eps=eps,
            book_value_per_share=book_value_per_share,
            price_to_book=pb,
            market_cap=price * shares if price and shares else None,
        )

    def _source(self, as_of: date, notes: str) -> SourceMeta:
        return SourceMeta(
            source="twse_openapi",
            as_of=as_of,
            retrieved_at=self.retrieved_at,
            url=BASE_URL,
            notes=notes,
        )


def request_twse_rows(path: str) -> list[dict[str, Any]]:
    req = Request(
        BASE_URL + path,
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "If-Modified-Since": "Mon, 26 Jul 1997 05:00:00 GMT",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return _decode_rows(resp.read())
    except Exception:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with urlopen(req, timeout=30, context=context) as resp:
            return _decode_rows(resp.read())


def _decode_rows(raw: bytes) -> list[dict[str, Any]]:
    data = json.loads(raw.decode("utf-8-sig"))
    return data if isinstance(data, list) else []


def _index_latest(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = _row_code(row)
        if not code:
            continue
        if code not in latest or _sort_key(row) > _sort_key(latest[code]):
            latest[code] = row
    return latest


def _row_code(row: dict[str, Any]) -> str:
    return _normalize_code(_pick(row, "公司代號", "Code", "證券代號", "股票代號", "代號"))


def _normalize_code(code: Any) -> str:
    text = _clean_text(code)
    return text.replace(".TW", "")


def _sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    year = _clean_int(_pick(row, "年度", "Year")) or 0
    quarter = _clean_int(_pick(row, "季別", "Quarter")) or 0
    raw_date = _clean_text(_pick(row, "Date", "日期", "出表日期"))
    return year, quarter, raw_date


def _report_period_end(row: dict[str, Any]) -> date | None:
    year = _clean_int(_pick(row, "年度", "Year"))
    quarter = _clean_int(_pick(row, "季別", "Quarter"))
    if year is None or quarter is None:
        return None
    if year < 1911:
        year += 1911
    quarter_ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    month_day = quarter_ends.get(quarter)
    if month_day is None:
        return None
    return date(year, month_day[0], month_day[1])


def _parse_date(value: Any) -> date | None:
    text = _clean_text(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    if len(digits) == 8:
        try:
            return datetime.strptime(digits, "%Y%m%d").date()
        except ValueError:
            return None
    if len(digits) == 7:
        try:
            return date(int(digits[:3]) + 1911, int(digits[3:5]), int(digits[5:7]))
        except ValueError:
            return None
    return None


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in {"", "--", "---", "N/A", "NA", "null", "None"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _clean_int(value: Any) -> int | None:
    number = _clean_float(value)
    return int(number) if number is not None else None


def _pick(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and _clean_text(row[key]) != "":
            return row[key]
    return None


def _pick_contains(row: dict[str, Any], *fragments: str) -> Any:
    for key, value in row.items():
        if all(fragment in key for fragment in fragments) and _clean_text(value):
            return value
    return None


def _tw_sector(industry: str) -> str:
    if "金融" in industry or "銀行" in industry:
        return "Financials"
    if "半導體" in industry or "電子" in industry:
        return "Technology"
    if "電信" in industry:
        return "Communication Services"
    if "塑膠" in industry or "鋼" in industry or "化學" in industry:
        return "Cyclicals"
    return industry or "Unknown"

