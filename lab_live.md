# Papier-Test aller Strategien

Start 2026-10-27 (gerechnet ab Schlusskurs des Vortags), Stand 2026-11-27: **23 Handelstage**. Gleiche Regeln, Kosten und Ausfuehrung wie im Backtest, nur mit neuen Kursen.

- S&P 500 halten seit Start: **-4.80 %**
- Varianten mit mehr Rendite als SPY seit Start: 7153 von 9430

## Eingefrorene Liste (am Start festgelegt)

| Liste | Rang | Strategie | Markt | Parameter | Rendite seit Start | Max. Verlust | besser als SPY |
|---|---|---|---|---|---|---|---|
| robust | 1 | VAA (Keller) | TAA | set=G4, top=2, breite=1 | +0.37 % | -2.1 % | ja |
| robust | 2 | Risk-Parity | MULTI | n=126, trend=200 | -0.71 % | -2.3 % | ja |
| robust | 3 | Hebel + Trendfilter | HEBEL-QQQ | L=1.0, regel=vola-regime, ausweich=IEF | -3.96 % | -7.4 % | ja |
| robust | 4 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | +1.69 % | -1.4 % | ja |
| robust | 5 | DAA (Keller) | TAA | top=6, breite=1 | +0.37 % | -2.1 % | ja |
| robust | 6 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | -0.79 % | -2.9 % | ja |
| robust | 7 | Williams-%R | SPY | n=10, x=-90, trend=200 | -2.78 % | -10.1 % | ja |
| robust | 8 | PAA (Keller) | TAA | L=126, schutz=1, top=6, anleihe=IEF | +0.43 % | -2.1 % | ja |
| robust | 9 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | +2.54 % | -5.3 % | ja |
| robust | 10 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | +0.31 % | -1.8 % | ja |
| robust | 11 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | -10.62 % | -12.5 % | nein |
| robust | 12 | Statische Portfolios | TAA | mischung=All-Weather (vereinfacht), trend=200 | -2.12 % | -4.1 % | ja |
| robust | 13 | Williams-%R | SEKTOREN | n=5, x=-95, trend=0 | +0.93 % | -3.4 % | ja |
| robust | 14 | IBS-Rücksetzer | SPY | x=0.15, exit=vortageshoch, trend=0 | +3.83 % | -3.9 % | ja |
| robust | 15 | Williams-%R | IWM | n=5, x=-90, trend=0 | +2.92 % | -6.6 % | ja |
| robust | 16 | GTAA (Faber) | MULTI | n=150 | -1.04 % | -2.0 % | ja |
| robust | 17 | Niedrige-Vola-Auswahl | ALLE-KLASSEN | n=63, N=5, filt=keiner | -0.77 % | -1.4 % | ja |
| robust | 18 | Vola-Regime | QQQ | k=1.2 | -3.88 % | -6.2 % | ja |
| robust | 19 | SMA-Kreuz | MULTI | typ=sma, f=50, s=150 | -2.38 % | -3.5 % | ja |
| robust | 20 | ConnorsRSI | AKTIEN | x=5, exit=sma5, trend=200 | +0.68 % | -0.0 % | ja |
| robust | 21 | HAA (Keller) | TAA | top=4 | -3.65 % | -7.7 % | ja |
| robust | 22 | ConnorsRSI | QQQ | x=10, exit=sma5, trend=0 | +0.37 % | -0.0 % | ja |
| robust | 23 | Hebel + Trendfilter | HEBEL-SPY | L=1.0, regel=sma100, ausweich=IEF | -3.79 % | -6.8 % | ja |
| robust | 24 | RSI-Rücksetzer | AKTIEN | n=3, x=15, exit=rsi50, trend=200 | +0.90 % | -0.6 % | ja |
| robust | 25 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | -4.80 % | -10.7 % | nein |
| rendite | 1 | Hebel + Trendfilter | HEBEL-QQQ | L=3.0, regel=vola-regime, ausweich=IEF | -12.61 % | -18.7 % | nein |
| rendite | 2 | Hebel + Trendfilter | HEBEL-SPY | L=3.0, regel=sma200-band, ausweich=IEF | -17.77 % | -30.6 % | nein |
| rendite | 3 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | +1.52 % | -6.1 % | ja |
| rendite | 4 | Vola-Regime | QQQ | k=1.2 | -3.88 % | -6.2 % | ja |
| rendite | 5 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | -0.79 % | -2.9 % | ja |
| rendite | 6 | Dividende + niedrige Vola | AKTIEN | N=5 | +3.62 % | -5.1 % | ja |
| rendite | 7 | Januar-Barometer | QQQ | - | -8.56 % | -16.2 % | nein |
| rendite | 8 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | -7.91 % | -16.7 % | nein |
| rendite | 9 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | -10.62 % | -12.5 % | nein |
| rendite | 10 | Momentum-Rotation | AKTIEN | L=189, skip=21, N=5, reb=M, filt=spy200 | -9.95 % | -19.3 % | nein |
| rendite | 11 | Momentum-Rotation | SEKTOREN | L=252, skip=21, N=1, reb=W, filt=keiner | -11.47 % | -14.5 % | nein |
| rendite | 12 | Hohe Dividendenrendite | AKTIEN | N=10, reb=M, filt=keiner | +8.19 % | -4.6 % | ja |
| rendite | 13 | Momentum-Rotation | MULTI | L=189, skip=21, N=5, reb=M, filt=keiner | -6.23 % | -12.5 % | nein |
| rendite | 14 | Vola-Regime | IWM | k=1.5 | -3.96 % | -9.7 % | ja |
| rendite | 15 | IBS-Rücksetzer | QQQ | x=0.2, exit=vortageshoch, trend=0 | -1.10 % | -9.1 % | ja |
| rendite | 16 | Kurzfrist-Umkehr | MULTI | L=10, N=1, reb=M, filt=keiner | -18.92 % | -25.1 % | nein |
| rendite | 17 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | -4.80 % | -10.7 % | nein |
| rendite | 18 | Abwärtstage | QQQ | N=2, exit=sma5, trend=0 | -5.49 % | -12.4 % | nein |
| rendite | 19 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=3, filt=spy200 | +5.15 % | -5.5 % | ja |
| rendite | 20 | Momentum-Rotation | ALLE-KLASSEN | L=252, skip=21, N=1, reb=W, filt=spy200 | -17.99 % | -19.6 % | nein |
| rendite | 21 | RSI-Rücksetzer | QQQ | n=2, x=30, exit=rsi70, trend=0 | -3.39 % | -11.3 % | ja |
| rendite | 22 | Dividenden-Wachstum | AKTIEN | wachstum=0.0, reb=M, filt=spy200 | +0.65 % | -6.9 % | ja |
| rendite | 23 | Januar-Barometer | SPY | - | -4.80 % | -10.7 % | nein |
| rendite | 24 | Vola-Regime | SEKTOREN | k=1.5 | -2.38 % | -5.3 % | ja |
| rendite | 25 | Zeitreihen-Momentum | QQQ | n=21, skip=0 | +0.37 % | -0.0 % | ja |
| vergleich | 1 | 60/40 SPY/AGG | MULTI | - | -2.59 % | -6.3 % | ja |
| vergleich | 2 | Kaufen & Halten | QQQ | - | -8.56 % | -16.2 % | nein |
| vergleich | 3 | Kaufen & Halten | SPY | - | -4.80 % | -10.7 % | nein |

## Nach Gruppe

| Gruppe | Varianten | Median-Rendite seit Start | besser als SPY |
|---|---|---|---|
| Dividenden | 27 | +2.13 % | 27 |
| Hebel + Trend | 176 | -8.27 % | 23 |
| Kalender & Saison | 245 | +0.37 % | 210 |
| Long-Short | 646 | -0.70 % | 499 |
| Maschinelles Lernen | 120 | -1.89 % | 89 |
| Paarhandel | 72 | +0.22 % | 72 |
| Quartalszahlen | 33 | +0.41 % | 33 |
| Rotation & Faktoren | 1858 | -6.92 % | 695 |
| Rücksetzer kaufen | 3900 | -0.13 % | 3459 |
| Tageshandel & Overnight | 510 | -0.24 % | 488 |
| Taktische Asset-Allokation | 78 | -1.06 % | 63 |
| Trendfolge | 1228 | -0.95 % | 1073 |
| Volatilität & VIX | 537 | -2.90 % | 422 |
