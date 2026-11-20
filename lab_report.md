# Strategie-Labor v2: Ergebnis

Kurse bis 2026-11-19. **9449 Varianten**, 7989 davon mit Auswahl-Zeitraum A+B, 665 nur mit B+C (kurze Historie).

SPY halten im Test (2020-heute): 13.9 % p.a., Sharpe 0.61, max. Verlust -34.0 %.

## Top 10 robust (Rang = min(Sharpe A, Sharpe B), geprueft im Test C)

| # | Strategie | Markt | Parameter | Sharpe A | Sharpe B | Sharpe C | Rendite C | Max. Verlust C | Sharpe C teuer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | VAA (Keller) | TAA | set=G4, top=2, breite=1 | 0.96 | 0.99 | **0.25** | 5.1 % | -20.5 % | 0.16 |
| 2 | Risk-Parity | MULTI | n=126, trend=200 | 0.90 | 0.92 | **0.34** | 4.7 % | -10.1 % | 0.31 |
| 3 | Hebel + Trendfilter | HEBEL-QQQ | L=1.0, regel=vola-regime, ausweich=IEF | 0.89 | 1.15 | **1.02** | 21.3 % | -21.6 % | 0.97 |
| 4 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | 0.84 | 0.85 | **0.40** | 6.1 % | -19.4 % | 0.27 |
| 5 | DAA (Keller) | TAA | top=6, breite=1 | 0.84 | 0.91 | **0.41** | 6.6 % | -17.7 % | 0.31 |
| 6 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 0.81 | 0.91 | **0.45** | 10.1 % | -29.1 % | 0.42 |
| 7 | Williams-%R | SPY | n=10, x=-90, trend=200 | 0.92 | 0.81 | **0.20** | 4.7 % | -31.1 % | 0.14 |
| 8 | PAA (Keller) | TAA | L=126, schutz=1, top=6, anleihe=IEF | 0.91 | 0.81 | **0.43** | 7.0 % | -21.0 % | 0.38 |
| 9 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | 0.80 | 0.85 | **0.47** | 7.6 % | -15.0 % | 0.41 |
| 10 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | 0.83 | 0.80 | **-0.02** | 2.5 % | -19.4 % | -0.03 |

## Top 10 Rendite (Rang = min(Rendite A, Rendite B), mind. 30 % investiert)

| # | Strategie | Markt | Parameter | Rendite A | Rendite B | Rendite C | Max. Verlust C | Sharpe C |
|---|---|---|---|---|---|---|---|---|
| 1 | Hebel + Trendfilter | HEBEL-QQQ | L=3.0, regel=vola-regime, ausweich=IEF | 32.2 % | 41.3 % | **55.6 %** | -56.9 % | 1.06 |
| 2 | Hebel + Trendfilter | HEBEL-SPY | L=3.0, regel=sma200-band, ausweich=IEF | 17.0 % | 28.7 % | **14.7 %** | -61.8 % | 0.47 |
| 3 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | 16.7 % | 14.5 % | **15.0 %** | -44.6 % | 0.58 |
| 4 | Vola-Regime | QQQ | k=1.2 | 13.0 % | 14.4 % | **22.1 %** | -21.6 % | 1.09 |
| 5 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 14.1 % | 13.0 % | **10.1 %** | -29.1 % | 0.45 |
| 6 | Dividende + niedrige Vola | AKTIEN | N=5 | 13.0 % | 14.3 % | **4.9 %** | -43.6 % | 0.20 |
| 7 | Januar-Barometer | QQQ | - | 12.8 % | 13.1 % | **21.4 %** | -29.1 % | 0.91 |
| 8 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | 12.3 % | 12.7 % | **-3.4 %** | -57.6 % | -0.06 |
| 9 | IBS-Rücksetzer | QQQ | x=0.3, exit=vortageshoch, trend=0 | 10.9 % | 11.7 % | **16.7 %** | -28.8 % | 0.77 |
| 10 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | 10.7 % | 10.8 % | **13.2 %** | -33.6 % | 0.61 |

## Beste je Gruppe

| Gruppe | Varianten | Beste | Markt | Sharpe C | Rendite C | Max. Verlust C | schlagen SPY (Sharpe C) |
|---|---|---|---|---|---|---|---|
| Dividenden | 27 | Dividende + niedrige Vola | AKTIEN | 0.20 | 4.9 % | -43.6 % | 11 |
| Hebel + Trend | 176 | Hebel + Trendfilter | HEBEL-QQQ | 1.02 | 21.3 % | -21.6 % | 113 |
| Kalender & Saison | 245 | Monatswechsel | AKTIEN | 0.42 | 6.8 % | -12.8 % | 42 |
| Long-Short | 646 | Momentum marktneutral | ALLE-KLASSEN | 0.27 | 6.3 % | -61.9 % | 4 |
| Maschinelles Lernen | 120 | ML: lineares Modell | SEKTOREN | 0.33 | 6.7 % | -27.5 % | 3 |
| Paarhandel | 72 | Paarhandel | PAARE | 0.71 | 6.9 % | -11.5 % | 23 |
| Quartalszahlen | 33 | Vor Quartalszahlen | AKTIEN | 0.69 | 4.1 % | -2.8 % | 11 |
| Rotation & Faktoren | 1858 | Risk-Parity | MULTI | 0.34 | 4.7 % | -10.1 % | 215 |
| Rücksetzer kaufen | 3900 | Williams-%R | AKTIEN | 0.40 | 6.1 % | -19.4 % | 365 |
| Tageshandel & Overnight | 510 | Gap-Momentum (Tageshandel) | QQQ | -0.07 | 2.0 % | -10.6 % | 18 |
| Taktische Asset-Allokation | 78 | VAA (Keller) | TAA | 0.25 | 5.1 % | -20.5 % | 12 |
| Trendfolge | 1228 | SMA-Kreuz | MULTI | 0.40 | 6.2 % | -20.8 % | 297 |
| Volatilität & VIX | 537 | VIX-Filter | QQQ | 0.61 | 13.2 % | -33.6 % | 88 |

## Verlaesslichkeit

- Zusammenhang Auswahl-Rang <-> Test (Spearman): **0.52**
- Von den 50 besten der Auswahl schlagen im Test 15 die Sharpe von SPY (0.61).
- Alle Varianten: 1202 von 9430 schlagen SPY im Test (Sharpe).
- Median-Sharpe im Test: Top-50 der Auswahl 0.45, alle 0.29.
- Gluecks-Schwelle: bei 7989 Varianten waere die beste Sharpe ueber 15 Jahre allein durch Zufall etwa 0.95.

## Intraday (Stundenkurse, ~2 Jahre)

- Noise-Area (1h) QQQ (n=21, mult=1.5, seite=long-short, exit=tagesende): Sharpe Auswahl 0.72, Test 0.28, Rendite Test 2.2 %
- Noise-Area (1h) QQQ (n=14, mult=1.0, seite=nur-long, exit=tagesende): Sharpe Auswahl 0.67, Test -0.35, Rendite Test -2.5 %
- Noise-Area (1h) QQQ (n=7, mult=1.5, seite=long-short, exit=band-zurueck): Sharpe Auswahl 0.65, Test -1.22, Rendite Test -9.3 %
- Noise-Area (1h) QQQ (n=21, mult=1.25, seite=nur-long, exit=tagesende): Sharpe Auswahl 0.59, Test 0.18, Rendite Test 0.9 %
- Noise-Area (1h) QQQ (n=21, mult=1.25, seite=long-short, exit=tagesende): Sharpe Auswahl 0.59, Test 0.19, Rendite Test 1.5 %
- Kaufen & Halten SPY: Rendite Test 19.5 %
- Kaufen & Halten QQQ: Rendite Test 21.8 %
- Kaufen & Halten IWM: Rendite Test 24.7 %
- Kaufen & Halten DIA: Rendite Test 14.6 %
