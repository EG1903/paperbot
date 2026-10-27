#!/usr/bin/env python3
"""Strategie-Labor v2: testet rund 10.000 Varianten von Handelsstrategien und schreibt alles in eine Excel-Datei.

    python strategielabor.py               # alles: Daten laden, rechnen, Strategie-Labor.xlsx schreiben
    python strategielabor.py --refresh     # Kurs- und SEC-Daten neu laden
    python strategielabor.py --quick       # kurzer Probelauf
    python strategielabor.py --workers 4

Methode (damit oben keine Zufallstreffer stehen):
  * Zeitraeume: A = 2005-2012 und B = 2013-2019 dienen der AUSWAHL,
    C = 2020-heute ist der TEST und wird fuer die Auswahl nie benutzt.
  * Rangfolge nach min(Sharpe A, Sharpe B): eine Strategie muss in beiden Phasen taugen.
  * Signal zum Tagesschluss -> Order zur NAECHSTEN Eroeffnung (kein Blick in die Zukunft).
    Ausnahmen: Tageshandel entscheidet zur Eroeffnung, Kalender handelt zum Schluss
    (Termine stehen vorher fest), Overnight kauft zum Schluss.
  * Kosten je Order 0,03 % (Aktien/ETFs) bis 0,20 % (Krypto); Gegencheck mit 3,3-fachen Kosten.
    Leerverkauf: 0,5 % Leihgebuehr p.a. Cash bekommt den T-Bill-Zins (^IRX).
  * Hebel-ETFs simuliert: Tagesrendite x Hebel - Finanzierung (T-Bill) - 0,95 % Gebuehr p.a.
Daten: Yahoo Finance (Tageskurse, Dividenden, CBOE-Optionsindizes), SEC EDGAR (Termine der Quartalszahlen).
Ergebnisse: Strategie-Labor.xlsx, lab_report.md, lab_results.json
"""
import argparse, bisect, collections, datetime as dt, heapq, itertools, json, math, os, pickle, sys, time
import urllib.parse, urllib.request, warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

warnings.filterwarnings("ignore")

# ======================= Werte, Maerkte, Kosten =======================
ETF_EQ = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"]
MULTI = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "LQD", "HYG", "GLD", "SLV", "DBC", "VNQ", "AGG"]
STOCKS = ["MSFT", "GE", "XOM", "PFE", "C", "WMT", "INTC", "AIG", "CSCO", "IBM", "JNJ", "BAC", "PG", "KO",
          "MRK", "VZ", "HD", "ORCL", "AMGN", "WFC", "MO", "PEP", "T", "JPM", "CVX", "TXN", "QCOM", "BMY",
          "MDT", "UNH", "LLY", "ABT", "CMCSA", "DIS", "MMM", "UPS", "HPQ", "MS", "GS", "AXP", "USB", "EBAY",
          "AMZN", "LOW", "COP", "SLB", "F", "BRK-B", "MSI"]
# Fannie Mae / Freddie Mac (FNMA, FMCC) bewusst NICHT dabei: seit 2010 ausserboerslich gehandelte
# Pennystocks mit Spruengen von mehreren 100 %, mit 0,03 % Kosten nicht realistisch handelbar.
# Sie haben Umkehr- und Momentum-Ergebnisse stark verfaelscht (Umkehr 2005-2012: 18,6 % statt 0,3 % p.a.).
TAA_SET = ["SPY", "IWM", "QQQ", "VGK", "EWJ", "EEM", "VNQ", "DBC", "GLD", "TLT", "HYG", "LQD", "IEF", "SHY", "BIL",
           "AGG", "EFA", "TIP"]
FX = ["FXA", "FXB", "FXC", "FXE", "FXF", "FXY", "UUP"]
CMDTY = ["DBC", "GLD", "SLV", "USO", "UNG", "DBA", "DBB"]
ALLCLS = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "LQD", "HYG", "VNQ", "GLD", "SLV", "DBC", "USO", "UNG",
          "DBA", "FXA", "FXE", "FXY", "UUP"]
PAIRS = [("KO", "PEP"), ("XOM", "CVX"), ("HD", "LOW"), ("GS", "MS"), ("JPM", "BAC"), ("WMT", "TGT"), ("UPS", "FDX"),
         ("EWA", "EWC"), ("CAT", "DE"), ("MCD", "YUM"), ("PG", "CL"), ("MRK", "PFE"), ("GLD", "GDX")]
PAIR_SYMS = sorted({s for pr in PAIRS for s in pr})
OPT_IDX = {"OPT-BXM": "^BXM", "OPT-PUT": "^PUT", "OPT-BXMD": "^BXMD", "OPT-CNDR": "^CNDR", "OPT-CLL": "^CLL",
           "OPT-PPUT": "^PPUT"}
VOLP = {"VOL-SVXY": "SVXY", "VOL-VIXY": "VIXY"}
CRYPTO = ["BTC-USD", "ETH-USD"]
EXTRA = ["^VIX", "^VIX3M", "^IRX"]
LEVS = [("SPY", 1.5), ("SPY", 2.0), ("SPY", 3.0), ("QQQ", 1.5), ("QQQ", 2.0), ("QQQ", 3.0)]
LEV_FEE, BORROW = 0.0095, 0.005


def levname(base, L):
    return base if L == 1 else "%sx%.1f" % (base, L)


SYNTH = {levname(b, L) for b, L in LEVS}
UNIVERSES = {"SPY": ["SPY"], "QQQ": ["QQQ"], "IWM": ["IWM"], "SEKTOREN": ETF_EQ, "MULTI": MULTI, "AKTIEN": STOCKS,
             "ALLE-KLASSEN": ALLCLS, "DEVISEN": FX, "ROHSTOFFE": CMDTY, "KRYPTO": CRYPTO, "TAA": TAA_SET,
             "HEBEL-SPY": ["SPY"] + [levname("SPY", L) for L in (1.5, 2.0, 3.0)] + ["IEF"],
             "HEBEL-QQQ": ["QQQ"] + [levname("QQQ", L) for L in (1.5, 2.0, 3.0)] + ["IEF"],
             "PAARE": PAIR_SYMS}
UNIVERSES.update({u: [s] for u, s in OPT_IDX.items()})
UNIVERSES.update({u: [s] for u, s in VOLP.items()})
CORE = ["SPY", "QQQ", "IWM", "SEKTOREN", "MULTI", "AKTIEN", "ALLE-KLASSEN", "DEVISEN", "ROHSTOFFE", "KRYPTO"]
EQ_UNIS = ["SPY", "QQQ", "IWM", "SEKTOREN", "AKTIEN"]
OPT_UNIS, VOL_UNIS = list(OPT_IDX), list(VOLP)
UNI_INFO = {
    "SPY": "S&P 500 (SPY)", "QQQ": "Nasdaq-100 (QQQ)", "IWM": "Russell 2000 Nebenwerte (IWM)",
    "SEKTOREN": "13 US-Aktien-ETFs (Indizes + Sektoren)",
    "MULTI": "14 ETFs: Aktien, Anleihen, Gold, Rohstoffe, Immobilien",
    "AKTIEN": "49 große US-Aktien (Liste von 2004)",
    "ALLE-KLASSEN": "20 ETFs aller Anlageklassen inkl. Devisen",
    "DEVISEN": "7 Währungs-ETFs (AUD, GBP, CAD, EUR, CHF, JPY, USD)",
    "ROHSTOFFE": "7 Rohstoff-ETFs (breit, Gold, Silber, Öl, Gas, Agrar, Metalle)",
    "KRYPTO": "Bitcoin + Ethereum", "TAA": "18 ETFs für taktische Asset-Allokation",
    "HEBEL-SPY": "S&P 500 mit 1- bis 3-fachem Hebel (simuliert)",
    "HEBEL-QQQ": "Nasdaq-100 mit 1- bis 3-fachem Hebel (simuliert)",
    "PAARE": "13 Paare verwandter Aktien/ETFs",
    "OPT-BXM": "Optionen: Covered Call auf S&P 500 (CBOE BXM)",
    "OPT-PUT": "Optionen: Puts verkaufen auf S&P 500 (CBOE PUT)",
    "OPT-BXMD": "Optionen: Covered Call 30-Delta (CBOE BXMD)",
    "OPT-CNDR": "Optionen: Iron Condor (CBOE CNDR)",
    "OPT-CLL": "Optionen: Collar (CBOE CLL)",
    "OPT-PPUT": "Optionen: Protective Put (CBOE PPUT)",
    "VOL-SVXY": "Volatilität: Short-VIX-ETF (SVXY)",
    "VOL-VIXY": "Volatilität: Long-VIX-ETF (VIXY)",
}
COST = 0.0003
COST_BY_UNI = {"KRYPTO": 0.0020, "DEVISEN": 0.0005, "ROHSTOFFE": 0.0005, "ALLE-KLASSEN": 0.0004, "PAARE": 0.0005,
               "VOL-SVXY": 0.0005, "VOL-VIXY": 0.0005, "HEBEL-SPY": 0.0004, "HEBEL-QQQ": 0.0004}
HIGH_COST_X = 10.0 / 3.0


def uni_cost(u):
    return COST_BY_UNI.get(u, COST)


PERIODS = [("A", "2005-01-01", "2013-01-01"), ("B", "2013-01-01", "2020-01-01"),
           ("C", "2020-01-01", "2100-01-01"), ("AB", "2005-01-01", "2020-01-01"),
           ("G", "2005-01-01", "2100-01-01")]
DAILY_CACHE, HOURLY_CACHE, EVENTS_FILE = "lab_daily.pkl", "lab_hourly.pkl", "lab_events.json"
CONFIG_FILE = "lab_config.json"            # lokal, NICHT im Repo: {"sec_user_agent": "Name email@..."}
SETTINGS_FILE = "lab_settings.json"        # im Repo: {"live_start": "JJJJ-MM-TT"}
PAPER_FILE = "lab_papiertest.json"         # im Repo: am Start eingefrorene Liste fuer den Papier-Test
STAND_FILE = "lab_stand.json"
NAN = float("nan")


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def sec_user_agent():
    """Die SEC verlangt eine Kontaktadresse im User-Agent (Umgebungsvariable oder lokale lab_config.json)."""
    return os.environ.get("SEC_USER_AGENT") or (read_json(CONFIG_FILE, {}) or {}).get("sec_user_agent")

# werden von setup() gefuellt
DATES, T, RAW, RF, SPYR = [], 0, {}, [], []
MONTH, MON, YEAR, WD, POS_START, POS_END, PREHOL = [], [], [], [], [], [], []
REB_M, REB_W, REB_Y, REB_ALL, OPEXW, AFTER_OPEX = [], [], [], [], [], []
PI, SLOTS, U_START, MKT, EVENTS = {}, {}, {}, {}, {}
LIVE_I0 = None                             # erster Handelstag des Papier-Tests (Index in DATES)


# ======================= Daten =======================
def _get(url):
    last = None
    for host in ("query2", "query1"):
        u = url.replace("query2", host)
        for attempt in range(3):
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 strategielabor"})
                with urllib.request.urlopen(req, timeout=40) as r:
                    return json.loads(r.read())["chart"]["result"][0]
            except Exception as e:
                last = e
                time.sleep(2 + 3 * attempt)
    raise last


def fetch_daily(sym):
    res = _get("https://query2.finance.yahoo.com/v8/finance/chart/%s?period1=946684800&period2=%d"
               "&interval=1d&events=div%%2Csplit" % (urllib.parse.quote(sym), int(time.time())))
    q = res["indicators"]["quote"][0]
    adj = ((res["indicators"].get("adjclose") or [{}])[0].get("adjclose")) or q["close"]
    off = (res.get("meta") or {}).get("gmtoffset") or 0
    rows, divs = {}, {}
    for i, ts in enumerate(res.get("timestamp") or []):
        o, h, l, c, a = q["open"][i], q["high"][i], q["low"][i], q["close"][i], adj[i]
        if c is None or a is None or c <= 0 or a <= 0:
            continue
        o = o if o and o > 0 else c
        h = max(h if h and h > 0 else c, o, c)
        l = min(l if l and l > 0 else c, o, c)
        f = a / c
        d = dt.datetime.fromtimestamp(ts + off, dt.timezone.utc).strftime("%Y-%m-%d")
        rows[d] = (o * f, h * f, l * f, a, c)
    for ev in ((res.get("events") or {}).get("dividends") or {}).values():
        try:
            d = dt.datetime.fromtimestamp(int(ev["date"]) + off, dt.timezone.utc).strftime("%Y-%m-%d")
            divs[d] = divs.get(d, 0.0) + float(ev["amount"])
        except Exception:
            pass
    return rows, divs


CBOE_SYMS = set(OPT_IDX.values())


def fetch_cboe(sym):
    """CBOE-Strategieindizes (BXM, PUT, ...) als Tagesschlusskurse direkt von cboe.com."""
    url = "https://cdn.cboe.com/api/global/us_indices/daily_prices/%s_History.csv" % sym.lstrip("^")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 strategielabor"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8", "replace")
    rows = {}
    for line in text.splitlines()[1:]:
        parts = line.strip().split(",")
        try:
            m, d, y = parts[0].split("/")
            v = float(parts[1])
        except (ValueError, IndexError):
            continue
        if v > 0:
            rows["%s-%s-%s" % (y, m.zfill(2), d.zfill(2))] = (v, v, v, v, v)
    return rows, {}


def all_symbols():
    out = []
    for lst in UNIVERSES.values():
        out += [s for s in lst if s not in SYNTH]
    return list(dict.fromkeys(out + EXTRA))


def load_daily(refresh=False):
    need = all_symbols()
    if os.path.exists(DAILY_CACHE) and not refresh:
        with open(DAILY_CACHE, "rb") as f:
            data = pickle.load(f)
        if data.get("version") == 2 and all(s in data["assets"] or s in data["missing"] for s in need):
            return data
    raw, divs, missing = {}, {}, []
    for i, s in enumerate(need):
        try:
            rows, dv = fetch_cboe(s) if s in CBOE_SYMS else fetch_daily(s)
            if len(rows) < 50:
                raise ValueError("zu wenige Kurse")
            raw[s], divs[s] = rows, dv
            print("  [%3d/%d] %-8s %5d Tage ab %s" % (i + 1, len(need), s, len(rows), min(rows)), flush=True)
        except Exception as e:
            missing.append(s)
            print("  [%3d/%d] %-8s FEHLT: %s" % (i + 1, len(need), s, e), flush=True)
        time.sleep(0.3)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    dates = sorted(d for d in raw["SPY"] if d < today)
    n = len(dates)
    data = {"version": 2, "dates": dates, "assets": {}, "missing": missing}
    for s, rows in raw.items():
        O, H, L, C, RC = [NAN] * n, [NAN] * n, [NAN] * n, [NAN] * n, [NAN] * n
        start, last = None, None
        for t, d in enumerate(dates):
            r = rows.get(d)
            if r is not None:
                o, h, l, c, rc = r
                last = (c, rc)
                if start is None:
                    start = t
            elif last is not None:
                o = h = l = c = last[0]          # fehlender Tag: Kurs unveraendert
                rc = last[1]
            else:
                continue
            O[t], H[t], L[t], C[t], RC[t] = o, h, l, c, rc
        if start is None:
            missing.append(s)
            continue
        D = [0.0] * n
        for d, amt in divs.get(s, {}).items():
            t = bisect.bisect_left(dates, d)
            if t < n:
                D[t] += amt
        data["assets"][s] = {"O": O, "H": H, "L": L, "C": C, "RAWC": RC, "DIV": D, "start": start}
    with open(DAILY_CACHE, "wb") as f:
        pickle.dump(data, f)
    return data


def _sec_get(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def load_events(refresh=False):
    """Termine der Quartalszahlen = Datum der 8-K-Meldungen mit Item 2.02 (Results of Operations).
    Gespeichert in lab_events.json (nur oeffentliche Meldedaten, keine Kontaktdaten)."""
    old = read_json(EVENTS_FILE, {}) or {}
    if old and not refresh:
        return old
    ua = sec_user_agent()
    if not ua:
        print("  Kein SEC-Kontakt eingetragen (SEC_USER_AGENT oder lab_config.json) -> gespeicherte Termine: %d Werte" % len(old))
        return old
    out = dict(old)
    try:
        tick = _sec_get("https://www.sec.gov/files/company_tickers.json", ua)
    except Exception as e:
        print("  SEC nicht erreichbar (%s) -> gespeicherte Termine: %d Werte" % (e, len(old)))
        return old
    cik = {v["ticker"].upper(): int(v["cik_str"]) for v in tick.values()}
    for s in STOCKS:
        c = cik.get(s.upper()) or cik.get(s.replace("-", ".").upper())
        if not c:
            print("  %-6s keine CIK gefunden" % s)
            continue
        try:
            sub = _sec_get("https://data.sec.gov/submissions/CIK%010d.json" % c, ua)
            time.sleep(0.15)
            blocks = [sub["filings"]["recent"]]
            for fl in sub["filings"].get("files", []):
                blocks.append(_sec_get("https://data.sec.gov/submissions/" + fl["name"], ua))
                time.sleep(0.15)
            ds = set()
            for b in blocks:
                for form, fd, items in zip(b.get("form", []), b.get("filingDate", []), b.get("items", [])):
                    if form == "8-K" and items and "2.02" in str(items).split(","):
                        ds.add(fd)
            out[s] = sorted(ds)
            print("  %-6s %3d Quartalsmeldungen ab %s" % (s, len(ds), min(ds) if ds else "-"), flush=True)
        except Exception as e:
            print("  %-6s SEC-Fehler: %s" % (s, e))
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=0, sort_keys=True)
    return out


def third_friday(y, m):
    d = dt.date(y, m, 1)
    return d + dt.timedelta(days=(4 - d.weekday()) % 7 + 14)


def setup(data):
    global DATES, T, RAW, RF, SPYR, MONTH, MON, YEAR, WD, POS_START, POS_END, PREHOL
    global REB_M, REB_W, REB_Y, REB_ALL, OPEXW, AFTER_OPEX, PI, SLOTS, U_START, EVENTS, LIVE_I0
    DATES, RAW = data["dates"], dict(data["assets"])
    T = len(DATES)
    ls = data.get("live_start")
    LIVE_I0 = bisect.bisect_left(DATES, ls) if ls else None
    RF = [0.0] * T
    irx = RAW.get("^IRX")
    if irx:
        for t in range(1, T):
            v = irx["C"][t - 1]
            if v == v and v > 0:
                RF[t] = v / 100.0 / 252.0
    spc = RAW["SPY"]["C"]
    SPYR = [0.0] + [spc[t] / spc[t - 1] - 1.0 for t in range(1, T)]
    dd = [dt.date.fromisoformat(d) for d in DATES]
    MONTH = [d.year * 12 + d.month for d in dd]
    MON = [d.month for d in dd]
    YEAR = [d.year for d in dd]
    WD = [d.weekday() for d in dd]
    POS_START, POS_END = [0] * T, [0] * T
    groups = collections.defaultdict(list)
    for t in range(T):
        groups[MONTH[t]].append(t)
    for idx in groups.values():
        for i, t in enumerate(idx):
            POS_START[t], POS_END[t] = i, len(idx) - 1 - i
    PREHOL = [0] * T
    for t in range(T - 1):
        gap = (dd[t + 1] - dd[t]).days
        if not (gap == 1 or (WD[t] == 4 and gap == 3)):
            PREHOL[t] = 1
    REB_M = [1 if t == T - 1 or MONTH[t + 1] != MONTH[t] else 0 for t in range(T)]
    REB_W = [1 if t == T - 1 or WD[t + 1] <= WD[t] or (dd[t + 1] - dd[t]).days > 4 else 0 for t in range(T)]
    REB_Y = [1 if t == T - 1 or YEAR[t + 1] != YEAR[t] else 0 for t in range(T)]
    REB_ALL = [1] * T
    OPEXW, AFTER_OPEX = [0] * T, [0] * T
    for t, d in enumerate(dd):
        tf = third_friday(d.year, d.month)
        if tf - dt.timedelta(days=4) <= d <= tf:
            OPEXW[t] = 1
        prev = tf if d > tf else third_friday(d.year - (d.month == 1), 12 if d.month == 1 else d.month - 1)
        if prev + dt.timedelta(days=3) <= d <= prev + dt.timedelta(days=7):
            AFTER_OPEX[t] = 1
    PI = {}
    for name, a, b in PERIODS:
        i0 = next(t for t, d in enumerate(DATES) if d >= a)
        i1 = next((t for t, d in enumerate(DATES) if d >= b), T)
        PI[name] = (i0, i1)
    # simulierte Hebel-ETFs: Tagesrendite x Hebel - Finanzierung - Gebuehr
    for b, L in LEVS:
        src = RAW.get(b)
        if not src:
            continue
        O0, C0, s0 = src["O"], src["C"], src["start"]
        O, C = [NAN] * T, [NAN] * T
        O[s0] = C[s0] = 100.0
        fee = LEV_FEE / 252.0
        for t in range(s0 + 1, T):
            rcc, ron = C0[t] / C0[t - 1] - 1.0, O0[t] / C0[t - 1] - 1.0
            C[t] = max(1e-6, C[t - 1] * (1.0 + L * rcc - (L - 1) * RF[t] - fee))
            O[t] = max(1e-6, C[t - 1] * (1.0 + L * ron))
        H = [max(o, c) if o == o else NAN for o, c in zip(O, C)]
        Lw = [min(o, c) if o == o else NAN for o, c in zip(O, C)]
        RAW[levname(b, L)] = {"O": O, "H": H, "L": Lw, "C": C, "RAWC": C, "DIV": [0.0] * T, "start": s0}
    EVENTS = {}
    for s, ds in (data.get("events") or {}).items():
        idx = sorted({bisect.bisect_left(DATES, d) for d in ds})
        EVENTS[s] = [t for t in idx if t < T]
    SLOTS, U_START = {}, {}
    for u, syms in UNIVERSES.items():
        starts = [RAW[s]["start"] for s in syms if s in RAW]
        U_START[u] = min(starts) if starts else None
        cnt = [0] * T
        for s0 in starts:
            for t in range(s0, T):
                cnt[t] += 1
        SLOTS[u] = [1.0 / c if c else 0.0 for c in cnt]


def init_worker(live_start=None):
    with open(DAILY_CACHE, "rb") as f:
        data = pickle.load(f)
    data["events"] = read_json(EVENTS_FILE, {}) or {}
    data["live_start"] = live_start
    setup(data)


# ======================= Indikatoren =======================
class Asset:
    __slots__ = ("sym", "O", "H", "L", "C", "s0", "cache")

    def __init__(self, sym):
        r = RAW[sym]
        self.sym, self.O, self.H, self.L, self.C, self.s0 = sym, r["O"], r["H"], r["L"], r["C"], r["start"]
        self.cache = {}

    def ind(self, name, *args):
        key = (name,) + args
        v = self.cache.get(key)
        if v is None:
            v = self.cache[key] = IND[name](self, *args)
        return v


def first_valid(x, s0=0):
    for t in range(s0, len(x)):
        if x[t] == x[t]:
            return t
    return len(x)


def roll_mean(x, n, s0):
    out, acc = [NAN] * len(x), 0.0
    for t in range(s0, len(x)):
        acc += x[t]
        if t - s0 >= n:
            acc -= x[t - n]
        if t - s0 >= n - 1:
            out[t] = acc / n
    return out


def roll_std(x, n, s0):
    out, a1, a2 = [NAN] * len(x), 0.0, 0.0
    for t in range(s0, len(x)):
        v = x[t]
        a1 += v
        a2 += v * v
        if t - s0 >= n:
            w = x[t - n]
            a1 -= w
            a2 -= w * w
        if t - s0 >= n - 1:
            m = a1 / n
            var = a2 / n - m * m
            out[t] = math.sqrt(var) if var > 0 else 0.0
    return out


def ema_list(x, n, s0):
    out, k, e = [NAN] * len(x), 2.0 / (n + 1), None
    for t in range(s0, len(x)):
        e = x[t] if e is None else e + k * (x[t] - e)
        if t - s0 >= n - 1:
            out[t] = e
    return out


def roll_max(x, n, s0):
    out, dq = [NAN] * len(x), collections.deque()
    for t in range(s0, len(x)):
        v = x[t]
        while dq and x[dq[-1]] <= v:
            dq.pop()
        dq.append(t)
        if dq[0] <= t - n:
            dq.popleft()
        if t - s0 >= n - 1:
            out[t] = x[dq[0]]
    return out


def roll_min(x, n, s0):
    out, dq = [NAN] * len(x), collections.deque()
    for t in range(s0, len(x)):
        v = x[t]
        while dq and x[dq[-1]] >= v:
            dq.pop()
        dq.append(t)
        if dq[0] <= t - n:
            dq.popleft()
        if t - s0 >= n - 1:
            out[t] = x[dq[0]]
    return out


def rsi_list(x, n, s0):
    out, ag, al = [NAN] * len(x), 0.0, 0.0
    for t in range(s0 + 1, len(x)):
        d = x[t] - x[t - 1]
        g = d if d > 0 else 0.0
        l = -d if d < 0 else 0.0
        k = t - s0
        if k < n:
            ag += g
            al += l
            continue
        if k == n:
            ag, al = (ag + g) / n, (al + l) / n
        else:
            ag, al = (ag * (n - 1) + g) / n, (al * (n - 1) + l) / n
        out[t] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


def i_sma(a, n): return roll_mean(a.C, n, a.s0)
def i_ema(a, n): return ema_list(a.C, n, a.s0)
def i_std(a, n): return roll_std(a.C, n, a.s0)
def i_hh(a, n, src): return roll_max(getattr(a, src), n, a.s0)
def i_ll(a, n, src): return roll_min(getattr(a, src), n, a.s0)
def i_rsi(a, n): return rsi_list(a.C, n, a.s0)


def i_ret(a):
    C, out = a.C, [NAN] * T
    for t in range(a.s0 + 1, T):
        out[t] = math.log(C[t] / C[t - 1])
    return out


def i_vol(a, n):
    f = math.sqrt(252)
    return [v * f for v in roll_std(a.ind("ret"), n, a.s0 + 1)]


def i_volavg(a, n, m):
    v = a.ind("vol", n)
    s1 = first_valid(v, a.s0)
    return roll_mean(v, m, s1) if s1 < T else [NAN] * T


def i_atr(a, n):
    H, L, C, tr = a.H, a.L, a.C, [NAN] * T
    for t in range(a.s0 + 1, T):
        pc = C[t - 1]
        tr[t] = max(H[t] - L[t], abs(H[t] - pc), abs(L[t] - pc))
    return roll_mean(tr, n, a.s0 + 1)


def i_ibs(a):
    H, L, C, out = a.H, a.L, a.C, [NAN] * T
    for t in range(a.s0, T):
        rg = H[t] - L[t]
        out[t] = (C[t] - L[t]) / rg if rg > 0 else 0.5
    return out


def i_willr(a, n):
    hh, ll, C, out = a.ind("hh", n, "H"), a.ind("ll", n, "L"), a.C, [NAN] * T
    for t in range(a.s0, T):
        rg = hh[t] - ll[t]
        if rg == rg:
            out[t] = -100.0 * (hh[t] - C[t]) / rg if rg > 0 else -50.0
    return out


def i_cci(a, n):
    H, L, C, s0 = a.H, a.L, a.C, a.s0
    tp = [NAN] * T
    for t in range(s0, T):
        tp[t] = (H[t] + L[t] + C[t]) / 3.0
    m, out = roll_mean(tp, n, s0), [NAN] * T
    for t in range(s0 + n - 1, T):
        mt, md = m[t], 0.0
        for j in range(t - n + 1, t + 1):
            md += abs(tp[j] - mt)
        md /= n
        out[t] = (tp[t] - mt) / (0.015 * md) if md > 0 else 0.0
    return out


def i_adx(a, n):
    H, L, C, s0 = a.H, a.L, a.C, a.s0
    adx, pdi, mdi = [NAN] * T, [NAN] * T, [NAN] * T
    trs = pms = mms = 0.0
    dxs, adxv = [], None
    for t in range(s0 + 1, T):
        up, dn = H[t] - H[t - 1], L[t - 1] - L[t]
        pdm = up if (up > dn and up > 0) else 0.0
        mdm = dn if (dn > up and dn > 0) else 0.0
        tr = max(H[t] - L[t], abs(H[t] - C[t - 1]), abs(L[t] - C[t - 1]))
        k = t - s0
        if k <= n:
            trs += tr
            pms += pdm
            mms += mdm
            if k < n:
                continue
        else:
            trs, pms, mms = trs - trs / n + tr, pms - pms / n + pdm, mms - mms / n + mdm
        if trs <= 0:
            continue
        p, m = 100 * pms / trs, 100 * mms / trs
        pdi[t], mdi[t] = p, m
        dx = 100 * abs(p - m) / (p + m) if p + m > 0 else 0.0
        if adxv is None:
            dxs.append(dx)
            if len(dxs) == n:
                adxv = sum(dxs) / n
                adx[t] = adxv
        else:
            adxv = (adxv * (n - 1) + dx) / n
            adx[t] = adxv
    return (adx, pdi, mdi)


def i_psar(a, step, mx):
    H, L, s0, out = a.H, a.L, a.s0, [0.0] * T
    if T - s0 < 3:
        return out
    long_, af, ep, sar = True, step, H[s0], L[s0]
    for t in range(s0 + 1, T):
        sar = sar + af * (ep - sar)
        if long_:
            sar = min(sar, L[t - 1], L[t - 2] if t - 2 >= s0 else L[t - 1])
            if L[t] < sar:
                long_, sar, ep, af = False, ep, L[t], step
            elif H[t] > ep:
                ep, af = H[t], min(af + step, mx)
        else:
            sar = max(sar, H[t - 1], H[t - 2] if t - 2 >= s0 else H[t - 1])
            if H[t] > sar:
                long_, sar, ep, af = True, ep, H[t], step
            elif L[t] < ep:
                ep, af = L[t], min(af + step, mx)
        out[t] = 1.0 if long_ else 0.0
    return out


def i_ichi(a, p1, p2, p3):
    def mid(n):
        hh, ll = roll_max(a.H, n, a.s0), roll_min(a.L, n, a.s0)
        return [(hh[t] + ll[t]) / 2 for t in range(T)]
    ten, kij, sb = mid(p1), mid(p2), mid(p3)
    sa = [(ten[t] + kij[t]) / 2 for t in range(T)]
    ca, cb = [NAN] * T, [NAN] * T
    for t in range(p2, T):
        ca[t], cb[t] = sa[t - p2], sb[t - p2]
    return (ten, kij, ca, cb)


def i_slope(a, n):
    C, s0, out = a.C, a.s0, [NAN] * T
    sx, sxx = n * (n - 1) / 2.0, (n - 1) * n * (2 * n - 1) / 6.0
    den = n * sxx - sx * sx
    sy = sty = 0.0
    for t in range(s0, T):
        y, k = C[t], t - s0
        if k < n:
            sty += k * y
            sy += y
        else:
            y0 = C[t - n]
            sty = sty - (sy - y0) + (n - 1) * y
            sy = sy - y0 + y
        if k >= n - 1:
            out[t] = (n * sty - sx * sy) / den
    return out


def i_macd(a, f, s, g):
    ef, es = ema_list(a.C, f, a.s0), ema_list(a.C, s, a.s0)
    m = [ef[t] - es[t] for t in range(T)]
    s1 = first_valid(m, a.s0)
    return (m, ema_list(m, g, s1) if s1 < T else [NAN] * T)


def i_absmove(a, n):
    O, C, x = a.O, a.C, [NAN] * T
    for t in range(a.s0, T):
        x[t] = abs(C[t] / O[t] - 1.0)
    m = roll_mean(x, n, a.s0)
    return [NAN] + m[:-1]                 # Wert an Tag t nutzt nur Tage t-n .. t-1


def i_crsi(a):
    C, s0 = a.C, a.s0
    r3 = a.ind("rsi", 3)
    streak = [0.0] * T
    for t in range(s0 + 1, T):
        if C[t] > C[t - 1]:
            streak[t] = streak[t - 1] + 1 if streak[t - 1] > 0 else 1.0
        elif C[t] < C[t - 1]:
            streak[t] = streak[t - 1] - 1 if streak[t - 1] < 0 else -1.0
    rs = rsi_list(streak, 2, s0)
    roc = [NAN] * T
    for t in range(s0 + 1, T):
        roc[t] = C[t] / C[t - 1] - 1
    pr = [NAN] * T
    for t in range(s0 + 101, T):
        x, cnt = roc[t], 0
        for j in range(t - 100, t):
            if roc[j] < x:
                cnt += 1
        pr[t] = float(cnt)
    return [(r3[t] + rs[t] + pr[t]) / 3.0 for t in range(T)]


def i_divttm(a):
    D = RAW[a.sym].get("DIV") or [0.0] * T
    out, acc = [NAN] * T, 0.0
    for t in range(a.s0, T):
        acc += D[t]
        if t - a.s0 >= 252:
            acc -= D[t - 252]
        if t - a.s0 >= 251:
            out[t] = acc
    return out


def i_feat(a):
    """10 Merkmale fuer die ML-Modelle, alle zum Tagesschluss bekannt und grob normiert."""
    C, s0 = a.C, a.s0
    s50, s200, v20 = a.ind("sma", 50), a.ind("sma", 200), a.ind("vol", 20)
    r2, ib = a.ind("rsi", 2), a.ind("ibs")
    V = MKT.get("^VIX")
    vs = V.ind("sma", 20) if V else None
    X = [None] * T
    for t in range(s0 + 201, T):
        try:
            vz = 0.0
            if V is not None and V.C[t] == V.C[t] and vs[t] == vs[t] and vs[t] > 0:
                vz = (V.C[t] / vs[t] - 1.0) / 0.15
            f = [math.log(C[t] / C[t - 1]) / 0.01, math.log(C[t] / C[t - 5]) / 0.02,
                 math.log(C[t] / C[t - 20]) / 0.045, math.log(C[t] / C[t - 60]) / 0.08,
                 (C[t] / s50[t] - 1.0) / 0.04, (C[t] / s200[t] - 1.0) / 0.08, (v20[t] - 0.18) / 0.10,
                 (r2[t] - 50.0) / 30.0, (ib[t] - 0.5) / 0.3, vz]
        except (ZeroDivisionError, ValueError):
            continue
        if all(x == x for x in f):
            X[t] = f
    return X


def solve(M, b):
    n = len(b)
    A = [row[:] + [b[i]] for i, row in enumerate(M)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        if abs(A[p][c]) < 1e-12:
            return None
        A[c], A[p] = A[p], A[c]
        piv = A[c][c]
        for r in range(c + 1, n):
            f = A[r][c] / piv
            if f:
                rr, rc = A[r], A[c]
                for k in range(c, n + 1):
                    rr[k] -= f * rc[k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (A[r][n] - sum(A[r][k] * x[k] for k in range(r + 1, n))) / A[r][r]
    return x


def i_mlpred(a, h, win):
    """Lineares Modell (Ridge), jede Woche neu geschaetzt, nur mit Daten, deren Ergebnis schon bekannt ist."""
    X, C = a.ind("feat"), a.C
    nf = 11
    XtX, Xty = [[0.0] * nf for _ in range(nf)], [0.0] * nf
    q, n, beta, out = collections.deque(), 0, None, [NAN] * T
    start = a.s0 + 202

    def add(s, sign):
        x = [1.0] + X[s]
        y = C[s + h] / C[s] - 1.0
        for i in range(nf):
            xi = x[i] * sign
            row = XtX[i]
            for j in range(nf):
                row[j] += xi * x[j]
            Xty[i] += xi * y
    for t in range(start, T):
        s = t - h
        if s >= start and X[s] is not None:
            add(s, 1.0)
            q.append(s)
            n += 1
            if win and n > win:
                add(q.popleft(), -1.0)
                n -= 1
        if n >= 500 and (beta is None or REB_W[t]):
            M = [row[:] for row in XtX]
            for i in range(1, nf):
                M[i][i] += 1.0
            b = solve(M, Xty[:])
            if b is not None:
                beta = b
        if beta is not None and X[t] is not None:
            xt = X[t]
            out[t] = beta[0] + sum(beta[i + 1] * xt[i] for i in range(nf - 1))
    return out


def i_knn(a, h, win):
    """k-naechste-Nachbarn: mittlere Folgerendite der 25 bzw. 100 aehnlichsten frueheren Tage."""
    X, C = a.ind("feat"), a.C
    start = a.s0 + 202
    Y = [NAN] * T
    for s in range(start, T - h):
        Y[s] = C[s + h] / C[s] - 1.0
    out = [None] * T
    for t in range(start, T):
        xt = X[t]
        if xt is None:
            continue
        hi = t - h
        lo = max(start, hi - win)
        if hi - lo < 250:
            continue
        x0, x1, x2, x3, x4, x5, x6, x7, x8, x9 = xt
        cand = []
        for s in range(lo, hi + 1):
            xs = X[s]
            if xs is None:
                continue
            d = ((xs[0] - x0) ** 2 + (xs[1] - x1) ** 2 + (xs[2] - x2) ** 2 + (xs[3] - x3) ** 2 + (xs[4] - x4) ** 2
                 + (xs[5] - x5) ** 2 + (xs[6] - x6) ** 2 + (xs[7] - x7) ** 2 + (xs[8] - x8) ** 2 + (xs[9] - x9) ** 2)
            cand.append((d, Y[s]))
        best = heapq.nsmallest(100, cand)
        if len(best) < 25:
            continue
        out[t] = (sum(y for _, y in best[:25]) / 25.0, sum(y for _, y in best) / len(best))
    return out


IND = {"sma": i_sma, "ema": i_ema, "std": i_std, "hh": i_hh, "ll": i_ll, "rsi": i_rsi, "ret": i_ret,
       "vol": i_vol, "volavg": i_volavg, "atr": i_atr, "ibs": i_ibs, "willr": i_willr, "cci": i_cci,
       "adx": i_adx, "psar": i_psar, "ichi": i_ichi, "slope": i_slope, "macd": i_macd, "absmove": i_absmove,
       "crsi": i_crsi, "divttm": i_divttm, "feat": i_feat, "mlpred": i_mlpred, "knn": i_knn}


# ======================= Strategien je Wert (Timing) =======================
def machine(a, entry, exit_, maxhold=0):
    S, inpos, held = [0.0] * T, False, 0
    for t in range(a.s0 + 1, T):
        if inpos:
            held += 1
            if exit_(t) or (maxhold and held >= maxhold):
                inpos = False
        elif entry(t):
            inpos, held = True, 0
        if inpos:
            S[t] = 1.0
    return S


def trend(a, p):
    return a.ind("sma", p["trend"]) if p.get("trend") else None


def f_bh(a, p):
    S = [0.0] * T
    for t in range(a.s0, T):
        S[t] = 1.0
    return ("pos", S)


def f_sma_trend(a, p):
    C, m = a.C, a.ind("sma", p["n"])
    return ("pos", [1.0 if C[t] > m[t] else 0.0 for t in range(T)])


def f_ma_cross(a, p):
    f, s = a.ind(p["typ"], p["f"]), a.ind(p["typ"], p["s"])
    return ("pos", [1.0 if f[t] > s[t] else 0.0 for t in range(T)])


def f_donchian(a, p):
    C, hh, ll = a.C, a.ind("hh", p["n"], "H"), a.ind("ll", p["m"], "L")
    return ("pos", machine(a, lambda t: C[t] > hh[t - 1], lambda t: C[t] < ll[t - 1]))


def f_tsmom(a, p):
    C, n, k, S = a.C, p["n"], p["skip"], [0.0] * T
    for t in range(a.s0 + n, T):
        if C[t - k] > C[t - n]:
            S[t] = 1.0
    return ("pos", S)


def f_macd(a, p):
    m, sg = a.ind("macd", p["f"], p["s"], p["g"])
    if p["regel"] == "signal":
        return ("pos", [1.0 if m[t] > sg[t] else 0.0 for t in range(T)])
    return ("pos", [1.0 if m[t] > 0 else 0.0 for t in range(T)])


def f_keltner(a, p):
    C, m, at, k = a.C, a.ind("sma", p["n"]), a.ind("atr", p["n"]), p["k"]
    return ("pos", machine(a, lambda t: C[t] > m[t] + k * at[t], lambda t: C[t] < m[t]))


def f_chandelier(a, p):
    C, hh, at, k = a.C, a.ind("hh", p["n"], "C"), a.ind("atr", 22), p["k"]
    S, inpos, peak = [0.0] * T, False, 0.0
    for t in range(a.s0 + 1, T):
        if inpos:
            if C[t] > peak:
                peak = C[t]
            if C[t] < peak - k * at[t]:
                inpos = False
        elif C[t] > hh[t - 1]:
            inpos, peak = True, C[t]
        if inpos:
            S[t] = 1.0
    return ("pos", S)


def f_adx(a, p):
    adx, pdi, mdi = a.ind("adx", 14)
    thr = p["thr"]
    return ("pos", machine(a, lambda t: adx[t] > thr and pdi[t] > mdi[t], lambda t: pdi[t] < mdi[t]))


def f_psar(a, p):
    return ("pos", a.ind("psar", p["step"], p["max"]))


def f_ichi(a, p):
    ten, kij, ca, cb = a.ind("ichi", *p["set"])
    C, tk, S = a.C, p["tk"], [0.0] * T
    for t in range(a.s0, T):
        x, y = ca[t], cb[t]
        if x == x and y == y and C[t] > max(x, y) and (not tk or ten[t] > kij[t]):
            S[t] = 1.0
    return ("pos", S)


def f_slope(a, p):
    s = a.ind("slope", p["n"])
    return ("pos", [1.0 if s[t] > 0 else 0.0 for t in range(T)])


def f_bb_break(a, p):
    C, m, sd, k = a.C, a.ind("sma", p["n"]), a.ind("std", p["n"]), p["k"]
    return ("pos", machine(a, lambda t: C[t] > m[t] + k * sd[t], lambda t: C[t] < m[t]))


def f_rsi(a, p):
    C, r, x, tf = a.C, a.ind("rsi", p["n"]), p["x"], trend(a, p)
    ent = (lambda t: r[t] < x and C[t] > tf[t]) if tf else (lambda t: r[t] < x)
    if p["exit"] == "sma5":
        s5 = a.ind("sma", 5)
        exf = lambda t: C[t] > s5[t]
    elif p["exit"] == "rsi50":
        exf = lambda t: r[t] > 50
    else:
        exf = lambda t: r[t] > 70
    return ("pos", machine(a, ent, exf))


def f_crsi(a, p):
    C, c, x, tf = a.C, a.ind("crsi"), p["x"], trend(a, p)
    ent = (lambda t: c[t] < x and C[t] > tf[t]) if tf else (lambda t: c[t] < x)
    if p["exit"] == "sma5":
        s5 = a.ind("sma", 5)
        exf = lambda t: C[t] > s5[t]
    else:
        lvl = 50 if p["exit"] == "crsi50" else 70
        exf = lambda t: c[t] > lvl
    return ("pos", machine(a, ent, exf))


def f_bb_mr(a, p):
    C, m, sd, k, tf = a.C, a.ind("sma", p["n"]), a.ind("std", p["n"]), p["k"], trend(a, p)
    ent = lambda t: C[t] < m[t] - k * sd[t] and (tf is None or C[t] > tf[t])
    if p["exit"] == "mitte":
        exf = lambda t: C[t] > m[t]
    else:
        s5 = a.ind("sma", 5)
        exf = lambda t: C[t] > s5[t]
    return ("pos", machine(a, ent, exf))


def f_ibs(a, p):
    C, H, ib, x, tf = a.C, a.H, a.ind("ibs"), p["x"], trend(a, p)
    ent = lambda t: ib[t] < x and (tf is None or C[t] > tf[t])
    ex = p["exit"]
    if ex == "ibs70":
        exf = lambda t: ib[t] > 0.7
    elif ex == "ibs50":
        exf = lambda t: ib[t] > 0.5
    elif ex == "vortageshoch":
        exf = lambda t: C[t] > H[t - 1]
    else:
        exf = lambda t: True                 # nach einem Tag raus
    return ("pos", machine(a, ent, exf))


def f_down(a, p):
    C, N, tf = a.C, p["N"], trend(a, p)
    cnt = [0] * T
    for t in range(a.s0 + 1, T):
        cnt[t] = cnt[t - 1] + 1 if C[t] < C[t - 1] else 0
    ent = lambda t: cnt[t] >= N and (tf is None or C[t] > tf[t])
    if p["exit"] == "plustag":
        exf = lambda t: C[t] > C[t - 1]
    else:
        s5 = a.ind("sma", 5)
        exf = lambda t: C[t] > s5[t]
    return ("pos", machine(a, ent, exf))


def f_nlow(a, p):
    C, n, tf = a.C, p["n"], trend(a, p)
    ll = a.ind("ll", n, "C")
    ent = lambda t: C[t] <= ll[t] and (tf is None or C[t] > tf[t])
    mh = 0
    if p["exit"] == "sma5":
        s5 = a.ind("sma", 5)
        exf = lambda t: C[t] > s5[t]
    elif p["exit"] == "nhoch":
        hh = a.ind("hh", n, "C")
        exf = lambda t: C[t] >= hh[t]
    else:
        exf, mh = (lambda t: False), 5
    return ("pos", machine(a, ent, exf, mh))


def f_willr(a, p):
    C, w, x, tf = a.C, a.ind("willr", p["n"]), p["x"], trend(a, p)
    return ("pos", machine(a, lambda t: w[t] < x and (tf is None or C[t] > tf[t]), lambda t: w[t] > -30))


def f_cci(a, p):
    C, c, x, tf = a.C, a.ind("cci", p["n"]), p["x"], trend(a, p)
    return ("pos", machine(a, lambda t: c[t] < x and (tf is None or C[t] > tf[t]), lambda t: c[t] > 0))


def f_gapfade(a, p):
    O, C, L, g, tf = a.O, a.C, a.L, p["g"], trend(a, p)
    G, RET = [0.0] * T, [0.0] * T
    for t in range(a.s0 + 1, T):
        pc = C[t - 1]
        cond = O[t] < L[t - 1] if g == "unter-vortagestief" else O[t] < pc * (1 - g)
        if cond and (tf is None or pc > tf[t - 1]):
            G[t], RET[t] = 1.0, C[t] / O[t] - 1.0
    return ("intra", G, RET)


def f_gapgo(a, p):
    O, C, g, tf = a.O, a.C, p["g"], trend(a, p)
    G, RET = [0.0] * T, [0.0] * T
    for t in range(a.s0 + 1, T):
        pc = C[t - 1]
        if O[t] > pc * (1 + g) and (tf is None or pc > tf[t - 1]):
            G[t], RET[t] = 1.0, C[t] / O[t] - 1.0
    return ("intra", G, RET)


def f_volbreak(a, p):
    O, H, L, C, k, tf = a.O, a.H, a.L, a.C, p["k"], trend(a, p)
    G, RET = [0.0] * T, [0.0] * T
    for t in range(a.s0 + 1, T):
        if tf is not None and not (C[t - 1] > tf[t - 1]):
            continue
        e = O[t] + k * (H[t - 1] - L[t - 1])
        if e > 0 and H[t] >= e:
            G[t], RET[t] = 1.0, C[t] / e - 1.0
    return ("intra", G, RET)


def f_noise(a, p):
    O, H, C, mult, tf = a.O, a.H, a.C, p["mult"], trend(a, p)
    am = a.ind("absmove", p["n"])
    G, RET = [0.0] * T, [0.0] * T
    for t in range(a.s0 + 1, T):
        s = am[t]
        if s != s or (tf is not None and not (C[t - 1] > tf[t - 1])):
            continue
        ub = max(O[t], C[t - 1]) * (1 + mult * s)
        if H[t] >= ub:
            G[t], RET[t] = 1.0, C[t] / ub - 1.0
    return ("intra", G, RET)


def f_overnight(a, p):
    C, mode, tf, ib = a.C, p["bed"], a.ind("sma", 200), a.ind("ibs")
    OS = [0.0] * T
    for t in range(a.s0 + 1, T):
        if mode == "immer":
            ok = True
        elif mode == "trend200":
            ok = C[t] > tf[t]
        elif mode == "nach-minustag":
            ok = C[t] < C[t - 1]
        elif mode == "ibs<0.5":
            ok = ib[t] < 0.5
        else:
            ok = C[t] < C[t - 1] and C[t] > tf[t]
        if ok:
            OS[t] = 1.0
    return ("on", OS)


def f_tom(a, p):
    N, M, Hd = p["letzte"], p["erste"], [0.0] * T
    for t in range(a.s0 + 1, T):
        if POS_END[t] < N or POS_START[t] < M:
            Hd[t] = 1.0
    return ("moc", Hd)


def f_weekday(a, p):
    d, Hd = p["tag"], [0.0] * T
    for t in range(a.s0 + 1, T):
        if (d == "ohne-montag" and WD[t] != 0) or WD[t] == d:
            Hd[t] = 1.0
    return ("moc", Hd)


def f_prehol(a, p):
    Hd = [0.0] * T
    for t in range(a.s0 + 1, T):
        Hd[t] = float(PREHOL[t])
    return ("moc", Hd)


def f_season(a, p):
    C, tf, S = a.C, trend(a, p), [0.0] * T
    for t in range(a.s0, T):
        if (MON[t] >= 11 or MON[t] <= 4) and (tf is None or C[t] > tf[t]):
            S[t] = 1.0
    return ("pos", S)


def f_opex(a, p):
    mode, Hd = p["modus"], [0.0] * T
    for t in range(a.s0 + 1, T):
        if mode == "opex-woche":
            v = OPEXW[t]
        elif mode == "woche-nach-opex":
            v = AFTER_OPEX[t]
        else:
            v = 0 if AFTER_OPEX[t] else 1
        Hd[t] = float(v)
    return ("moc", Hd)


def f_santa(a, p):
    mode, Hd = p["modus"], [0.0] * T
    for t in range(a.s0 + 1, T):
        m = MON[t]
        if mode == "5+2-tage":
            v = (m == 12 and POS_END[t] < 5) or (m == 1 and POS_START[t] < 2)
        else:
            v = m == 12
        Hd[t] = 1.0 if v else 0.0
    return ("moc", Hd)


def f_janbaro(a, p):
    C, S = a.C, [0.0] * T
    years = collections.defaultdict(dict)
    for t in range(T):
        if MON[t] == 1 and POS_START[t] == 4:
            years[YEAR[t]]["j5"] = t
        if REB_Y[t]:
            years[YEAR[t]]["end"] = t
    for y, d in years.items():
        j5, end = d.get("j5"), d.get("end")
        if j5 is None or end is None or j5 - 5 < a.s0:
            continue
        if C[j5] > C[j5 - 5]:            # erste 5 Januartage positiv -> Rest des Jahres investiert
            for t in range(j5, end):
                S[t] = 1.0
    return ("pos", S)


def f_january(a, p):
    Hd = [0.0] * T
    for t in range(a.s0 + 1, T):
        Hd[t] = 1.0 if MON[t] == 1 else 0.0
    return ("moc", Hd)


def f_election(a, p):
    mode, Hd = p["modus"], [0.0] * T
    for t in range(a.s0 + 1, T):
        c = YEAR[t] % 4                   # 0 Wahljahr, 1 nach der Wahl, 2 Midterm, 3 Vorwahljahr
        if mode == "vorwahljahr":
            v = c == 3
        elif mode == "ohne-midterm-jahr":
            v = c != 2
        else:
            v = (c == 2 and MON[t] >= 10) or c == 3
        Hd[t] = 1.0 if v else 0.0
    return ("moc", Hd)


def f_vix(a, p):
    S, V = [0.0] * T, MKT.get("^VIX")
    if V is None:
        return ("pos", S)
    v, r, s0 = V.C, p["regel"], max(a.s0, V.s0)
    if r in ("vix<vix3m", "vix>vix3m"):
        V3 = MKT.get("^VIX3M")
        if V3 is None:
            return ("pos", S)
        v3, f, lt = V3.C, p["f"], r == "vix<vix3m"
        for t in range(max(s0, V3.s0), T):
            x, y = v[t], f * v3[t]
            if (x < y) if lt else (x > y):
                S[t] = 1.0
    elif r == "vix<sma":
        m = V.ind("sma", p["n"])
        for t in range(s0, T):
            if v[t] < m[t]:
                S[t] = 1.0
    elif r == "vix<niveau":
        for t in range(s0, T):
            if v[t] < p["n"]:
                S[t] = 1.0
    else:                                     # Angst-Kauf: VIX deutlich ueber Schnitt -> h Tage halten
        m, x, h, left = V.ind("sma", 20), p["x"], p["h"], 0
        for t in range(s0, T):
            if left > 0:
                left -= 1
                S[t] = 1.0
            elif v[t] > m[t] * (1 + x):
                left, S[t] = h - 1, 1.0
    return ("pos", S)


def f_voltarget(a, p):
    C, v, tgt, tf, S = a.C, a.ind("vol", p["n"]), p["ziel"], trend(a, p), [0.0] * T
    for t in range(a.s0, T):
        x = v[t]
        if x == x and x > 0 and (tf is None or C[t] > tf[t]):
            S[t] = min(1.0, tgt / x)
    return ("pos", S)


def f_volregime(a, p):
    v, m, k = a.ind("vol", 20), a.ind("volavg", 20, 252), p["k"]
    return ("pos", [1.0 if v[t] < k * m[t] else 0.0 for t in range(T)])


def f_trend_ls(a, p):
    C, m, S = a.C, a.ind("sma", p["n"]), [0.0] * T
    for t in range(a.s0, T):
        x = m[t]
        if x == x:
            S[t] = 1.0 if C[t] > x else -1.0
    return ("pos", S)


def f_tsmom_ls(a, p):
    C, n, k, S = a.C, p["n"], p["skip"], [0.0] * T
    for t in range(a.s0 + n, T):
        S[t] = 1.0 if C[t - k] > C[t - n] else -1.0
    return ("pos", S)


def f_donchian_ls(a, p):
    C, hh, ll = a.C, a.ind("hh", p["n"], "H"), a.ind("ll", p["n"], "L")
    S, pos = [0.0] * T, 0.0
    for t in range(a.s0 + 1, T):
        if C[t] > hh[t - 1]:
            pos = 1.0
        elif C[t] < ll[t - 1]:
            pos = -1.0
        S[t] = pos
    return ("pos", S)


def f_rsi_ls(a, p):
    r, (lo, hi) = a.ind("rsi", p["n"]), p["grenzen"]
    S, pos = [0.0] * T, 0.0
    for t in range(a.s0 + 1, T):
        v = r[t]
        if v != v:
            continue
        if pos == 0.0:
            if v < lo:
                pos = 1.0
            elif v > hi:
                pos = -1.0
        elif (pos > 0 and v > 50) or (pos < 0 and v < 50):
            pos = 0.0
        S[t] = pos
    return ("pos", S)


def f_pead(a, p):
    """Nach den Quartalszahlen: Reaktion ueber 2 Tage (abzgl. S&P 500) -> H Tage in Reaktionsrichtung (oder dagegen)."""
    ev, S = EVENTS.get(a.sym), [0.0] * T
    spy = MKT.get("SPY")
    if not ev or spy is None:
        return ("pos", S)
    C, x, H, r = a.C, p["x"], p["H"], p["richtung"]
    last = -999
    for d0 in ev:
        if d0 - last < 20 or d0 < a.s0 + 2 or d0 + 1 >= T:
            continue
        last = d0
        abn = (C[d0 + 1] / C[d0 - 1] - 1.0) - (spy.C[d0 + 1] / spy.C[d0 - 1] - 1.0)
        if r == "gewinner":
            sgn = 1.0 if abn > x else 0.0
        elif r == "verlierer":
            sgn = 1.0 if abn < -x else 0.0
        else:
            sgn = 1.0 if abn > x else (-1.0 if abn < -x else 0.0)
        if sgn:
            for t in range(d0 + 1, min(T, d0 + 1 + H)):
                S[t] = sgn
    return ("pos", S)


def f_pre_earn(a, p):
    """Vor den Quartalszahlen kaufen (Termin wird als vorab bekannt angenommen)."""
    ev, S = EVENTS.get(a.sym), [0.0] * T
    if not ev:
        return ("pos", S)
    N, mode = p["N"], p["modus"]
    for d0 in ev:
        lo, hi = d0 - N - 1, (d0 - 2 if mode == "vorher-raus" else d0)
        for t in range(max(a.s0, lo), min(T, hi + 1)):
            S[t] = 1.0
    return ("pos", S)


def f_ml_lin(a, p):
    h = p["h"]
    pred = a.ind("mlpred", h, 0 if p["fenster"] == "wachsend" else 1000)
    thr = 0.0 if p["schwelle"] == "0" else 0.0005 * h
    ls, S = p["seite"] == "long-short", [0.0] * T
    for t in range(T):
        v = pred[t]
        if v == v:
            if v > thr:
                S[t] = 1.0
            elif ls and v < -thr:
                S[t] = -1.0
    return ("pos", S)


def f_ml_knn(a, p):
    res = a.ind("knn", p["h"], 1500)
    k = 0 if p["k"] == 25 else 1
    ls, S = p["seite"] == "long-short", [0.0] * T
    for t in range(T):
        r = res[t]
        if r is not None:
            if r[k] > 0:
                S[t] = 1.0
            elif ls and r[k] < 0:
                S[t] = -1.0
    return ("pos", S)


def grid(**kw):
    return [dict(zip(kw, v)) for v in itertools.product(*kw.values())]


G_BENCH, G_TR, G_MR, G_DT, G_KAL = "Vergleich", "Trendfolge", "Rücksetzer kaufen", "Tageshandel & Overnight", "Kalender & Saison"
G_VOL, G_ROT, G_TAA, G_LEV = "Volatilität & VIX", "Rotation & Faktoren", "Taktische Asset-Allokation", "Hebel + Trend"
G_LS, G_PAIR, G_DIV, G_QZ, G_ML = "Long-Short", "Paarhandel", "Dividenden", "Quartalszahlen", "Maschinelles Lernen"
TF = [0, 200]
VIX_P = ([dict(regel="vix<vix3m", f=f) for f in (1.0, 0.95, 0.9)] + [dict(regel="vix>vix3m", f=f) for f in (1.0, 1.05)]
         + [dict(regel="vix<sma", n=n) for n in (10, 20, 50)] + [dict(regel="vix<niveau", n=n) for n in (15, 20, 25, 30)]
         + [dict(regel="angst-kauf", x=x, h=h) for x in (0.1, 0.2, 0.3) for h in (5, 10, 20)])
SPECIAL = CORE + OPT_UNIS + VOL_UNIS
TIMING = [  # Name, Funktion, Parameter, Gruppe, Maerkte
    ("Kaufen & Halten", f_bh, [{}], G_BENCH, SPECIAL),
    ("SMA-Trend", f_sma_trend, grid(n=[20, 50, 100, 150, 200, 250]), G_TR, SPECIAL),
    ("SMA-Kreuz", f_ma_cross, [p for p in grid(typ=["sma"], f=[5, 10, 20, 50], s=[50, 100, 150, 200]) if p["f"] < p["s"]], G_TR, CORE),
    ("EMA-Kreuz", f_ma_cross, [p for p in grid(typ=["ema"], f=[5, 10, 12, 20, 50], s=[26, 30, 50, 100, 200]) if p["f"] < p["s"]], G_TR, CORE),
    ("Donchian-Ausbruch", f_donchian, [p for p in grid(n=[20, 50, 100, 200], m=[10, 20, 50]) if p["m"] < p["n"]], G_TR, CORE),
    ("Zeitreihen-Momentum", f_tsmom, [p for p in grid(n=[21, 42, 63, 126, 189, 252], skip=[0, 21]) if p["skip"] < p["n"]], G_TR, CORE),
    ("MACD", f_macd, [dict(f=f, s=s, g=g, regel=r) for (f, s, g) in [(12, 26, 9), (8, 17, 9), (5, 35, 5), (19, 39, 9)]
                      for r in ("signal", "null")], G_TR, CORE),
    ("Keltner-Ausbruch", f_keltner, grid(n=[20, 50], k=[0.5, 1, 1.5, 2]), G_TR, CORE),
    ("Chandelier-Trend", f_chandelier, grid(n=[20, 50, 100], k=[2, 3, 4]), G_TR, CORE),
    ("ADX-Trend", f_adx, grid(thr=[15, 20, 25, 30]), G_TR, CORE),
    ("Parabolic-SAR", f_psar, grid(step=[0.01, 0.02, 0.03], max=[0.1, 0.2]), G_TR, CORE),
    ("Ichimoku", f_ichi, grid(set=[(9, 26, 52), (20, 60, 120)], tk=[0, 1]), G_TR, CORE),
    ("Regressions-Trend", f_slope, grid(n=[20, 50, 100, 200]), G_TR, CORE),
    ("Bollinger-Ausbruch", f_bb_break, grid(n=[20, 50, 100], k=[0.5, 1, 1.5, 2]), G_TR, CORE),
    ("RSI-Rücksetzer", f_rsi, grid(n=[2, 3, 4, 5, 14], x=[5, 10, 15, 20, 25, 30], exit=["sma5", "rsi50", "rsi70"], trend=TF), G_MR, CORE),
    ("ConnorsRSI", f_crsi, grid(x=[5, 10, 15, 20, 25], exit=["crsi50", "crsi70", "sma5"], trend=TF), G_MR, CORE),
    ("Bollinger-Rücksetzer", f_bb_mr, grid(n=[5, 10, 20, 50], k=[1, 1.5, 2, 2.5], exit=["mitte", "sma5"], trend=TF), G_MR, CORE),
    ("IBS-Rücksetzer", f_ibs, grid(x=[0.1, 0.15, 0.2, 0.25, 0.3], exit=["ibs70", "ibs50", "vortageshoch", "1tag"], trend=TF), G_MR, CORE),
    ("Abwärtstage", f_down, grid(N=[2, 3, 4, 5], exit=["plustag", "sma5"], trend=TF), G_MR, CORE),
    ("N-Tage-Tief", f_nlow, grid(n=[5, 7, 10, 20], exit=["sma5", "nhoch", "5tage"], trend=TF), G_MR, CORE),
    ("Williams-%R", f_willr, grid(n=[2, 5, 10, 14], x=[-80, -90, -95], trend=TF), G_MR, CORE),
    ("CCI-Rücksetzer", f_cci, grid(n=[10, 20], x=[-100, -150, -200], trend=TF), G_MR, CORE),
    ("Gap-Fade (Tageshandel)", f_gapfade, grid(g=[0.0025, 0.005, 0.01, 0.015, 0.02, "unter-vortagestief"], trend=TF), G_DT, CORE),
    ("Gap-Momentum (Tageshandel)", f_gapgo, grid(g=[0.0025, 0.005, 0.01, 0.02], trend=TF), G_DT, CORE),
    ("Vola-Ausbruch Williams (Tageshandel)", f_volbreak, grid(k=[0.3, 0.5, 0.7, 1.0], trend=TF), G_DT, CORE),
    ("Noise-Band (Tageshandel)", f_noise, grid(n=[7, 14, 21], mult=[0.5, 1.0, 1.5], trend=TF), G_DT, CORE),
    ("Overnight", f_overnight, grid(bed=["immer", "trend200", "nach-minustag", "ibs<0.5", "trend+minustag"]), G_DT, CORE),
    ("Monatswechsel", f_tom, grid(letzte=[0, 1, 2, 3, 4, 5], erste=[1, 2, 3, 4, 5]), G_KAL, EQ_UNIS),
    ("Wochentag", f_weekday, grid(tag=[0, 1, 2, 3, 4, "ohne-montag"]), G_KAL, EQ_UNIS),
    ("Vor-Feiertag", f_prehol, [{}], G_KAL, EQ_UNIS),
    ("Saison Nov-Apr", f_season, grid(trend=TF), G_KAL, EQ_UNIS),
    ("Optionsverfall", f_opex, grid(modus=["opex-woche", "woche-nach-opex", "ohne-woche-nach-opex"]), G_KAL, EQ_UNIS),
    ("Jahresend-Rally", f_santa, grid(modus=["5+2-tage", "ganzer-dezember"]), G_KAL, EQ_UNIS),
    ("Januar-Barometer", f_janbaro, [{}], G_KAL, EQ_UNIS),
    ("Nur Januar", f_january, [{}], G_KAL, EQ_UNIS),
    ("Wahlzyklus", f_election, grid(modus=["vorwahljahr", "ohne-midterm-jahr", "midterm-oktober-bis-vorwahljahr"]), G_KAL, EQ_UNIS),
    ("VIX-Filter", f_vix, VIX_P, G_VOL, EQ_UNIS + OPT_UNIS + VOL_UNIS),
    ("Vola-Ziel", f_voltarget, grid(ziel=[0.10, 0.15, 0.20], n=[20, 60], trend=TF), G_VOL, CORE + OPT_UNIS),
    ("Vola-Regime", f_volregime, grid(k=[0.8, 1.0, 1.2, 1.5]), G_VOL, SPECIAL),
    ("Trend Long-Short", f_trend_ls, grid(n=[50, 100, 150, 200, 250]), G_LS, CORE),
    ("Zeitreihen-Momentum Long-Short", f_tsmom_ls, [p for p in grid(n=[21, 63, 126, 252], skip=[0, 21]) if p["skip"] < p["n"]], G_LS, CORE),
    ("Donchian Long-Short", f_donchian_ls, grid(n=[20, 50, 100, 200]), G_LS, CORE),
    ("RSI Long-Short", f_rsi_ls, grid(n=[2, 3, 14], grenzen=[(10, 90), (20, 80), (30, 70)]), G_LS, CORE),
    ("Nach Quartalszahlen (PEAD)", f_pead, grid(richtung=["gewinner", "verlierer", "long-short"], x=[0.02, 0.04, 0.06], H=[5, 20, 60]), G_QZ, ["AKTIEN"]),
    ("Vor Quartalszahlen", f_pre_earn, grid(N=[3, 5, 10], modus=["vorher-raus", "durch-zahlen"]), G_QZ, ["AKTIEN"]),
    ("ML: lineares Modell", f_ml_lin, grid(h=[1, 5], schwelle=["0", "hoch"], fenster=["wachsend", "1000"], seite=["long", "long-short"]),
     G_ML, ["SPY", "QQQ", "IWM", "SEKTOREN", "MULTI", "ALLE-KLASSEN"]),
    ("ML: k-nächste Nachbarn", f_ml_knn, grid(h=[1, 5], k=[25, 100], seite=["long", "long-short"]), G_ML, ["SPY", "QQQ", "IWM"]),
]


# ======================= Strategien (Portfolio / Rotation) =======================
def port_weights(assets, reb, choose):
    W = {a.sym: [0.0] * T for a in assets}
    cur = {}
    for t in range(T):
        if reb[t]:
            cur = choose(t)
        for s, w in cur.items():
            W[s][t] = w
    return W


def spy_ok(t):
    spy = MKT["SPY"]
    return spy.C[t] > spy.ind("sma", 200)[t]


def m13612(a, t):
    if t - a.s0 <= 252:
        return None
    C = a.C
    return 12 * (C[t] / C[t - 21] - 1) + 4 * (C[t] / C[t - 63] - 1) + 2 * (C[t] / C[t - 126] - 1) + (C[t] / C[t - 252] - 1)


def g_mom(assets, p):
    L, k, N, filt = p["L"], p["skip"], p["N"], p["filt"]

    def choose(t):
        if filt == "spy200" and not spy_ok(t):
            return {}
        sc = []
        for a in assets:
            if t - a.s0 > L:
                r = a.C[t - k] / a.C[t - L] - 1.0
                if filt == "absolut" and r <= 0:
                    continue
                sc.append((r, a.sym))
        sc.sort(reverse=True)
        return {s: 1.0 / N for _, s in sc[:N]}
    return port_weights(assets, REB_M if p["reb"] == "M" else REB_W, choose)


def g_momvol(assets, p):
    L, N, filt = p["L"], p["N"], p["filt"]

    def choose(t):
        if filt == "spy200" and not spy_ok(t):
            return {}
        sc = []
        for a in assets:
            v = a.ind("vol", 63)[t]
            if t - a.s0 > L and v == v and v > 0:
                sc.append(((a.C[t] / a.C[t - L] - 1.0) / v, a.sym))
        sc.sort(reverse=True)
        return {s: 1.0 / N for _, s in sc[:N]}
    return port_weights(assets, REB_M, choose)


def g_lowvol(assets, p):
    n, N, filt = p["n"], p["N"], p["filt"]

    def choose(t):
        if filt == "spy200" and not spy_ok(t):
            return {}
        sc = []
        for a in assets:
            v = a.ind("vol", n)[t]
            if v == v and v > 0:
                sc.append((v, a.sym))
        sc.sort()
        return {s: 1.0 / N for _, s in sc[:N]}
    return port_weights(assets, REB_M, choose)


def g_rev(assets, p):
    L, N, filt = p["L"], p["N"], p["filt"]

    def choose(t):
        if filt == "spy200" and not spy_ok(t):
            return {}
        sc = [(a.C[t] / a.C[t - L] - 1.0, a.sym) for a in assets if t - a.s0 > L]
        sc.sort()
        return {s: 1.0 / N for _, s in sc[:N]}
    return port_weights(assets, REB_M if p["reb"] == "M" else REB_W, choose)


def g_52(assets, p):
    N, filt = p["N"], p["filt"]

    def choose(t):
        if filt == "spy200" and not spy_ok(t):
            return {}
        sc = []
        for a in assets:
            hh = a.ind("hh", 252, "C")[t]
            if hh == hh and hh > 0:
                sc.append((a.C[t] / hh, a.sym))
        sc.sort(reverse=True)
        return {s: 1.0 / N for _, s in sc[:N]}
    return port_weights(assets, REB_M, choose)


def g_rp(assets, p):
    n, tr = p["n"], p["trend"]

    def choose(t):
        inv = {}
        for a in assets:
            v = a.ind("vol", n)[t]
            if v == v and v > 0:
                inv[a.sym] = (1.0 / v, a)
        tot = sum(x for x, _ in inv.values())
        out = {}
        for s, (x, a) in inv.items():
            if tr and not (a.C[t] > a.ind("sma", tr)[t]):
                continue
            out[s] = x / tot
        return out
    return port_weights(assets, REB_M, choose)


def g_gtaa(assets, p):
    n = p["n"]

    def choose(t):
        av = [a for a in assets if t >= a.s0]
        out = {}
        for a in av:
            if a.C[t] > a.ind("sma", n)[t]:
                out[a.sym] = 1.0 / len(av)
        return out
    return port_weights(assets, REB_M, choose)


def g_gem(assets, p):
    L, risky = p["L"], p["risk"].split("/")
    A = {a.sym: a for a in assets}

    def choose(t):
        best, br = None, -9.0
        for s in risky:
            a = A.get(s)
            if a is None or t - a.s0 <= L:
                continue
            r = a.C[t] / a.C[t - L] - 1.0
            if r > br:
                best, br = s, r
        if best is None:
            return {}
        if br > sum(RF[t - L + 1:t + 1]):
            return {best: 1.0}
        for s in ("AGG", "IEF"):
            if s in A and t >= A[s].s0:
                return {s: 1.0}
        return {}
    return port_weights(assets, REB_M, choose)


def g_6040(assets, p):
    A = {a.sym: a for a in assets}

    def choose(t):
        bond = "AGG" if t >= A["AGG"].s0 else "IEF"
        return {"SPY": 0.6, bond: 0.4}
    return port_weights(assets, REB_M, choose)


G12 = ["SPY", "IWM", "QQQ", "VGK", "EWJ", "EEM", "VNQ", "DBC", "GLD", "TLT", "HYG", "LQD"]
G4 = ["SPY", "EFA", "EEM", "AGG"]
DEFENSIV = ["LQD", "IEF", "SHY"]


def _scores(A, syms, t, fn):
    out = []
    for s in syms:
        if s in A:
            v = fn(A[s], t)
            if v is not None:
                out.append((v, s))
    return out


def _risky_def(A, risky, cf, top, t):
    out = {}
    if cf < 1.0:
        sc = sorted(_scores(A, risky, t, m13612), reverse=True)[:top]
        for _, s in sc:
            out[s] = out.get(s, 0.0) + (1.0 - cf) / len(sc)
    if cf > 0.0:
        d = _scores(A, DEFENSIV, t, m13612)
        if d:
            s = max(d)[1]
            out[s] = out.get(s, 0.0) + cf
    return out


def g_vaa(assets, p):
    A = {a.sym: a for a in assets}
    risky, top, B = (G4 if p["set"] == "G4" else G12), p["top"], p["breite"]

    def choose(t):
        sc = _scores(A, risky, t, m13612)
        if len(sc) < max(2, len(risky) // 2):
            return {}
        bad = sum(1 for v, _ in sc if v <= 0)
        return _risky_def(A, risky, min(1.0, bad / B), top, t)
    return port_weights(assets, REB_M, choose)


def g_daa(assets, p):
    A = {a.sym: a for a in assets}
    top, B = p["top"], p["breite"]

    def choose(t):
        can = _scores(A, ["EEM", "AGG"], t, m13612)
        if len(can) < 2:
            return {}
        bad = sum(1 for v, _ in can if v <= 0)
        return _risky_def(A, G12, min(1.0, bad / B), top, t)
    return port_weights(assets, REB_M, choose)


def g_paa(assets, p):
    A = {a.sym: a for a in assets}
    L, prot, top, bond = p["L"], p["schutz"], p["top"], p["anleihe"]

    def mom(a, t):
        m = a.ind("sma", L)[t]
        return a.C[t] / m - 1.0 if m == m and m > 0 else None

    def choose(t):
        sc = _scores(A, G12, t, mom)
        N = len(sc)
        if N < 6 or bond not in A or t < A[bond].s0:
            return {}
        n = sum(1 for v, _ in sc if v > 0)
        n1 = prot * N / 4.0
        bf = 1.0 if N - n1 <= 0 else min(1.0, max(0.0, (N - n) / (N - n1)))
        pos = sorted([x for x in sc if x[0] > 0], reverse=True)[:top]
        out = {}
        if pos and bf < 1.0:
            for _, s in pos:
                out[s] = (1.0 - bf) / len(pos)
        else:
            bf = 1.0
        out[bond] = out.get(bond, 0.0) + bf
        return out
    return port_weights(assets, REB_M, choose)


HAA_OFF = ["SPY", "IWM", "EFA", "EEM", "VNQ", "DBC", "IEF", "TLT"]


def m4(a, t):
    if t - a.s0 <= 252:
        return None
    C = a.C
    return ((C[t] / C[t - 21] - 1) + (C[t] / C[t - 63] - 1) + (C[t] / C[t - 126] - 1) + (C[t] / C[t - 252] - 1)) / 4.0


def g_haa(assets, p):
    A = {a.sym: a for a in assets}
    top = p["top"]

    def choose(t):
        if "TIP" not in A:
            return {}
        tip = m4(A["TIP"], t)
        if tip is None:
            return {}
        cash = "BIL" if "BIL" in A and t - A["BIL"].s0 > 252 else "SHY"
        safe = _scores(A, ["IEF", cash], t, m4)
        safe_s = max(safe)[1] if safe else None
        out = {}
        if tip > 0:
            sc = sorted(_scores(A, HAA_OFF, t, m4), reverse=True)[:top]
            for v, s in sc:
                tgt = s if v > 0 else safe_s
                if tgt:
                    out[tgt] = out.get(tgt, 0.0) + 1.0 / top
        elif safe_s:
            out[safe_s] = 1.0
        return out
    return port_weights(assets, REB_M, choose)


def g_adm(assets, p):
    A = {a.sym: a for a in assets}
    eq, bond = p["aktien"].split("/"), p["anleihe"]

    def sc(a, t):
        if t - a.s0 <= 126:
            return None
        C = a.C
        return (C[t] / C[t - 21] - 1) + (C[t] / C[t - 63] - 1) + (C[t] / C[t - 126] - 1)

    def choose(t):
        s = _scores(A, eq, t, sc)
        if not s:
            return {}
        v, best = max(s)
        if v > 0:
            return {best: 1.0}
        return {bond: 1.0} if bond in A and t >= A[bond].s0 else {}
    return port_weights(assets, REB_M, choose)


STATIC = {"Permanent Portfolio": {"SPY": .25, "TLT": .25, "GLD": .25, "SHY": .25},
          "All-Weather (vereinfacht)": {"SPY": .30, "TLT": .40, "IEF": .15, "GLD": .075, "DBC": .075},
          "Golden Butterfly": {"SPY": .2, "IWM": .2, "TLT": .2, "SHY": .2, "GLD": .2},
          "3-Fonds (US/Welt/Anleihen)": {"SPY": .4, "EFA": .2, "AGG": .4}}


def g_static(assets, p):
    A = {a.sym: a for a in assets}
    mix, tr = STATIC[p["mischung"]], p["trend"]

    def choose(t):
        out = {}
        for s, w in mix.items():
            a = A.get(s)
            if a is None or t < a.s0:
                continue
            if tr and not (a.C[t] > a.ind("sma", tr)[t]):
                continue
            out[s] = w
        return out
    return port_weights(assets, REB_M, choose)


LEV_RULES = ["immer", "sma50", "sma100", "sma150", "sma200", "sma250", "sma200-band", "ema50/200",
             "vola-regime", "sma200+vola-regime", "vola-ziel-20%"]


def g_lev(assets, p):
    A = {a.sym: a for a in assets}
    base, L, rule = assets[0], p["L"], p["regel"]
    name = levname(base.sym, L)
    if name not in A:
        return {}
    C = base.C
    safe = A.get("IEF") if p["ausweich"] == "IEF" else None
    sma = {n: base.ind("sma", n) for n in (50, 100, 150, 200, 250)}
    e50, e200 = base.ind("ema", 50), base.ind("ema", 200)
    v20, va = base.ind("vol", 20), base.ind("volavg", 20, 252)
    state = [False]

    def sig(t):
        if rule == "immer":
            return 1.0
        if rule.startswith("sma") and rule[3:].isdigit():
            return 1.0 if C[t] > sma[int(rule[3:])][t] else 0.0
        if rule == "sma200-band":
            m = sma[200][t]
            if m != m:
                return 0.0
            if state[0] and C[t] < 0.97 * m:
                state[0] = False
            elif not state[0] and C[t] > 1.03 * m:
                state[0] = True
            return 1.0 if state[0] else 0.0
        if rule == "ema50/200":
            return 1.0 if e50[t] > e200[t] else 0.0
        vr = v20[t] < 1.2 * va[t]
        if rule == "vola-regime":
            return 1.0 if vr else 0.0
        if rule == "sma200+vola-regime":
            return 1.0 if vr and C[t] > sma[200][t] else 0.0
        x = v20[t]
        return min(1.0, 0.20 / (L * x)) if x == x and x > 0 else 0.0

    def choose(t):
        if t < base.s0:
            return {}
        w = sig(t)
        out = {}
        if w > 0:
            out[name] = w
        if safe is not None and w < 1.0 and t >= safe.s0:
            out["IEF"] = 1.0 - w
        return out
    return port_weights(assets, REB_ALL, choose)


def g_mom_ls(assets, p):
    L, k, N = p["L"], p["skip"], p["N"]

    def choose(t):
        sc = sorted((a.C[t - k] / a.C[t - L] - 1.0, a.sym) for a in assets if t - a.s0 > L)
        if len(sc) < 2 * N:
            return {}
        out = {s: -0.5 / N for _, s in sc[:N]}
        out.update({s: 0.5 / N for _, s in sc[-N:]})
        return out
    return port_weights(assets, REB_M if p["reb"] == "M" else REB_W, choose)


def g_rev_ls(assets, p):
    L, N = p["L"], p["N"]

    def choose(t):
        sc = sorted((a.C[t] / a.C[t - L] - 1.0, a.sym) for a in assets if t - a.s0 > L)
        if len(sc) < 2 * N:
            return {}
        out = {s: 0.5 / N for _, s in sc[:N]}
        out.update({s: -0.5 / N for _, s in sc[-N:]})
        return out
    return port_weights(assets, REB_M if p["reb"] == "M" else REB_W, choose)


def g_lowvol_ls(assets, p):
    n, N = p["n"], p["N"]

    def choose(t):
        sc = []
        for a in assets:
            v = a.ind("vol", n)[t]
            if v == v and v > 0:
                sc.append((v, a.sym))
        sc.sort()
        if len(sc) < 2 * N:
            return {}
        out = {s: 0.5 / N for _, s in sc[:N]}
        out.update({s: -0.5 / N for _, s in sc[-N:]})
        return out
    return port_weights(assets, REB_M, choose)


def g_pairs(assets, p):
    A = {a.sym: a for a in assets}
    L, k, e, H, side = p["L"], p["z_rein"], p["z_raus"], p["max_tage"], p["seite"]
    data = []
    for x, y in PAIRS:
        if x not in A or y not in A:
            continue
        a, b = A[x], A[y]
        s0 = max(a.s0, b.s0)
        sp = [NAN] * T
        for t in range(s0, T):
            sp[t] = math.log(a.C[t] / b.C[t])
        data.append((x, y, s0, sp, roll_mean(sp, L, s0), roll_std(sp, L, s0)))
    state = {d[0]: [0, 0] for d in data}

    def choose(t):
        live = [d for d in data if t >= d[2] + L]
        out = {}
        if not live:
            return out
        slot = 1.0 / len(live)
        for x, y, _s0, sp, m, sd in live:
            st = state[x]
            z = (sp[t] - m[t]) / sd[t] if sd[t] == sd[t] and sd[t] > 0 else 0.0
            pos = st[0]
            if pos != 0:
                st[1] += 1
                if (pos == 1 and z >= -e) or (pos == -1 and z <= e) or st[1] >= H:
                    pos = 0
            if pos == 0:
                if z > k:
                    pos, st[1] = -1, 0
                elif z < -k:
                    pos, st[1] = 1, 0
            st[0] = pos
            if pos == 1:                       # x billig: x kaufen (y leerverkaufen)
                out[x] = out.get(x, 0.0) + slot / 2
                if side == "beide":
                    out[y] = out.get(y, 0.0) - slot / 2
            elif pos == -1:                    # y billig: y kaufen (x leerverkaufen)
                out[y] = out.get(y, 0.0) + slot / 2
                if side == "beide":
                    out[x] = out.get(x, 0.0) - slot / 2
        return out
    return port_weights(assets, REB_ALL, choose)


def div_yield(a, t):
    d, c = a.ind("divttm")[t], RAW[a.sym]["RAWC"][t]
    return d / c if d == d and c == c and c > 0 else None


def g_divyield(assets, p):
    N, filt = p["N"], p["filt"]

    def choose(t):
        if filt == "spy200" and not spy_ok(t):
            return {}
        sc = []
        for a in assets:
            y = div_yield(a, t)
            if y is not None and y > 0:
                sc.append((y, a.sym))
        sc.sort(reverse=True)
        return {s: 1.0 / N for _, s in sc[:N]}
    return port_weights(assets, REB_M if p["reb"] == "M" else REB_Y, choose)


def g_divgrowth(assets, p):
    g, filt = p["wachstum"], p["filt"]

    def choose(t):
        if filt == "spy200" and not spy_ok(t):
            return {}
        picks = []
        for a in assets:
            d = a.ind("divttm")
            if t - 252 < a.s0:
                continue
            now, before = d[t], d[t - 252]
            if now == now and before == before and before > 0 and now >= before * (1 + g):
                picks.append(a.sym)
        return {s: 1.0 / len(picks) for s in picks} if picks else {}
    return port_weights(assets, REB_M if p["reb"] == "M" else REB_Y, choose)


def g_divlowvol(assets, p):
    N = p["N"]

    def choose(t):
        vs = []
        for a in assets:
            v, y = a.ind("vol", 252)[t], div_yield(a, t)
            if v == v and y is not None and y > 0:
                vs.append((v, y, a.sym))
        if len(vs) < 4:
            return {}
        vs.sort()
        calm = sorted(vs[:len(vs) // 2], key=lambda x: -x[1])
        return {s: 1.0 / N for _, _, s in calm[:N]}
    return port_weights(assets, REB_M, choose)


NS = {"SEKTOREN": [1, 2, 3, 5], "MULTI": [1, 2, 3, 5], "AKTIEN": [3, 5, 10, 15], "ALLE-KLASSEN": [1, 2, 3, 5],
      "DEVISEN": [1, 2, 3], "ROHSTOFFE": [1, 2, 3]}
XS_UNIS = ["SEKTOREN", "MULTI", "AKTIEN", "ALLE-KLASSEN", "DEVISEN", "ROHSTOFFE"]
PORT = [  # Name, Funktion, Maerkte, Parameter je Markt, Gruppe
    ("Momentum-Rotation", g_mom, XS_UNIS,
     lambda u: [p for p in grid(L=[21, 63, 126, 189, 252], skip=[0, 21], N=NS[u], reb=["M", "W"],
                                filt=["keiner", "spy200", "absolut"]) if p["skip"] < p["L"]], G_ROT),
    ("Momentum/Vola-Rotation", g_momvol, XS_UNIS, lambda u: grid(L=[63, 126, 252], N=NS[u], filt=["keiner", "spy200"]), G_ROT),
    ("Niedrige-Vola-Auswahl", g_lowvol, XS_UNIS, lambda u: grid(n=[21, 63, 126, 252], N=NS[u], filt=["keiner", "spy200"]), G_ROT),
    ("Kurzfrist-Umkehr", g_rev, XS_UNIS, lambda u: grid(L=[5, 10, 21], N=NS[u], reb=["W", "M"], filt=["keiner", "spy200"]), G_ROT),
    ("52-Wochen-Hoch", g_52, XS_UNIS, lambda u: grid(N=NS[u], filt=["keiner", "spy200"]), G_ROT),
    ("Risk-Parity", g_rp, ["SEKTOREN", "MULTI", "ALLE-KLASSEN", "ROHSTOFFE"], lambda u: grid(n=[21, 63, 126], trend=TF), G_ROT),
    ("GTAA (Faber)", g_gtaa, XS_UNIS, lambda u: grid(n=[100, 150, 200, 210, 250]), G_ROT),
    ("Dual-Momentum GEM", g_gem, ["MULTI"], lambda u: grid(L=[63, 126, 189, 252], risk=["SPY/EFA", "SPY/QQQ/EFA"]), G_TAA),
    ("60/40 SPY/AGG", g_6040, ["MULTI"], lambda u: [{}], G_BENCH),
    ("VAA (Keller)", g_vaa, ["TAA"], lambda u: [p for p in grid(set=["G4", "G12"], top=[1, 2, 3, 5], breite=[1, 2, 4])
                                                 if p["top"] <= (4 if p["set"] == "G4" else 12)], G_TAA),
    ("DAA (Keller)", g_daa, ["TAA"], lambda u: grid(top=[2, 3, 6], breite=[1, 2]), G_TAA),
    ("PAA (Keller)", g_paa, ["TAA"], lambda u: grid(L=[126, 252], schutz=[0, 1, 2], top=[3, 6], anleihe=["IEF", "SHY"]), G_TAA),
    ("HAA (Keller)", g_haa, ["TAA"], lambda u: grid(top=[2, 4]), G_TAA),
    ("Accelerating Dual Momentum", g_adm, ["TAA"], lambda u: grid(aktien=["SPY/EFA", "SPY/EFA/EEM", "SPY/QQQ/EFA"],
                                                                  anleihe=["TLT", "IEF", "SHY"]), G_TAA),
    ("Statische Portfolios", g_static, ["TAA"], lambda u: grid(mischung=list(STATIC), trend=TF), G_TAA),
    ("Hebel + Trendfilter", g_lev, ["HEBEL-SPY", "HEBEL-QQQ"], lambda u: grid(L=[1.0, 1.5, 2.0, 3.0], regel=LEV_RULES,
                                                                              ausweich=["cash", "IEF"]), G_LEV),
    ("Momentum marktneutral", g_mom_ls, XS_UNIS, lambda u: [p for p in grid(L=[21, 63, 126, 252], skip=[0, 21], N=NS[u][:3],
                                                                            reb=["M", "W"]) if p["skip"] < p["L"]], G_LS),
    ("Umkehr marktneutral", g_rev_ls, XS_UNIS, lambda u: grid(L=[5, 10, 21], N=NS[u][:3], reb=["W", "M"]), G_LS),
    ("Niedrige Vola marktneutral", g_lowvol_ls, XS_UNIS, lambda u: grid(n=[63, 252], N=NS[u][:3]), G_LS),
    ("Paarhandel", g_pairs, ["PAARE"], lambda u: grid(L=[20, 60, 120], z_rein=[1.5, 2.0, 2.5], z_raus=[0.0, 0.5],
                                                      max_tage=[20, 60], seite=["beide", "nur-long"]), G_PAIR),
    ("Hohe Dividendenrendite", g_divyield, ["AKTIEN"], lambda u: grid(N=[5, 10, 15], reb=["M", "J"], filt=["keiner", "spy200"]), G_DIV),
    ("Dividenden-Wachstum", g_divgrowth, ["AKTIEN"], lambda u: grid(wachstum=[0.0, 0.05, 0.10], reb=["M", "J"], filt=["keiner", "spy200"]), G_DIV),
    ("Dividende + niedrige Vola", g_divlowvol, ["AKTIEN"], lambda u: grid(N=[5, 10, 15]), G_DIV),
]
BENCH_FAMS = ("Kaufen & Halten", "60/40 SPY/AGG")

FAMILY_DESC = {
    "Kaufen & Halten": "Einfach kaufen und liegen lassen (Vergleichsmaßstab).",
    "SMA-Trend": "Investiert, solange der Kurs über seinem gleitenden Durchschnitt der letzten n Tage liegt.",
    "SMA-Kreuz": "Investiert, solange der schnelle über dem langsamen gleitenden Durchschnitt liegt.",
    "EMA-Kreuz": "Wie SMA-Kreuz, mit exponentiell gewichteten Durchschnitten.",
    "Donchian-Ausbruch": "Kauf bei neuem n-Tage-Hoch, Verkauf bei neuem m-Tage-Tief (Turtle-Prinzip).",
    "Zeitreihen-Momentum": "Investiert, wenn der Kurs höher ist als vor n Tagen.",
    "MACD": "Investiert, wenn die MACD-Linie über ihrer Signallinie bzw. über null liegt.",
    "Keltner-Ausbruch": "Kauf, wenn der Kurs k ATR über dem Durchschnitt schließt; Verkauf unter dem Durchschnitt.",
    "Chandelier-Trend": "Kauf bei n-Tage-Hoch, nachgezogener Stop k ATR unter dem Höchstkurs.",
    "ADX-Trend": "Kauf bei starkem Aufwärtstrend (ADX über Schwelle und +DI über -DI).",
    "Parabolic-SAR": "Folgt den Aufwärtsphasen des Parabolic-SAR-Indikators.",
    "Ichimoku": "Investiert, wenn der Kurs über der Ichimoku-Wolke liegt.",
    "Regressions-Trend": "Investiert, wenn die Regressionsgerade der letzten n Tage steigt.",
    "Bollinger-Ausbruch": "Kauf über dem oberen Bollinger-Band, Verkauf unter dem Durchschnitt.",
    "RSI-Rücksetzer": "Kauf nach einem Rücksetzer (RSI unter x), Verkauf bei Erholung.",
    "ConnorsRSI": "Kauf bei sehr niedrigem ConnorsRSI (kombiniertes Überverkauft-Maß).",
    "Bollinger-Rücksetzer": "Kauf unter dem unteren Bollinger-Band, Verkauf bei Rückkehr zur Mitte.",
    "IBS-Rücksetzer": "Kauf, wenn der Kurs nahe dem Tagestief schließt (Internal Bar Strength).",
    "Abwärtstage": "Kauf nach N Verlusttagen in Folge.",
    "N-Tage-Tief": "Kauf, wenn der Kurs auf einem n-Tage-Tief schließt.",
    "Williams-%R": "Kauf, wenn Williams-%R extrem überverkauft ist.",
    "CCI-Rücksetzer": "Kauf bei stark negativem CCI, Verkauf über null.",
    "Gap-Fade (Tageshandel)": "Kauf zur Eröffnung nach einer Kurslücke nach unten, Verkauf zum Schluss.",
    "Gap-Momentum (Tageshandel)": "Kauf zur Eröffnung nach einer Kurslücke nach oben, Verkauf zum Schluss.",
    "Vola-Ausbruch Williams (Tageshandel)": "Kauf, wenn der Kurs k-mal die Vortagesspanne über die Eröffnung steigt; Verkauf zum Schluss.",
    "Noise-Band (Tageshandel)": "Kauf beim Ausbruch über das normale Tagesrauschen; Verkauf zum Schluss.",
    "Overnight": "Nur über Nacht halten: Kauf zum Schluss, Verkauf zur Eröffnung.",
    "Monatswechsel": "Nur an den letzten bzw. ersten Handelstagen des Monats investiert.",
    "Wochentag": "Nur an bestimmten Wochentagen investiert (0 = Montag).",
    "Vor-Feiertag": "Nur am Handelstag vor Börsenfeiertagen investiert.",
    "Saison Nov-Apr": "Nur von November bis April investiert („Sell in May“).",
    "Optionsverfall": "Investiert in der Woche des monatlichen Optionsverfalls, in der Woche danach oder außerhalb davon.",
    "Jahresend-Rally": "Nur in den letzten Dezember- und ersten Januartagen bzw. im ganzen Dezember investiert.",
    "Januar-Barometer": "Rest des Jahres investiert, wenn die ersten 5 Januartage positiv waren.",
    "Nur Januar": "Nur im Januar investiert (Januar-Effekt).",
    "Wahlzyklus": "Investiert nach dem US-Präsidentschafts-Wahlzyklus.",
    "VIX-Filter": "Investiert abhängig vom Angstbarometer VIX (z. B. nur bei ruhigem Markt oder nach Panik).",
    "Vola-Ziel": "Positionsgröße so, dass die Schwankung etwa dem Ziel entspricht.",
    "Vola-Regime": "Investiert, solange die aktuelle Schwankung nicht deutlich über ihrem Jahresschnitt liegt.",
    "Trend Long-Short": "Über dem gleitenden Durchschnitt kaufen, darunter leerverkaufen.",
    "Zeitreihen-Momentum Long-Short": "Kaufen, wenn höher als vor n Tagen, sonst leerverkaufen.",
    "Donchian Long-Short": "Kauf bei n-Tage-Hoch, Leerverkauf bei n-Tage-Tief (immer im Markt).",
    "RSI Long-Short": "Kauf bei überverkauft, Leerverkauf bei überkauft, raus bei RSI 50.",
    "Nach Quartalszahlen (PEAD)": "Nach starker Kursreaktion auf Quartalszahlen H Tage in Reaktionsrichtung (oder dagegen) handeln.",
    "Vor Quartalszahlen": "N Tage vor dem Zahlentermin kaufen (Termin wird als vorab bekannt angenommen).",
    "ML: lineares Modell": "Lineares Prognosemodell aus 10 Indikatoren, wöchentlich nur mit Vergangenheitsdaten neu geschätzt.",
    "ML: k-nächste Nachbarn": "Sucht die 25 bzw. 100 ähnlichsten früheren Tage und folgt deren Entwicklung.",
    "Momentum-Rotation": "Kauft monatlich bzw. wöchentlich die stärksten Werte der letzten L Tage.",
    "Momentum/Vola-Rotation": "Wie Momentum-Rotation, aber Rendite geteilt durch Schwankung.",
    "Niedrige-Vola-Auswahl": "Kauft die ruhigsten Werte.",
    "Kurzfrist-Umkehr": "Kauft die größten Verlierer der letzten Tage.",
    "52-Wochen-Hoch": "Kauft Werte nahe ihrem 52-Wochen-Hoch.",
    "Risk-Parity": "Gewichtet alle Werte umgekehrt zu ihrer Schwankung.",
    "GTAA (Faber)": "Jeden Wert nur über seinem gleitenden Durchschnitt halten (monatlich geprüft).",
    "Dual-Momentum GEM": "Stärkster Aktienmarkt, wenn besser als Zinsen; sonst Anleihen.",
    "60/40 SPY/AGG": "60 % Aktien, 40 % Anleihen, monatlich ausgeglichen (Vergleichsmaßstab).",
    "VAA (Keller)": "Vigilant Asset Allocation: Momentum-Rotation, bei schwachen Märkten in sichere Anleihen.",
    "DAA (Keller)": "Defensive Asset Allocation: Schwellenländer und Anleihen als Frühwarnsignal.",
    "PAA (Keller)": "Protective Asset Allocation: Anleihenanteil steigt mit der Zahl schwacher Märkte.",
    "HAA (Keller)": "Hybrid Asset Allocation: inflationsgeschützte Anleihen (TIP) als Frühwarnsignal.",
    "Accelerating Dual Momentum": "Stärkster Aktienmarkt nach 1-, 3- und 6-Monats-Momentum, sonst Anleihen.",
    "Statische Portfolios": "Feste Mischungen (Permanent Portfolio, All-Weather, Golden Butterfly, 3-Fonds), optional mit Trendfilter.",
    "Hebel + Trendfilter": "S&P 500 bzw. Nasdaq-100 mit 1- bis 3-fachem Hebel, nur wenn Trend oder Volatilität passt.",
    "Momentum marktneutral": "Die stärksten Werte kaufen, die schwächsten leerverkaufen.",
    "Umkehr marktneutral": "Die Verlierer kaufen, die Gewinner leerverkaufen.",
    "Niedrige Vola marktneutral": "Ruhige Werte kaufen, schwankungsstarke leerverkaufen.",
    "Paarhandel": "Bei ungewöhnlichem Abstand zweier verwandter Werte den billigeren kaufen (und den teureren leerverkaufen).",
    "Hohe Dividendenrendite": "Kauft die Aktien mit der höchsten Dividendenrendite (Dogs-of-the-Dow-Prinzip bei jährlichem Wechsel).",
    "Dividenden-Wachstum": "Kauft Aktien, die ihre Dividende im letzten Jahr erhöht haben.",
    "Dividende + niedrige Vola": "Höchste Dividendenrendite unter der ruhigeren Hälfte der Aktien.",
}


# ======================= Backtest-Motor =======================
def add_pos(R, E, NE, a, S, slot, cost):
    """S[t] = Zielgewicht (negativ = Leerverkauf), entschieden zum Schluss von Tag t, ausgefuehrt zur Eroeffnung t+1."""
    O, C = a.O, a.C
    w2 = w1 = 0.0
    bd = BORROW / 252.0
    for t in range(a.s0, T):
        if w1 != 0.0 or w2 != 0.0:
            R[t] += w2 * (O[t] / C[t - 1] - 1.0) + w1 * (C[t] / O[t] - 1.0) - cost * abs(w1 - w2)
            if w1 < 0.0:
                R[t] += w1 * bd
                E[t] -= w1
            else:
                E[t] += w1
            if w2 == 0.0:
                NE[t] += 1
        s = S[t]
        w2, w1 = w1, (s * slot[t] if slot is not None else s) if s else 0.0


def add_intra(R, E, NE, a, G, RET, slot, cost):
    for t in range(a.s0 + 1, T):
        if G[t]:
            w = G[t] * slot[t - 1]
            R[t] += w * (RET[t] - 2 * cost)
            E[t] += w
            NE[t] += 1


def add_moc(R, E, NE, a, Hd, slot, cost):
    C, wp = a.C, 0.0
    for t in range(a.s0 + 1, T):
        w = Hd[t] * slot[t - 1]
        if w or wp:
            R[t] += w * (C[t] / C[t - 1] - 1.0) - cost * abs(w - wp)
            E[t] += w
            if w and not wp:
                NE[t] += 1
        wp = w


def add_on(R, E, NE, a, OS, slot, cost):
    O, C = a.O, a.C
    for t in range(a.s0 + 1, T):
        if OS[t - 1]:
            w = OS[t - 1] * slot[t - 1]
            R[t] += w * (O[t] / C[t - 1] - 1.0 - 2 * cost)
            E[t] += w
            NE[t] += 1


def metrics(R, E, NE, i0, i1):
    n = i1 - i0
    if n < 126:
        return None
    eq = peak = 1.0
    mdd = s = ss = dn = 0.0
    under = maxunder = 0
    sm = smm = sr = srr = smr = 0.0
    mon, mc, ex, tr = [], 1.0, 0.0, 0
    for t in range(i0, i1):
        r = R[t]
        eq *= 1.0 + r
        if eq >= peak:
            peak, under = eq, 0
        else:
            under += 1
            if under > maxunder:
                maxunder = under
            dd = 1.0 - eq / peak
            if dd > mdd:
                mdd = dd
        x = r - RF[t]
        s += x
        ss += x * x
        if x < 0:
            dn += x * x
        m = SPYR[t]
        sm += m
        smm += m * m
        sr += r
        srr += r * r
        smr += m * r
        mc *= 1.0 + r
        if REB_M[t] or t == i1 - 1:
            mon.append(mc - 1.0)
            mc = 1.0
        ex += E[t]
        tr += NE[t]
    mu = s / n
    var = ss / n - mu * mu
    sh = mu / math.sqrt(var) * math.sqrt(252) if var > 1e-18 else 0.0
    so = mu / math.sqrt(dn / n) * math.sqrt(252) if dn > 1e-18 else 0.0
    vr = srr / n - (sr / n) ** 2
    vm = smm / n - (sm / n) ** 2
    cov = smr / n - (sm / n) * (sr / n)
    yrs = n / 252.0
    return {"cagr": round(eq ** (1 / yrs) - 1, 4) if eq > 0 else -1.0, "total": round(eq - 1, 4),
            "vol": round(math.sqrt(vr * 252), 4) if vr > 0 else 0.0, "sharpe": round(sh, 3), "sortino": round(so, 3),
            "mdd": round(mdd, 4), "dd_tage": maxunder, "expo": round(ex / n, 3), "trades": tr, "tpj": round(tr / yrs, 1),
            "beta": round(cov / vm, 3) if vm > 0 else 0.0,
            "korr": round(cov / math.sqrt(vm * vr), 3) if vm > 0 and vr > 0 else 0.0,
            "mon_pos": round(sum(1 for v in mon if v > 0) / len(mon), 3) if mon else None, "von": None}


def live_metrics(R, E, NE, i0, i1):
    """Papier-Test: Ergebnis seit dem Start (Schlusskurs vor dem ersten Live-Tag) - ohne Mindestlaenge."""
    n = i1 - i0
    if n <= 0:
        return None
    eq = peak = 1.0
    mdd = s = ss = ex = 0.0
    tr = 0
    for t in range(i0, i1):
        r = R[t]
        eq *= 1.0 + r
        if eq > peak:
            peak = eq
        dd = 1.0 - eq / peak
        if dd > mdd:
            mdd = dd
        x = r - RF[t]
        s += x
        ss += x * x
        ex += E[t]
        tr += NE[t]
    sh = None
    if n >= 20:
        mu, var = s / n, ss / n - (s / n) ** 2
        sh = round(mu / math.sqrt(var) * math.sqrt(252), 3) if var > 1e-18 else 0.0
    return {"tage": n, "rendite": round(eq - 1, 5), "mdd": round(mdd, 4), "sharpe": sh, "expo": round(ex / n, 3),
            "trades": tr, "von": DATES[i0], "bis": DATES[i1 - 1]}


def period_bounds(u, name):
    i0, i1 = PI[name]
    us = U_START.get(u)
    if us is None:
        return None
    if us + 252 > i0:
        i0 = us + 252
    return (i0, i1) if i1 - i0 >= 252 else None


def make_row(fam, grp, u, p, cost, R, E, NE):
    for t in range(T):
        e = E[t]
        if e < 1.0:
            R[t] += (1.0 - e) * RF[t]
    row = {"fam": fam, "grp": grp, "uni": u, "p": p, "cost": cost}
    for name, _, _ in PERIODS:
        b = period_bounds(u, name)
        m = metrics(R, E, NE, b[0], b[1]) if b else None
        if m and b[0] != PI[name][0]:
            m["von"] = DATES[b[0]]
        row[name] = m
    jahre = {}
    gb = period_bounds(u, "G")
    if gb:
        eq, cur = 1.0, YEAR[gb[0]]
        for t in range(gb[0], T):
            if YEAR[t] != cur:
                jahre[str(cur)] = round(eq - 1, 4)
                eq, cur = 1.0, YEAR[t]
            eq *= 1.0 + R[t]
        jahre[str(cur)] = round(eq - 1, 4)
    row["jahre"] = jahre
    row["LIVE"] = live_metrics(R, E, NE, LIVE_I0, T) if LIVE_I0 is not None else None
    return row


def run_task(task, cost=None, only=None):
    global MKT
    kind, i, u = task
    if cost is None:
        cost = uni_cost(u)
    MKT = {s: Asset(s) for s in ("SPY", "QQQ", "^VIX", "^VIX3M") if s in RAW}
    assets = [Asset(s) for s in UNIVERSES[u] if s in RAW]
    rows = []
    if not assets:
        return rows
    if kind == "T":
        fam, fn, params, grp, _unis = TIMING[i]
        slot = SLOTS[u]
        for p in params:
            if only is not None and p != only:
                continue
            R, E, NE = [0.0] * T, [0.0] * T, [0] * T
            for a in assets:
                res = fn(a, p)
                if res[0] == "pos":
                    add_pos(R, E, NE, a, res[1], slot, cost)
                elif res[0] == "intra":
                    add_intra(R, E, NE, a, res[1], res[2], slot, cost)
                elif res[0] == "moc":
                    add_moc(R, E, NE, a, res[1], slot, cost)
                else:
                    add_on(R, E, NE, a, res[1], slot, cost)
            rows.append(make_row(fam, grp, u, p, cost, R, E, NE))
    else:
        fam, fn, _unis, gridf, grp = PORT[i]
        for p in gridf(u):
            if only is not None and p != only:
                continue
            R, E, NE = [0.0] * T, [0.0] * T, [0] * T
            W = fn(assets, p)
            for a in assets:
                w = W.get(a.sym)
                if w and any(w):
                    add_pos(R, E, NE, a, w, None, cost)
            rows.append(make_row(fam, grp, u, p, cost, R, E, NE))
    return rows


def task_name(task):
    return TIMING[task[1]][0] if task[0] == "T" else PORT[task[1]][0]


def build_tasks(quick=False):
    tasks = []
    for i, (fam, fn, params, grp, unis) in enumerate(TIMING):
        if grp == G_QZ and not EVENTS:
            continue                       # ohne SEC-Termine keine Quartalszahlen-Strategien
        for u in unis:
            if U_START.get(u) is not None:
                tasks.append(("T", i, u, len(params)))
    for i, (fam, fn, unis, gridf, grp) in enumerate(PORT):
        for u in unis:
            if U_START.get(u) is not None:
                tasks.append(("P", i, u, len(gridf(u))))
    if quick:
        tasks = [t for t in tasks if t[2] in ("SPY", "SEKTOREN", "TAA", "HEBEL-QQQ", "PAARE", "OPT-PUT", "VOL-SVXY",
                                               "KRYPTO", "AKTIEN", "DEVISEN") and t[3] <= 40]
    weight = {u: len(s) for u, s in UNIVERSES.items()}
    heavy = {"ML: k-nächste Nachbarn": 400, "ML: lineares Modell": 20}
    tasks.sort(key=lambda t: -t[3] * weight[t[2]] * heavy.get(task_name(t), 1))
    return [t[:3] for t in tasks], sum(t[3] for t in tasks)


def find_task(fam, uni):
    for i, row in enumerate(TIMING):
        if row[0] == fam:
            return ("T", i, uni)
    for i, row in enumerate(PORT):
        if row[0] == fam:
            return ("P", i, uni)


# ======================= Intraday-Studie (Stundenkurse) =======================
INTRA_SYMS = ["SPY", "QQQ", "IWM", "DIA"]


def ny_offset(utc):
    y = utc.year

    def nth_sun(m, n):
        d = dt.datetime(y, m, 1)
        return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1))
    start = nth_sun(3, 2) + dt.timedelta(hours=7)
    end = nth_sun(11, 1) + dt.timedelta(hours=6)
    return -4 if start <= utc < end else -5


def load_hourly(refresh=False):
    if os.path.exists(HOURLY_CACHE) and not refresh:
        with open(HOURLY_CACHE, "rb") as f:
            return pickle.load(f)
    u = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    today_ny = (u + dt.timedelta(hours=ny_offset(u))).date().isoformat()
    out = {}
    for sym in INTRA_SYMS:
        try:
            res = _get("https://query2.finance.yahoo.com/v8/finance/chart/%s?range=730d&interval=60m" % sym)
        except Exception as e:
            print("  %s Stundenkurse FEHLEN: %s" % (sym, e))
            continue
        q = res["indicators"]["quote"][0]
        days = collections.OrderedDict()
        for i, ts in enumerate(res.get("timestamp") or []):
            o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
            if None in (o, h, l, c):
                continue
            uu = dt.datetime.fromtimestamp(ts, dt.timezone.utc).replace(tzinfo=None)
            n = uu + dt.timedelta(hours=ny_offset(uu))
            if not (dt.time(9, 30) <= n.time() < dt.time(16, 0)):
                continue
            d = n.date().isoformat()
            if d >= today_ny:
                continue
            days.setdefault(d, []).append((n.strftime("%H:%M"), o, h, l, c))
        out[sym] = collections.OrderedDict((d, sorted(b)) for d, b in days.items())
        time.sleep(0.5)
    with open(HOURLY_CACHE, "wb") as f:
        pickle.dump(out, f)
    return out


def run_noise(days, p, cost):
    res, hist, prev_close = [], collections.defaultdict(list), None
    n, mult = p["n"], p["mult"]
    for d, b in days.items():
        m, r, ntr = len(b), 0.0, 0
        if prev_close is not None and m >= 4:
            op = b[0][1]
            ub0, lb0 = max(op, prev_close), min(op, prev_close)
            pos, entry = 0, 0.0
            for k in range(m - 1):
                h = hist[k][-n:]
                if len(h) < n:
                    continue
                sig = sum(h) / n
                px = b[k][4]
                ub, lb = ub0 * (1 + mult * sig), lb0 * (1 - mult * sig)
                if pos == 0:
                    if px > ub:
                        pos, entry, ntr = 1, px, ntr + 1
                    elif p["seite"] == "long-short" and px < lb:
                        pos, entry, ntr = -1, px, ntr + 1
                elif p["exit"] == "band-zurueck":
                    if pos == 1 and px < ub:
                        r += px / entry - 1 - 2 * cost
                        pos = 0
                    elif pos == -1 and px > lb:
                        r += -(px / entry - 1) - 2 * cost
                        pos = 0
            if pos != 0:
                r += pos * (b[m - 1][4] / entry - 1) - 2 * cost
        res.append((d, r, ntr))
        if m >= 2:
            op = b[0][1]
            for k in range(m - 1):
                hist[k].append(abs(b[k][4] / op - 1))
        prev_close = b[-1][4]
    return res


def run_orb(days, p, cost):
    res = []
    for d, b in days.items():
        m, r, ntr = len(b), 0.0, 0
        if m >= 3:
            rh, rl = b[0][2], b[0][3]
            stop = rl if p["stop"] == "tief" else (rh + rl) / 2
            for k in range(1, m - 1):
                if b[k][4] > rh:
                    e = b[k][4]
                    risk = e - stop
                    if risk <= 0:
                        break
                    tgt = e + p["ziel_R"] * risk if p["ziel_R"] else None
                    out = None
                    for j in range(k + 1, m):
                        if b[j][3] <= stop:
                            out = stop
                            break
                        if tgt and b[j][2] >= tgt:
                            out = tgt
                            break
                    if out is None:
                        out = b[m - 1][4]
                    r, ntr = out / e - 1 - 2 * cost, 1
                    break
        res.append((d, r, ntr))
    return res


def run_imom(days, p, cost):
    res, prev = [], None
    for d, b in days.items():
        m, r, ntr = len(b), 0.0, 0
        if prev is not None and m >= 3:
            ref = b[0][4] if p["signal"] == "erste-stunde" else b[m - 2][4]
            s = ref / prev - 1
            last = b[m - 1][4] / b[m - 2][4] - 1
            if s > 0:
                r, ntr = last - 2 * cost, 1
            elif s < 0 and p["seite"] == "long-short":
                r, ntr = -last - 2 * cost, 1
        res.append((d, r, ntr))
        prev = b[-1][4]
    return res


def run_bh_intra(days, p, cost):
    res, prev = [], None
    for d, b in days.items():
        c = b[-1][4]
        res.append((d, c / prev - 1 if prev else 0.0, 0))
        prev = c
    return res


INTRA = ([("Noise-Area (1h)", run_noise, dict(n=n, mult=mu, seite=s, exit=e))
          for n in (7, 14, 21) for mu in (0.5, 0.75, 1.0, 1.25, 1.5)
          for s in ("nur-long", "long-short") for e in ("tagesende", "band-zurueck")]
         + [("ORB erste Stunde", run_orb, dict(stop=s, ziel_R=z)) for s in ("tief", "mitte") for z in (0, 2)]
         + [("Intraday-Momentum letzte 30 Min", run_imom, dict(signal=s, seite=e))
            for s in ("erste-stunde", "bis-15:30") for e in ("nur-long", "long-short")])


def imetrics(res):
    n = len(res)
    if n < 20:
        return None
    rs = [r for _, r, _ in res]
    mu = sum(rs) / n
    var = sum((x - mu) ** 2 for x in rs) / n
    eq, peak, mdd = 1.0, 1.0, 0.0
    for x in rs:
        eq *= 1 + x
        peak = max(peak, eq)
        mdd = max(mdd, 1 - eq / peak)
    return {"sharpe": round(mu / math.sqrt(var) * math.sqrt(252), 2) if var > 0 else 0.0,
            "rendite": round(eq - 1, 4), "mdd": round(mdd, 4), "trades": sum(k for _, _, k in res)}


def intraday_study(hourly):
    rows = []
    for sym, days in hourly.items():
        if len(days) < 100:
            continue
        keys = list(days)
        half = len(keys) // 2
        for fam, fn, p in INTRA + [("Kaufen & Halten", run_bh_intra, {})]:
            res = fn(days, p, COST)
            rows.append({"fam": fam, "sym": sym, "p": p, "train": imetrics(res[:half]), "test": imetrics(res[half:]),
                         "von": keys[0], "mitte": keys[half], "bis": keys[-1]})
    return rows


# ======================= Auswertung =======================
def fmt_p(p):
    return ", ".join("%s=%s" % (k, "/".join(map(str, v)) if isinstance(v, (list, tuple)) else v) for k, v in p.items()) or "-"


def spearman(x, y):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        for r, i in enumerate(order):
            rk[i] = float(r)
        return rk
    rx, ry = ranks(x), ranks(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    vy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return cov / (vx * vy) if vx and vy else 0.0


def luck_sharpe(n, years):
    if n < 2:
        return 0.0
    z = math.sqrt(2 * math.log(n))
    return (z - (math.log(math.log(n)) + math.log(4 * math.pi)) / (2 * z)) / math.sqrt(years)


def distinct(lst, n):
    seen, out = set(), []
    for r in lst:
        k = (r["fam"], r["uni"])
        if k not in seen:
            seen.add(k)
            out.append(r)
            if len(out) == n:
                break
    return out


def analyse(rows):
    for k, r in enumerate(rows, 1):
        r["id"] = k
        r["score"] = None
    bench = [r for r in rows if r["fam"] in BENCH_FAMS]
    spy = next(r for r in bench if r["fam"] == "Kaufen & Halten" and r["uni"] == "SPY")
    spy_c = spy["C"]["sharpe"]
    cand = [r for r in rows if r["fam"] not in BENCH_FAMS]
    elig = [r for r in cand if r["A"] and r["B"] and r["C"] and r["A"]["trades"] >= 5 and r["B"]["trades"] >= 5]
    for r in elig:
        r["score"] = min(r["A"]["sharpe"], r["B"]["sharpe"])
    elig.sort(key=lambda r: -r["score"])
    rc = sorted([r for r in elig if r["G"] and r["G"]["expo"] >= 0.3], key=lambda r: -min(r["A"]["cagr"], r["B"]["cagr"]))
    short = sorted([r for r in cand if not r["A"] and r["B"] and r["C"] and r["B"]["trades"] >= 5],
                   key=lambda r: -r["B"]["sharpe"])

    def best_by(keyf):
        groups = collections.OrderedDict()
        for r in cand:
            groups.setdefault(keyf(r), []).append(r)
        out = []
        for k, lst in groups.items():
            el = [r for r in lst if r["score"] is not None]
            if el:
                best = max(el, key=lambda r: r["score"])
            else:
                bl = [r for r in lst if r["B"]]
                best = max(bl, key=lambda r: r["B"]["sharpe"]) if bl else None
            beat = sum(1 for r in lst if r["C"] and r["C"]["sharpe"] > spy_c)
            out.append({"key": k, "n": len(lst), "best": best, "beat": beat, "nur_bc": not el})
        return out
    sc = [r["score"] for r in elig]
    cs = [r["C"]["sharpe"] for r in elig]
    yrs_ab = (PI["AB"][1] - PI["AB"][0]) / 252.0
    med = lambda v: sorted(v)[len(v) // 2] if v else 0.0
    return {"spy": spy, "bench": bench, "elig": elig, "top": distinct(elig, 25), "topr": distinct(rc, 25),
            "short": distinct(short, 40), "by_group": best_by(lambda r: r["grp"]), "by_market": best_by(lambda r: r["uni"]),
            "rho": spearman(sc, cs) if len(elig) > 2 else 0.0,
            "beat50": sum(1 for r in elig[:50] if r["C"]["sharpe"] > spy_c),
            "beat_all": sum(1 for r in cand if r["C"] and r["C"]["sharpe"] > spy_c),
            "n_cand": len(cand), "luck": luck_sharpe(len(elig), yrs_ab), "years_ab": yrs_ab,
            "med_top50": med([r["C"]["sharpe"] for r in elig[:50]]), "med_all": med(cs)}


def report(rows, ana, intra):
    out = []

    def P(s=""):
        print(s, flush=True)
        out.append(s)
    spy = ana["spy"]
    pc = lambda v: "%.1f %%" % (100 * v) if v is not None else "-"
    P("# Strategie-Labor v2: Ergebnis\n")
    P("Kurse bis %s. **%d Varianten**, %d davon mit Auswahl-Zeitraum A+B, %d nur mit B+C (kurze Historie).\n"
      % (DATES[-1], len(rows), len(ana["elig"]), len([r for r in rows if not r["A"] and r["B"]])))
    P("SPY halten im Test (2020-heute): %s p.a., Sharpe %.2f, max. Verlust -%s.\n"
      % (pc(spy["C"]["cagr"]), spy["C"]["sharpe"], pc(spy["C"]["mdd"])))
    P("## Top 10 robust (Rang = min(Sharpe A, Sharpe B), geprueft im Test C)\n")
    P("| # | Strategie | Markt | Parameter | Sharpe A | Sharpe B | Sharpe C | Rendite C | Max. Verlust C | Sharpe C teuer |")
    P("|---|---|---|---|---|---|---|---|---|---|")
    for k, r in enumerate(ana["top"][:10], 1):
        c, h = r["C"], r.get("C_teuer")
        P("| %d | %s | %s | %s | %.2f | %.2f | **%.2f** | %s | -%s | %s |" % (
            k, r["fam"], r["uni"], fmt_p(r["p"]), r["A"]["sharpe"], r["B"]["sharpe"], c["sharpe"], pc(c["cagr"]),
            pc(c["mdd"]), "%.2f" % h["sharpe"] if h else "-"))
    P("\n## Top 10 Rendite (Rang = min(Rendite A, Rendite B), mind. 30 % investiert)\n")
    P("| # | Strategie | Markt | Parameter | Rendite A | Rendite B | Rendite C | Max. Verlust C | Sharpe C |")
    P("|---|---|---|---|---|---|---|---|---|")
    for k, r in enumerate(ana["topr"][:10], 1):
        P("| %d | %s | %s | %s | %s | %s | **%s** | -%s | %.2f |" % (
            k, r["fam"], r["uni"], fmt_p(r["p"]), pc(r["A"]["cagr"]), pc(r["B"]["cagr"]), pc(r["C"]["cagr"]),
            pc(r["C"]["mdd"]), r["C"]["sharpe"]))
    P("\n## Beste je Gruppe\n")
    P("| Gruppe | Varianten | Beste | Markt | Sharpe C | Rendite C | Max. Verlust C | schlagen SPY (Sharpe C) |")
    P("|---|---|---|---|---|---|---|---|")
    for g in ana["by_group"]:
        b = g["best"]
        if b and b["C"]:
            P("| %s | %d | %s%s | %s | %.2f | %s | -%s | %d |" % (g["key"], g["n"], b["fam"], " (nur B/C)" if g["nur_bc"] else "",
                                                               b["uni"], b["C"]["sharpe"], pc(b["C"]["cagr"]), pc(b["C"]["mdd"]), g["beat"]))
    P("\n## Verlaesslichkeit\n")
    P("- Zusammenhang Auswahl-Rang <-> Test (Spearman): **%.2f**" % ana["rho"])
    P("- Von den 50 besten der Auswahl schlagen im Test %d die Sharpe von SPY (%.2f)." % (ana["beat50"], spy["C"]["sharpe"]))
    P("- Alle Varianten: %d von %d schlagen SPY im Test (Sharpe)." % (ana["beat_all"], ana["n_cand"]))
    P("- Median-Sharpe im Test: Top-50 der Auswahl %.2f, alle %.2f." % (ana["med_top50"], ana["med_all"]))
    P("- Gluecks-Schwelle: bei %d Varianten waere die beste Sharpe ueber %.0f Jahre allein durch Zufall etwa %.2f."
      % (len(ana["elig"]), ana["years_ab"], ana["luck"]))
    if intra:
        cand = sorted([r for r in intra if r["fam"] != "Kaufen & Halten" and r["train"] and r["train"]["trades"] >= 20],
                      key=lambda r: -r["train"]["sharpe"])
        P("\n## Intraday (Stundenkurse, ~2 Jahre)\n")
        for r in cand[:5]:
            P("- %s %s (%s): Sharpe Auswahl %.2f, Test %.2f, Rendite Test %s" % (
                r["fam"], r["sym"], fmt_p(r["p"]), r["train"]["sharpe"], r["test"]["sharpe"], pc(r["test"]["rendite"])))
        for r in intra:
            if r["fam"] == "Kaufen & Halten":
                P("- Kaufen & Halten %s: Rendite Test %s" % (r["sym"], pc(r["test"]["rendite"])))
    return out


def pkey(fam, uni, p):
    return "%s|%s|%s" % (fam, uni, json.dumps(p, sort_keys=True))


def paper_list(rows, ana, live_start):
    """Papier-Test-Liste: am Start eingefroren (lab_papiertest.json) und danach nie mehr veraendert,
    damit spaeter niemand im Nachhinein die Gewinner aussucht."""
    data = read_json(PAPER_FILE)
    if not data or data.get("start") != live_start:
        def pick(r):
            return {"fam": r["fam"], "uni": r["uni"], "p": r["p"]}
        items = [dict(liste="robust", rang=k + 1, **pick(r)) for k, r in enumerate(ana["top"])]
        items += [dict(liste="rendite", rang=k + 1, **pick(r)) for k, r in enumerate(ana["topr"])]
        bench = [r for r in ana["bench"] if r["uni"] in ("SPY", "QQQ") or r["fam"] != "Kaufen & Halten"]
        items += [dict(liste="vergleich", rang=k + 1, **pick(r)) for k, r in enumerate(bench)]
        data = {"start": live_start, "eingefroren": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "strategien": items}
        with open(PAPER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)
    idx = {pkey(r["fam"], r["uni"], r["p"]): r for r in rows}
    return data, [(it, idx.get(pkey(it["fam"], it["uni"], it["p"]))) for it in data["strategien"]]


def live_report(rows, ana, paper, live_start):
    out = ["# Papier-Test aller Strategien", ""]
    spy = ana["spy"].get("LIVE")
    if not spy:
        out.append("Start: %s. Noch keine Handelstage seit dem Start - erste Ergebnisse nach dem ersten Handelstag." % live_start)
        return out
    pc = lambda v: "%+.2f %%" % (100 * v)
    live = [r for r in rows if r.get("LIVE") and r["fam"] not in BENCH_FAMS]
    beat = sum(1 for r in live if r["LIVE"]["rendite"] > spy["rendite"])
    out += ["Start %s (gerechnet ab Schlusskurs des Vortags), Stand %s: **%d Handelstage**. Gleiche Regeln, Kosten und "
            "Ausfuehrung wie im Backtest, nur mit neuen Kursen." % (spy["von"], spy["bis"], spy["tage"]), "",
            "- S&P 500 halten seit Start: **%s**" % pc(spy["rendite"]),
            "- Varianten mit mehr Rendite als SPY seit Start: %d von %d" % (beat, len(live)), "",
            "## Eingefrorene Liste (am Start festgelegt)", "",
            "| Liste | Rang | Strategie | Markt | Parameter | Rendite seit Start | Max. Verlust | besser als SPY |",
            "|---|---|---|---|---|---|---|---|"]
    for it, r in paper:
        L = r.get("LIVE") if r else None
        out.append("| %s | %d | %s | %s | %s | %s | %s | %s |" % (
            it["liste"], it["rang"], it["fam"], it["uni"], fmt_p(it["p"]), pc(L["rendite"]) if L else "-",
            ("-%.1f %%" % (100 * L["mdd"])) if L else "-", ("ja" if L["rendite"] > spy["rendite"] else "nein") if L else "-"))
    out += ["", "## Nach Gruppe", "", "| Gruppe | Varianten | Median-Rendite seit Start | besser als SPY |", "|---|---|---|---|"]
    groups = collections.defaultdict(list)
    for r in live:
        groups[r["grp"]].append(r["LIVE"]["rendite"])
    for g, v in sorted(groups.items()):
        v.sort()
        out.append("| %s | %d | %s | %d |" % (g, len(v), pc(v[len(v) // 2]), sum(1 for x in v if x > spy["rendite"])))
    return out


def main():
    ap = argparse.ArgumentParser(description="Strategie-Labor v2")
    ap.add_argument("--refresh", action="store_true", help="Kurs- und SEC-Daten neu laden")
    ap.add_argument("--quick", action="store_true", help="kurzer Probelauf")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--xlsx", default="Strategie-Labor.xlsx")
    ap.add_argument("--ohne-intraday", action="store_true", help="Stundenkurs-Studie auslassen")
    ap.add_argument("--nur-wenn-neu", action="store_true", help="nur rechnen, wenn es neue Tageskurse gibt")
    a = ap.parse_args()
    t0 = time.time()
    live_start = (read_json(SETTINGS_FILE, {}) or {}).get("live_start")
    if a.nur_wenn_neu:
        stand = read_json(STAND_FILE, {}) or {}
        try:
            spy_rows, _ = fetch_daily("SPY")
            today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
            latest = max(d for d in spy_rows if d < today)
        except Exception as e:
            print("SPY-Pruefung fehlgeschlagen (%s) -> rechne trotzdem" % e, flush=True)
            latest = None
        if latest and stand.get("datum") and latest <= stand["datum"]:
            print("Keine neuen Tageskurse seit %s - nichts zu tun." % stand["datum"], flush=True)
            return
    print("Lade Tageskurse ...", flush=True)
    data = load_daily(a.refresh)
    print("Lade Termine der Quartalszahlen (SEC EDGAR) ...", flush=True)
    data["events"] = load_events(a.refresh)
    data["live_start"] = live_start
    setup(data)
    print("%d Handelstage %s .. %s, %d Werte (fehlend: %s)" % (T, DATES[0], DATES[-1], len(RAW),
                                                               ", ".join(data.get("missing", [])) or "-"), flush=True)
    tasks, nvar = build_tasks(a.quick)
    print("%d Aufgaben, %d Varianten, %d Prozesse" % (len(tasks), nvar, a.workers), flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=init_worker, initargs=(live_start,)) as ex:
        futs = {ex.submit(run_task, tk): tk for tk in tasks}
        for k, f in enumerate(as_completed(futs), 1):
            tk = futs[f]
            rs = f.result()
            rows.extend(rs)
            print("[%3d/%d] %-36s %-10s %4d Varianten  %5.0fs" % (k, len(tasks), task_name(tk), tk[2], len(rs),
                                                                 time.time() - t0), flush=True)
    rows.sort(key=lambda r: (r["grp"], r["fam"], r["uni"], json.dumps(r["p"], sort_keys=True)))
    ana = analyse(rows)
    print("Gegencheck mit 3,3-fachen Kosten ...", flush=True)
    for r in {r["id"]: r for r in ana["top"] + ana["topr"] + ana["short"]}.values():
        res = run_task(find_task(r["fam"], r["uni"]), cost=r["cost"] * HIGH_COST_X, only=r["p"])
        r["C_teuer"] = res[0]["C"] if res else None
    pdata, paper = paper_list(rows, ana, live_start) if live_start else (None, [])
    ana["paper"], ana["paper_meta"] = paper, pdata
    intra = []
    if not a.ohne_intraday:
        print("Lade Stundenkurse ...", flush=True)
        intra = intraday_study(load_hourly(a.refresh))
    with open("lab_results.json", "w", encoding="utf-8") as f:
        json.dump(rows, f)
    lines = report(rows, ana, intra)
    with open("lab_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    if live_start:
        with open("lab_live.md", "w", encoding="utf-8") as f:
            f.write("\n".join(live_report(rows, ana, paper, live_start)) + "\n")
    fams = collections.OrderedDict()
    for r in rows:
        e = fams.setdefault(r["fam"], {"grp": r["grp"], "unis": [], "n": 0})
        e["n"] += 1
        if r["uni"] not in e["unis"]:
            e["unis"].append(r["uni"])
    info = {"datum": DATES[-1], "erster_tag": DATES[0], "g_start": DATES[PI["G"][0]], "uni_info": UNI_INFO,
            "desc": FAMILY_DESC, "fams": fams,
            "kosten": [(u, uni_cost(u)) for u in UNIVERSES if U_START.get(u) is not None],
            "intraday": intra, "fehlend": data.get("missing", []), "n_tage": T,
            "fmt_p": fmt_p, "high_x": HIGH_COST_X, "borrow": BORROW, "lev_fee": LEV_FEE, "live_start": live_start}
    import lab_excel
    lab_excel.build_excel(rows, ana, info, a.xlsx)
    with open(STAND_FILE, "w", encoding="utf-8") as f:
        json.dump({"datum": DATES[-1], "erstellt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                   "varianten": len(rows), "live_start": live_start,
                   "live_tage": max(0, T - LIVE_I0) if LIVE_I0 is not None else 0}, f, indent=1)
    print("\nFertig in %.0f s. Excel: %s, Bericht: lab_report.md" % (time.time() - t0, a.xlsx), flush=True)


if __name__ == "__main__":
    main()
