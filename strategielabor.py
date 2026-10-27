#!/usr/bin/env python3
"""Strategie-Labor: testet tausende Varianten von Handelsstrategien und sucht die robustesten.

    python strategielabor.py               # alles (Daten laden + einige Minuten rechnen)
    python strategielabor.py --refresh     # Kursdaten neu laden
    python strategielabor.py --quick       # kurzer Probelauf
    python strategielabor.py --workers 4

Methode (damit oben keine Zufallstreffer stehen):
  * Zeitraeume: A = 2005-2012 und B = 2013-2019 dienen der AUSWAHL,
    C = 2020-heute ist der TEST und wird fuer die Auswahl nie benutzt.
  * Rangfolge nach min(Sharpe A, Sharpe B): eine Strategie muss in beiden Phasen taugen.
  * Signal zum Tagesschluss -> Order zur NAECHSTEN Eroeffnung (kein Blick in die Zukunft).
    Ausnahmen: Tageshandel-Strategien entscheiden zur Eroeffnung, Kalender-Strategien
    handeln zum Schluss (Termine stehen vorher fest), Overnight kauft zum Schluss.
  * Kosten 0,03 % je Order, Gegencheck mit 0,10 %. Cash bekommt den T-Bill-Zins (^IRX).
  * Sharpe = Ueberrendite ueber T-Bill geteilt durch Volatilitaet, annualisiert.
Universen: SPY, QQQ, 13 Aktien-ETFs, 14 Multi-Asset-ETFs, ~50 groesste US-Aktien von 2004
(spaetere Pleiten wie Lehman fehlen bei Yahoo -> Aktien-Ergebnisse eher zu gut).
Zusaetzlich: Intraday-Studie (Noise-Area, ORB, Intraday-Momentum) auf Stundenkursen (~2 Jahre).
Ergebnisse: lab_report.md, lab_results.csv, lab_results.json
"""
import argparse, collections, datetime as dt, itertools, json, math, os, pickle, sys, time
import urllib.parse, urllib.request, warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

warnings.filterwarnings("ignore")

ETF_EQ = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"]
MULTI = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "LQD", "HYG", "GLD", "SLV", "DBC", "VNQ", "AGG"]
STOCKS = ["MSFT", "GE", "XOM", "PFE", "C", "WMT", "INTC", "AIG", "CSCO", "IBM", "JNJ", "BAC", "PG", "KO",
          "MRK", "VZ", "HD", "ORCL", "AMGN", "WFC", "MO", "PEP", "T", "JPM", "CVX", "TXN", "QCOM", "BMY",
          "MDT", "UNH", "LLY", "ABT", "CMCSA", "DIS", "MMM", "UPS", "HPQ", "MS", "GS", "AXP", "USB", "EBAY",
          "AMZN", "LOW", "COP", "SLB", "F", "BRK-B", "MSI"]
# Fannie Mae / Freddie Mac (FNMA, FMCC) bewusst NICHT dabei: seit 2010 ausserboerslich gehandelte
# Pennystocks mit Spruengen von mehreren 100 %, mit 0,03 % Kosten nicht realistisch handelbar.
# Sie haben Umkehr- und Momentum-Ergebnisse stark verfaelscht (Umkehr 2005-2012: 18,6 % statt 0,3 % p.a.).
EXTRA = ["^VIX", "^VIX3M", "^IRX"]
UNIVERSES = {"SPY": ["SPY"], "QQQ": ["QQQ"], "SEKTOREN": ETF_EQ, "MULTI": MULTI, "AKTIEN": STOCKS}
ALL_UNIS = list(UNIVERSES)
PERIODS = [("A", "2005-01-01", "2013-01-01"), ("B", "2013-01-01", "2020-01-01"),
           ("C", "2020-01-01", "2100-01-01"), ("AB", "2005-01-01", "2020-01-01"),
           ("G", "2005-01-01", "2100-01-01")]
COST, COST_HIGH = 0.0003, 0.0010
DAILY_CACHE, HOURLY_CACHE = "lab_daily.pkl", "lab_hourly.pkl"
NAN = float("nan")

# werden von setup() gefuellt
DATES, T, RAW, RF = [], 0, {}, []
MONTH, WD, POS_START, POS_END, PREHOL, REB_M, REB_W = [], [], [], [], [], [], []
PI, SLOTS, MKT = {}, {}, {}


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
    out = {}
    for i, ts in enumerate(res.get("timestamp") or []):
        o, h, l, c, a = q["open"][i], q["high"][i], q["low"][i], q["close"][i], adj[i]
        if c is None or a is None or c <= 0 or a <= 0:
            continue
        o = o if o and o > 0 else c
        h = max(h if h and h > 0 else c, o, c)
        l = min(l if l and l > 0 else c, o, c)
        f = a / c
        d = (dt.datetime.fromtimestamp(ts, dt.timezone.utc) - dt.timedelta(hours=5)).strftime("%Y-%m-%d")
        out[d] = (o * f, h * f, l * f, a)
    return out


def load_daily(refresh=False):
    if os.path.exists(DAILY_CACHE) and not refresh:
        with open(DAILY_CACHE, "rb") as f:
            return pickle.load(f)
    syms = list(dict.fromkeys(ETF_EQ + MULTI + STOCKS + EXTRA))
    raw = {}
    for i, s in enumerate(syms):
        try:
            raw[s] = fetch_daily(s)
            print("  [%2d/%d] %-7s %5d Tage ab %s" % (i + 1, len(syms), s, len(raw[s]), min(raw[s])), flush=True)
        except Exception as e:
            print("  [%2d/%d] %-7s FEHLT: %s" % (i + 1, len(syms), s, e), flush=True)
        time.sleep(0.3)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    dates = sorted(d for d in raw["SPY"] if d < today)
    data = {"dates": dates, "assets": {}}
    n = len(dates)
    for s, rows in raw.items():
        O, H, L, C = [NAN] * n, [NAN] * n, [NAN] * n, [NAN] * n
        start, last = None, None
        for t, d in enumerate(dates):
            r = rows.get(d)
            if r is not None:
                o, h, l, c = r
                last = c
                if start is None:
                    start = t
            elif last is not None:
                o = h = l = c = last          # fehlender Tag: Kurs unveraendert
            else:
                continue
            O[t], H[t], L[t], C[t] = o, h, l, c
        if start is not None:
            data["assets"][s] = {"O": O, "H": H, "L": L, "C": C, "start": start}
    with open(DAILY_CACHE, "wb") as f:
        pickle.dump(data, f)
    return data


def setup(data):
    global DATES, T, RAW, RF, MONTH, WD, POS_START, POS_END, PREHOL, REB_M, REB_W, PI, SLOTS
    DATES, RAW = data["dates"], data["assets"]
    T = len(DATES)
    RF = [0.0] * T
    irx = RAW.get("^IRX")
    if irx:
        for t in range(1, T):
            v = irx["C"][t - 1]
            if v == v and v > 0:
                RF[t] = v / 100.0 / 252.0
    dd = [dt.date.fromisoformat(d) for d in DATES]
    MONTH = [d.year * 12 + d.month for d in dd]
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
    PI = {}
    for name, a, b in PERIODS:
        i0 = next(t for t, d in enumerate(DATES) if d >= a)
        i1 = next((t for t, d in enumerate(DATES) if d >= b), T)
        PI[name] = (i0, i1)
    SLOTS = {}
    for u, syms in UNIVERSES.items():
        starts = [RAW[s]["start"] for s in syms if s in RAW]
        cnt = [0] * T
        for s0 in starts:
            for t in range(s0, T):
                cnt[t] += 1
        SLOTS[u] = [1.0 / c if c else 0.0 for c in cnt]


def init_worker():
    with open(DAILY_CACHE, "rb") as f:
        setup(pickle.load(f))


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


IND = {"sma": i_sma, "ema": i_ema, "std": i_std, "hh": i_hh, "ll": i_ll, "rsi": i_rsi, "ret": i_ret,
       "vol": i_vol, "atr": i_atr, "ibs": i_ibs, "willr": i_willr, "cci": i_cci, "adx": i_adx,
       "psar": i_psar, "ichi": i_ichi, "slope": i_slope, "macd": i_macd, "absmove": i_absmove,
       "crsi": i_crsi}


# ======================= Strategien (je Wert) =======================
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
        mo = (MONTH[t] - 1) % 12 + 1
        if (mo >= 11 or mo <= 4) and (tf is None or C[t] > tf[t]):
            S[t] = 1.0
    return ("pos", S)


def f_vix(a, p):
    S, V = [0.0] * T, MKT.get("^VIX")
    if V is None:
        return ("pos", S)
    v, r, s0 = V.C, p["regel"], max(a.s0, V.s0)
    if r == "vix<vix3m":
        V3 = MKT.get("^VIX3M")
        if V3 is None:
            return ("pos", S)
        v3, f = V3.C, p["f"]
        for t in range(max(s0, V3.s0), T):
            if v[t] < f * v3[t]:
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
    v = a.ind("vol", 20)
    s1 = first_valid(v, a.s0)
    m = roll_mean(v, 252, s1) if s1 < T else [NAN] * T
    k = p["k"]
    return ("pos", [1.0 if v[t] < k * m[t] else 0.0 for t in range(T)])


def grid(**kw):
    return [dict(zip(kw, v)) for v in itertools.product(*kw.values())]


TF = [0, 200]
TIMING = [
    ("Kaufen & Halten", f_bh, [{}]),
    ("SMA-Trend", f_sma_trend, grid(n=[20, 50, 100, 150, 200, 250])),
    ("SMA-Kreuz", f_ma_cross, [p for p in grid(typ=["sma"], f=[5, 10, 20, 50], s=[50, 100, 150, 200]) if p["f"] < p["s"]]),
    ("EMA-Kreuz", f_ma_cross, [p for p in grid(typ=["ema"], f=[5, 10, 12, 20, 50], s=[26, 30, 50, 100, 200]) if p["f"] < p["s"]]),
    ("Donchian-Ausbruch", f_donchian, [p for p in grid(n=[20, 50, 100, 200], m=[10, 20, 50]) if p["m"] < p["n"]]),
    ("Zeitreihen-Momentum", f_tsmom, [p for p in grid(n=[21, 42, 63, 126, 189, 252], skip=[0, 21]) if p["skip"] < p["n"]]),
    ("MACD", f_macd, [dict(f=f, s=s, g=g, regel=r) for (f, s, g) in [(12, 26, 9), (8, 17, 9), (5, 35, 5), (19, 39, 9)]
                      for r in ("signal", "null")]),
    ("Keltner-Ausbruch", f_keltner, grid(n=[20, 50], k=[0.5, 1, 1.5, 2])),
    ("Chandelier-Trend", f_chandelier, grid(n=[20, 50, 100], k=[2, 3, 4])),
    ("ADX-Trend", f_adx, grid(thr=[15, 20, 25, 30])),
    ("Parabolic-SAR", f_psar, grid(step=[0.01, 0.02, 0.03], max=[0.1, 0.2])),
    ("Ichimoku", f_ichi, grid(set=[(9, 26, 52), (20, 60, 120)], tk=[0, 1])),
    ("Regressions-Trend", f_slope, grid(n=[20, 50, 100, 200])),
    ("Bollinger-Ausbruch", f_bb_break, grid(n=[20, 50, 100], k=[0.5, 1, 1.5, 2])),
    ("RSI-Ruecksetzer", f_rsi, grid(n=[2, 3, 4, 5, 14], x=[5, 10, 15, 20, 25, 30], exit=["sma5", "rsi50", "rsi70"], trend=TF)),
    ("ConnorsRSI", f_crsi, grid(x=[5, 10, 15, 20, 25], exit=["crsi50", "crsi70", "sma5"], trend=TF)),
    ("Bollinger-Ruecksetzer", f_bb_mr, grid(n=[5, 10, 20, 50], k=[1, 1.5, 2, 2.5], exit=["mitte", "sma5"], trend=TF)),
    ("IBS-Ruecksetzer", f_ibs, grid(x=[0.1, 0.15, 0.2, 0.25, 0.3], exit=["ibs70", "ibs50", "vortageshoch", "1tag"], trend=TF)),
    ("Abwaertstage", f_down, grid(N=[2, 3, 4, 5], exit=["plustag", "sma5"], trend=TF)),
    ("N-Tage-Tief", f_nlow, grid(n=[5, 7, 10, 20], exit=["sma5", "nhoch", "5tage"], trend=TF)),
    ("Williams-%R", f_willr, grid(n=[2, 5, 10, 14], x=[-80, -90, -95], trend=TF)),
    ("CCI-Ruecksetzer", f_cci, grid(n=[10, 20], x=[-100, -150, -200], trend=TF)),
    ("Gap-Fade (Tageshandel)", f_gapfade, grid(g=[0.0025, 0.005, 0.01, 0.015, 0.02, "unter-vortagestief"], trend=TF)),
    ("Gap-Momentum (Tageshandel)", f_gapgo, grid(g=[0.0025, 0.005, 0.01, 0.02], trend=TF)),
    ("Vola-Ausbruch Williams (Tageshandel)", f_volbreak, grid(k=[0.3, 0.5, 0.7, 1.0], trend=TF)),
    ("Noise-Band (Tageshandel)", f_noise, grid(n=[7, 14, 21], mult=[0.5, 1.0, 1.5], trend=TF)),
    ("Overnight", f_overnight, grid(bed=["immer", "trend200", "nach-minustag", "ibs<0.5", "trend+minustag"])),
    ("Monatswechsel", f_tom, grid(letzte=[0, 1, 2, 3, 4, 5], erste=[1, 2, 3, 4, 5])),
    ("Wochentag", f_weekday, grid(tag=[0, 1, 2, 3, 4, "ohne-montag"])),
    ("Vor-Feiertag", f_prehol, [{}]),
    ("Saison Nov-Apr", f_season, grid(trend=TF)),
    ("VIX-Filter", f_vix, [dict(regel="vix<vix3m", f=f) for f in (1.0, 0.95, 0.9)]
     + [dict(regel="vix<sma", n=n) for n in (10, 20, 50)]
     + [dict(regel="vix<niveau", n=n) for n in (15, 20, 25, 30)]
     + [dict(regel="angst-kauf", x=x, h=h) for x in (0.1, 0.2, 0.3) for h in (5, 10, 20)]),
    ("Vola-Ziel", f_voltarget, grid(ziel=[0.10, 0.15, 0.20], n=[20, 60], trend=TF)),
    ("Vola-Regime", f_volregime, grid(k=[0.8, 1.0, 1.2])),
]
TIMING_UNIS = {"VIX-Filter": ["SPY", "QQQ", "SEKTOREN", "AKTIEN"]}


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


NS = {"SEKTOREN": [1, 2, 3, 5], "MULTI": [1, 2, 3, 5], "AKTIEN": [3, 5, 10, 15]}
XS_UNIS = ["SEKTOREN", "MULTI", "AKTIEN"]
PORT = [
    ("Momentum-Rotation", g_mom, XS_UNIS,
     lambda u: [p for p in grid(L=[21, 63, 126, 189, 252], skip=[0, 21], N=NS[u], reb=["M", "W"],
                                filt=["keiner", "spy200", "absolut"]) if p["skip"] < p["L"]]),
    ("Momentum/Vola-Rotation", g_momvol, XS_UNIS, lambda u: grid(L=[63, 126, 252], N=NS[u], filt=["keiner", "spy200"])),
    ("Niedrige-Vola-Auswahl", g_lowvol, XS_UNIS, lambda u: grid(n=[21, 63, 126, 252], N=NS[u], filt=["keiner", "spy200"])),
    ("Kurzfrist-Umkehr", g_rev, XS_UNIS, lambda u: grid(L=[5, 10, 21], N=NS[u], reb=["W", "M"], filt=["keiner", "spy200"])),
    ("52-Wochen-Hoch", g_52, XS_UNIS, lambda u: grid(N=NS[u], filt=["keiner", "spy200"])),
    ("Risk-Parity", g_rp, ["SEKTOREN", "MULTI"], lambda u: grid(n=[21, 63, 126], trend=TF)),
    ("GTAA (Faber)", g_gtaa, XS_UNIS, lambda u: grid(n=[100, 150, 200, 210, 250])),
    ("Dual-Momentum GEM", g_gem, ["MULTI"], lambda u: grid(L=[63, 126, 189, 252], risk=["SPY/EFA", "SPY/QQQ/EFA"])),
    ("60/40 SPY/AGG", g_6040, ["MULTI"], lambda u: [{}]),
]
BENCH_FAMS = ("Kaufen & Halten", "60/40 SPY/AGG")


# ======================= Backtest-Motor =======================
def add_pos(R, E, NE, a, S, slot, cost):
    """S[t] = Zielgewicht, entschieden zum Schluss von Tag t, ausgefuehrt zur Eroeffnung t+1."""
    O, C = a.O, a.C
    w2 = w1 = 0.0
    for t in range(a.s0, T):
        if w1 != 0.0 or w2 != 0.0:
            R[t] += w2 * (O[t] / C[t - 1] - 1.0) + w1 * (C[t] / O[t] - 1.0) - cost * abs(w1 - w2)
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
    if n < 20:
        return None
    eq = peak = 1.0
    mdd = s = ss = 0.0
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
    mu = s / n
    var = ss / n - mu * mu
    sh = mu / math.sqrt(var) * math.sqrt(252) if var > 1e-18 else 0.0
    yrs = n / 252.0
    tr = sum(NE[i0:i1])
    return {"sharpe": round(sh, 3), "cagr": round(100 * (eq ** (1 / yrs) - 1), 2) if eq > 0 else -100.0,
            "mdd": round(100 * mdd, 1), "expo": round(100 * sum(E[i0:i1]) / n, 1), "trades": tr,
            "tpj": round(tr / yrs, 1), "ende": round(eq, 3)}


def make_row(fam, u, p, R, E, NE):
    for t in range(T):
        e = E[t]
        if e < 1.0:
            R[t] += (1.0 - e) * RF[t]
    row = {"fam": fam, "uni": u, "p": p}
    for name, _, _ in PERIODS:
        i0, i1 = PI[name]
        row[name] = metrics(R, E, NE, i0, i1)
    return row


def run_task(task, cost=COST, only=None):
    global MKT
    kind, i, u = task
    MKT = {s: Asset(s) for s in ("SPY", "^VIX", "^VIX3M") if s in RAW}
    assets = [Asset(s) for s in UNIVERSES[u] if s in RAW]
    rows = []
    if kind == "T":
        fam, fn, params = TIMING[i]
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
            rows.append(make_row(fam, u, p, R, E, NE))
    else:
        fam, fn, _, gridf = PORT[i]
        for p in gridf(u):
            if only is not None and p != only:
                continue
            R, E, NE = [0.0] * T, [0.0] * T, [0] * T
            W = fn(assets, p)
            for a in assets:
                if any(W[a.sym]):
                    add_pos(R, E, NE, a, W[a.sym], None, cost)
            rows.append(make_row(fam, u, p, R, E, NE))
    return rows


def task_name(task):
    return TIMING[task[1]][0] if task[0] == "T" else PORT[task[1]][0]


def build_tasks(quick=False):
    tasks = []
    for i, (fam, fn, params) in enumerate(TIMING):
        for u in TIMING_UNIS.get(fam, ALL_UNIS):
            tasks.append(("T", i, u, len(params)))
    for i, (fam, fn, unis, gridf) in enumerate(PORT):
        for u in unis:
            tasks.append(("P", i, u, len(gridf(u))))
    if quick:
        tasks = [t for t in tasks if t[2] in ("SPY", "SEKTOREN") and t[3] <= 40]
    # grosse Aufgaben zuerst (bessere Auslastung)
    weight = {"AKTIEN": 50, "MULTI": 14, "SEKTOREN": 13, "SPY": 1, "QQQ": 1}
    tasks.sort(key=lambda t: -t[3] * weight[t[2]])
    return [t[:3] for t in tasks], sum(t[3] for t in tasks)


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
        print("  %s: %d Handelstage Stundenkurse (%s .. %s)" % (sym, len(out[sym]), min(out[sym]), max(out[sym])))
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
    eq = 1.0
    peak, mdd = 1.0, 0.0
    for x in rs:
        eq *= 1 + x
        peak = max(peak, eq)
        mdd = max(mdd, 1 - eq / peak)
    return {"sharpe": round(mu / math.sqrt(var) * math.sqrt(252), 2) if var > 0 else 0.0,
            "rendite": round(100 * (eq - 1), 1), "mdd": round(100 * mdd, 1),
            "trades": sum(k for _, _, k in res)}


def intraday_study(hourly, P):
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
    if not rows:
        P("Keine Stundenkurse verfuegbar.")
        return rows
    r0 = rows[0]
    P("\n## Intraday-Studie (Stundenkurse, nur ~2 Jahre -> wenig aussagekraeftig)\n")
    P("Auswahl: %s .. %s, Test: %s .. %s. %d Varianten auf %s.\n"
      % (r0["von"], r0["mitte"], r0["mitte"], r0["bis"], len(INTRA) * len(hourly), ", ".join(hourly)))
    cand = [r for r in rows if r["fam"] != "Kaufen & Halten" and r["train"] and r["train"]["trades"] >= 20]
    cand.sort(key=lambda r: -r["train"]["sharpe"])
    P("| # | Strategie | ETF | Parameter | Sharpe Auswahl | Sharpe Test | Rendite Test | Trades Test |")
    P("|---|---|---|---|---|---|---|---|")
    for k, r in enumerate(cand[:5], 1):
        P("| %d | %s | %s | %s | %.2f | %.2f | %+.1f %% | %d |" % (k, r["fam"], r["sym"], fmt_p(r["p"]), r["train"]["sharpe"],
                                                            r["test"]["sharpe"], r["test"]["rendite"], r["test"]["trades"]))
    for r in rows:
        if r["fam"] == "Kaufen & Halten":
            P("| - | Kaufen & Halten | %s | - | %.2f | %.2f | %+.1f %% | - |" % (r["sym"], r["train"]["sharpe"],
                                                                         r["test"]["sharpe"], r["test"]["rendite"]))
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


def find_task(fam, uni):
    for i, (f, *_rest) in enumerate(TIMING):
        if f == fam:
            return ("T", i, uni)
    for i, (f, *_rest) in enumerate(PORT):
        if f == fam:
            return ("P", i, uni)


def report(rows, P):
    bench = [r for r in rows if r["fam"] in BENCH_FAMS]
    cand = [r for r in rows if r["fam"] not in BENCH_FAMS and r["A"] and r["B"] and r["C"]]
    elig = [r for r in cand if r["A"]["trades"] >= 5 and r["B"]["trades"] >= 5]
    for r in elig:
        r["score"] = min(r["A"]["sharpe"], r["B"]["sharpe"])
    elig.sort(key=lambda r: -r["score"])
    spy = next(r for r in bench if r["fam"] == "Kaufen & Halten" and r["uni"] == "SPY")
    yrs_ab = (PI["AB"][1] - PI["AB"][0]) / 252.0

    P("# Strategie-Labor: Ergebnis\n")
    P("Stand der Kurse: %s. Getestet: **%d Varianten** aus %d Strategie-Familien auf 5 Universen; "
      "%d davon mit genug Trades fuer die Auswahl.\n" % (DATES[-1], len(rows), len(TIMING) + len(PORT), len(elig)))
    P("Auswahl = Zeitraum A (2005-2012) und B (2013-2019). Test = C (2020-%s), nie zur Auswahl benutzt. "
      "Rang = min(Sharpe A, Sharpe B). Order zur naechsten Eroeffnung, 0,03 %% Kosten je Order.\n" % DATES[-1][:4])

    P("## Vergleichswerte (Kaufen & Halten)\n")
    P("| Universum | Sharpe A | Sharpe B | Sharpe C | Rendite/J C | Max. Verlust C | Rendite/J 2005-heute |")
    P("|---|---|---|---|---|---|---|")
    for r in bench:
        name = r["uni"] if r["fam"] == "Kaufen & Halten" else "60/40 SPY/Anleihen"
        P("| %s | %.2f | %.2f | %.2f | %.1f %% | -%.0f %% | %.1f %% |" % (name, r["A"]["sharpe"], r["B"]["sharpe"], r["C"]["sharpe"],
                                                                   r["C"]["cagr"], r["C"]["mdd"], r["G"]["cagr"]))

    # Top 10, je Familie+Universum nur die beste Variante
    seen, top = set(), []
    for r in elig:
        key = (r["fam"], r["uni"])
        if key not in seen:
            seen.add(key)
            top.append(r)
        if len(top) == 10:
            break
    for r in top:
        hi = run_task(find_task(r["fam"], r["uni"]), cost=COST_HIGH, only=r["p"])
        r["C_teuer"] = hi[0]["C"] if hi else None

    P("\n## Die 10 robustesten Strategien (Auswahl A+B, geprueft im Test C)\n")
    P("| # | Strategie | Universum | Parameter | Sharpe A | Sharpe B | **Sharpe C (Test)** | Rendite/J C | Max. Verlust C "
      "| investiert | Trades/J | Sharpe C bei 0,10 % Kosten |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k, r in enumerate(top, 1):
        c = r["C"]
        P("| %d | %s | %s | %s | %.2f | %.2f | **%.2f** | %.1f %% | -%.0f %% | %.0f %% | %.0f | %s |"
          % (k, r["fam"], r["uni"], fmt_p(r["p"]), r["A"]["sharpe"], r["B"]["sharpe"], c["sharpe"], c["cagr"], c["mdd"],
             c["expo"], c["tpj"], "%.2f" % r["C_teuer"]["sharpe"] if r.get("C_teuer") else "-"))
    P("\nZum Vergleich SPY halten im Test C: Sharpe %.2f, %.1f %% pro Jahr, max. Verlust -%.0f %%."
      % (spy["C"]["sharpe"], spy["C"]["cagr"], spy["C"]["mdd"]))

    # renditestarke robuste Strategien
    by_ret = sorted([r for r in elig if r["A"]["expo"] > 30], key=lambda r: -min(r["A"]["cagr"], r["B"]["cagr"]))
    seen, topr = set(), []
    for r in by_ret:
        key = (r["fam"], r["uni"])
        if key not in seen:
            seen.add(key)
            topr.append(r)
        if len(topr) == 5:
            break
    P("\n## Die 5 renditestaerksten robusten Strategien (Rang = min(Rendite A, Rendite B))\n")
    P("| # | Strategie | Universum | Parameter | Rendite/J A | Rendite/J B | **Rendite/J C** | Max. Verlust C | Sharpe C |")
    P("|---|---|---|---|---|---|---|---|---|")
    for k, r in enumerate(topr, 1):
        P("| %d | %s | %s | %s | %.1f %% | %.1f %% | **%.1f %%** | -%.0f %% | %.2f |"
          % (k, r["fam"], r["uni"], fmt_p(r["p"]), r["A"]["cagr"], r["B"]["cagr"], r["C"]["cagr"], r["C"]["mdd"], r["C"]["sharpe"]))

    # Diagnose
    sc = [r["score"] for r in elig]
    cs = [r["C"]["sharpe"] for r in elig]
    rho = spearman(sc, cs)
    top50 = elig[:50]
    beat = sum(1 for r in top50 if r["C"]["sharpe"] > spy["C"]["sharpe"])
    med = lambda v: sorted(v)[len(v) // 2]
    P("\n## Wie verlaesslich ist das?\n")
    P("- Zusammenhang Auswahl-Rang <-> Test-Ergebnis (Spearman): **%.2f** (0 = Auswahl sagt nichts voraus, 1 = perfekt)." % rho)
    P("- Von den 50 besten der Auswahl schlagen im Test **%d** die Sharpe von SPY halten (%.2f)." % (beat, spy["C"]["sharpe"]))
    P("- Median-Sharpe im Test: Top-50 der Auswahl %.2f, alle Varianten %.2f." % (med([r["C"]["sharpe"] for r in top50]), med(cs)))
    P("- Bei %d unabhaengigen Strategien ohne echten Vorteil waere die beste Sharpe ueber %.0f Jahre allein durch Glueck etwa **%.2f**. "
      "(Die Varianten sind stark verwandt, die echte Zahl ist kleiner.)" % (len(elig), yrs_ab, luck_sharpe(len(elig), yrs_ab)))

    # Top 10 nach Test (nur Info)
    seen, topc = set(), []
    for r in sorted(cand, key=lambda r: -r["C"]["sharpe"]):
        key = (r["fam"], r["uni"])
        if key not in seen:
            seen.add(key)
            topc.append(r)
        if len(topc) == 10:
            break
    P("\n## Nur zur Info: die 10 besten im Test C (im Nachhinein ausgesucht = NICHT ehrlich waehlbar)\n")
    P("| # | Strategie | Universum | Parameter | Sharpe A | Sharpe B | Sharpe C | Rendite/J C |")
    P("|---|---|---|---|---|---|---|---|")
    for k, r in enumerate(topc, 1):
        P("| %d | %s | %s | %s | %.2f | %.2f | %.2f | %.1f %% |" % (k, r["fam"], r["uni"], fmt_p(r["p"]), r["A"]["sharpe"],
                                                              r["B"]["sharpe"], r["C"]["sharpe"], r["C"]["cagr"]))
    return top


def write_csv(rows, path="lab_results.csv"):
    def num(v):
        return ("%s" % v).replace(".", ",")
    cols = ["sharpe", "cagr", "mdd", "expo", "tpj"]
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(";".join(["Strategie", "Universum", "Parameter"] + ["%s_%s" % (p, c) for p in ("A", "B", "C", "G") for c in cols]) + "\n")
        for r in rows:
            vals = []
            for p in ("A", "B", "C", "G"):
                m = r.get(p) or {}
                vals += [num(m.get(c, "")) for c in cols]
            f.write(";".join([r["fam"], r["uni"], fmt_p(r["p"])] + vals) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Strategie-Labor")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    a = ap.parse_args()
    t0 = time.time()
    print("Lade Tageskurse ...", flush=True)
    data = load_daily(a.refresh)
    setup(data)
    print("%d Handelstage %s .. %s, %d Werte" % (T, DATES[0], DATES[-1], len(RAW)), flush=True)
    tasks, nvar = build_tasks(a.quick)
    print("%d Aufgaben, %d Varianten, %d Prozesse" % (len(tasks), nvar, a.workers), flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=init_worker) as ex:
        futs = {ex.submit(run_task, tk): tk for tk in tasks}
        for k, f in enumerate(as_completed(futs), 1):
            tk = futs[f]
            rs = f.result()
            rows.extend(rs)
            print("[%3d/%d] %-38s %-9s %4d Varianten  %5.0fs" % (k, len(tasks), task_name(tk), tk[2], len(rs), time.time() - t0), flush=True)
    with open("lab_results.json", "w", encoding="utf-8") as f:
        json.dump(rows, f)
    write_csv(rows)
    lines = []

    def P(s=""):
        print(s, flush=True)
        lines.append(s)
    report(rows, P)
    print("\nLade Stundenkurse ...", flush=True)
    intraday_study(load_hourly(a.refresh), P)
    P("\nLaufzeit: %.0f Sekunden. Alle Varianten: lab_results.csv" % (time.time() - t0))
    with open("lab_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
