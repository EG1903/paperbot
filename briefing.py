#!/usr/bin/env python3
"""Makro- und News-Briefing fuer den Paperbot (nur oeffentliche Quellen, keine Anlageberatung).

    python briefing.py                 # schreibt briefing.md
    NTFY_TOPIC=geheimes-thema python briefing.py   # zusaetzlich Kurzfassung als Push-Nachricht (ntfy.sh, optional)

Inhalt: wichtige Termine (Fed-Zinsentscheide samt Pressekonferenz, US-Wirtschaftsdaten wie Inflation und
Arbeitsmarkt), Marktlage (Futures, DAX, VIX, Gold, Oel, Zinsen, Dollar, Bitcoin), Mitteilungen der Fed und
des Weissen Hauses, Schlagzeilen zu Geopolitik, Zoellen, Fed und Praesident, deutsche Wirtschaftsnachrichten
und was der Paperbot heute vorhat.
Quellen: federalreserve.gov, whitehouse.gov, bls.gov, Google News, tagesschau.de, Yahoo Finance, Alpaca (Paper).
"""
import datetime as dt
import email.utils
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 paperbot-briefing"}
OUT = "briefing.md"
WICHTIG = re.compile(r"\b(war|attack|strike|missile|sanction|tariff|emergency|default|crash|invasion|nuclear|"
                     r"shutdown|recession|Krieg|Angriff|Zoll|Zölle|Sanktion|Notstand|Rezession)", re.I)


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def berlin_offset(utc):
    def last_sunday(m):
        d = dt.datetime(utc.year, m + 1, 1) - dt.timedelta(days=1) if m < 12 else dt.datetime(utc.year, 12, 31)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    start = last_sunday(3).replace(hour=1)
    end = last_sunday(10).replace(hour=1)
    return 2 if start <= utc < end else 1


def ny_offset(utc):
    y = utc.year

    def nth_sun(m, n):
        d = dt.datetime(y, m, 1)
        return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1))
    return -4 if nth_sun(3, 2) + dt.timedelta(hours=7) <= utc < nth_sun(11, 1) + dt.timedelta(hours=6) else -5


NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
BERLIN = NOW + dt.timedelta(hours=berlin_offset(NOW))
NY = NOW + dt.timedelta(hours=ny_offset(NOW))


def de_time(utc):
    return (utc + dt.timedelta(hours=berlin_offset(utc))).strftime("%d.%m. %H:%M")


# ---------------- Termine ----------------
def fomc_days():
    """Zinsentscheide der Fed (zweiter Sitzungstag) fuer dieses und naechstes Jahr."""
    h = get("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    months = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                          "September", "October", "November", "December"], 1)}
    out = []
    for y in (NY.year, NY.year + 1):
        i = h.find("%d FOMC Meetings" % y)
        if i < 0:
            continue
        nxt = [k for k in (h.find("%d FOMC Meetings" % yy, i + 10) for yy in range(2015, 2035)) if k > i]
        sec = h[i:min(nxt) if nxt else len(h)]
        for mon, days in re.findall(r'fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>\s*([^<]+?)\s*<',
                                    sec, re.S):
            mon_last = mon.split("/")[-1].strip()
            day = re.findall(r"\d+", days)[-1]
            if mon_last in months:
                out.append((dt.date(y, months[mon_last], int(day)), "*" in days))
    return out


def bls_events():
    txt = get("https://www.bls.gov/schedule/news_release/bls.ics")
    out = []
    for block in txt.split("BEGIN:VEVENT")[1:]:
        m_t = re.search(r"DTSTART;TZID=US-Eastern:(\d{8})T(\d{4})", block)
        m_s = re.search(r"SUMMARY:(.+)", block)
        if m_t and m_s:
            when = dt.datetime.strptime(m_t.group(1) + m_t.group(2), "%Y%m%d%H%M")
            out.append((when, m_s.group(1).strip()))
    return out


WICHTIGE_DATEN = {"Employment Situation": "US-Arbeitsmarktbericht", "Consumer Price Index": "US-Inflation (CPI)",
                  "Producer Price Index": "US-Erzeugerpreise (PPI)", "Job Openings and Labor Turnover Survey": "US-Offene Stellen (JOLTS)",
                  "Employment Cost Index": "US-Lohnkosten", "Real Earnings": "US-Reallöhne"}


def termine():
    rows = []
    heute = NY.date()
    try:
        for d, sep in fomc_days():
            if heute <= d <= heute + dt.timedelta(days=14):
                rows.append((dt.datetime.combine(d, dt.time(14, 0)), "**Fed-Zinsentscheid** (Pressekonferenz 30 Min. später%s)"
                             % (", mit neuen Prognosen" if sep else "")))
    except Exception as e:
        rows.append((None, "Fed-Kalender nicht ladbar (%s)" % e))
    try:
        for when, name in bls_events():
            if heute <= when.date() <= heute + dt.timedelta(days=7) and name in WICHTIGE_DATEN:
                rows.append((when, WICHTIGE_DATEN[name]))
    except Exception as e:
        rows.append((None, "BLS-Kalender nicht ladbar (%s)" % e))
    rows.sort(key=lambda r: (r[0] is None, r[0] or NOW))
    try:
        naechste = [d for d, _ in fomc_days() if d >= heute]
        if naechste and not any("Fed-Zinsentscheid" in w for _, w in rows):
            rows.append((None, "Nächster Fed-Zinsentscheid: %s (20:00 Uhr Berlin)" % naechste[0].strftime("%d.%m.%Y")))
    except Exception:
        pass
    lines = ["| Wann (New York) | Wann (Berlin) | Was |", "|---|---|---|"]
    for when, what in rows:
        if when is None:
            lines.append("| - | - | %s |" % what)
            continue
        utc = when - dt.timedelta(hours=ny_offset(when))
        tag = "**heute** " if when.date() == heute else ""
        wtag = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][when.weekday()]
        lines.append("| %s%s %s | %s | %s |" % (tag, wtag, when.strftime("%d.%m. %H:%M"), de_time(utc), what))
    if len(lines) == 2:
        lines.append("| - | - | keine großen Termine in den nächsten Tagen |")
    return lines


# ---------------- Marktlage ----------------
MARKT = [("S&P 500 (Future)", "ES=F"), ("Nasdaq-100 (Future)", "NQ=F"), ("DAX", "^GDAXI"), ("VIX (Angst-Index)", "^VIX"),
         ("Gold", "GC=F"), ("Öl Brent", "BZ=F"), ("Öl WTI", "CL=F"), ("US-Zins 10 Jahre (%)", "^TNX"),
         ("US-Dollar-Index", "DX-Y.NYB"), ("Euro in Dollar", "EURUSD=X"), ("Bitcoin", "BTC-USD")]


def quote(sym):
    res = json.loads(get("https://query2.finance.yahoo.com/v8/finance/chart/%s?range=5d&interval=1d"
                         % urllib.parse.quote(sym)))["chart"]["result"][0]["meta"]
    return res.get("regularMarketPrice"), res.get("chartPreviousClose") or res.get("previousClose")


def marktlage():
    lines = ["| Markt | Stand | seit Vortag |", "|---|---|---|"]
    vix = vix3 = None
    for name, sym in MARKT:
        try:
            px, prev = quote(sym)
            ch = (px / prev - 1) * 100 if px and prev else None
            if sym == "^VIX":
                vix = px
            lines.append("| %s | %s | %s |" % (name, ("%.2f" % px).replace(".", ","), ("%+.1f %%" % ch).replace(".", ",") if ch is not None else "-"))
        except Exception:
            lines.append("| %s | - | - |" % name)
    try:
        vix3, _ = quote("^VIX3M")
    except Exception:
        pass
    if vix and vix3:
        lage = ("**angespannt** (kurzfristige Angst höher als langfristige)" if vix > vix3 else "normal (ruhig)")
        lines += ["", "Angst-Struktur: VIX %.1f gegen 3-Monats-VIX %.1f -> %s." % (vix, vix3, lage)]
    return lines


# ---------------- Nachrichten ----------------
def rss(url, n=6, max_h=36):
    root = ET.fromstring(get(url).encode("utf-8"))
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate")
        try:
            t = email.utils.parsedate_to_datetime(pub).astimezone(dt.timezone.utc).replace(tzinfo=None) if pub else None
        except (TypeError, ValueError):
            t = None
        if t and NOW - t > dt.timedelta(hours=max_h):
            continue
        items.append({"title": title, "link": link, "t": t})
    items.sort(key=lambda x: x["t"] or NOW, reverse=True)
    return items[:n]


def gnews(q, n=6):
    return rss("https://news.google.com/rss/search?q=%s&hl=en-US&gl=US&ceid=US:en" % urllib.parse.quote(q + " when:1d"), n, 30)


def block(title, fn):
    lines = ["", "## " + title, ""]
    try:
        items = fn()
    except Exception as e:
        return lines + ["(Quelle nicht erreichbar: %s)" % e]
    if not items:
        return lines + ["Nichts Neues."]
    for it in items:
        mark = "⚠️ " if WICHTIG.search(it["title"]) else ""
        lines.append("- %s[%s](%s)%s" % (mark, it["title"].replace("[", "(").replace("]", ")"), it["link"],
                                         " · %s" % de_time(it["t"]) if it["t"] else ""))
    return lines


# ---------------- Bot ----------------
def bot_lage():
    lines = ["", "## Was der Paperbot heute vorhat", ""]
    try:
        import paperbot as P
        if not P.alpaca_on():
            return lines + ["(keine Alpaca-Keys - nur Signale)"] + bot_signale(P)
        acct = P.alpaca("GET", "/v2/account") or {}
        lines.append("Konto: $%s (Papiergeld)." % ("{:,.0f}".format(float(acct.get("equity") or 0)).replace(",", ".")))
        return lines + bot_signale(P)
    except Exception as e:
        return lines + ["(nicht verfügbar: %s)" % e]


def bot_signale(P):
    lines = ["", "| Teil | Signal | soll halten |", "|---|---|---|"]
    for name, tg in P.mix_targets().items():
        lines.append("| %s | %s | %s |" % (name, "an" if tg["an"] else "aus", "Cash" if tg["sym"] == "CASH" else tg["sym"]))
    return lines


def main():
    L = ["# Briefing %s Uhr (Berlin) · %s Uhr (New York)" % (BERLIN.strftime("%d.%m.%Y %H:%M"), NY.strftime("%H:%M")), "",
         "Automatisch erstellt aus öffentlichen Quellen. Keine Anlageberatung.", "", "## Termine (nächste Tage)", ""]
    L += termine()
    L += ["", "## Marktlage", ""] + marktlage()
    L += block("Fed: Mitteilungen und Reden", lambda: rss("https://www.federalreserve.gov/feeds/press_all.xml", 4, 72)
               + rss("https://www.federalreserve.gov/feeds/speeches.xml", 3, 72))
    L += block("Weißes Haus (Präsident)", lambda: rss("https://www.whitehouse.gov/news/feed/", 6, 36))
    L += block("Geopolitik (Iran, Israel, Russland, China ...)", lambda: gnews(
        '(Iran OR Israel OR Russia OR Ukraine OR China OR Taiwan OR "Middle East" OR sanctions OR OPEC) (markets OR oil OR stocks)'))
    L += block("Zölle und Handel", lambda: gnews('(tariffs OR "trade war" OR "trade deal") (markets OR stocks OR economy)'))
    L += block("Fed und Zinsen in den Nachrichten", lambda: gnews('("Federal Reserve" OR "Jerome Powell" OR "Fed rate" OR "rate cut" OR "US inflation") markets'))
    L += block("Wirtschaft auf Deutsch (tagesschau)", lambda: rss("https://www.tagesschau.de/wirtschaft/index~rss2.xml", 5, 30))
    L += bot_lage()
    L += ["", "---", "⚠️ = Schlagzeile mit Risiko-Stichwort (Krieg, Angriff, Zölle, Sanktionen ...). "
          "Quellen: federalreserve.gov, whitehouse.gov, bls.gov, Google News, tagesschau.de, Yahoo Finance."]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("Briefing geschrieben: %s (%d Zeilen)" % (OUT, len(L)))
    topic = os.environ.get("NTFY_TOPIC")
    if topic:
        kurz = [l for l in L if l.startswith("| ") and "heute" in l][:4] + [l for l in L if l.startswith("- ⚠️")][:4]
        body = "\n".join(re.sub(r"\]\(.*?\)", "]", l) for l in kurz) or "Keine besonderen Termine oder Warnungen."
        req = urllib.request.Request("https://ntfy.sh/" + topic, data=body.encode("utf-8"), method="POST",
                                     headers={"Title": "Markt-Briefing %s" % BERLIN.strftime("%d.%m. %H:%M"), "Tags": "chart_with_upwards_trend"})
        try:
            urllib.request.urlopen(req, timeout=20)
            print("Push-Nachricht gesendet.")
        except Exception as e:
            print("Push fehlgeschlagen: %s" % e)


if __name__ == "__main__":
    main()
