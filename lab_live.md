# Papier-Test aller Strategien

Start 2026-10-27 (gerechnet ab Schlusskurs des Vortags), Stand 2026-11-20: **19 Handelstage**. Gleiche Regeln, Kosten und Ausfuehrung wie im Backtest, nur mit neuen Kursen.

- S&P 500 halten seit Start: **-9.89 %**
- Varianten mit mehr Rendite als SPY seit Start: 7847 von 9430

## Eingefrorene Liste (am Start festgelegt)

| Liste | Rang | Strategie | Markt | Parameter | Rendite seit Start | Max. Verlust | besser als SPY |
|---|---|---|---|---|---|---|---|
| robust | 1 | VAA (Keller) | TAA | set=G4, top=2, breite=1 | +0.35 % | -2.1 % | ja |
| robust | 2 | Risk-Parity | MULTI | n=126, trend=200 | -1.99 % | -2.3 % | ja |
| robust | 3 | Hebel + Trendfilter | HEBEL-QQQ | L=1.0, regel=vola-regime, ausweich=IEF | -3.98 % | -7.4 % | ja |
| robust | 4 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | -0.31 % | -1.4 % | ja |
| robust | 5 | DAA (Keller) | TAA | top=6, breite=1 | +0.35 % | -2.1 % | ja |
| robust | 6 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | -0.88 % | -2.9 % | ja |
| robust | 7 | Williams-%R | SPY | n=10, x=-90, trend=200 | -7.97 % | -10.1 % | ja |
| robust | 8 | PAA (Keller) | TAA | L=126, schutz=1, top=6, anleihe=IEF | +0.42 % | -2.1 % | ja |
| robust | 9 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | -1.08 % | -5.3 % | ja |
| robust | 10 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | +0.20 % | -1.8 % | ja |
| robust | 11 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | -10.68 % | -12.5 % | nein |
| robust | 12 | Statische Portfolios | TAA | mischung=All-Weather (vereinfacht), trend=200 | -3.84 % | -4.1 % | ja |
| robust | 13 | Williams-%R | SEKTOREN | n=5, x=-95, trend=0 | -2.59 % | -3.4 % | ja |
| robust | 14 | IBS-Rücksetzer | SPY | x=0.15, exit=vortageshoch, trend=0 | +0.12 % | -3.9 % | ja |
| robust | 15 | Williams-%R | IWM | n=5, x=-90, trend=0 | -2.87 % | -6.6 % | ja |
| robust | 16 | GTAA (Faber) | MULTI | n=150 | -1.55 % | -2.0 % | ja |
| robust | 17 | Niedrige-Vola-Auswahl | ALLE-KLASSEN | n=63, N=5, filt=keiner | -0.98 % | -1.4 % | ja |
| robust | 18 | Vola-Regime | QQQ | k=1.2 | -3.94 % | -6.2 % | ja |
| robust | 19 | SMA-Kreuz | MULTI | typ=sma, f=50, s=150 | -3.00 % | -3.5 % | ja |
| robust | 20 | ConnorsRSI | AKTIEN | x=5, exit=sma5, trend=200 | +0.54 % | -0.0 % | ja |
| robust | 21 | HAA (Keller) | TAA | top=4 | -7.13 % | -7.7 % | ja |
| robust | 22 | ConnorsRSI | QQQ | x=10, exit=sma5, trend=0 | +0.31 % | -0.0 % | ja |
| robust | 23 | Hebel + Trendfilter | HEBEL-SPY | L=1.0, regel=sma100, ausweich=IEF | -3.81 % | -6.8 % | ja |
| robust | 24 | RSI-Rücksetzer | AKTIEN | n=3, x=15, exit=rsi50, trend=200 | -0.12 % | -0.6 % | ja |
| robust | 25 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | -9.89 % | -10.7 % | nein |
| rendite | 1 | Hebel + Trendfilter | HEBEL-QQQ | L=3.0, regel=vola-regime, ausweich=IEF | -12.62 % | -18.7 % | nein |
| rendite | 2 | Hebel + Trendfilter | HEBEL-SPY | L=3.0, regel=sma200-band, ausweich=IEF | -28.71 % | -30.6 % | nein |
| rendite | 3 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | -1.46 % | -6.1 % | ja |
| rendite | 4 | Vola-Regime | QQQ | k=1.2 | -3.94 % | -6.2 % | ja |
| rendite | 5 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | -0.88 % | -2.9 % | ja |
| rendite | 6 | Dividende + niedrige Vola | AKTIEN | N=5 | +0.40 % | -5.1 % | ja |
| rendite | 7 | Januar-Barometer | QQQ | - | -14.65 % | -16.2 % | nein |
| rendite | 8 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | -14.52 % | -16.7 % | nein |
| rendite | 9 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | -10.68 % | -12.5 % | nein |
| rendite | 10 | Momentum-Rotation | AKTIEN | L=189, skip=21, N=5, reb=M, filt=spy200 | -17.80 % | -19.3 % | nein |
| rendite | 11 | Momentum-Rotation | SEKTOREN | L=252, skip=21, N=1, reb=W, filt=keiner | -13.14 % | -13.6 % | nein |
| rendite | 12 | Hohe Dividendenrendite | AKTIEN | N=10, reb=M, filt=keiner | +2.45 % | -4.6 % | ja |
| rendite | 13 | Momentum-Rotation | MULTI | L=189, skip=21, N=5, reb=M, filt=keiner | -11.30 % | -12.5 % | nein |
| rendite | 14 | Vola-Regime | IWM | k=1.5 | -7.40 % | -9.7 % | ja |
| rendite | 15 | IBS-Rücksetzer | QQQ | x=0.2, exit=vortageshoch, trend=0 | -6.05 % | -9.1 % | ja |
| rendite | 16 | Kurzfrist-Umkehr | MULTI | L=10, N=1, reb=M, filt=keiner | -24.20 % | -25.0 % | nein |
| rendite | 17 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | -9.89 % | -10.7 % | nein |
| rendite | 18 | Abwärtstage | QQQ | N=2, exit=sma5, trend=0 | -10.90 % | -12.4 % | nein |
| rendite | 19 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=3, filt=spy200 | +1.52 % | -5.5 % | ja |
| rendite | 20 | Momentum-Rotation | ALLE-KLASSEN | L=252, skip=21, N=1, reb=W, filt=spy200 | -16.15 % | -19.6 % | nein |
| rendite | 21 | RSI-Rücksetzer | QQQ | n=2, x=30, exit=rsi70, trend=0 | -9.81 % | -11.3 % | ja |
| rendite | 22 | Dividenden-Wachstum | AKTIEN | wachstum=0.0, reb=M, filt=spy200 | -4.14 % | -6.9 % | ja |
| rendite | 23 | Januar-Barometer | SPY | - | -9.89 % | -10.7 % | nein |
| rendite | 24 | Vola-Regime | SEKTOREN | k=1.5 | -4.00 % | -5.3 % | ja |
| rendite | 25 | Zeitreihen-Momentum | QQQ | n=21, skip=0 | +0.31 % | -0.0 % | ja |
| vergleich | 1 | 60/40 SPY/AGG | MULTI | - | -5.81 % | -6.3 % | ja |
| vergleich | 2 | Kaufen & Halten | QQQ | - | -14.65 % | -16.2 % | nein |
| vergleich | 3 | Kaufen & Halten | SPY | - | -9.89 % | -10.7 % | nein |

## Nach Gruppe

| Gruppe | Varianten | Median-Rendite seit Start | besser als SPY |
|---|---|---|---|
| Dividenden | 27 | -2.35 % | 27 |
| Hebel + Trend | 176 | -10.88 % | 72 |
| Kalender & Saison | 245 | -4.82 % | 204 |
| Long-Short | 646 | -0.33 % | 604 |
| Maschinelles Lernen | 120 | -5.85 % | 87 |
| Paarhandel | 72 | -0.17 % | 72 |
| Quartalszahlen | 33 | +0.10 % | 33 |
| Rotation & Faktoren | 1858 | -9.99 % | 912 |
| Rücksetzer kaufen | 3900 | -1.12 % | 3604 |
| Tageshandel & Overnight | 510 | -0.39 % | 504 |
| Taktische Asset-Allokation | 78 | -2.31 % | 65 |
| Trendfolge | 1228 | -1.45 % | 1165 |
| Volatilität & VIX | 537 | -4.01 % | 498 |
