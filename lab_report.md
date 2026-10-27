# Strategie-Labor v2: Ergebnis

Kurse bis 2026-10-23. **9449 Varianten**, 7989 davon mit Auswahl-Zeitraum A+B, 665 nur mit B+C (kurze Historie).

SPY halten im Test (2020-heute): 15.0 % p.a., Sharpe 0.66, max. Verlust -34.0 %.

## Top 10 robust (Rang = min(Sharpe A, Sharpe B), geprueft im Test C)

| # | Strategie | Markt | Parameter | Sharpe A | Sharpe B | Sharpe C | Rendite C | Max. Verlust C | Sharpe C teuer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | VAA (Keller) | TAA | set=G4, top=2, breite=1 | 0.96 | 0.99 | **0.26** | 5.2 % | -20.5 % | 0.18 |
| 2 | Risk-Parity | MULTI | n=126, trend=200 | 0.90 | 0.92 | **0.39** | 5.0 % | -10.1 % | 0.36 |
| 3 | Hebel + Trendfilter | HEBEL-QQQ | L=1.0, regel=vola-regime, ausweich=IEF | 0.89 | 1.15 | **1.06** | 22.2 % | -21.6 % | 1.02 |
| 4 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | 0.84 | 0.85 | **0.40** | 6.1 % | -19.4 % | 0.27 |
| 5 | DAA (Keller) | TAA | top=6, breite=1 | 0.84 | 0.91 | **0.42** | 6.8 % | -17.7 % | 0.33 |
| 6 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 0.81 | 0.91 | **0.46** | 10.3 % | -29.1 % | 0.43 |
| 7 | Williams-%R | SPY | n=10, x=-90, trend=200 | 0.92 | 0.81 | **0.26** | 5.4 % | -31.1 % | 0.19 |
| 8 | PAA (Keller) | TAA | L=126, schutz=1, top=6, anleihe=IEF | 0.91 | 0.81 | **0.45** | 7.1 % | -21.0 % | 0.40 |
| 9 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | 0.80 | 0.85 | **0.49** | 7.8 % | -15.0 % | 0.42 |
| 10 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | 0.83 | 0.80 | **-0.01** | 2.5 % | -19.4 % | -0.02 |

## Top 10 Rendite (Rang = min(Rendite A, Rendite B), mind. 30 % investiert)

| # | Strategie | Markt | Parameter | Rendite A | Rendite B | Rendite C | Max. Verlust C | Sharpe C |
|---|---|---|---|---|---|---|---|---|
| 1 | Hebel + Trendfilter | HEBEL-QQQ | L=3.0, regel=vola-regime, ausweich=IEF | 32.2 % | 41.3 % | **59.0 %** | -56.9 % | 1.10 |
| 2 | Hebel + Trendfilter | HEBEL-SPY | L=3.0, regel=sma200-band, ausweich=IEF | 17.0 % | 28.7 % | **18.3 %** | -61.8 % | 0.55 |
| 3 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | 16.7 % | 14.5 % | **15.1 %** | -44.6 % | 0.59 |
| 4 | Vola-Regime | QQQ | k=1.2 | 13.0 % | 14.4 % | **22.9 %** | -21.6 % | 1.12 |
| 5 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 14.1 % | 13.0 % | **10.3 %** | -29.1 % | 0.46 |
| 6 | Dividende + niedrige Vola | AKTIEN | N=5 | 13.0 % | 14.3 % | **5.2 %** | -43.6 % | 0.21 |
| 7 | Januar-Barometer | QQQ | - | 12.8 % | 13.1 % | **23.3 %** | -29.1 % | 1.00 |
| 8 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | 12.3 % | 12.7 % | **-2.3 %** | -57.6 % | -0.03 |
| 9 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | 10.7 % | 10.8 % | **15.1 %** | -33.6 % | 0.70 |
| 10 | Momentum-Rotation | AKTIEN | L=189, skip=21, N=5, reb=M, filt=spy200 | 10.7 % | 11.3 % | **7.4 %** | -26.0 % | 0.32 |

## Beste je Gruppe

| Gruppe | Varianten | Beste | Markt | Sharpe C | Rendite C | Max. Verlust C | schlagen SPY (Sharpe C) |
|---|---|---|---|---|---|---|---|
| Dividenden | 27 | Dividende + niedrige Vola | AKTIEN | 0.21 | 5.2 % | -43.6 % | 5 |
| Hebel + Trend | 176 | Hebel + Trendfilter | HEBEL-QQQ | 1.06 | 22.2 % | -21.6 % | 118 |
| Kalender & Saison | 245 | Monatswechsel | AKTIEN | 0.47 | 7.3 % | -12.8 % | 38 |
| Long-Short | 646 | Momentum marktneutral | ALLE-KLASSEN | 0.27 | 6.5 % | -61.9 % | 4 |
| Maschinelles Lernen | 120 | ML: lineares Modell | SEKTOREN | 0.35 | 7.0 % | -27.5 % | 5 |
| Paarhandel | 72 | Paarhandel | PAARE | 0.72 | 7.0 % | -11.5 % | 14 |
| Quartalszahlen | 33 | Vor Quartalszahlen | AKTIEN | 0.71 | 4.1 % | -2.8 % | 10 |
| Rotation & Faktoren | 1858 | Risk-Parity | MULTI | 0.39 | 5.0 % | -10.1 % | 263 |
| Rücksetzer kaufen | 3900 | Williams-%R | AKTIEN | 0.40 | 6.1 % | -19.4 % | 337 |
| Tageshandel & Overnight | 510 | Gap-Momentum (Tageshandel) | QQQ | 0.01 | 2.6 % | -10.6 % | 18 |
| Taktische Asset-Allokation | 78 | VAA (Keller) | TAA | 0.26 | 5.2 % | -20.5 % | 12 |
| Trendfolge | 1228 | SMA-Kreuz | MULTI | 0.44 | 6.6 % | -20.8 % | 279 |
| Volatilität & VIX | 537 | VIX-Filter | QQQ | 0.70 | 15.1 % | -33.6 % | 99 |

## Verlaesslichkeit

- Zusammenhang Auswahl-Rang <-> Test (Spearman): **0.50**
- Von den 50 besten der Auswahl schlagen im Test 11 die Sharpe von SPY (0.66).
- Alle Varianten: 1202 von 9430 schlagen SPY im Test (Sharpe).
- Median-Sharpe im Test: Top-50 der Auswahl 0.46, alle 0.34.
- Gluecks-Schwelle: bei 7989 Varianten waere die beste Sharpe ueber 15 Jahre allein durch Zufall etwa 0.95.

## Intraday (Stundenkurse, ~2 Jahre)

- Noise-Area (1h) QQQ (n=21, mult=1.5, seite=long-short, exit=tagesende): Sharpe Auswahl 0.87, Test 0.50, Rendite Test 3.8 %
- Noise-Area (1h) QQQ (n=14, mult=1.0, seite=nur-long, exit=tagesende): Sharpe Auswahl 0.85, Test -0.19, Rendite Test -1.4 %
- Noise-Area (1h) QQQ (n=7, mult=1.5, seite=long-short, exit=band-zurueck): Sharpe Auswahl 0.78, Test -1.49, Rendite Test -10.7 %
- Noise-Area (1h) QQQ (n=14, mult=1.5, seite=long-short, exit=tagesende): Sharpe Auswahl 0.71, Test -0.37, Rendite Test -3.3 %
- Noise-Area (1h) QQQ (n=21, mult=1.25, seite=long-short, exit=tagesende): Sharpe Auswahl 0.67, Test 0.36, Rendite Test 2.8 %
- Kaufen & Halten SPY: Rendite Test 30.4 %
- Kaufen & Halten QQQ: Rendite Test 38.7 %
- Kaufen & Halten IWM: Rendite Test 32.6 %
- Kaufen & Halten DIA: Rendite Test 22.9 %
