# Strategie-Labor v2: Ergebnis

Kurse bis 2026-11-13. **9449 Varianten**, 7989 davon mit Auswahl-Zeitraum A+B, 665 nur mit B+C (kurze Historie).

SPY halten im Test (2020-heute): 14.8 % p.a., Sharpe 0.65, max. Verlust -34.0 %.

## Top 10 robust (Rang = min(Sharpe A, Sharpe B), geprueft im Test C)

| # | Strategie | Markt | Parameter | Sharpe A | Sharpe B | Sharpe C | Rendite C | Max. Verlust C | Sharpe C teuer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | VAA (Keller) | TAA | set=G4, top=2, breite=1 | 0.96 | 0.99 | **0.24** | 5.0 % | -20.5 % | 0.15 |
| 2 | Risk-Parity | MULTI | n=126, trend=200 | 0.90 | 0.92 | **0.38** | 4.9 % | -10.1 % | 0.35 |
| 3 | Hebel + Trendfilter | HEBEL-QQQ | L=1.0, regel=vola-regime, ausweich=IEF | 0.89 | 1.15 | **1.01** | 21.2 % | -21.6 % | 0.97 |
| 4 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | 0.84 | 0.85 | **0.41** | 6.3 % | -19.4 % | 0.29 |
| 5 | DAA (Keller) | TAA | top=6, breite=1 | 0.84 | 0.91 | **0.40** | 6.5 % | -17.7 % | 0.30 |
| 6 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 0.81 | 0.91 | **0.44** | 10.0 % | -29.1 % | 0.41 |
| 7 | Williams-%R | SPY | n=10, x=-90, trend=200 | 0.92 | 0.81 | **0.26** | 5.5 % | -31.1 % | 0.20 |
| 8 | PAA (Keller) | TAA | L=126, schutz=1, top=6, anleihe=IEF | 0.91 | 0.81 | **0.42** | 6.8 % | -21.0 % | 0.37 |
| 9 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | 0.80 | 0.85 | **0.53** | 8.3 % | -15.0 % | 0.46 |
| 10 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | 0.83 | 0.80 | **-0.03** | 2.4 % | -19.4 % | -0.04 |

## Top 10 Rendite (Rang = min(Rendite A, Rendite B), mind. 30 % investiert)

| # | Strategie | Markt | Parameter | Rendite A | Rendite B | Rendite C | Max. Verlust C | Sharpe C |
|---|---|---|---|---|---|---|---|---|
| 1 | Hebel + Trendfilter | HEBEL-QQQ | L=3.0, regel=vola-regime, ausweich=IEF | 32.2 % | 41.3 % | **55.6 %** | -56.9 % | 1.06 |
| 2 | Hebel + Trendfilter | HEBEL-SPY | L=3.0, regel=sma200-band, ausweich=IEF | 17.0 % | 28.7 % | **17.4 %** | -61.8 % | 0.53 |
| 3 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | 16.7 % | 14.5 % | **15.9 %** | -44.6 % | 0.62 |
| 4 | Vola-Regime | QQQ | k=1.2 | 13.0 % | 14.4 % | **22.2 %** | -21.6 % | 1.09 |
| 5 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 14.1 % | 13.0 % | **10.0 %** | -29.1 % | 0.44 |
| 6 | Dividende + niedrige Vola | AKTIEN | N=5 | 13.0 % | 14.3 % | **5.6 %** | -43.6 % | 0.23 |
| 7 | Januar-Barometer | QQQ | - | 12.8 % | 13.1 % | **22.4 %** | -29.1 % | 0.95 |
| 8 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | 12.3 % | 12.7 % | **-2.6 %** | -57.6 % | -0.04 |
| 9 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | 10.7 % | 10.8 % | **13.7 %** | -33.6 % | 0.63 |
| 10 | Momentum-Rotation | AKTIEN | L=189, skip=21, N=5, reb=M, filt=spy200 | 10.7 % | 11.3 % | **6.2 %** | -26.0 % | 0.26 |

## Beste je Gruppe

| Gruppe | Varianten | Beste | Markt | Sharpe C | Rendite C | Max. Verlust C | schlagen SPY (Sharpe C) |
|---|---|---|---|---|---|---|---|
| Dividenden | 27 | Dividende + niedrige Vola | AKTIEN | 0.23 | 5.6 % | -43.6 % | 11 |
| Hebel + Trend | 176 | Hebel + Trendfilter | HEBEL-QQQ | 1.01 | 21.2 % | -21.6 % | 107 |
| Kalender & Saison | 245 | Monatswechsel | AKTIEN | 0.51 | 7.8 % | -12.8 % | 39 |
| Long-Short | 646 | Momentum marktneutral | ALLE-KLASSEN | 0.26 | 5.9 % | -61.9 % | 4 |
| Maschinelles Lernen | 120 | ML: lineares Modell | SEKTOREN | 0.38 | 7.4 % | -27.5 % | 3 |
| Paarhandel | 72 | Paarhandel | PAARE | 0.73 | 7.1 % | -11.5 % | 21 |
| Quartalszahlen | 33 | Vor Quartalszahlen | AKTIEN | 0.72 | 4.2 % | -2.8 % | 10 |
| Rotation & Faktoren | 1858 | Risk-Parity | MULTI | 0.38 | 4.9 % | -10.1 % | 211 |
| Rücksetzer kaufen | 3900 | Williams-%R | AKTIEN | 0.41 | 6.3 % | -19.4 % | 346 |
| Tageshandel & Overnight | 510 | Gap-Momentum (Tageshandel) | QQQ | 0.00 | 2.6 % | -10.6 % | 18 |
| Taktische Asset-Allokation | 78 | VAA (Keller) | TAA | 0.24 | 5.0 % | -20.5 % | 12 |
| Trendfolge | 1228 | SMA-Kreuz | MULTI | 0.42 | 6.4 % | -20.8 % | 267 |
| Volatilität & VIX | 537 | VIX-Filter | QQQ | 0.63 | 13.7 % | -33.6 % | 88 |

## Verlaesslichkeit

- Zusammenhang Auswahl-Rang <-> Test (Spearman): **0.53**
- Von den 50 besten der Auswahl schlagen im Test 13 die Sharpe von SPY (0.65).
- Alle Varianten: 1137 von 9430 schlagen SPY im Test (Sharpe).
- Median-Sharpe im Test: Top-50 der Auswahl 0.47, alle 0.32.
- Gluecks-Schwelle: bei 7989 Varianten waere die beste Sharpe ueber 15 Jahre allein durch Zufall etwa 0.95.

## Intraday (Stundenkurse, ~2 Jahre)

- Noise-Area (1h) QQQ (n=14, mult=1.0, seite=nur-long, exit=tagesende): Sharpe Auswahl 0.78, Test -0.54, Rendite Test -4.0 %
- Noise-Area (1h) QQQ (n=21, mult=1.5, seite=long-short, exit=tagesende): Sharpe Auswahl 0.75, Test 0.34, Rendite Test 2.8 %
- Noise-Area (1h) QQQ (n=21, mult=1.25, seite=nur-long, exit=tagesende): Sharpe Auswahl 0.67, Test 0.14, Rendite Test 0.7 %
- Noise-Area (1h) QQQ (n=21, mult=1.25, seite=long-short, exit=tagesende): Sharpe Auswahl 0.66, Test 0.18, Rendite Test 1.4 %
- Noise-Area (1h) QQQ (n=7, mult=1.5, seite=long-short, exit=band-zurueck): Sharpe Auswahl 0.59, Test -1.23, Rendite Test -9.3 %
- Kaufen & Halten SPY: Rendite Test 27.3 %
- Kaufen & Halten QQQ: Rendite Test 29.9 %
- Kaufen & Halten IWM: Rendite Test 34.9 %
- Kaufen & Halten DIA: Rendite Test 23.5 %
