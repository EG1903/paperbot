# Strategie-Labor: Ergebnis

Stand der Kurse: 2026-10-23. Getestet: **4166 Varianten** aus 43 Strategie-Familien auf 5 Universen; 3878 davon mit genug Trades fuer die Auswahl.

Auswahl = Zeitraum A (2005-2012) und B (2013-2019). Test = C (2020-2026), nie zur Auswahl benutzt. Rang = min(Sharpe A, Sharpe B). Order zur naechsten Eroeffnung, 0,03 % Kosten je Order.

## Vergleichswerte (Kaufen & Halten)

| Universum | Sharpe A | Sharpe B | Sharpe C | Rendite/J C | Max. Verlust C | Rendite/J 2005-heute |
|---|---|---|---|---|---|---|
| AKTIEN | 0.36 | 1.09 | 0.68 | 15.1 % | -36 % | 12.3 % |
| MULTI | 0.58 | 0.62 | 0.53 | 9.0 % | -22 % | 7.9 % |
| 60/40 SPY/Anleihen | 0.32 | 1.19 | 0.56 | 9.6 % | -22 % | 8.0 % |
| SEKTOREN | 0.30 | 1.04 | 0.61 | 13.7 % | -37 % | 10.9 % |
| SPY | 0.21 | 1.07 | 0.66 | 15.0 % | -34 % | 10.7 % |
| QQQ | 0.33 | 1.16 | 0.74 | 19.9 % | -35 % | 14.9 % |

## Die 10 robustesten Strategien (Auswahl A+B, geprueft im Test C)

| # | Strategie | Universum | Parameter | Sharpe A | Sharpe B | **Sharpe C (Test)** | Rendite/J C | Max. Verlust C | investiert | Trades/J | Sharpe C bei 0,10 % Kosten |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Risk-Parity | MULTI | n=126, trend=200 | 0.90 | 0.92 | **0.39** | 5.0 % | -10 % | 67 % | 13 | 0.36 |
| 2 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | 0.83 | 0.85 | **0.40** | 6.1 % | -19 % | 21 % | 384 | 0.27 |
| 3 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 0.81 | 0.91 | **0.46** | 10.3 % | -29 % | 100 % | 4 | 0.43 |
| 4 | Williams-%R | SPY | n=10, x=-90, trend=200 | 0.92 | 0.81 | **0.26** | 5.4 % | -31 % | 18 % | 6 | 0.19 |
| 5 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | 0.80 | 0.85 | **0.49** | 7.8 % | -15 % | 80 % | 72 | 0.42 |
| 6 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | 0.83 | 0.80 | **-0.01** | 2.5 % | -19 % | 100 % | 2 | -0.02 |
| 7 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | 0.79 | 0.86 | **0.70** | 15.1 % | -34 % | 80 % | 10 | 0.63 |
| 8 | Williams-%R | SEKTOREN | n=5, x=-95, trend=0 | 0.78 | 0.83 | **0.52** | 7.6 % | -17 % | 19 % | 105 | 0.40 |
| 9 | IBS-Ruecksetzer | SPY | x=0.15, exit=vortageshoch, trend=0 | 0.78 | 0.78 | **0.76** | 12.5 % | -21 % | 33 % | 26 | 0.48 |
| 10 | GTAA (Faber) | MULTI | n=150 | 0.76 | 0.77 | **0.63** | 7.7 % | -8 % | 66 % | 16 | 0.61 |

Zum Vergleich SPY halten im Test C: Sharpe 0.66, 15.0 % pro Jahr, max. Verlust -34 %.

## Die 5 renditestaerksten robusten Strategien (Rang = min(Rendite A, Rendite B))

| # | Strategie | Universum | Parameter | Rendite/J A | Rendite/J B | **Rendite/J C** | Max. Verlust C | Sharpe C |
|---|---|---|---|---|---|---|---|---|
| 1 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | 16.7 % | 14.5 % | **15.1 %** | -45 % | 0.59 |
| 2 | Vola-Regime | QQQ | k=1.2 | 13.0 % | 14.4 % | **22.9 %** | -22 % | 1.12 |
| 3 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | 14.1 % | 13.0 % | **10.3 %** | -29 % | 0.46 |
| 4 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | 12.3 % | 12.7 % | **-2.3 %** | -58 % | -0.03 |
| 5 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | 10.7 % | 10.8 % | **15.1 %** | -34 % | 0.70 |

## Wie verlaesslich ist das?

- Zusammenhang Auswahl-Rang <-> Test-Ergebnis (Spearman): **0.22** (0 = Auswahl sagt nichts voraus, 1 = perfekt).
- Von den 50 besten der Auswahl schlagen im Test **13** die Sharpe von SPY halten (0.66).
- Median-Sharpe im Test: Top-50 der Auswahl 0.52, alle Varianten 0.43.
- Bei 3878 unabhaengigen Strategien ohne echten Vorteil waere die beste Sharpe ueber 15 Jahre allein durch Glueck etwa **0.90**. (Die Varianten sind stark verwandt, die echte Zahl ist kleiner.)

## Nur zur Info: die 10 besten im Test C (im Nachhinein ausgesucht = NICHT ehrlich waehlbar)

| # | Strategie | Universum | Parameter | Sharpe A | Sharpe B | Sharpe C | Rendite/J C |
|---|---|---|---|---|---|---|---|
| 1 | ConnorsRSI | QQQ | x=25, exit=crsi50, trend=200 | -0.09 | 0.34 | 1.15 | 14.0 % |
| 2 | RSI-Ruecksetzer | QQQ | n=2, x=25, exit=sma5, trend=200 | 0.18 | 0.66 | 1.15 | 16.1 % |
| 3 | Vola-Regime | QQQ | k=1.2 | 0.74 | 1.12 | 1.12 | 22.9 % |
| 4 | IBS-Ruecksetzer | AKTIEN | x=0.1, exit=vortageshoch, trend=200 | 0.71 | 0.44 | 1.12 | 7.6 % |
| 5 | Momentum-Rotation | SEKTOREN | L=252, skip=0, N=1, reb=W, filt=keiner | 0.26 | 0.66 | 1.09 | 33.2 % |
| 6 | Bollinger-Ruecksetzer | QQQ | n=5, k=1.5, exit=mitte, trend=200 | 0.01 | 0.86 | 1.09 | 13.4 % |
| 7 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=3, filt=spy200 | 0.89 | 0.76 | 1.08 | 16.0 % |
| 8 | IBS-Ruecksetzer | SEKTOREN | x=0.15, exit=vortageshoch, trend=200 | 0.39 | 0.65 | 1.06 | 9.8 % |
| 9 | Williams-%R | QQQ | n=2, x=-80, trend=200 | -0.18 | 0.60 | 1.06 | 15.8 % |
| 10 | IBS-Ruecksetzer | QQQ | x=0.15, exit=ibs70, trend=0 | 0.33 | 0.75 | 1.05 | 17.9 % |

## Intraday-Studie (Stundenkurse, nur ~2 Jahre -> wenig aussagekraeftig)

Auswahl: 2023-11-28 .. 2025-05-13, Test: 2025-05-13 .. 2026-10-23. 272 Varianten auf SPY, QQQ, IWM, DIA.

| # | Strategie | ETF | Parameter | Sharpe Auswahl | Sharpe Test | Rendite Test | Trades Test |
|---|---|---|---|---|---|---|---|
| 1 | Noise-Area (1h) | QQQ | n=21, mult=1.5, seite=long-short, exit=tagesende | 0.87 | 0.50 | +3.8 % | 102 |
| 2 | Noise-Area (1h) | QQQ | n=14, mult=1.0, seite=nur-long, exit=tagesende | 0.85 | -0.19 | -1.4 % | 100 |
| 3 | Noise-Area (1h) | QQQ | n=7, mult=1.5, seite=long-short, exit=band-zurueck | 0.78 | -1.49 | -10.7 % | 149 |
| 4 | Noise-Area (1h) | QQQ | n=14, mult=1.5, seite=long-short, exit=tagesende | 0.71 | -0.37 | -3.3 % | 112 |
| 5 | Noise-Area (1h) | QQQ | n=21, mult=1.25, seite=long-short, exit=tagesende | 0.67 | 0.36 | +2.8 % | 140 |
| - | Kaufen & Halten | SPY | - | 1.08 | 1.59 | +30.4 % | - |
| - | Kaufen & Halten | QQQ | - | 0.92 | 1.34 | +38.7 % | - |
| - | Kaufen & Halten | IWM | - | 0.58 | 1.16 | +32.6 % | - |
| - | Kaufen & Halten | DIA | - | 0.90 | 1.24 | +22.9 % | - |

Laufzeit: 88 Sekunden. Alle Varianten: lab_results.csv
