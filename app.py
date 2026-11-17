"""India Company Financials Explorer — The Mountain Path Academy.
NSE/BSE company data from Yahoo Finance via the open-source yfinance library (no API key).
For research and education only; check figures against the company's annual report.
"""
import datetime as dt
import hashlib
import io
import os
import numpy as np
import requests
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------- palette (Mountain Path) ----------------
GOLD, BLUE, MID, CARD = "#FFD700", "#003366", "#004d80", "#112240"
TXT, MUTED, GRN, RED, LB = "#e6f1ff", "#8892b0", "#28a745", "#dc3545", "#ADD8E6"
BG = "linear-gradient(135deg,#1a2332,#243447,#2a3f5f)"
BASE = "https://financialmodelingprep.com/stable"
SITE = "https://themountainpathacademy.com"

st.set_page_config(page_title="India Company Financials Explorer | Mountain Path", page_icon="📊", layout="wide")
st.html(f"""<style>
.stApp{{background:{BG};}}
header[data-testid="stHeader"]{{background:transparent;}}
section[data-testid="stSidebar"]{{background:{CARD};border-right:1px solid {MID};}}
/* inputs: dark field, light text, visible border */
div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"]{{
  background:#0b1a33!important;border:1px solid {MID}!important;}}
div[data-baseweb="input"] *, div[data-baseweb="base-input"], div[data-baseweb="select"] > div *,
div[data-testid="stTextInputRootElement"], div[data-testid="stNumberInputContainer"]{{background:#0b1a33!important;}}
input, textarea{{background:#0b1a33!important;color:{TXT}!important;-webkit-text-fill-color:{TXT}!important;caret-color:{GOLD};}}
div[data-baseweb="select"] svg{{fill:{LB}!important;}}
input::placeholder{{color:{MUTED}!important;-webkit-text-fill-color:{MUTED}!important;opacity:1}}
div[data-baseweb="select"] *{{color:{TXT}!important;-webkit-text-fill-color:{TXT}!important;}}
ul[role="listbox"]{{background:{CARD}!important;}}
ul[role="listbox"] li{{color:{TXT}!important;-webkit-text-fill-color:{TXT}!important;}}
ul[role="listbox"] li:hover, ul[role="listbox"] li[aria-selected="true"]{{background:{MID}!important;}}
button[data-testid="stNumberInputStepDown"], button[data-testid="stNumberInputStepUp"]{{background:{MID}!important;color:{TXT}!important;}}
/* labels and captions */
label, label p, div[data-testid="stWidgetLabel"] p{{color:{LB}!important;-webkit-text-fill-color:{LB}!important;font-weight:600}}
div[data-testid="stCaptionContainer"] p{{color:{MUTED}!important;-webkit-text-fill-color:{MUTED}!important}}
h1,h2,h3,h4{{color:{TXT}!important}}
/* tabs */
[role="tab"], [role="tab"] *{{color:{LB}!important;-webkit-text-fill-color:{LB}!important;font-weight:600}}
[role="tab"][aria-selected="true"], [role="tab"][aria-selected="true"] *{{color:{GOLD}!important;-webkit-text-fill-color:{GOLD}!important}}
div[data-baseweb="tab-highlight"]{{background:{GOLD}!important}}
/* buttons: primary = gold with navy text; secondary = navy with gold border and white text */
button[data-testid="stBaseButton-primary"], button[kind="primary"]{{background:{GOLD}!important;border:1px solid {GOLD}!important;}}
button[data-testid="stBaseButton-primary"] *, button[kind="primary"] *{{color:{BLUE}!important;-webkit-text-fill-color:{BLUE}!important;font-weight:800}}
button[data-testid="stBaseButton-secondary"], button[kind="secondary"]{{background:{MID}!important;border:1px solid {GOLD}!important;}}
button[data-testid="stBaseButton-secondary"] *, button[kind="secondary"] *{{color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;font-weight:700}}
button[data-testid="stBaseButton-secondary"]:hover, button[kind="secondary"]:hover{{background:{BLUE}!important;}}
/* alerts readable on dark */
div[data-testid="stAlert"]{{background:{CARD}!important;border:1px solid {GOLD}!important;}}
div[data-testid="stAlert"] p, div[data-testid="stAlert"] div{{color:{TXT}!important;-webkit-text-fill-color:{TXT}!important;}}
/* expander */
details summary p{{color:{GOLD}!important;-webkit-text-fill-color:{GOLD}!important;font-weight:700}}
div[data-testid="stExpander"] details{{background:{CARD};border:1px solid {MID};}}
div[data-testid="stExpander"] li, div[data-testid="stExpander"] p{{color:{TXT}!important}}
/* radio / slider text */
div[role="radiogroup"] p{{color:{TXT}!important;-webkit-text-fill-color:{TXT}!important}}
div[data-testid="stSliderTickBarMin"], div[data-testid="stSliderTickBarMax"], div[data-testid="stThumbValue"]{{color:{GOLD}!important}}
div[data-testid="stSlider"] div[role="slider"]{{background:{GOLD}!important;border-color:{GOLD}!important}}
</style>""")


def t(text, color=TXT, size=15, weight=400, extra=""):
    """Inline-styled text node (colour + -webkit-text-fill-color) per house style."""
    return (f'<span style="color:{color};-webkit-text-fill-color:{color};font-size:{size}px;'
            f'font-weight:{weight};{extra}">{text}</span>')


def card(inner, border=MID, pad="14px 18px"):
    return (f'<div style="background:{CARD};border:1px solid {border};border-radius:12px;padding:{pad};'
            f'user-select:none;-webkit-user-select:none;height:100%">{inner}</div>')


def indian(n, dec=0):
    """Indian digit grouping: 12,34,567."""
    neg = n < 0; n = abs(n)
    whole = f"{n:.{dec}f}".split(".")
    w, frac = whole[0], ("." + whole[1]) if dec else ""
    if len(w) > 3:
        head, tail = w[:-3], w[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        w = ",".join(parts) + "," + tail
    return ("-" if neg else "") + w + frac


def money(v, cur="₹"):
    """Rupee amounts in crore (1 crore = 10 million)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    return f"₹{indian(v / 1e7, 0)} cr"


def pct(v):
    return "–" if v is None or pd.isna(v) else f"{v*100:.1f}%"


# ---------------- data layer: Yahoo Finance via yfinance ----------------
class FMPError(Exception):  # kept name so the rest of the app is shared with the US version
    pass


IS_MAP = {"revenue": ["Total Revenue", "Operating Revenue"], "costOfRevenue": ["Cost Of Revenue"],
          "grossProfit": ["Gross Profit"], "operatingExpenses": ["Operating Expense"],
          "operatingIncome": ["Operating Income", "EBIT"], "ebitda": ["EBITDA", "Normalized EBITDA"],
          "interestExpense": ["Interest Expense", "Interest Expense Non Operating"], "incomeBeforeTax": ["Pretax Income"],
          "incomeTaxExpense": ["Tax Provision"], "netIncome": ["Net Income", "Net Income Common Stockholders"],
          "epsDiluted": ["Diluted EPS", "Basic EPS"], "weightedAverageShsOutDil": ["Diluted Average Shares", "Basic Average Shares"]}
BS_MAP = {"cashAndCashEquivalents": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"],
          "totalCurrentAssets": ["Current Assets"], "propertyPlantEquipmentNet": ["Net PPE"], "totalAssets": ["Total Assets"],
          "totalCurrentLiabilities": ["Current Liabilities"], "totalDebt": ["Total Debt"],
          "totalLiabilities": ["Total Liabilities Net Minority Interest"],
          "totalStockholdersEquity": ["Stockholders Equity", "Common Stock Equity"]}
CF_MAP = {"netIncome": ["Net Income From Continuing Operations", "Net Income"],
          "depreciationAndAmortization": ["Depreciation And Amortization", "Depreciation Amortization Depletion"],
          "operatingCashFlow": ["Operating Cash Flow"], "capitalExpenditure": ["Capital Expenditure"],
          "freeCashFlow": ["Free Cash Flow"], "commonDividendsPaid": ["Cash Dividends Paid", "Common Stock Dividend Paid"],
          "commonStockRepurchased": ["Repurchase Of Capital Stock", "Common Stock Payments"],
          "netChangeInCash": ["Changes In Cash"]}


def _rows(df, mapping, quarterly):
    """yfinance statement (rows = items, columns = dates) → list of dicts, newest first, FMP-style keys."""
    out = []
    if df is None or df.empty:
        return out
    for col_ in df.columns:
        d = {"date": str(pd.Timestamp(col_).date()), "fiscalYear": str(pd.Timestamp(col_).year),
             "period": ("Q" + str((pd.Timestamp(col_).month - 1) // 3 + 1)) if quarterly else "FY"}
        for k, names in mapping.items():
            for n in names:
                if n in df.index and pd.notna(df.loc[n, col_]):
                    d[k] = float(df.loc[n, col_]); break
        out.append(d)
    return sorted(out, key=lambda r: r["date"], reverse=True)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def fmp(endpoint, symbol, key=None, period="annual", limit=5, extra=None):
    """Same call shape as the US app, answered from Yahoo Finance."""
    try:
        tk = yf.Ticker(symbol)
        q = period == "quarter"
        if endpoint == "income-statement":
            return _rows(tk.quarterly_income_stmt if q else tk.income_stmt, IS_MAP, q)[:limit]
        if endpoint == "balance-sheet-statement":
            return _rows(tk.quarterly_balance_sheet if q else tk.balance_sheet, BS_MAP, q)[:limit]
        if endpoint == "cash-flow-statement":
            return _rows(tk.quarterly_cashflow if q else tk.cashflow, CF_MAP, q)[:limit]
        info = tk.info or {}
        if endpoint == "profile":
            if not info.get("longName") and not info.get("shortName"):
                return []
            lo, hi = info.get("fiftyTwoWeekLow"), info.get("fiftyTwoWeekHigh")
            return [{"symbol": symbol, "companyName": info.get("longName") or info.get("shortName"),
                     "currency": info.get("currency", "INR"), "exchange": {"NSI": "NSE", "BSE": "BSE"}.get(info.get("exchange"), info.get("exchange", "")),
                     "sector": info.get("sector", ""), "industry": info.get("industry", ""), "beta": info.get("beta"),
                     "marketCap": info.get("marketCap"), "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                     "description": info.get("longBusinessSummary", "–"), "fullTimeEmployees": info.get("fullTimeEmployees"),
                     "country": info.get("country"), "website": info.get("website"),
                     "range": f"{lo:,.2f} – {hi:,.2f}" if lo and hi else None, "ceo": None, "ipoDate": None}]
        if endpoint == "quote":
            return [{"price": info.get("currentPrice") or info.get("regularMarketPrice"),
                     "changePercentage": info.get("regularMarketChangePercent"), "marketCap": info.get("marketCap")}]
        if endpoint == "ratios-ttm":
            de = info.get("debtToEquity")
            return [{"grossProfitMarginTTM": info.get("grossMargins"), "operatingProfitMarginTTM": info.get("operatingMargins"),
                     "netProfitMarginTTM": info.get("profitMargins"), "returnOnEquityTTM": info.get("returnOnEquity"),
                     "currentRatioTTM": info.get("currentRatio"), "debtToEquityRatioTTM": de / 100 if de is not None else None,
                     "priceToEarningsRatioTTM": info.get("trailingPE"), "priceToBookRatioTTM": info.get("priceToBook"),
                     "enterpriseValueMultipleTTM": info.get("enterpriseToEbitda"),
                     "dividendYieldTTM": info.get("trailingAnnualDividendYield"), "name": info.get("longName") or info.get("shortName")}]
        return []
    except Exception as e:
        msg = str(e)
        if "Too Many Requests" in msg or "429" in msg or "Rate" in msg:
            raise FMPError("Yahoo Finance is limiting requests right now. Wait a minute and click Fetch data again.")
        raise FMPError(f"Could not load {endpoint} for {symbol}: {msg[:120]}")


def calls_today(key):
    return 0


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def search_company(query, key=None):
    """Company name search on Yahoo Finance; NSE first, then BSE."""
    try:
        quotes = yf.Search(query, max_results=15).quotes
    except Exception:
        return []
    out = []
    for d in quotes:
        sym_ = d.get("symbol", "")
        if (sym_.endswith(".NS") or sym_.endswith(".BO")) and "-" not in sym_:
            out.append({"symbol": sym_, "name": d.get("longname") or d.get("shortname", ""),
                        "exchange": "NSE" if sym_.endswith(".NS") else "BSE"})
    return sorted(out, key=lambda x: x["exchange"] != "NSE")[:20]


def get_key():
    return "yahoo"


def safe(endpoint, symbol, key=None, **kw):
    try:
        return fmp(endpoint, symbol, key, **kw)
    except FMPError as e:
        return {"_error": str(e)}


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def latest_10y(key=None):
    """India 10-year G-Sec yield from CCIL's tenor-wise indicative yields (official, published daily)."""
    try:
        import re
        h = requests.get("https://www.ccilindia.com/tenorwise-indicative-yields", timeout=15,
                         headers={"User-Agent": "Mozilla/5.0"}).text
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", h, re.S)]
        for i_ in range(len(cells) - 3):
            if cells[i_ + 1].replace(" ", "") in ("9Y-10Y", "10Y"):
                return float(cells[i_ + 3]) / 100, cells[i_][:10]
    except Exception:
        pass
    return None, None


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def price_history(symbol, key=None, years=5):
    try:
        h = yf.Ticker(symbol).history(period=f"{years}y", interval="1d", auto_adjust=True)
    except Exception:
        return None
    if h is None or h.empty:
        return None
    sr = h["Close"].astype(float)
    sr.index = pd.to_datetime(sr.index).tz_localize(None)
    return sr


def pick(d, *names):
    for n in names:
        if isinstance(d, dict) and d.get(n) is not None:
            return d.get(n)
    return None


# ---------------- sidebar ----------------
with st.sidebar:
    st.html(card(t("THE MOUNTAIN PATH ACADEMY", GOLD, 12, 800, "letter-spacing:1.5px") + "<br>" +
                 t("India Company Financials Explorer", TXT, 18, 700)))
    key = get_key()
    st.caption("Data: Yahoo Finance (yfinance). No API key needed.")
    if "ticker" not in st.session_state:
        st.session_state.ticker = "TCS.NS"
    q = st.text_input("Search company name", placeholder="e.g. Tata Steel, Infosys, HDFC Bank")
    if q.strip() and key:
        try:
            hits = search_company(q.strip(), key)
        except FMPError as e:
            hits = []
            st.error(str(e))
        if hits:
            labels = [f"{h['symbol']} — {h['name']} ({h['exchange']})" for h in hits]
            choice = st.selectbox(f"{len(hits)} NSE/BSE matches", labels, index=None, placeholder="Choose a company")
            if choice:
                st.session_state.ticker = choice.split(" — ")[0]
        else:
            st.caption("No NSE/BSE match. Try a shorter name.")
    elif q.strip():
        st.caption("Enter your API key first to search.")
    symbol = st.text_input("NSE ticker (.NS) or BSE (.BO)", key="ticker",
                           help="Type TCS or TCS.NS; .NS is added if you leave it out.").strip().upper()
    if symbol and "." not in symbol and not symbol.startswith("^"):
        symbol += ".NS"
    period = st.radio("Statements", ["annual", "quarter"], horizontal=True)
    limit = st.slider("Periods", 2, 5, 5)
    st.divider()
    st.subheader("Cost of capital inputs")
    y10, y10_date = latest_10y(key) if key else (None, None)
    rf = st.number_input("Risk-free rate (10-yr G-Sec)", 0.0, 0.15, round(y10, 4) if y10 else 0.0731, 0.001,
                         format="%.4f", help="Filled from CCIL's latest 10-year G-Sec indicative yield when available.")
    if y10:
        st.caption(f"10-yr G-Sec {y10:.2%} on {y10_date} (CCIL indicative).")
    mrp = st.number_input("Market risk premium (India)", 0.0, 0.15, 0.07, 0.001, format="%.3f")
    tax = st.number_input("Tax rate (new regime 25.17%)", 0.0, 0.5, 0.2517, 0.0001, format="%.4f")
    go_btn = st.button("Fetch data", type="primary", width="stretch")
    usage_box = st.empty()
    st.caption("Yahoo Finance data via yfinance, kept for 6 hours. If data does not load, wait a minute and retry.")

st.html(card(t("FREE LEARNING TOOL · MBA · CFA · FRM", BLUE, 12, 800,
               f"background:{GOLD};-webkit-text-fill-color:{BLUE};padding:4px 10px;border-radius:5px;letter-spacing:1px") +
             "<br><br>" + t("India Company Financials Explorer", TXT, 34, 800) + "<br>" +
             t("Statements, ratios, trends, beta, WACC and DCF for NSE/BSE-listed companies, "
               "in ₹ crore.", LB, 16), pad="22px 26px"))

if "loaded" not in st.session_state:
    st.session_state.loaded = None
if go_btn:
    st.session_state.loaded = (symbol, period, limit)

if not st.session_state.loaded:
    st.html(card(t("How to start", GOLD, 16, 700) + "<br>" +
                 t("1. Search a company name in the sidebar, or type an NSE ticker such as TCS, INFY or HDFCBANK.<br>"
                   "2. Click <b>Fetch data</b>.<br>"
                   "3. Figures are in ₹ crore. Banks and insurers do not report some lines (gross margin, current ratio).", TXT, 15)))
elif not key:
    st.error("Enter a ticker first.")
else:
    sym, per, lim = st.session_state.loaded
    try:
        with st.spinner(f"Fetching {sym} from Yahoo Finance…"):
            prof = fmp("profile", sym, key)
            quote = fmp("quote", sym, key)
            inc = fmp("income-statement", sym, key, per, lim)
            bal = fmp("balance-sheet-statement", sym, key, per, lim)
            cfs = fmp("cash-flow-statement", sym, key, per, lim)
    except FMPError as e:
        st.error(str(e))
        st.stop()
    if not prof or not inc:
        st.warning(f"No data returned for '{sym}'. Check the ticker (NSE: .NS, BSE: .BO) or wait a minute and retry.")
        st.stop()

    p = prof[0] if isinstance(prof, list) else prof
    q = (quote[0] if isinstance(quote, list) and quote else {}) or {}
    cur = "₹"

    def frame(rows):
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        lab = df["period"].astype(str) + " " + df["fiscalYear"].astype(str) if per == "quarter" and "fiscalYear" in df else df["date"].astype(str).str[:4]
        if per == "quarter" and "fiscalYear" not in df:
            lab = df["date"].astype(str)
        df.index = lab
        return df.iloc[::-1]  # oldest → newest

    I, B, C = frame(inc), frame(bal), frame(cfs)

    def frame_annual(rows):
        df = pd.DataFrame(rows)
        if not df.empty:
            df.index = df["date"].astype(str).str[:4]
            df = df.iloc[::-1]
        return df

    def col(df, name):
        return pd.to_numeric(df[name], errors="coerce") if name in df else pd.Series(index=df.index, dtype=float)

    # ---------------- ratios (simple whiteboard formulas) ----------------
    R = pd.DataFrame(index=I.index)
    rev, gp, op, ni = col(I, "revenue"), col(I, "grossProfit"), col(I, "operatingIncome"), col(I, "netIncome")
    ebitda, intexp = col(I, "ebitda"), col(I, "interestExpense")
    ta, te = col(B, "totalAssets").reindex(I.index), col(B, "totalStockholdersEquity").reindex(I.index)
    ca, cl = col(B, "totalCurrentAssets").reindex(I.index), col(B, "totalCurrentLiabilities").reindex(I.index)
    debt, cash = col(B, "totalDebt").reindex(I.index), col(B, "cashAndCashEquivalents").reindex(I.index)
    ocf, capex = col(C, "operatingCashFlow").reindex(I.index), col(C, "capitalExpenditure").reindex(I.index)
    fcf = col(C, "freeCashFlow").reindex(I.index)
    fcf = fcf.where(fcf.notna(), ocf + capex)
    R["Revenue growth"] = rev.pct_change()
    R["Gross margin"] = gp / rev
    R["Operating margin"] = op / rev
    R["Net margin"] = ni / rev
    R["ROE (NI ÷ equity)"] = ni / te
    R["ROA (NI ÷ assets)"] = ni / ta
    R["Asset turnover (×)"] = rev / ta
    R["Current ratio (×)"] = ca / cl
    R["Debt ÷ equity (×)"] = debt / te
    R["Interest cover (×)"] = op / intexp.replace(0, pd.NA)
    R["FCF margin"] = fcf / rev
    R["Cash conversion (OCF ÷ NI) (×)"] = ocf / ni

    # ---------------- header cards ----------------
    price = q.get("price") or p.get("price")
    chg = q.get("changePercentage", p.get("changePercentage"))
    mcap = q.get("marketCap") or p.get("marketCap")
    if not price:  # Yahoo sometimes withholds the quote summary: use the last close
        _px = price_history(sym, key)
        price = float(_px.iloc[-1]) if _px is not None and len(_px) else None
    if not mcap and price:  # market cap = price × diluted shares
        _sh = col(I, "weightedAverageShsOutDil").dropna()
        mcap = price * float(_sh.iloc[-1]) if len(_sh) else None
    beta = p.get("beta")
    st.html(card(t(p.get("companyName", sym), TXT, 26, 800) + "&nbsp;&nbsp;" +
                 t(f"{sym} · {p.get('exchange', p.get('exchangeFullName', ''))} · {p.get('sector', '')} · {p.get('industry', '')}", LB, 14),
                 pad="16px 22px"))
    kp = [("Price", f"₹{price:,.2f}" if price else "–",
           (t(f"{chg:+.2f}% today", GRN if (chg or 0) >= 0 else RED, 13, 700) if chg is not None else "")),
          ("Market cap", money(mcap, cur), ""), ("Beta", f"{beta:.2f}" if beta else "–", t("vs market", MUTED, 12)),
          ("Latest revenue", money(rev.iloc[-1], cur), t(I.index[-1], MUTED, 12)),
          ("Latest net income", money(ni.iloc[-1], cur), t(pct(R['Net margin'].iloc[-1]) + " margin", MUTED, 12))]
    cols = st.columns(len(kp))
    for c_, (h, v, s) in zip(cols, kp):
        c_.html(card(t(h.upper(), GOLD, 11, 800, "letter-spacing:1px") + "<br>" + t(v, TXT, 22, 800) + "<br>" + s))

    tabs = st.tabs(["📈 Trends", "🧮 Ratios", "📑 Statements", "📉 Beta & returns", "👥 Peers", "🏦 Cost of capital",
                    "💵 DCF", "ℹ️ Company", "⬇️ Download"])

    def fig_base(title):
        f = go.Figure()
        f.update_layout(title=dict(text=title, font=dict(color=TXT)), paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(17,34,64,.6)", font=dict(color=TXT), height=380,
                        legend=dict(orientation="h", y=-0.2, font=dict(color=TXT)), margin=dict(l=20, r=20, t=50, b=20))
        f.update_xaxes(gridcolor="rgba(255,255,255,.08)", type="category")
        f.update_yaxes(gridcolor="rgba(255,255,255,.08)")
        return f

    with tabs[0]:
        a, b = st.columns(2)
        f = fig_base(f"Revenue and net income ({cur.strip()})")
        f.add_bar(x=I.index, y=rev, name="Revenue", marker_color=MID)
        f.add_bar(x=I.index, y=ni, name="Net income", marker_color=GOLD)
        a.plotly_chart(f, width="stretch")
        f = fig_base("Margins")
        for nm, s, c_ in [("Gross", R["Gross margin"], LB), ("Operating", R["Operating margin"], GOLD), ("Net", R["Net margin"], GRN)]:
            f.add_scatter(x=I.index, y=s * 100, name=nm, mode="lines+markers", line=dict(color=c_, width=3))
        f.update_yaxes(ticksuffix="%")
        b.plotly_chart(f, width="stretch")
        a, b = st.columns(2)
        f = fig_base(f"Cash flow ({cur.strip()})")
        f.add_bar(x=I.index, y=ocf, name="Operating cash flow", marker_color=MID)
        f.add_bar(x=I.index, y=fcf, name="Free cash flow", marker_color=GRN)
        a.plotly_chart(f, width="stretch")
        f = fig_base("Returns and leverage")
        f.add_scatter(x=I.index, y=R["ROE (NI ÷ equity)"] * 100, name="ROE %", mode="lines+markers", line=dict(color=GOLD, width=3))
        f.add_scatter(x=I.index, y=R["ROA (NI ÷ assets)"] * 100, name="ROA %", mode="lines+markers", line=dict(color=LB, width=3))
        f.add_bar(x=I.index, y=R["Debt ÷ equity (×)"], name="Debt ÷ equity (×)", marker_color=RED, opacity=.5, yaxis="y2")
        f.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False))
        b.plotly_chart(f, width="stretch")

    with tabs[1]:
        st.caption("All ratios use one-line formulas on the reported figures (equity and assets at period end).")
        show = R.T.astype(object)
        for r_ in show.index:
            fmt = (lambda v: "–" if pd.isna(v) else f"{v:.2f}×") if "(×)" in r_ else pct
            show.loc[r_] = [fmt(v) for v in show.loc[r_]]
        st.dataframe(show, width="stretch")
        with st.expander("Formulas used"):
            st.markdown("""
- Gross / operating / net margin = gross profit / operating income / net income ÷ revenue
- ROE = net income ÷ shareholders' equity · ROA = net income ÷ total assets
- Asset turnover = revenue ÷ total assets · Current ratio = current assets ÷ current liabilities
- Debt ÷ equity = total debt ÷ equity · Interest cover = operating income ÷ interest expense
- FCF = operating cash flow − capital expenditure · FCF margin = FCF ÷ revenue · Cash conversion = OCF ÷ net income
""")

    with tabs[2]:
        rows_i = [("Revenue", "revenue"), ("Cost of revenue", "costOfRevenue"), ("Gross profit", "grossProfit"),
                  ("Operating expenses", "operatingExpenses"), ("Operating income", "operatingIncome"),
                  ("EBITDA", "ebitda"), ("Interest expense", "interestExpense"), ("Income before tax", "incomeBeforeTax"),
                  ("Income tax", "incomeTaxExpense"), ("Net income", "netIncome"), ("EPS (diluted)", "epsDiluted")]
        rows_b = [("Cash & equivalents", "cashAndCashEquivalents"), ("Total current assets", "totalCurrentAssets"),
                  ("Net PP&E", "propertyPlantEquipmentNet"), ("Total assets", "totalAssets"),
                  ("Total current liabilities", "totalCurrentLiabilities"), ("Total debt", "totalDebt"),
                  ("Total liabilities", "totalLiabilities"), ("Shareholders' equity", "totalStockholdersEquity")]
        rows_c = [("Net income", "netIncome"), ("Depreciation & amortisation", "depreciationAndAmortization"),
                  ("Operating cash flow", "operatingCashFlow"), ("Capital expenditure", "capitalExpenditure"),
                  ("Free cash flow", "freeCashFlow"), ("Dividends paid", "commonDividendsPaid"),
                  ("Share buybacks", "commonStockRepurchased"), ("Net change in cash", "netChangeInCash")]

        def tidy(df, rows):
            out = pd.DataFrame({lab: pd.to_numeric(df[k], errors="coerce") if k in df else pd.NA for lab, k in rows}).T
            out.columns = df.index
            return out

        ST = {"Income statement": tidy(I, rows_i), "Balance sheet": tidy(B, rows_b), "Cash flow": tidy(C, rows_c)}
        unit = "crore"
        div = 1e7
        for name, df in ST.items():
            st.subheader(f"{name} (₹ crore)")
            view = df.astype(object)
            for r_ in view.index:
                view.loc[r_] = [("–" if pd.isna(v) else (f"{v:,.2f}" if "EPS" in r_ else indian(v / div, 0))) for v in df.loc[r_]]
            st.dataframe(view, width="stretch")
        st.caption("Source: Yahoo Finance (consolidated, as reported). Check against the company's annual report before using in graded work.")

    # ---------------- beta from price history ----------------
    with tabs[3]:
        st.caption("Beta by regression: the slope of the stock's returns on the market's (Nifty 50), up to 5 years.")
        freq = st.radio("Return frequency", ["Monthly", "Weekly"], horizontal=True)
        yrs = st.slider("Years of history", 1, 5, 5)
        px_s, px_m = price_history(sym, key), price_history("^NSEI", key)
        reg_beta, RET = None, None
        if px_s is None or px_m is None:
            st.warning("Price history could not be loaded. Wait a minute and retry.")
        else:
            cut = pd.Timestamp(dt.date.today().replace(year=dt.date.today().year - yrs))
            rule = "ME" if freq == "Monthly" else "W-FRI"
            ps = px_s[px_s.index >= cut].resample(rule).last()
            pm = px_m[px_m.index >= cut].resample(rule).last()
            RET = pd.DataFrame({"Stock price": ps, "Nifty 50": pm}).dropna()
            RET["Stock return"] = RET["Stock price"].pct_change()
            RET["Market return"] = RET["Nifty 50"].pct_change()
            rr = RET.dropna()
            if len(rr) >= 12:
                cov = np.cov(rr["Stock return"], rr["Market return"], ddof=1)
                reg_beta = cov[0, 1] / cov[1, 1]
                alpha = rr["Stock return"].mean() - reg_beta * rr["Market return"].mean()
                r2 = np.corrcoef(rr["Stock return"], rr["Market return"])[0, 1] ** 2
                k_ = 12 if freq == "Monthly" else 52
                vol_s, vol_m = rr["Stock return"].std() * np.sqrt(k_), rr["Market return"].std() * np.sqrt(k_)
                cc = st.columns(5)
                for c_, (h, v_) in zip(cc, [("Regression beta", f"{reg_beta:.2f}"), ("Yahoo beta", f"{beta:.2f}" if beta else "–"),
                                           ("R²", f"{r2:.2f}"), ("Stock volatility (ann.)", pct(vol_s)),
                                           ("Market volatility (ann.)", pct(vol_m))]):
                    c_.html(card(t(h.upper(), GOLD, 11, 800, "letter-spacing:1px") + "<br>" + t(v_, TXT, 22, 800)))
                a, b = st.columns(2)
                f = fig_base(f"{freq} returns: {sym} vs Nifty 50")
                f.add_scatter(x=rr["Market return"] * 100, y=rr["Stock return"] * 100, mode="markers", name="Periods",
                              marker=dict(color=LB, size=8, opacity=.75))
                xs = np.linspace(rr["Market return"].min(), rr["Market return"].max(), 20)
                f.add_scatter(x=xs * 100, y=(alpha + reg_beta * xs) * 100, mode="lines", name=f"Fit: β = {reg_beta:.2f}",
                              line=dict(color=GOLD, width=3))
                f.update_xaxes(title="Market return %", type="linear"); f.update_yaxes(title="Stock return %")
                a.plotly_chart(f, width="stretch")
                f = fig_base("Growth of $100")
                f.update_xaxes(type="date")
                f.add_scatter(x=RET.index, y=RET["Stock price"] / RET["Stock price"].iloc[0] * 100, name=sym, line=dict(color=GOLD, width=3))
                f.add_scatter(x=RET.index, y=RET["Nifty 50"] / RET["Nifty 50"].iloc[0] * 100, name="Nifty 50", line=dict(color=LB, width=3))
                b.plotly_chart(f, width="stretch")
                st.caption(f"β = Cov(Rs, Rm) ÷ Var(Rm) on {len(rr)} {freq.lower()} returns. In Excel: =SLOPE(stock returns, market returns).")
            else:
                st.warning("Not enough price history to estimate beta.")

    # ---------------- peers ----------------
    with tabs[4]:
        st.caption("Compare the company with up to 4 peers on TTM (trailing twelve months) ratios.")
        PEERS = st.session_state.get("peers") if st.session_state.get("peers_for") == sym else None
        if st.session_state.get("peer_sug_for") != sym:
            st.session_state.peer_sug_for, st.session_state.peer_text = sym, ""
        a = st
        peer_text = a.text_input("Peer tickers (NSE, comma-separated)", key="peer_text",
                                 placeholder="e.g. INFY, WIPRO, HCLTECH, TECHM")
        if st.button("Load peer comparison", key="peer_btn"):
            tick = [sym] + [(x.strip().upper() if "." in x else x.strip().upper() + ".NS") for x in peer_text.split(",")
                            if x.strip()][:4]
            tick = list(dict.fromkeys(tick))
            if len(tick) == 1:
                st.warning("Add at least one peer ticker.")
            else:
                rows = []
                for tk in tick:
                    r_ = safe("ratios-ttm", tk, key)
                    r_ = r_[0] if isinstance(r_, list) and r_ else (r_ if isinstance(r_, dict) and "_error" not in r_ else {})
                    nm = p.get("companyName") if tk == sym else (r_.get("name") or "")
                    npm = pick(r_, "netProfitMarginTTM")
                    roe_ = pick(r_, "returnOnEquityTTM")
                    at_, lev = None, None
                    rows.append({"Ticker": tk, "Company": nm,
                                 "Gross margin": pick(r_, "grossProfitMarginTTM"),
                                 "Operating margin": pick(r_, "operatingProfitMarginTTM"),
                                 "Net margin": npm, "ROE": roe_,
                                 "Current ratio (×)": pick(r_, "currentRatioTTM"),
                                 "Debt ÷ equity (×)": pick(r_, "debtToEquityRatioTTM"),
                                 "P/E (×)": pick(r_, "priceToEarningsRatioTTM", "peRatioTTM"),
                                 "P/B (×)": pick(r_, "priceToBookRatioTTM"),
                                 "EV/EBITDA (×)": pick(r_, "enterpriseValueMultipleTTM"),
                                 "Dividend yield": pick(r_, "dividendYieldTTM")})
                PEERS = pd.DataFrame(rows).set_index("Ticker")
                st.session_state.peers, st.session_state.peers_for = PEERS, sym
        if PEERS is not None:
            view = PEERS.astype(object)
            for c_ in view.columns:
                if c_ == "Company":
                    continue
                view[c_] = [("–" if v_ is None or pd.isna(v_) else (f"{v_:.2f}×" if "(×)" in c_ else f"{v_*100:.1f}%"))
                            for v_ in PEERS[c_]]
            st.dataframe(view, width="stretch")
            st.caption("Trailing-twelve-month ratios from Yahoo Finance. Type NSE symbols; .NS is added automatically.")
        else:
            st.html(card(t("Type up to 4 peer tickers from the same sector (e.g. for TCS: INFY, WIPRO, HCLTECH, TECHM), then <b>Load peer comparison</b>.", TXT, 14)))

    # ---------------- cost of capital ----------------
    with tabs[5]:
        st.caption("WACC with CAPM. Risk-free rate, market risk premium and tax rate are in the sidebar.")
        e_val = mcap or 0
        if not e_val:
            st.warning("Market value of equity is not available right now, so the WACC below is not meaningful. Retry in a minute.")
        d_val = float(debt.iloc[-1]) if pd.notna(debt.iloc[-1]) else 0.0
        kd_pre = float(intexp.iloc[-1] / d_val) if d_val and pd.notna(intexp.iloc[-1]) and intexp.iloc[-1] > 0 else 0.0
        opts = ["Yahoo beta"] + (["Regression beta"] if reg_beta is not None else []) + ["Manual"]
        src = st.radio("Beta to use", opts, horizontal=True, index=1 if reg_beta is not None else 0)
        dflt = float(reg_beta) if src == "Regression beta" else float(beta or 1.0)
        b_ = st.number_input("Beta", 0.0, 4.0, round(dflt, 2), 0.01, key=f"beta_{src}", disabled=(src != "Manual"))
        kd_in = st.number_input("Pre-tax cost of debt (default = interest ÷ debt)", 0.0, 0.3, round(kd_pre, 4), 0.001, format="%.4f")
        ke = rf + b_ * mrp
        v = e_val + d_val
        we, wd = (e_val / v, d_val / v) if v else (1.0, 0.0)
        wacc = we * ke + wd * kd_in * (1 - tax)
        steps = [("Cost of equity  Ke = Rf + β × MRP", f"{rf:.2%} + {b_:.2f} × {mrp:.2%}", f"{ke:.2%}"),
                 ("After-tax cost of debt  Kd(1 − t)", f"{kd_in:.2%} × (1 − {tax:.0%})", f"{kd_in*(1-tax):.2%}"),
                 ("Weights  E/V and D/V (market cap, book debt)", f"{money(e_val, cur)} : {money(d_val, cur)}", f"{we:.1%} / {wd:.1%}"),
                 ("WACC = E/V·Ke + D/V·Kd(1 − t)", f"{we:.1%}×{ke:.2%} + {wd:.1%}×{kd_in*(1-tax):.2%}", f"{wacc:.2%}")]
        for i_, (h, w, v_) in enumerate(steps):
            hl = i_ == 3
            st.html(card(t(h, GOLD if hl else LB, 15, 700) + "<br>" + t(w, TXT, 14) +
                         f'<div style="float:right;margin-top:-30px">{t(v_, GOLD if hl else TXT, 24, 800)}</div>',
                         border=GOLD if hl else MID))
        st.caption("Teaching estimate: book debt from the latest balance sheet; cost of debt from reported interest.")

    # ---------------- DCF ----------------
    with tabs[6]:
        st.caption("A simple 5-year free cash flow DCF, discounted at the WACC from the previous tab.")
        Ia, fcf_d = I, fcf
        if per == "quarter":  # DCF always runs on annual figures (2 extra cached calls)
            try:
                Ia = frame_annual(fmp("income-statement", sym, key, "annual", 5))
                Ca = frame_annual(fmp("cash-flow-statement", sym, key, "annual", 5))
                o_, c_x = col(Ca, "operatingCashFlow"), col(Ca, "capitalExpenditure")
                fcf_d = col(Ca, "freeCashFlow"); fcf_d = fcf_d.where(fcf_d.notna(), o_ + c_x)
                st.caption("Quarterly view selected: the DCF uses the last 5 annual cash flow statements.")
            except FMPError as e:
                st.warning(f"Annual statements needed for the DCF could not be loaded: {e}")
        shares = col(Ia, "weightedAverageShsOutDil").iloc[-1] if "weightedAverageShsOutDil" in Ia else None
        if (shares is None or pd.isna(shares)) and mcap and price:
            shares = mcap / price
        f0 = float(fcf_d.iloc[-1]) if pd.notna(fcf_d.iloc[-1]) else 0.0
        fv = fcf_d.dropna()
        cagr = (fv.iloc[-1] / fv.iloc[0]) ** (1 / (len(fv) - 1)) - 1 if len(fv) > 1 and fv.iloc[0] > 0 and fv.iloc[-1] > 0 else 0.05
        a, b, c3 = st.columns(3)
        g = a.number_input("FCF growth, years 1–5", -0.2, 0.4, float(round(min(max(cagr, 0.0), 0.15), 3)), 0.005, format="%.3f",
                           help="Default: historical FCF growth, capped between 0% and 15%.")
        gt = b.number_input("Terminal growth", 0.0, 0.05, 0.025, 0.0025, format="%.4f")
        r_d = c3.number_input("Discount rate (WACC)", 0.03, 0.25, float(round(wacc, 4)), 0.0025, format="%.4f")
        yrs_ = list(range(1, 6))
        proj = [f0 * (1 + g) ** n for n in yrs_]
        pv = [cf / (1 + r_d) ** n for cf, n in zip(proj, yrs_)]
        tv = proj[-1] * (1 + gt) / (r_d - gt) if r_d > gt else float("nan")
        pv_tv = tv / (1 + r_d) ** 5
        ev = sum(pv) + pv_tv
        cash0 = float(cash.iloc[-1]) if pd.notna(cash.iloc[-1]) else 0.0
        eq = ev - d_val + cash0
        ps_ = eq / shares if shares else float("nan")
        dcf_fmp = None
        tbl = pd.DataFrame({"Year": [f"Year {n}" for n in yrs_], "FCF": proj, "Discount factor": [1 / (1 + r_d) ** n for n in yrs_], "PV of FCF": pv})
        show = tbl.copy()
        show["FCF"] = show["FCF"].map(lambda x: money(x, cur)); show["PV of FCF"] = show["PV of FCF"].map(lambda x: money(x, cur))
        show["Discount factor"] = show["Discount factor"].map(lambda x: f"{x:.4f}")
        st.dataframe(show.set_index("Year"), width="stretch")
        up = ps_ / price - 1 if price and pd.notna(ps_) else None
        lines = [("Latest FCF (base)", money(f0, cur)), ("PV of 5 years' FCF", money(sum(pv), cur)),
                 ("Terminal value = FCF₅ × (1 + g) ÷ (WACC − g)", money(tv, cur)), ("PV of terminal value", money(pv_tv, cur)),
                 ("Enterprise value", money(ev, cur)), ("− Debt + cash  →  equity value", money(eq, cur)),
                 ("Value per share (÷ diluted shares)", f"₹{ps_:,.2f}" if pd.notna(ps_) else "–"),
                 ("Market price", f"₹{price:,.2f}" if price else "–"),
                 ]
        a, b = st.columns([3, 2])
        a.html(card("<br>".join(t(h, LB, 14, 600) + "&nbsp;&nbsp;" + t(v_, GOLD if "per share" in h.lower() else TXT, 15, 800)
                                for h, v_ in lines)))
        if up is not None:
            b.html(card(t("MODEL VALUE vs PRICE", GOLD, 12, 800, "letter-spacing:1px") + "<br>" +
                        t(f"{up:+.1%}", GRN if up >= 0 else RED, 40, 800) + "<br>" +
                        t("Positive = model value above market price. A teaching model, not a recommendation.", MUTED, 13),
                        border=GOLD))

    with tabs[7]:
        a, b = st.columns([2, 1])
        a.html(card(t("About the company", GOLD, 15, 700) + "<br>" + t(p.get("description", "–"), TXT, 14, extra="line-height:1.55")))
        facts = [("CEO", p.get("ceo")), ("Employees", p.get("fullTimeEmployees")), ("Country", p.get("country")),
                 ("IPO date", p.get("ipoDate")), ("Website", p.get("website")), ("52-week range", p.get("range"))]
        b.html(card("<br>".join(t(k + ": ", GOLD, 13, 700) + t(str(v_ or "–"), TXT, 13) for k, v_ in facts)))

    # ---------------- formatted Excel ----------------
    with tabs[8]:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter as CL

        NAVY_, GOLD_, LBF, YEL = "003366", "C9A227", "EAF3F8", "FFF2CC"
        thin = Side(style="thin", color="B7C4D6"); BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
        F = lambda **k: Font(name="Arial", size=k.pop("size", 11), **k)
        NUM, PCT, X2, PS = '#,##0.0;(#,##0.0);"–"', '0.0%;-0.0%;"–"', '0.00"×"', '#,##0.00'
        wb = Workbook(); wb.remove(wb.active)

        def sheet(name, title, widths):
            ws = wb.create_sheet(name); ws.sheet_view.showGridLines = False
            ws.column_dimensions["A"].width = widths[0]
            for i_, w_ in enumerate(widths[1:], start=2):
                ws.column_dimensions[CL(i_)].width = w_
            ws["A1"] = title; ws["A1"].font = F(size=15, bold=True, color="FFFFFF")
            ws["A2"] = f"{p.get('companyName', sym)} ({sym}) · Source: Yahoo Finance (yfinance) · {SITE}"
            ws["A2"].font = F(size=9, italic=True, color="5A6B85")
            for c_ in range(1, len(widths) + 1):
                ws.cell(1, c_).fill = PatternFill("solid", fgColor=NAVY_)
                ws.cell(3, c_).fill = PatternFill("solid", fgColor=GOLD_)
            ws.row_dimensions[3].height = 4
            return ws

        def header(ws, r, labels):
            for j, lab in enumerate(labels, start=1):
                c_ = ws.cell(r, j, lab); c_.font = F(bold=True, color="FFFFFF"); c_.fill = PatternFill("solid", fgColor=NAVY_)
                c_.alignment = Alignment(horizontal="left" if j == 1 else "center", vertical="center", wrap_text=True); c_.border = BOX

        def put(ws, r, c_, v_, fmt=None, bold=False, inp=False, fill=None):
            cell = ws.cell(r, c_, v_)
            cell.font = F(bold=bold, color="0000FF" if inp else "000000"); cell.border = BOX
            if fmt: cell.number_format = fmt
            if inp: cell.fill = PatternFill("solid", fgColor=LBF)
            if fill: cell.fill = PatternFill("solid", fgColor=fill)
            return cell

        years = list(I.index); ny = len(years)
        ROWPOS = {}
        for name, df in ST.items():
            ws = sheet(name, f"{name} (₹ crore; EPS in ₹)", [34] + [14] * ny)
            header(ws, 5, ["Line item"] + years)
            for i_, (lab, vals) in enumerate(df.iterrows()):
                r = 6 + i_; ROWPOS[(name, lab)] = r
                put(ws, r, 1, lab, bold=lab in ("Revenue", "Net income", "Total assets", "Free cash flow", "Operating cash flow"))
                for j, yv in enumerate(years):
                    v_ = vals.get(yv)
                    v_ = None if v_ is None or pd.isna(v_) else (float(v_) if "EPS" in lab else float(v_) / 1e7)
                    put(ws, r, 2 + j, v_, PS if "EPS" in lab else NUM)
            ws.freeze_panes = "B6"

        # ratios with live formulas
        ws = sheet("Ratios", "Ratios (live formulas on the statement sheets)", [34] + [14] * ny + [52])
        header(ws, 5, ["Ratio"] + years + ["Formula"])
        IS_, BS_, CF_ = "'Income statement'!", "'Balance sheet'!", "'Cash flow'!"
        def ref(sh, lab, col_):
            return f"{sh}{col_}{ROWPOS[(dict(zip([IS_, BS_, CF_], ST))[sh], lab)]}"
        ratio_defs = [("Revenue growth", PCT, lambda c_, p_: f"={ref(IS_, 'Revenue', c_)}/{ref(IS_, 'Revenue', p_)}-1" if p_ else None, "Revenue ÷ previous revenue − 1"),
                      ("Gross margin", PCT, lambda c_, p_: f"={ref(IS_, 'Gross profit', c_)}/{ref(IS_, 'Revenue', c_)}", "Gross profit ÷ revenue"),
                      ("Operating margin", PCT, lambda c_, p_: f"={ref(IS_, 'Operating income', c_)}/{ref(IS_, 'Revenue', c_)}", "Operating income ÷ revenue"),
                      ("Net margin", PCT, lambda c_, p_: f"={ref(IS_, 'Net income', c_)}/{ref(IS_, 'Revenue', c_)}", "Net income ÷ revenue"),
                      ("ROE", PCT, lambda c_, p_: f"={ref(IS_, 'Net income', c_)}/{ref(BS_, chr(39).join(['Shareholders', ' equity']), c_)}", "Net income ÷ shareholders' equity"),
                      ("ROA", PCT, lambda c_, p_: f"={ref(IS_, 'Net income', c_)}/{ref(BS_, 'Total assets', c_)}", "Net income ÷ total assets"),
                      ("Asset turnover", X2, lambda c_, p_: f"={ref(IS_, 'Revenue', c_)}/{ref(BS_, 'Total assets', c_)}", "Revenue ÷ total assets"),
                      ("Current ratio", X2, lambda c_, p_: f"={ref(BS_, 'Total current assets', c_)}/{ref(BS_, 'Total current liabilities', c_)}", "Current assets ÷ current liabilities"),
                      ("Debt ÷ equity", X2, lambda c_, p_: f"={ref(BS_, 'Total debt', c_)}/{ref(BS_, chr(39).join(['Shareholders', ' equity']), c_)}", "Total debt ÷ equity"),
                      ("Interest cover", X2, lambda c_, p_: f"=IFERROR({ref(IS_, 'Operating income', c_)}/{ref(IS_, 'Interest expense', c_)},\"–\")", "Operating income ÷ interest expense"),
                      ("FCF margin", PCT, lambda c_, p_: f"={ref(CF_, 'Free cash flow', c_)}/{ref(IS_, 'Revenue', c_)}", "Free cash flow ÷ revenue"),
                      ("Cash conversion", X2, lambda c_, p_: f"={ref(CF_, 'Operating cash flow', c_)}/{ref(IS_, 'Net income', c_)}", "Operating cash flow ÷ net income")]
        for i_, (lab, fmt, fn, txt) in enumerate(ratio_defs):
            r = 6 + i_; put(ws, r, 1, lab, bold=True)
            for j in range(ny):
                c_, p_ = CL(2 + j), (CL(1 + j) if j else None)
                fx = fn(c_, p_)
                put(ws, r, 2 + j, ("=IFERROR(" + fx[1:] + ",\"–\")") if fx and not fx.startswith("=IFERROR") else fx, fmt)
            put(ws, r, 2 + ny, txt).font = F(italic=True, color="5A6B85")
        ws.freeze_panes = "B6"

        # WACC with formulas
        ws = sheet("WACC", "Cost of capital (CAPM and WACC): change the blue inputs", [44, 18, 50])
        header(ws, 5, ["Item", "Value", "Formula / source"])
        rows_w = [("Risk-free rate (10-yr G-Sec)", rf, PCT, True, "Input (sidebar / CCIL indicative)"),
                  ("Beta", b_, PS, True, f"Input ({src})"), ("Market risk premium", mrp, PCT, True, "Input"),
                  ("Cost of equity Ke", "=B6+B7*B8", '0.00%', False, "Rf + β × MRP"),
                  ("Pre-tax cost of debt Kd", kd_in, '0.00%', True, "Input (default interest ÷ debt)"),
                  ("Tax rate", tax, PCT, True, "Input"), ("After-tax cost of debt", "=B10*(1-B11)", '0.00%', False, "Kd × (1 − t)"),
                  ("Equity value E (₹ crore, market cap)", (e_val or 0) / 1e7, NUM, True, "Market capitalisation"),
                  ("Debt D (₹ crore, book)", d_val / 1e7, NUM, True, "Total debt, latest balance sheet"),
                  ("E / V", "=B13/(B13+B14)", PCT, False, "E ÷ (E + D)"), ("D / V", "=B14/(B13+B14)", PCT, False, "D ÷ (E + D)"),
                  ("WACC", "=B15*B9+B16*B12", '0.00%', False, "E/V × Ke + D/V × Kd(1 − t)")]
        for i_, (lab, v_, fmt, inp, txt) in enumerate(rows_w):
            r = 6 + i_; put(ws, r, 1, lab, bold=(lab == "WACC"))
            put(ws, r, 2, v_, fmt, bold=(lab == "WACC"), inp=inp, fill=YEL if lab == "WACC" else None)
            put(ws, r, 3, txt).font = F(italic=True, color="5A6B85")

        # DCF with formulas
        ws = sheet("DCF", "Simple 5-year FCF DCF: change the blue inputs", [40, 16, 16, 16, 16, 16])
        header(ws, 5, ["Input", "Value", "", "", "", ""])
        ins = [("Base FCF (₹ crore, latest year)", f0 / 1e7, NUM), ("FCF growth, years 1–5", g, PCT),
               ("Terminal growth", gt, PCT), ("Discount rate (WACC)", "=WACC!B17", '0.00%'),
               ("Debt (₹ crore)", d_val / 1e7, NUM), ("Cash (₹ crore)", cash0 / 1e7, NUM),
               ("Diluted shares (crore)", (shares or 0) / 1e7, NUM), (f"Market price ({cur.strip()})", price or 0, PS)]
        for i_, (lab, v_, fmt) in enumerate(ins):
            put(ws, 6 + i_, 1, lab); put(ws, 6 + i_, 2, v_, fmt, inp=not str(v_).startswith("="))
        header(ws, 15, ["Projection", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"])
        put(ws, 16, 1, "Year number"); put(ws, 17, 1, "FCF"); put(ws, 18, 1, "Discount factor"); put(ws, 19, 1, "PV of FCF")
        for j in range(5):
            c_ = CL(2 + j)
            put(ws, 16, 2 + j, j + 1)
            put(ws, 17, 2 + j, f"=$B$6*(1+$B$7)^{c_}16", NUM)
            put(ws, 18, 2 + j, f"=1/(1+$B$9)^{c_}16", '0.0000')
            put(ws, 19, 2 + j, f"={c_}17*{c_}18", NUM)
        outs = [("PV of 5 years' FCF", "=SUM(B19:F19)", NUM), ("Terminal value", "=F17*(1+B8)/(B9-B8)", NUM),
                ("PV of terminal value", "=B22*F18", NUM), ("Enterprise value", "=B21+B23", NUM),
                ("Equity value = EV − debt + cash", "=B24-B10+B11", NUM), (f"Value per share ({cur.strip()})", "=B25/B12", PS),
                ("Upside vs market price", "=B26/B13-1", PCT)]
        for i_, (lab, fx, fmt) in enumerate(outs):
            r = 21 + i_; put(ws, r, 1, lab, bold=r in (26, 27)); put(ws, r, 2, fx, fmt, bold=r in (26, 27), fill=YEL if r == 26 else None)


        # beta sheet
        if RET is not None and len(RET.dropna()) >= 12:
            ws = sheet("Beta", f"Beta by regression ({freq.lower()} returns vs Nifty 50)", [14, 14, 14, 15, 15, 4, 30, 14])
            header(ws, 5, ["Date", f"{sym} price", "Nifty 50", f"{sym} return", "Nifty return"])
            for i_, (d_, row) in enumerate(RET.iterrows()):
                r = 6 + i_
                put(ws, r, 1, d_.date(), "yyyy-mm-dd"); put(ws, r, 2, float(row["Stock price"]), PS); put(ws, r, 3, float(row["Nifty 50"]), PS)
                if i_:
                    put(ws, r, 4, f"=B{r}/B{r-1}-1", '0.00%'); put(ws, r, 5, f"=C{r}/C{r-1}-1", '0.00%')
            last = 5 + len(RET)
            for k_, (lab, fx, fmt) in enumerate([("Beta = SLOPE", f"=SLOPE(D7:D{last},E7:E{last})", '0.00'),
                                                ("R² = RSQ", f"=RSQ(D7:D{last},E7:E{last})", '0.00'),
                                                ("Correlation", f"=CORREL(D7:D{last},E7:E{last})", '0.00')]):
                put(ws, 6 + k_, 7, lab, bold=True); put(ws, 6 + k_, 8, fx, fmt, bold=True, fill=YEL if k_ == 0 else None)
            ws.freeze_panes = "A6"

        if PEERS is not None:
            ws = sheet("Peers", "Peer comparison (TTM ratios)", [10, 30] + [13] * (len(PEERS.columns) - 1))
            header(ws, 5, ["Ticker"] + list(PEERS.columns))
            for i_, (tk, row) in enumerate(PEERS.iterrows()):
                r = 6 + i_; put(ws, r, 1, tk, bold=True, fill=YEL if tk == sym else None)
                for j, c_ in enumerate(PEERS.columns):
                    v_ = row[c_]
                    put(ws, r, 2 + j, None if v_ is None or (not isinstance(v_, str) and pd.isna(v_)) else v_,
                        None if c_ == "Company" else (X2 if "(×)" in c_ else PCT))

        # summary first
        ws = sheet("Summary", f"{p.get('companyName', sym)}: summary", [36, 22, 40])
        header(ws, 5, ["Item", "Value", "Note"])
        summ = [("Ticker / exchange", f"{sym} · {p.get('exchange', '')}", None, ""), ("Sector / industry", f"{p.get('sector', '')} / {p.get('industry', '')}", None, ""),
                ("Price (₹)", price, PS, "Yahoo Finance"), ("Market cap (₹ crore)", (mcap or 0) / 1e7, NUM, ""),
                ("Beta (Yahoo)", beta, '0.00', ""), ("Beta (regression)", reg_beta, '0.00', "See Beta sheet" if reg_beta is not None else "n/a"),
                ("WACC", "=WACC!B17", '0.00%', "See WACC sheet"), (f"DCF value per share ({cur.strip()})", "=DCF!B26", PS, "See DCF sheet"),
                ("Statements", f"{per}, {ny} periods", None, f"{years[0]} to {years[-1]}"),
                ("Downloaded", dt.date.today().isoformat(), None, "Blue = input, black = formula"),
                ("Built with", SITE, None, "Education only, not investment advice")]
        for i_, (lab, v_, fmt, note) in enumerate(summ):
            r = 6 + i_; put(ws, r, 1, lab, bold=True); put(ws, r, 2, v_, fmt); put(ws, r, 3, note).font = F(italic=True, color="5A6B85")
        wb.move_sheet("Summary", offset=-(len(wb.sheetnames) - 1))

        raw = wb.create_sheet("Raw data")
        r0 = 1
        for name_, df_ in (("Income statement (raw)", I), ("Balance sheet (raw)", B), ("Cash flow (raw)", C)):
            raw.cell(r0, 1, name_).font = F(bold=True, color="003366", size=12)
            tdf = df_.T
            raw.cell(r0 + 1, 1, "Field").font = F(bold=True)
            for j, cn in enumerate(tdf.columns, start=2):
                raw.cell(r0 + 1, j, str(cn)).font = F(bold=True)
            for i_, (idx, row) in enumerate(tdf.iterrows(), start=r0 + 2):
                raw.cell(i_, 1, str(idx))
                for j, v_ in enumerate(row, start=2):
                    raw.cell(i_, j, v_ if isinstance(v_, (int, float, str)) and not (isinstance(v_, float) and pd.isna(v_)) else None)
            r0 = i_ + 3
        raw.column_dimensions["A"].width = 38
        buf = io.BytesIO(); wb.save(buf)
        if os.environ.get("MPA_SAVE_XLSX"):
            open(os.environ["MPA_SAVE_XLSX"], "wb").write(buf.getvalue())
        st.download_button(f"Download {sym} financials (formatted Excel)", buf.getvalue(), f"{sym}_financials_{per}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
        st.html(card(t("What's in the workbook", GOLD, 15, 700) + "<br>" + t(
            "Summary · Income statement · Balance sheet · Cash flow (₹ crore) · Ratios (live formulas linked to the statements) · "
            "WACC (live CAPM and WACC formulas) · DCF (live 5-year model) · Beta (returns with SLOPE and RSQ) · Peers (if loaded) · Raw data. "
            "Blue cells are inputs; change them and the model updates.", TXT, 14)))

# ---------------- footer ----------------
st.html(f"""<div style="margin-top:28px;padding:16px 10px;border-top:2px solid {GOLD};text-align:center;user-select:none;-webkit-user-select:none">
{t("The Mountain Path Academy · Prof. V. Ravichandran", TXT, 14, 700)}<br>
<a href="{SITE}" target="_blank" style="color:{GOLD};-webkit-text-fill-color:{GOLD};text-decoration:none;font-weight:700">{SITE}</a>
{t(" · ", MUTED)}<a href="https://www.linkedin.com/in/trichyravis" target="_blank" style="color:{GOLD};-webkit-text-fill-color:{GOLD};text-decoration:none;font-weight:700">LinkedIn</a>
{t(" · ", MUTED)}<a href="https://github.com/trichyravis" target="_blank" style="color:{GOLD};-webkit-text-fill-color:{GOLD};text-decoration:none;font-weight:700">GitHub</a><br>
{t("Data: Yahoo Finance via yfinance (unofficial) and CCIL. Education only — not investment advice.", MUTED, 12)}</div>""")
