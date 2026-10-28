# Strategie-Labor v2: Ergebnis

Kurse bis 2026-10-27. **9449 Varianten**, 7989 davon mit Auswahl-Zeitraum A+B, 665 nur mit B+C (kurze Historie).

SPY halten im Test (2020-heute): 15.2 % p.a., Sharpe 0.67, max. Verlust -34.0 %.

## Top 10 robust (Rang = min(Sharpe A, Sharpe B), geprueft im Test C)

| # | Strategie | Markt | Parameter | Sharpe A | Sharpe B | Sharpe C | Rendite C | Max. Verlust C | Sharpe C teuer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | VAA (Keller) | TAA | set=G4, top=2, breite=1 | 0.96 | 0.99 | **0.26** | 5.2 % | -20.5 % | 0.17 |
| 2 | Risk-Parity | MULTI | n=126, trend=200 | 0.90 | 0.92 | **0.39** | 5.0 % | -10.1 % | 0.36 |
| 3 | Hebel + Trendfilter | HEBEL-QQQ | L=1.0, regel=vola-regime, ausweich=IEF | 0.89 | 1.15 | **1.08** | 22.6 % | -21.6 % | 1.04 |
| 4 | DAA (Keller) | TAA | top=6, breite=1 | 0.84 | 0.91 | **0.42** | 6.8 % | -17.7 % | 0.33 |
| 5 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | 0.83 | 0.85 | **0.40** | 6.2 % | -19.4 % | 0.28 |
| 6 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 0.81 | 0.91 | **0.47** | 10.5 % | -29.1 % | 0.44 |
| 7 | Williams-%R | SPY | n=10, x=-90, trend=200 | 0.92 | 0.81 | **0.27** | 5.5 % | -31.1 % | 0.20 |
| 8 | PAA (Keller) | TAA | L=126, schutz=1, top=6, anleihe=IEF | 0.91 | 0.81 | **0.45** | 7.1 % | -21.0 % | 0.40 |
| 9 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | 0.80 | 0.85 | **0.48** | 7.7 % | -15.0 % | 0.41 |
| 10 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | 0.83 | 0.80 | **-0.01** | 2.6 % | -19.4 % | -0.01 |

## Top 10 Rendite (Rang = min(Rendite A, Rendite B), mind. 30 % investiert)

| # | Strategie | Markt | Parameter | Rendite A | Rendite B | Rendite C | Max. Verlust C | Sharpe C |
|---|---|---|---|---|---|---|---|---|
| 1 | Hebel + Trendfilter | HEBEL-QQQ | L=3.0, regel=vola-regime, ausweich=IEF | 32.2 % | 41.3 % | **60.5 %** | -56.9 % | 1.12 |
| 2 | Hebel + Trendfilter | HEBEL-SPY | L=3.0, regel=sma200-band, ausweich=IEF | 17.0 % | 28.7 % | **18.9 %** | -61.8 % | 0.57 |
| 3 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | 16.7 % | 14.5 % | **15.4 %** | -44.6 % | 0.60 |
| 4 | Vola-Regime | QQQ | k=1.2 | 13.0 % | 14.4 % | **23.3 %** | -21.6 % | 1.14 |
| 5 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 14.1 % | 13.0 % | **10.5 %** | -29.1 % | 0.47 |
| 6 | Dividende + niedrige Vola | AKTIEN | N=5 | 13.0 % | 14.3 % | **5.0 %** | -43.6 % | 0.20 |
| 7 | Januar-Barometer | QQQ | - | 12.8 % | 13.1 % | **23.7 %** | -29.1 % | 1.01 |
| 8 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | 12.3 % | 12.7 % | **-2.2 %** | -57.6 % | -0.02 |
| 9 | IBS-Rücksetzer | QQQ | x=0.3, exit=vortageshoch, trend=0 | 11.1 % | 11.8 % | **17.0 %** | -28.8 % | 0.78 |
| 10 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | 10.7 % | 10.8 % | **15.5 %** | -33.6 % | 0.72 |

## Beste je Gruppe

| Gruppe | Varianten | Beste | Markt | Sharpe C | Rendite C | Max. Verlust C | schlagen SPY (Sharpe C) |
|---|---|---|---|---|---|---|---|
| Dividenden | 27 | Dividende + niedrige Vola | AKTIEN | 0.20 | 5.0 % | -43.6 % | 5 |
| Hebel + Trend | 176 | Hebel + Trendfilter | HEBEL-QQQ | 1.08 | 22.6 % | -21.6 % | 119 |
| Kalender & Saison | 245 | Monatswechsel | AKTIEN | 0.47 | 7.2 % | -12.8 % | 42 |
| Long-Short | 646 | Momentum marktneutral | ALLE-KLASSEN | 0.26 | 6.1 % | -61.9 % | 4 |
| Maschinelles Lernen | 120 | ML: lineares Modell | SEKTOREN | 0.36 | 7.1 % | -27.5 % | 5 |
| Paarhandel | 72 | Paarhandel | PAARE | 0.72 | 7.0 % | -11.5 % | 12 |
| Quartalszahlen | 33 | Vor Quartalszahlen | AKTIEN | 0.71 | 4.1 % | -2.8 % | 10 |
| Rotation & Faktoren | 1858 | Risk-Parity | MULTI | 0.39 | 5.0 % | -10.1 % | 244 |
| Rücksetzer kaufen | 3900 | Williams-%R | AKTIEN | 0.40 | 6.2 % | -19.4 % | 323 |
| Tageshandel & Overnight | 510 | Gap-Momentum (Tageshandel) | QQQ | 0.00 | 2.6 % | -10.6 % | 18 |
| Taktische Asset-Allokation | 78 | VAA (Keller) | TAA | 0.26 | 5.2 % | -20.5 % | 12 |
| Trendfolge | 1228 | SMA-Kreuz | MULTI | 0.45 | 6.6 % | -20.8 % | 275 |
| Volatilität & VIX | 537 | VIX-Filter | QQQ | 0.72 | 15.5 % | -33.6 % | 99 |

## Verlaesslichkeit

- Zusammenhang Auswahl-Rang <-> Test (Spearman): **0.51**
- Von den 50 besten der Auswahl schlagen im Test 11 die Sharpe von SPY (0.67).
- Alle Varianten: 1168 von 9430 schlagen SPY im Test (Sharpe).
- Median-Sharpe im Test: Top-50 der Auswahl 0.47, alle 0.34.
- Gluecks-Schwelle: bei 7989 Varianten waere die beste Sharpe ueber 15 Jahre allein durch Zufall etwa 0.95.

## Intraday (Stundenkurse, ~2 Jahre)

- Noise-Area (1h) QQQ (n=14, mult=1.0, seite=nur-long, exit=tagesende): Sharpe Auswahl 0.81, Test -0.11, Rendite Test -0.9 %
- Noise-Area (1h) QQQ (n=21, mult=1.5, seite=long-short, exit=tagesende): Sharpe Auswahl 0.73, Test 0.36, Rendite Test 2.6 %
- Noise-Area (1h) QQQ (n=7, mult=1.5, seite=long-short, exit=band-zurueck): Sharpe Auswahl 0.70, Test -1.44, Rendite Test -10.2 %
- Noise-Area (1h) QQQ (n=21, mult=1.25, seite=nur-long, exit=tagesende): Sharpe Auswahl 0.66, Test 0.86, Rendite Test 4.2 %
- Noise-Area (1h) QQQ (n=14, mult=1.25, seite=long-short, exit=tagesende): Sharpe Auswahl 0.63, Test -0.25, Rendite Test -2.5 %
- Kaufen & Halten SPY: Rendite Test 31.0 %
- Kaufen & Halten QQQ: Rendite Test 39.1 %
- Kaufen & Halten IWM: Rendite Test 35.5 %
- Kaufen & Halten DIA: Rendite Test 24.4 %
