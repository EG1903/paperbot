# Strategie-Labor v2: Ergebnis

Kurse bis 2026-11-02. **9449 Varianten**, 7989 davon mit Auswahl-Zeitraum A+B, 665 nur mit B+C (kurze Historie).

SPY halten im Test (2020-heute): 14.8 % p.a., Sharpe 0.65, max. Verlust -34.0 %.

## Top 10 robust (Rang = min(Sharpe A, Sharpe B), geprueft im Test C)

| # | Strategie | Markt | Parameter | Sharpe A | Sharpe B | Sharpe C | Rendite C | Max. Verlust C | Sharpe C teuer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | VAA (Keller) | TAA | set=G4, top=2, breite=1 | 0.96 | 0.99 | **0.26** | 5.2 % | -20.5 % | 0.17 |
| 2 | Risk-Parity | MULTI | n=126, trend=200 | 0.90 | 0.92 | **0.38** | 4.9 % | -10.1 % | 0.35 |
| 3 | Hebel + Trendfilter | HEBEL-QQQ | L=1.0, regel=vola-regime, ausweich=IEF | 0.89 | 1.15 | **1.03** | 21.5 % | -21.6 % | 0.98 |
| 4 | DAA (Keller) | TAA | top=6, breite=1 | 0.84 | 0.91 | **0.42** | 6.7 % | -17.7 % | 0.32 |
| 5 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | 0.84 | 0.86 | **0.41** | 6.2 % | -19.4 % | 0.28 |
| 6 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 0.81 | 0.91 | **0.45** | 10.2 % | -29.1 % | 0.42 |
| 7 | Williams-%R | SPY | n=10, x=-90, trend=200 | 0.92 | 0.81 | **0.27** | 5.5 % | -31.1 % | 0.20 |
| 8 | PAA (Keller) | TAA | L=126, schutz=1, top=6, anleihe=IEF | 0.91 | 0.81 | **0.45** | 7.1 % | -21.0 % | 0.40 |
| 9 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | 0.80 | 0.85 | **0.52** | 8.2 % | -15.0 % | 0.45 |
| 10 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | 0.83 | 0.80 | **-0.01** | 2.5 % | -19.4 % | -0.02 |

## Top 10 Rendite (Rang = min(Rendite A, Rendite B), mind. 30 % investiert)

| # | Strategie | Markt | Parameter | Rendite A | Rendite B | Rendite C | Max. Verlust C | Sharpe C |
|---|---|---|---|---|---|---|---|---|
| 1 | Hebel + Trendfilter | HEBEL-QQQ | L=3.0, regel=vola-regime, ausweich=IEF | 32.2 % | 41.3 % | **56.2 %** | -56.9 % | 1.07 |
| 2 | Hebel + Trendfilter | HEBEL-SPY | L=3.0, regel=sma200-band, ausweich=IEF | 17.0 % | 28.7 % | **17.6 %** | -61.8 % | 0.54 |
| 3 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | 16.7 % | 14.5 % | **15.0 %** | -44.6 % | 0.59 |
| 4 | Vola-Regime | QQQ | k=1.2 | 13.0 % | 14.4 % | **22.2 %** | -21.6 % | 1.09 |
| 5 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 14.1 % | 13.0 % | **10.2 %** | -29.1 % | 0.45 |
| 6 | Dividende + niedrige Vola | AKTIEN | N=5 | 13.0 % | 14.3 % | **5.5 %** | -43.6 % | 0.23 |
| 7 | Januar-Barometer | QQQ | - | 12.8 % | 13.1 % | **22.6 %** | -29.1 % | 0.97 |
| 8 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | 12.3 % | 12.7 % | **-2.3 %** | -57.6 % | -0.03 |
| 9 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | 10.7 % | 10.8 % | **14.5 %** | -33.6 % | 0.67 |
| 10 | Momentum-Rotation | AKTIEN | L=189, skip=21, N=5, reb=M, filt=spy200 | 10.7 % | 11.3 % | **6.3 %** | -26.0 % | 0.26 |

## Beste je Gruppe

| Gruppe | Varianten | Beste | Markt | Sharpe C | Rendite C | Max. Verlust C | schlagen SPY (Sharpe C) |
|---|---|---|---|---|---|---|---|
| Dividenden | 27 | Dividende + niedrige Vola | AKTIEN | 0.23 | 5.5 % | -43.6 % | 9 |
| Hebel + Trend | 176 | Hebel + Trendfilter | HEBEL-QQQ | 1.03 | 21.5 % | -21.6 % | 114 |
| Kalender & Saison | 245 | Monatswechsel | AKTIEN | 0.47 | 7.3 % | -12.8 % | 38 |
| Long-Short | 646 | Momentum marktneutral | ALLE-KLASSEN | 0.27 | 6.3 % | -61.9 % | 4 |
| Maschinelles Lernen | 120 | ML: lineares Modell | SEKTOREN | 0.36 | 7.1 % | -27.5 % | 4 |
| Paarhandel | 72 | Paarhandel | PAARE | 0.73 | 7.0 % | -11.5 % | 20 |
| Quartalszahlen | 33 | Vor Quartalszahlen | AKTIEN | 0.73 | 4.2 % | -2.8 % | 10 |
| Rotation & Faktoren | 1858 | Risk-Parity | MULTI | 0.38 | 4.9 % | -10.1 % | 231 |
| Rücksetzer kaufen | 3900 | Williams-%R | AKTIEN | 0.41 | 6.2 % | -19.4 % | 340 |
| Tageshandel & Overnight | 510 | Gap-Momentum (Tageshandel) | QQQ | 0.00 | 2.6 % | -10.6 % | 18 |
| Taktische Asset-Allokation | 78 | VAA (Keller) | TAA | 0.26 | 5.2 % | -20.5 % | 12 |
| Trendfolge | 1228 | SMA-Kreuz | MULTI | 0.43 | 6.5 % | -20.8 % | 280 |
| Volatilität & VIX | 537 | VIX-Filter | QQQ | 0.67 | 14.5 % | -33.6 % | 96 |

## Verlaesslichkeit

- Zusammenhang Auswahl-Rang <-> Test (Spearman): **0.52**
- Von den 50 besten der Auswahl schlagen im Test 12 die Sharpe von SPY (0.65).
- Alle Varianten: 1176 von 9430 schlagen SPY im Test (Sharpe).
- Median-Sharpe im Test: Top-50 der Auswahl 0.47, alle 0.32.
- Gluecks-Schwelle: bei 7989 Varianten waere die beste Sharpe ueber 15 Jahre allein durch Zufall etwa 0.95.

## Intraday (Stundenkurse, ~2 Jahre)

- Noise-Area (1h) QQQ (n=14, mult=1.0, seite=nur-long, exit=tagesende): Sharpe Auswahl 0.81, Test -0.47, Rendite Test -3.5 %
- Noise-Area (1h) QQQ (n=21, mult=1.5, seite=long-short, exit=tagesende): Sharpe Auswahl 0.77, Test -0.01, Rendite Test -0.3 %
- Noise-Area (1h) QQQ (n=7, mult=1.5, seite=long-short, exit=band-zurueck): Sharpe Auswahl 0.70, Test -1.59, Rendite Test -11.3 %
- Noise-Area (1h) QQQ (n=21, mult=1.25, seite=nur-long, exit=tagesende): Sharpe Auswahl 0.66, Test 0.26, Rendite Test 1.4 %
- Noise-Area (1h) QQQ (n=21, mult=1.25, seite=long-short, exit=tagesende): Sharpe Auswahl 0.63, Test 0.01, Rendite Test -0.2 %
- Kaufen & Halten SPY: Rendite Test 26.9 %
- Kaufen & Halten QQQ: Rendite Test 30.9 %
- Kaufen & Halten IWM: Rendite Test 33.5 %
- Kaufen & Halten DIA: Rendite Test 21.6 %
