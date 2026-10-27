"""Schreibt die Ergebnisse des Strategie-Labors in eine Excel-Datei (wird von strategielabor.py aufgerufen).

Blaetter: Uebersicht, Top 25 robust, Top 25 Rendite, Beste je Gruppe, Beste je Markt, Kurze Historie,
Jahresrenditen, Vergleich, Alle Strategien, Intraday (1h), Lexikon, Methodik.
Abgeleitete Werte (Robust-Score, Rang, Calmar, "schlaegt SPY?", Anteile) sind Excel-Formeln.
"""
import bisect

import xlsx_mini as X

Q = X.sheet_ref
UEB, TOP, TOPR, GRP, MKT, SHORT = "Übersicht", "Top 25 robust", "Top 25 Rendite", "Beste je Gruppe", "Beste je Markt", "Kurze Historie"
YRS, VGL, ALLE, INTRA, LEX, METH = "Jahresrenditen", "Vergleich", "Alle Strategien", "Intraday (1h)", "Lexikon", "Methodik"
PAPER = "Papier-Test (live)"
LISTE = {"robust": "Top 25 robust", "rendite": "Top 25 Rendite", "vergleich": "Vergleich"}


def gv(m, k):
    return None if not m or m.get(k) is None else m[k]


def ng(m, k):
    v = gv(m, k)
    return -v if v is not None else None


def put_header(sh, r, cols, height=48):
    for c, (name, width, _st) in enumerate(cols):
        sh.set(r, c, name, "head")
        sh.width(c, width)
    sh.heights[r] = height


def put_row(sh, r, cols, vals, hl=False):
    for c, v in enumerate(vals):
        st = cols[c][2]
        if hl:
            st = {"text": "hl", "pct": "hl_pct", "dec": "hl_dec", "int": "hl_int", "one": "hl_one"}.get(st, "hl")
        if isinstance(v, tuple):
            sh.set(r, c, v[0], st, v[1])
        else:
            sh.set(r, c, v, st)


def title(sh, text, note=None):
    sh.set(0, 0, text, "title")
    sh.heights[0] = 26
    if note:
        sh.set(1, 0, note, "note")


def build_excel(rows, ana, info, path):
    mk = lambda u: info["uni_info"].get(u, u)
    fp = info["fmt_p"]
    spy = ana["spy"]
    spy_c = spy["C"]["sharpe"]
    g_start = info["g_start"]

    def first_date(r):
        g = r.get("G")
        if g:
            return g.get("von") or g_start
        b = r.get("B") or r.get("C")
        return (b.get("von") if b else None) or "-"

    # ---------------- Vergleich (zuerst, weil andere Blaetter auf SPY verweisen) ----------------
    vg = X.Sheet(VGL)
    title(vg, "Vergleichswerte: einfach kaufen und halten",
          "Diese Werte muss eine Strategie schlagen. A = 2005-2012, B = 2013-2019, C = 2020-heute (Test-Zeitraum).")
    vcols = [("Markt", 14, "text"), ("Beschreibung", 46, "text"), ("Sharpe A", 9, "dec"), ("Sharpe B", 9, "dec"),
             ("Sharpe C (Test)", 9, "dec"), ("Rendite p.a. A", 10, "pct"), ("Rendite p.a. B", 10, "pct"),
             ("Rendite p.a. C (Test)", 10, "pct"), ("Max. Verlust C", 10, "pct"), ("Rendite p.a. 2005-heute", 11, "pct"),
             ("Max. Verlust 2005-heute", 11, "pct"), ("Volatilität p.a. 2005-heute", 11, "pct"), ("Daten ab", 11, "text")]
    put_header(vg, 3, vcols)
    bench = sorted(ana["bench"], key=lambda r: (r["uni"] != "SPY" or r["fam"] != "Kaufen & Halten", r["fam"] != "Kaufen & Halten", r["uni"]))
    assert bench[0] is spy
    for i, r in enumerate(bench):
        bh = r["fam"] == "Kaufen & Halten"
        put_row(vg, 4 + i, vcols, [r["uni"] if bh else "60/40",
                                   mk(r["uni"]) if bh else "60 % S&P 500, 40 % Anleihen (monatlich ausgeglichen)",
                                   gv(r["A"], "sharpe"), gv(r["B"], "sharpe"), gv(r["C"], "sharpe"),
                                   gv(r["A"], "cagr"), gv(r["B"], "cagr"), gv(r["C"], "cagr"), ng(r["C"], "mdd"),
                                   gv(r["G"], "cagr"), ng(r["G"], "mdd"), gv(r["G"], "vol"), first_date(r)], hl=(i == 0))
    vg.freeze = (4, 1)
    last_v = 3 + len(bench)
    vg.scale(4, 4, last_v, 4)
    vg.scale(4, 7, last_v, 7)
    spy_sh, spy_cagr = "%s!$E$5" % Q(VGL), "%s!$H$5" % Q(VGL)

    # ---------------- Alle Strategien ----------------
    al = X.Sheet(ALLE)
    acols = [("ID", 7, "int"), ("Gruppe", 20, "text"), ("Strategie", 30, "text"), ("Markt", 34, "text"),
             ("Parameter", 38, "text"), ("Daten ab", 11, "text"), ("Trades A", 8, "int"), ("Trades B", 8, "int"),
             ("Sharpe A (2005-12)", 9, "dec"), ("Sharpe B (2013-19)", 9, "dec"),
             ("Robust-Score = min(Sharpe A, B)", 10, "dec"), ("Rang (robust)", 8, "int"),
             ("Rendite p.a. A", 9, "pct"), ("Rendite p.a. B", 9, "pct"), ("Rendite p.a. C (Test 2020-heute)", 11, "pct"),
             ("Sharpe C (Test)", 9, "dec"), ("Max. Verlust C (Test)", 9, "pct"), ("Rendite p.a. 2005-heute", 10, "pct"),
             ("Gesamtrendite 2005-heute", 11, "pct"), ("Volatilität p.a.", 9, "pct"), ("Sharpe 2005-heute", 9, "dec"),
             ("Sortino 2005-heute", 9, "dec"), ("Max. Verlust 2005-heute", 9, "pct"),
             ("Calmar (Rendite / Max. Verlust)", 10, "dec"), ("Längste Verlustphase (Monate)", 10, "one"),
             ("Investiert (Anteil der Zeit)", 10, "pct"), ("Trades pro Jahr", 8, "one"), ("Beta zu SPY", 8, "dec"),
             ("Korrelation zu SPY", 9, "dec"), ("Gewinnmonate", 9, "pct"), ("Bestes Jahr", 9, "pct"),
             ("Schlechtestes Jahr", 10, "pct"), ("Kosten je Order", 8, "pct2"), ("Schlägt SPY im Test (Sharpe)?", 10, "text"),
             ("Papier-Test: Rendite seit Start", 11, "pct"), ("Papier-Test: Max. Verlust seit Start", 11, "pct")]
    put_header(al, 0, acols, 62)

    def xl_score(r):
        sa, sb, ta, tb = gv(r["A"], "sharpe"), gv(r["B"], "sharpe"), gv(r["A"], "trades"), gv(r["B"], "trades")
        if sa is not None and sb is not None and (ta or 0) >= 5 and (tb or 0) >= 5:
            return min(sa, sb)
        return ""
    xs = {r["id"]: xl_score(r) for r in rows}
    neg = sorted(-v for v in xs.values() if v != "")
    rank = {i: (1 + bisect.bisect_left(neg, -v) if v != "" else "") for i, v in xs.items()}
    order = sorted(rows, key=lambda r: (xs[r["id"]] == "", -(xs[r["id"]] or 0), -(gv(r["G"], "sharpe") or -99)))
    last = len(order) + 1
    for i, r in enumerate(order):
        rr = i + 2
        A_, B_, C_, G_ = r["A"], r["B"], r["C"], r["G"]
        cg, mg = gv(G_, "cagr"), ng(G_, "mdd")
        cal = cg / abs(mg) if cg is not None and mg is not None and mg < 0 else ""
        ys = [v for v in (r.get("jahre") or {}).values() if v is not None]
        beat = ("ja" if C_["sharpe"] > spy_c else "nein") if C_ else ""
        put_row(al, i + 1, acols, [
            r["id"], r["grp"], r["fam"], mk(r["uni"]), fp(r["p"]), first_date(r), gv(A_, "trades"), gv(B_, "trades"),
            gv(A_, "sharpe"), gv(B_, "sharpe"),
            (xs[r["id"]], 'IF(AND(ISNUMBER(I%d),ISNUMBER(J%d),N(G%d)>=5,N(H%d)>=5),MIN(I%d,J%d),"")' % ((rr,) * 6)),
            (rank[r["id"]], 'IF(ISNUMBER(K%d),RANK(K%d,$K$2:$K$%d),"")' % (rr, rr, last)),
            gv(A_, "cagr"), gv(B_, "cagr"), gv(C_, "cagr"), gv(C_, "sharpe"), ng(C_, "mdd"),
            cg, gv(G_, "total"), gv(G_, "vol"), gv(G_, "sharpe"), gv(G_, "sortino"), mg,
            (cal, 'IF(AND(ISNUMBER(R%d),ISNUMBER(W%d)),IF(W%d<0,R%d/ABS(W%d),""),"")' % ((rr,) * 5)),
            G_["dd_tage"] / 21.0 if G_ else None, gv(G_, "expo"), gv(G_, "tpj"), gv(G_, "beta"), gv(G_, "korr"),
            gv(G_, "mon_pos"), max(ys) if ys else None, min(ys) if ys else None, r["cost"],
            (beat, 'IF(ISNUMBER(P%d),IF(P%d>%s,"ja","nein"),"")' % (rr, rr, spy_sh)),
            gv(r.get("LIVE"), "rendite"), ng(r.get("LIVE"), "mdd")])
    al.freeze = (1, 5)
    al.filter = (0, 0, last - 1, len(acols) - 1)
    for c in (14, 15, 16, 17, 20, 22, 23):
        al.scale(1, c, last - 1, c)

    # ---------------- Papier-Test (live) ----------------
    pt = X.Sheet(PAPER)
    spl = spy.get("LIVE")
    live_start = info.get("live_start") or "-"
    if spl:
        note = ("Start %s (gerechnet ab Schlusskurs des Vortags), Stand %s: %d Handelstage. Jede Strategie läuft mit echten neuen "
                "Kursen weiter, mit denselben Regeln, Kosten und Ausführung wie im Backtest. Die Liste unten wurde am Start "
                "eingefroren; alle übrigen Varianten stehen mit ihren Live-Werten im Blatt '%s' (letzte Spalten)."
                % (spl["von"], spl["bis"], spl["tage"], ALLE))
    else:
        note = ("Start %s: noch keine Handelstage seit dem Start. Die ersten Ergebnisse erscheinen nach dem ersten Handelstag; "
                "die Datei wird jeden Börsentag automatisch neu berechnet." % live_start)
    title(pt, "Papier-Test: Strategien mit echten neuen Kursen", note)
    pt.heights[1] = 42
    pt.merge(1, 0, 1, 11)
    pt.set(2, 0, "S&P 500 halten seit Start", "key")
    pt.set(2, 1, spl["rendite"] if spl else None, "keypct")
    pcols = [("Liste", 16, "text"), ("Rang in der Liste", 8, "int"), ("Gruppe", 20, "text"), ("Strategie", 30, "text"),
             ("Markt", 34, "text"), ("Parameter", 38, "text"), ("Handelstage", 9, "int"), ("Rendite seit Start", 10, "pct"),
             ("Max. Verlust seit Start", 10, "pct"), ("Investiert", 9, "pct"), ("Trades", 8, "int"),
             ("Besser als SPY seit Start?", 10, "text"), ("Backtest: Rendite p.a. C (Test)", 11, "pct"),
             ("Backtest: Sharpe C (Test)", 10, "dec")]
    put_header(pt, 4, pcols, 48)
    paper = ana.get("paper") or []
    for k, (it, r) in enumerate(paper):
        rr, L = 6 + k, (r.get("LIVE") if r else None)
        better = ("ja" if L["rendite"] > spl["rendite"] else "nein") if (L and spl) else ""
        put_row(pt, 5 + k, pcols, [LISTE.get(it["liste"], it["liste"]), it["rang"], r["grp"] if r else "", it["fam"],
                                   mk(it["uni"]), fp(it["p"]), gv(L, "tage"), gv(L, "rendite"), ng(L, "mdd"), gv(L, "expo"),
                                   gv(L, "trades"),
                                   (better, 'IF(AND(ISNUMBER(H%d),ISNUMBER($B$3)),IF(H%d>$B$3,"ja","nein"),"")' % (rr, rr)),
                                   gv(r["C"], "cagr") if r else None, gv(r["C"], "sharpe") if r else None],
                hl=(it["liste"] == "vergleich"))
    n_paper_beat = sum(1 for it, r in paper if it["liste"] != "vergleich" and r and r.get("LIVE") and spl
                       and r["LIVE"]["rendite"] > spl["rendite"])
    if paper:
        pt.scale(5, 7, 4 + len(paper), 7)
    rg = 6 + len(paper)
    pt.set(rg, 0, "Alle Varianten nach Gruppe", "h2")
    gcols = [("Gruppe", 16, "text"), ("Varianten", 8, "int"), ("Median-Rendite seit Start", 20, "pct"),
             ("Besser als SPY seit Start", 30, "int")]
    for c, (name, _w, _s) in enumerate(gcols):
        pt.set(rg + 1, c, name, "head")
    groups = {}
    for r in rows:
        if r.get("LIVE") and r["grp"] != "Vergleich":
            groups.setdefault(r["grp"], []).append(r["LIVE"]["rendite"])
    for k, (g, v) in enumerate(sorted(groups.items())):
        v.sort()
        pt.set(rg + 2 + k, 0, g, "text")
        pt.set(rg + 2 + k, 1, len(v), "int")
        pt.set(rg + 2 + k, 2, v[len(v) // 2], "pct")
        pt.set(rg + 2 + k, 3, sum(1 for x in v if spl and x > spl["rendite"]), "int")
    if not groups:
        pt.set(rg + 2, 0, "noch keine Live-Daten", "note")
    pt.freeze = (5, 4)

    # ---------------- Top 25 robust ----------------
    tp = X.Sheet(TOP)
    title(tp, "Die 25 robustesten Strategien",
          "Rang nach Robust-Score = kleinere Sharpe aus A (2005-2012) und B (2013-2019); je Strategie und Markt nur die beste "
          "Variante. Spalten J bis M zeigen den Test-Zeitraum 2020-heute, der für die Auswahl nie benutzt wurde.")
    tcols = [("ID", 7, "int"), ("Rang (robust, alle Varianten)", 9, "int"), ("Gruppe", 20, "text"), ("Strategie", 30, "text"),
             ("Markt", 34, "text"), ("Parameter", 38, "text"), ("Sharpe A", 8, "dec"), ("Sharpe B", 8, "dec"),
             ("Robust-Score", 9, "dec"), ("Rendite p.a. C (Test)", 10, "pct"), ("Sharpe C (Test)", 9, "dec"),
             ("Max. Verlust C (Test)", 10, "pct"), ("Sharpe C bei 3,3-fachen Kosten", 11, "dec"),
             ("Rendite p.a. 2005-heute", 10, "pct"), ("Max. Verlust 2005-heute", 10, "pct"), ("Volatilität p.a.", 9, "pct"),
             ("Investiert", 9, "pct"), ("Trades pro Jahr", 8, "one"), ("Schlägt SPY im Test (Sharpe)?", 10, "text")]
    put_header(tp, 3, tcols)
    spy_row = 30                                   # Zeile 31 in Excel

    def top_vals(r, rr, k):
        C_, G_, h = r["C"], r["G"], r.get("C_teuer")
        return [r["id"], (rank.get(r["id"], ""), "IFERROR(INDEX(%s!$L:$L,MATCH(A%d,%s!$A:$A,0)),\"\")" % (Q(ALLE), rr, Q(ALLE), )),
                r["grp"], r["fam"], mk(r["uni"]), fp(r["p"]), gv(r["A"], "sharpe"), gv(r["B"], "sharpe"),
                (min(r["A"]["sharpe"], r["B"]["sharpe"]), "MIN(G%d,H%d)" % (rr, rr)),
                gv(C_, "cagr"), gv(C_, "sharpe"), ng(C_, "mdd"), gv(h, "sharpe"), gv(G_, "cagr"), ng(G_, "mdd"),
                gv(G_, "vol"), gv(G_, "expo"), gv(G_, "tpj"),
                ("ja" if C_["sharpe"] > spy_c else "nein", 'IF(K%d>$K$%d,"ja","nein")' % (rr, spy_row + 1))]
    for k, r in enumerate(ana["top"]):
        put_row(tp, 4 + k, tcols, top_vals(r, 5 + k, k))
    s = spy
    put_row(tp, spy_row, tcols, [s["id"], "", "Vergleich", "Kaufen & Halten", mk("SPY"), "-", gv(s["A"], "sharpe"),
                                 gv(s["B"], "sharpe"), (min(s["A"]["sharpe"], s["B"]["sharpe"]), "MIN(G%d,H%d)" % (spy_row + 1, spy_row + 1)),
                                 gv(s["C"], "cagr"), gv(s["C"], "sharpe"), ng(s["C"], "mdd"), None, gv(s["G"], "cagr"),
                                 ng(s["G"], "mdd"), gv(s["G"], "vol"), gv(s["G"], "expo"), gv(s["G"], "tpj"), ""], hl=True)
    tp.freeze = (4, 4)
    n_top = len(ana["top"])
    for c in (9, 10, 11):
        tp.scale(4, c, 3 + n_top, c)

    # ---------------- Top 25 Rendite ----------------
    tr = X.Sheet(TOPR)
    title(tr, "Die 25 renditestärksten robusten Strategien",
          "Rang nach der kleineren Jahresrendite aus A (2005-2012) und B (2013-2019), nur Strategien, die mindestens 30 % der Zeit "
          "investiert sind; je Strategie und Markt die beste Variante. Spalten I bis L zeigen den Test-Zeitraum 2020-heute.")
    rcols = [("ID", 7, "int"), ("Gruppe", 20, "text"), ("Strategie", 30, "text"), ("Markt", 34, "text"), ("Parameter", 38, "text"),
             ("Rendite p.a. A", 9, "pct"), ("Rendite p.a. B", 9, "pct"), ("Score = min(Rendite A, B)", 10, "pct"),
             ("Rendite p.a. C (Test)", 10, "pct"), ("Max. Verlust C (Test)", 10, "pct"), ("Sharpe C (Test)", 9, "dec"),
             ("Rendite C bei 3,3-fachen Kosten", 11, "pct"), ("Rendite p.a. 2005-heute", 10, "pct"),
             ("Max. Verlust 2005-heute", 10, "pct"), ("Volatilität p.a.", 9, "pct"), ("Investiert", 9, "pct"),
             ("Trades pro Jahr", 8, "one"), ("Schlägt SPY im Test (Rendite)?", 10, "text")]
    put_header(tr, 3, rcols)
    for k, r in enumerate(ana["topr"]):
        rr, C_, G_, h = 5 + k, r["C"], r["G"], r.get("C_teuer")
        put_row(tr, 4 + k, rcols, [r["id"], r["grp"], r["fam"], mk(r["uni"]), fp(r["p"]), gv(r["A"], "cagr"),
                                   gv(r["B"], "cagr"), (min(r["A"]["cagr"], r["B"]["cagr"]), "MIN(F%d,G%d)" % (rr, rr)),
                                   gv(C_, "cagr"), ng(C_, "mdd"), gv(C_, "sharpe"), gv(h, "cagr"), gv(G_, "cagr"),
                                   ng(G_, "mdd"), gv(G_, "vol"), gv(G_, "expo"), gv(G_, "tpj"),
                                   ("ja" if C_["cagr"] > spy["C"]["cagr"] else "nein", 'IF(I%d>$I$%d,"ja","nein")' % (rr, spy_row + 1))])
    put_row(tr, spy_row, rcols, [s["id"], "Vergleich", "Kaufen & Halten", mk("SPY"), "-", gv(s["A"], "cagr"), gv(s["B"], "cagr"),
                                 (min(s["A"]["cagr"], s["B"]["cagr"]), "MIN(F%d,G%d)" % (spy_row + 1, spy_row + 1)),
                                 gv(s["C"], "cagr"), ng(s["C"], "mdd"), gv(s["C"], "sharpe"), None, gv(s["G"], "cagr"),
                                 ng(s["G"], "mdd"), gv(s["G"], "vol"), gv(s["G"], "expo"), gv(s["G"], "tpj"), ""], hl=True)
    tr.freeze = (4, 3)
    for c in (8, 9, 10):
        tr.scale(4, c, 3 + len(ana["topr"]), c)

    # ---------------- Beste je Gruppe / Markt ----------------
    def best_sheet(name, head, note, items, label):
        sh = X.Sheet(name)
        title(sh, head, note)
        cols = [(label, 34, "text"), ("Getestete Varianten", 10, "int"), ("Beste Strategie (nach Robust-Score)", 32, "text"),
                ("Markt", 34, "text"), ("Parameter", 36, "text"), ("Robust-Score", 9, "dec"), ("Rendite p.a. C (Test)", 10, "pct"),
                ("Sharpe C (Test)", 9, "dec"), ("Max. Verlust C (Test)", 10, "pct"), ("Rendite p.a. 2005-heute", 10, "pct"),
                ("Max. Verlust 2005-heute", 10, "pct"), ("Varianten mit besserer Sharpe als SPY im Test", 12, "int"),
                ("Anteil", 9, "pct")]
        put_header(sh, 3, cols, 60)
        items = sorted([g for g in items if g["best"]], key=lambda g: -(g["best"]["score"] if g["best"]["score"] is not None else -9))
        for k, g in enumerate(items):
            b, rr = g["best"], 5 + k
            put_row(sh, 4 + k, cols, [g["key_label"], g["n"], b["fam"] + (" (nur B/C)" if g["nur_bc"] else ""), mk(b["uni"]),
                                      fp(b["p"]), b["score"], gv(b["C"], "cagr"), gv(b["C"], "sharpe"), ng(b["C"], "mdd"),
                                      gv(b["G"], "cagr"), ng(b["G"], "mdd"), g["beat"],
                                      (g["beat"] / g["n"] if g["n"] else "", 'IF(B%d>0,L%d/B%d,"")' % (rr, rr, rr))])
        sh.freeze = (4, 1)
        for c in (6, 7, 12):
            sh.scale(4, c, 3 + len(items), c)
        return sh
    for g in ana["by_group"]:
        g["key_label"] = g["key"]
    gs = best_sheet(GRP, "Beste Strategie je Gruppe", "Je Strategie-Gruppe die Variante mit dem höchsten Robust-Score "
                    "(bei Gruppen ohne Zeitraum A: höchste Sharpe in B). Anteil = wie viele Varianten der Gruppe im Test "
                    "eine bessere Sharpe hatten als SPY halten.", ana["by_group"], "Gruppe")
    for g in ana["by_market"]:
        g["key_label"] = mk(g["key"])
    ms = best_sheet(MKT, "Beste Strategie je Markt", "Je Markt die Variante mit dem höchsten Robust-Score (bei Märkten ohne "
                    "Zeitraum A, z. B. Krypto und VIX-ETFs: höchste Sharpe in B).", ana["by_market"], "Markt")

    # ---------------- Kurze Historie ----------------
    sh_s = X.Sheet(SHORT)
    title(sh_s, "Strategien mit kurzer Historie (kein Zeitraum A)",
          "Krypto, VIX-ETFs und andere Werte, die erst nach 2005 starten. Rang nach Sharpe in B (2013-2019); Test = C (2020-heute). "
          "Weniger aussagekräftig, weil nur ein Auswahl-Zeitraum vorhanden ist.")
    scols = [("Rang", 6, "int"), ("Gruppe", 20, "text"), ("Strategie", 30, "text"), ("Markt", 34, "text"), ("Parameter", 38, "text"),
             ("Daten ab", 11, "text"), ("Sharpe B", 9, "dec"), ("Rendite p.a. B", 10, "pct"), ("Sharpe C (Test)", 9, "dec"),
             ("Rendite p.a. C (Test)", 10, "pct"), ("Max. Verlust C (Test)", 10, "pct"), ("Sharpe C bei 3,3-fachen Kosten", 11, "dec"),
             ("Volatilität p.a.", 9, "pct")]
    put_header(sh_s, 3, scols)
    for k, r in enumerate(ana["short"]):
        put_row(sh_s, 4 + k, scols, [k + 1, r["grp"], r["fam"], mk(r["uni"]), fp(r["p"]), first_date(r), gv(r["B"], "sharpe"),
                                     gv(r["B"], "cagr"), gv(r["C"], "sharpe"), gv(r["C"], "cagr"), ng(r["C"], "mdd"),
                                     gv(r.get("C_teuer"), "sharpe"), gv(r["G"], "vol") if r["G"] else gv(r["C"], "vol")])
    sh_s.freeze = (4, 3)
    for c in (8, 9, 10):
        sh_s.scale(4, c, 3 + len(ana["short"]), c)

    # ---------------- Jahresrenditen ----------------
    yr = X.Sheet(YRS)
    title(yr, "Jahresrenditen", "Vergleichswerte und die 25 robustesten Strategien, Kalenderjahr für Kalenderjahr "
          "(%s = bis %s)." % (info["datum"][:4], info["datum"]))
    years = sorted(spy["jahre"])
    ycols = [("Strategie", 30, "text"), ("Markt", 30, "text"), ("Parameter", 34, "text")] + \
            [(y, 8, "pct") for y in years] + [("Rendite p.a. 2005-heute", 10, "pct")]
    put_header(yr, 3, ycols, 36)
    yrows = [r for r in bench if r["fam"] == "Kaufen & Halten" and r["uni"] in ("SPY", "QQQ")] + \
            [r for r in bench if r["fam"] != "Kaufen & Halten"] + list(ana["top"])
    for k, r in enumerate(yrows):
        put_row(yr, 4 + k, ycols, [r["fam"], mk(r["uni"]), fp(r["p"])] + [r["jahre"].get(y) for y in years] +
                [gv(r["G"], "cagr")], hl=(r["fam"] in ("Kaufen & Halten", "60/40 SPY/AGG")))
    yr.freeze = (4, 1)
    yr.scale(4, 3, 3 + len(yrows), 2 + len(years))

    # ---------------- Intraday ----------------
    it = X.Sheet(INTRA)
    intra = info.get("intraday") or []
    if intra:
        r0 = intra[0]
        title(it, "Intraday-Strategien auf Stundenkursen",
              "Nur ca. 2 Jahre Daten (Yahoo liefert Stundenkurse für 730 Tage): Auswahl %s bis %s, Test %s bis %s. "
              "Deshalb wenig aussagekräftig. Rang nach Sharpe im Auswahl-Zeitraum." % (r0["von"], r0["mitte"], r0["mitte"], r0["bis"]))
    icols = [("Strategie", 32, "text"), ("ETF", 8, "text"), ("Parameter", 44, "text"), ("Sharpe Auswahl", 9, "dec"),
             ("Sharpe Test", 9, "dec"), ("Rendite Test (gesamt)", 10, "pct"), ("Max. Verlust Test", 10, "pct"), ("Trades Test", 8, "int")]
    put_header(it, 3, icols)
    cand = sorted([r for r in intra if r["fam"] != "Kaufen & Halten" and r["train"] and r["train"]["trades"] >= 20],
                  key=lambda r: -r["train"]["sharpe"])[:20]
    k = 0
    for r in cand + [r for r in intra if r["fam"] == "Kaufen & Halten"]:
        bh = r["fam"] == "Kaufen & Halten"
        put_row(it, 4 + k, icols, [r["fam"], r["sym"], fp(r["p"]), gv(r["train"], "sharpe"), gv(r["test"], "sharpe"),
                                   gv(r["test"], "rendite"), ng(r["test"], "mdd"), None if bh else gv(r["test"], "trades")], hl=bh)
        k += 1
    it.freeze = (4, 1)

    # ---------------- Lexikon ----------------
    lx = X.Sheet(LEX)
    title(lx, "Lexikon der getesteten Strategien", "Was jede Strategie-Familie macht, in welchen Märkten sie getestet wurde "
          "und wie viele Varianten (Parameter-Kombinationen x Märkte) es gab.")
    lcols = [("Strategie", 32, "text"), ("Gruppe", 24, "text"), ("Beschreibung", 80, "wrap"), ("Märkte", 50, "wrap"), ("Varianten", 9, "int")]
    put_header(lx, 3, lcols, 30)
    fams = sorted(info["fams"].items(), key=lambda kv: (kv[1]["grp"], kv[0]))
    for k, (name, e) in enumerate(fams):
        put_row(lx, 4 + k, lcols, [name, e["grp"], info["desc"].get(name, ""), ", ".join(e["unis"]), e["n"]])
    lx.freeze = (4, 1)

    # ---------------- Methodik ----------------
    me = X.Sheet(METH)
    title(me, "Methodik, Annahmen und Grenzen")
    me.width(0, 34)
    me.width(1, 120)
    lines = [
        ("Ziel", "Herausfinden, welche Handelsstrategien in der Vergangenheit robust funktioniert hätten, und zeigen, "
                 "wie verlässlich solche Backtests sind."),
        ("Daten", "Tageskurse von Yahoo Finance (dividendenbereinigt) vom %s bis %s, %d Handelstage; CBOE-Optionsindizes "
                  "über Yahoo; Termine der Quartalszahlen aus SEC EDGAR (8-K-Meldungen mit Item 2.02); Cash-Zins = "
                  "13-Wochen-T-Bill (^IRX). Nicht verfügbar: %s." % (info["erster_tag"], info["datum"], info["n_tage"],
                                                                     ", ".join(info["fehlend"]) or "-")),
        ("Zeiträume", "A = 2005-2012 (inkl. Finanzkrise), B = 2013-2019, C = 2020 bis heute. Gesamt = 2005 bis heute. "
                      "Werte, die erst später starten (z. B. Krypto, VIX-ETFs), haben keinen Zeitraum A und stehen im Blatt "
                      "'Kurze Historie'."),
        ("Auswahl", "Robust-Score = kleinere Sharpe-Ratio aus A und B, mindestens 5 Trades in A und in B. Der Test-Zeitraum C "
                    "wurde nie zur Auswahl benutzt. Eine Strategie zählt nur, wenn sie auch in C trägt."),
        ("Ausführung", "Signal zum Tagesschluss, Order zur nächsten Eröffnung (kein Blick in die Zukunft). Tageshandel "
                       "entscheidet zur Eröffnung und verkauft zum Schluss. Kalender-Strategien handeln zum Schluss (Termine "
                       "stehen vorher fest). Overnight kauft zum Schluss und verkauft zur Eröffnung."),
        ("Kosten", "Je Kauf oder Verkauf, je nach Markt (Tabelle unten). In den Top-Listen zusätzlich mit %.1f-fachen Kosten "
                   "gegengerechnet. Leerverkauf: %.1f %% Leihgebühr pro Jahr; Erlöse aus Leerverkäufen bringen keine Zinsen. "
                   "Steuern sind nicht berücksichtigt." % (info["high_x"], 100 * info["borrow"])),
        ("Hebel", "Simuliert wie ein täglich neu gehebelter ETF (z. B. TQQQ): Tagesrendite x Hebel, minus Finanzierung zum "
                  "T-Bill-Zins, minus %.2f %% Gebühr pro Jahr." % (100 * info["lev_fee"])),
        ("Gewichtung", "Timing-Strategien geben jedem Wert eines Markts den gleichen Anteil; nicht investiertes Geld liegt "
                       "verzinst als Cash. Rotations-Strategien kaufen die N ausgewählten Werte zu gleichen Teilen."),
        ("Kennzahlen", "Rendite p.a. = durchschnittliche jährliche Rendite. Sharpe = Überrendite über dem T-Bill-Zins geteilt "
                       "durch die Schwankung (annualisiert); SPY halten liegt langfristig bei etwa 0,5 bis 0,7. Sortino = wie "
                       "Sharpe, zählt aber nur Abwärtsschwankung. Max. Verlust = größter Rückgang vom Höchststand. Calmar = "
                       "Rendite p.a. geteilt durch Max. Verlust. Beta und Korrelation = Abhängigkeit vom S&P 500. Gewinnmonate "
                       "= Anteil der Monate mit Plus. Investiert = Anteil der Zeit, in der Geld im Markt ist."),
        ("Verlässlichkeit", "Zusammenhang zwischen Auswahl-Rang und Test-Ergebnis (Spearman): %.2f. Von den 50 robustesten "
                            "Strategien der Auswahl hatten im Test %d eine bessere Sharpe als SPY halten. Bei %d Varianten über "
                            "%.0f Jahre wäre die beste Sharpe allein durch Zufall etwa %.2f (die Varianten sind verwandt, die "
                            "echte Schwelle ist niedriger)." % (ana["rho"], ana["beat50"], len(ana["elig"]), ana["years_ab"], ana["luck"])),
        ("Grenzen", "Aktien-Universum = große US-Aktien von 2004; später pleitegegangene Firmen (Lehman, Washington Mutual, "
                    "Merrill Lynch u. a.) fehlen bei Yahoo, das macht Aktien-Ergebnisse eher zu gut. Fannie Mae und Freddie Mac "
                    "wurden wegen unrealistischer Pennystock-Sprünge entfernt. Optionsindizes sind nicht direkt handelbar und "
                    "enthalten keine Handelskosten. Krypto wird nur an US-Börsentagen gehandelt. Der Short-VIX-ETF SVXY hat 2018 "
                    "seinen Hebel von -1 auf -0,5 gesenkt. Die ML-Modelle sind bewusst einfach (lineares Modell, k-nächste "
                    "Nachbarn). Termine der Quartalszahlen gelten für 'Vor Quartalszahlen' als vorab bekannt."),
        ("Hinweis", "Keine Anlageberatung. Backtests überschätzen die Zukunft fast immer."),
    ]
    for k, (a, b) in enumerate(lines):
        me.set(2 + k, 0, a, "key")
        me.set(2 + k, 1, b, "keyval")
        me.heights[2 + k] = max(28, 14 * (len(b) // 150 + 1))
    r0 = 4 + len(lines)
    me.set(r0, 0, "Kosten je Order nach Markt", "h2")
    put_header(me, r0 + 1, [("Markt", 34, "text"), ("Beschreibung", 120, "text"), ("Kosten je Order", 10, "pct2")], 20)
    for k, (u, c) in enumerate(info["kosten"]):
        me.set(r0 + 2 + k, 0, u, "text")
        me.set(r0 + 2 + k, 1, mk(u), "text")
        me.set(r0 + 2 + k, 2, c, "pct2")

    # ---------------- Uebersicht ----------------
    ue = X.Sheet(UEB)
    n, nf = len(rows), len(info["fams"])
    nm = len({r["uni"] for r in rows})
    title(ue, "Strategie-Labor: Ergebnisse",
          "Kurse bis %s. Erstellt mit strategielabor.py (Ordner paperbot). Keine Anlageberatung." % info["datum"])
    for c, w in enumerate([46, 34, 34, 36, 12, 12, 12, 14]):
        ue.width(c, w)
    ue.set(3, 0, "Kennzahlen", "h2")
    kv = [("Getestete Varianten (ohne Vergleichswerte)",
           (ana["n_cand"], 'COUNTA(%s!$C:$C)-1-COUNTIF(%s!$B:$B,"Vergleich")' % (Q(ALLE), Q(ALLE))), "keyint"),
          ("Strategie-Familien", nf, "keyint"),
          ("Märkte", nm, "keyint"),
          ("Auswahl-Zeitraum", "A: 2005-2012 und B: 2013-2019", "keyval"),
          ("Test-Zeitraum (nie zur Auswahl benutzt)", "C: 2020 bis %s" % info["datum"], "keyval"),
          ("S&P 500 halten im Test: Rendite p.a.", (spy["C"]["cagr"], spy_cagr), "keypct"),
          ("S&P 500 halten im Test: Sharpe", (spy_c, spy_sh), "keydec"),
          ("Varianten mit besserer Sharpe als SPY im Test",
           (ana["beat_all"], 'COUNTIFS(%s!$AH:$AH,"ja",%s!$B:$B,"<>Vergleich")' % (Q(ALLE), Q(ALLE))), "keyint"),
          ("Anteil an allen Varianten", (ana["beat_all"] / ana["n_cand"] if ana["n_cand"] else 0, "B12/B5"), "keypct"),
          ("Zusammenhang Auswahl-Rang und Test (Spearman, 1 = perfekt)", ana["rho"], "keydec"),
          ("Glücks-Schwelle: beste Sharpe allein durch Zufall", ana["luck"], "keydec"),
          ("Papier-Test läuft seit", live_start, "keyval"),
          ("Papier-Test: Handelstage bisher", spl["tage"] if spl else 0, "keyint"),
          ("Papier-Test: S&P 500 seit Start", (spl["rendite"], "%s!$B$3" % Q(PAPER)) if spl else "-", "keypct"),
          ("Papier-Test: Strategien der Liste mit mehr Rendite als SPY",
           (n_paper_beat, 'COUNTIFS(%s!$L:$L,"ja",%s!$A:$A,"<>Vergleich")' % (Q(PAPER), Q(PAPER))), "keyint")]
    for k, (a, b, st) in enumerate(kv):
        ue.set(4 + k, 0, a, "key")
        if isinstance(b, tuple):
            ue.set(4 + k, 1, b[0], st, b[1])
        else:
            ue.set(4 + k, 1, b, st)
    # Bei Zeilenumbau auf B5/B12 achten: Zeile 5 = Varianten, Zeile 12 = Varianten besser als SPY.
    assert kv[0][0].startswith("Getestete Varianten") and kv[7][0].startswith("Varianten mit besserer")
    pc = lambda v: ("%.1f %%" % (100 * v)).replace(".", ",")
    dc = lambda v: ("%.2f" % v).replace(".", ",")
    t0, tr0 = ana["top"][0], ana["topr"][0]
    good_both = sum(1 for r in ana["elig"] if r["C"]["cagr"] > spy["C"]["cagr"] and r["C"]["mdd"] < spy["C"]["mdd"])
    facts = [
        "%d Varianten aus %d Strategie-Familien auf %d Märkten getestet. Ausgewählt wurde nur mit 2005-2019, "
        "geprüft mit 2020 bis heute." % (n, nf, nm),
        "Nur %d von %d Varianten (%s) hatten im Test eine bessere Sharpe-Ratio als einfaches Halten des S&P 500 (%s)."
        % (ana["beat_all"], ana["n_cand"], pc(ana["beat_all"] / max(1, ana["n_cand"])), dc(spy_c)),
        "Von den 50 robustesten Strategien der Auswahl schlagen im Test %d den S&P 500. Die Auswahl sagt die Zukunft nur "
        "schwach voraus (Spearman %s)." % (ana["beat50"], dc(ana["rho"])),
        "Robusteste Strategie: %s auf %s (%s). Im Test: %s pro Jahr, Sharpe %s, max. Verlust -%s. "
        "S&P 500 halten: %s pro Jahr, Sharpe %s, max. Verlust -%s." % (
            t0["fam"], mk(t0["uni"]), fp(t0["p"]), pc(t0["C"]["cagr"]), dc(t0["C"]["sharpe"]), pc(t0["C"]["mdd"]),
            pc(spy["C"]["cagr"]), dc(spy_c), pc(spy["C"]["mdd"])),
        "Renditestärkste robuste Strategie: %s auf %s (%s). Im Test: %s pro Jahr bei max. Verlust -%s." % (
            tr0["fam"], mk(tr0["uni"]), fp(tr0["p"]), pc(tr0["C"]["cagr"]), pc(tr0["C"]["mdd"])),
        "%d Varianten hatten im Test sowohl mehr Rendite als auch einen kleineren maximalen Verlust als der S&P 500. "
        "Ob das mehr ist als Glück, zeigt erst die Zukunft (Paper-Trading)." % good_both,
        "Keine Anlageberatung. Backtests überschätzen die Zukunft fast immer: Kosten, Steuern, Datenfehler und Überanpassung.",
    ]
    r = 4 + len(kv) + 1
    ue.set(r, 0, "Wichtigste Erkenntnisse", "h2")
    for k, f in enumerate(facts):
        ue.set(r + 1 + k, 0, "• " + f, "wrap")
        ue.merge(r + 1 + k, 0, r + 1 + k, 7)
        ue.heights[r + 1 + k] = 30
    r = r + 2 + len(facts)
    ue.set(r, 0, "Die 10 robustesten Strategien (Details im Blatt '%s')" % TOP, "h2")
    ocols = [("Strategie", 46, "text"), ("Markt", 34, "text"), ("Parameter", 34, "text"), ("Gruppe", 36, "text"),
             ("Rendite p.a. Test", 12, "pct"), ("Sharpe Test", 12, "dec"), ("Max. Verlust Test", 12, "pct"),
             ("Schlägt SPY (Sharpe)?", 14, "text")]
    put_header(ue, r + 1, ocols, 32)
    src = [("D", "fam"), ("E", "uni"), ("F", "p"), ("C", "grp"), ("J", None), ("K", None), ("L", None), ("S", None)]
    for k, rw in enumerate(ana["top"][:10]):
        tr_ = 5 + k                                  # Zeile im Blatt Top 25 robust
        cached = [rw["fam"], mk(rw["uni"]), fp(rw["p"]), rw["grp"], rw["C"]["cagr"], rw["C"]["sharpe"], -rw["C"]["mdd"],
                  "ja" if rw["C"]["sharpe"] > spy_c else "nein"]
        put_row(ue, r + 2 + k, ocols, [(cached[c], "%s!%s%d" % (Q(TOP), col, tr_)) for c, (col, _) in enumerate(src)])
    r = r + 13
    ue.set(r, 0, "Blätter in dieser Datei", "h2")
    sheets_info = [(PAPER, "Papier-Test: wie sich die Strategien seit dem Start mit echten neuen Kursen schlagen (täglich aktualisiert)."),
                   (TOP, "Die 25 robustesten Strategien (Auswahl 2005-2019) und wie sie im Test 2020-heute abgeschnitten haben."),
                   (TOPR, "Die 25 renditestärksten robusten Strategien."),
                   (GRP, "Beste Strategie je Gruppe (Trendfolge, Rücksetzer, Hebel, Optionen ...)."),
                   (MKT, "Beste Strategie je Markt (S&P 500, Nasdaq, Aktien, Krypto, Devisen ...)."),
                   (SHORT, "Strategien auf Werten mit kurzer Historie (Krypto, VIX-ETFs)."),
                   (YRS, "Jahr-für-Jahr-Renditen der besten Strategien und der Vergleichswerte."),
                   (VGL, "Kaufen & Halten als Maßstab für jeden Markt."),
                   (ALLE, "Alle Varianten mit allen Kennzahlen, filterbar (Pfeile in der Kopfzeile)."),
                   (INTRA, "Intraday-Strategien auf Stundenkursen (nur ca. 2 Jahre Daten)."),
                   (LEX, "Was jede Strategie macht."),
                   (METH, "Methodik, Annahmen, Kosten und Grenzen.")]
    for k, (a, b) in enumerate(sheets_info):
        ue.set(r + 1 + k, 0, a, "bold")
        ue.set(r + 1 + k, 1, b, "text")
        ue.merge(r + 1 + k, 1, r + 1 + k, 7)

    X.save([ue, pt, tp, tr, gs, ms, sh_s, yr, vg, al, it, lx, me], path, title="Strategie-Labor", author="strategielabor.py")
    return path
