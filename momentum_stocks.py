#!/usr/bin/env python3
"""Momentum mit Einzelaktien. Universum = ca. die 50 größten US-Aktien Anfang 2004
(nicht die heutigen Gewinner -> weniger Survivorship-Bias). Firmen, die später
pleite/übernommen wurden und bei Yahoo fehlen, sind aufgelistet und fehlen leider
im Test (das macht das Ergebnis eher ZU GUT).

    python momentum_stocks.py [--refresh]

Regel: monatlich die TOP N nach 12-1-Monats-Rendite (12 Monate, letzter Monat
ausgelassen), gleichgewichtet; nur wenn SPY > SMA200, sonst Cash. Kosten 0,05 %.
Varianten: N = 5 und 10, mit und ohne SPY-Filter. Vergleich: SPY halten und
gleichgewichtet alle Aktien halten.
"""
import sys, os, pickle, time, warnings
warnings.filterwarnings("ignore")
import swing

TOP2004 = ["MSFT", "GE", "XOM", "PFE", "C", "WMT", "INTC", "AIG", "CSCO", "IBM", "JNJ", "BAC", "PG",
           "KO", "MRK", "VZ", "HD", "ORCL", "AMGN", "WFC", "MO", "PEP", "T", "JPM", "CVX", "TXN", "DELL",
           "QCOM", "BMY", "MDT", "UNH", "LLY", "ABT", "CMCSA", "DIS", "MMM", "UPS", "HPQ", "MS", "GS",
           "AXP", "USB", "EBAY", "AMZN", "FNMA", "FMCC", "LOW", "COP", "SLB", "F"]
MISSING_NOTE = "Fehlen (delistet): Merrill Lynch, Wachovia, Yahoo, Time Warner, Wyeth, Washington Mutual, Lehman"
CACHE = "stocks_cache.pkl"

def load(refresh):
    if os.path.exists(CACHE) and not refresh:
        return pickle.load(open(CACHE, "rb"))
    data = {}
    for s in TOP2004 + ["SPY"]:
        try:
            data[s] = swing.fetch(s)
            print("  %-5s %d Tage ab %s" % (s, len(data[s]), min(data[s])))
        except Exception as e:
            print("  %-5s FEHLT (%s)" % (s, e))
        time.sleep(0.4)
    pickle.dump(data, open(CACHE, "wb"))
    return data

def run(data, d0, d1, top=10, spy_filter=True, mode="mom"):
    days = sorted(d for d in data["SPY"] if d0 <= d < d1)
    hist = {s: [data[s][d] for d in sorted(data[s]) if d < d0][-260:] for s in data}
    cash, pos, eq, trades, month = 1.0, {}, [], [], None
    for d in days:
        px = {s: data[s][d] for s in data if d in data[s]}
        for s, p in px.items(): hist[s].append(p)
        if d[:7] != month:
            month = d[:7]
            for s in list(pos):
                q, e = pos.pop(s); p = px.get(s, hist[s][-1]); cash += q * p * (1 - swing.COST); trades.append(p / e - 1)
            if mode == "ew":
                picks = [s for s in px if s != "SPY"]
            elif mode == "spy":
                picks = ["SPY"]
            else:
                ok = not spy_filter or px["SPY"] > swing.sma(hist["SPY"], 200)
                picks = []
                if ok:
                    sc = sorted(((hist[s][-22] / hist[s][-253] - 1, s) for s in px
                                 if s != "SPY" and len(hist[s]) > 253), reverse=True)
                    picks = [s for _, s in sc[:top]]
            for s in picks:
                amt = cash / (len(picks) - len(pos))
                pos[s] = (amt * (1 - swing.COST) / px[s], px[s]); cash -= amt
        eq.append(cash + sum(q * px.get(s, hist[s][-1]) for s, (q, e) in pos.items()))
    return swing.stats(eq, trades, len(days))

if __name__ == "__main__":
    data = load("--refresh" in sys.argv)
    print(MISSING_NOTE)
    today = max(data["SPY"])
    variants = [("Top5 +Filter", dict(top=5)), ("Top10 +Filter", dict(top=10)),
                ("Top5 ohne", dict(top=5, spy_filter=False)), ("Top10 ohne", dict(top=10, spy_filter=False)),
                ("Alle gleich", dict(mode="ew")), ("SPY halten", dict(mode="spy"))]
    for name, a, b in [("TRAIN", "2005-01-01", "2016-01-01"), ("TEST", "2016-01-01", "9999"), ("GESAMT", "2005-01-01", "9999")]:
        print("\n== %s %s .. %s ==" % (name, a, b if b != "9999" else today))
        print("%-14s" % "", "  ".join("%9s" % k for k in ["CAGR %", "MaxDD %", "Sharpe", "Trades", "Win %", "PF", "Endwert x"]))
        for vn, kw in variants:
            print("%-14s" % vn, "  ".join("%9s" % v for v in run(data, a, b, **kw).values()))
