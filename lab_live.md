# Papier-Test aller Strategien

Start 2026-10-27 (gerechnet ab Schlusskurs des Vortags), Stand 2026-10-29: **3 Handelstage**. Gleiche Regeln, Kosten und Ausfuehrung wie im Backtest, nur mit neuen Kursen.

- S&P 500 halten seit Start: **+0.52 %**
- Varianten mit mehr Rendite als SPY seit Start: 1984 von 9430

## Eingefrorene Liste (am Start festgelegt)

| Liste | Rang | Strategie | Markt | Parameter | Rendite seit Start | Max. Verlust | besser als SPY |
|---|---|---|---|---|---|---|---|
| robust | 1 | VAA (Keller) | TAA | set=G4, top=2, breite=1 | +0.12 % | -0.0 % | nein |
| robust | 2 | Risk-Parity | MULTI | n=126, trend=200 | +0.27 % | -0.0 % | nein |
| robust | 3 | Hebel + Trendfilter | HEBEL-QQQ | L=1.0, regel=vola-regime, ausweich=IEF | +0.43 % | -1.4 % | nein |
| robust | 4 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | +0.33 % | -0.0 % | nein |
| robust | 5 | DAA (Keller) | TAA | top=6, breite=1 | +0.12 % | -0.0 % | nein |
| robust | 6 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | +0.52 % | -0.4 % | nein |
| robust | 7 | Williams-%R | SPY | n=10, x=-90, trend=200 | +0.43 % | -0.5 % | nein |
| robust | 8 | PAA (Keller) | TAA | L=126, schutz=1, top=6, anleihe=IEF | +0.24 % | -0.1 % | nein |
| robust | 9 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | +1.43 % | -0.7 % | ja |
| robust | 10 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | +0.14 % | -0.3 % | nein |
| robust | 11 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | +0.43 % | -1.4 % | nein |
| robust | 12 | Statische Portfolios | TAA | mischung=All-Weather (vereinfacht), trend=200 | +0.17 % | -0.1 % | nein |
| robust | 13 | Williams-%R | SEKTOREN | n=5, x=-95, trend=0 | +0.05 % | -0.0 % | nein |
| robust | 14 | IBS-Rücksetzer | SPY | x=0.15, exit=vortageshoch, trend=0 | +0.05 % | -0.0 % | nein |
| robust | 15 | Williams-%R | IWM | n=5, x=-90, trend=0 | +0.05 % | -0.0 % | nein |
| robust | 16 | GTAA (Faber) | MULTI | n=150 | +0.29 % | -0.2 % | nein |
| robust | 17 | Niedrige-Vola-Auswahl | ALLE-KLASSEN | n=63, N=5, filt=keiner | +0.15 % | -0.1 % | nein |
| robust | 18 | Vola-Regime | QQQ | k=1.2 | +0.43 % | -1.4 % | nein |
| robust | 19 | SMA-Kreuz | MULTI | typ=sma, f=50, s=150 | +0.47 % | -0.1 % | nein |
| robust | 20 | ConnorsRSI | AKTIEN | x=5, exit=sma5, trend=200 | +0.05 % | -0.0 % | nein |
| robust | 21 | HAA (Keller) | TAA | top=4 | +0.03 % | -0.0 % | nein |
| robust | 22 | ConnorsRSI | QQQ | x=10, exit=sma5, trend=0 | +0.05 % | -0.0 % | nein |
| robust | 23 | Hebel + Trendfilter | HEBEL-SPY | L=1.0, regel=sma100, ausweich=IEF | +0.52 % | -0.4 % | nein |
| robust | 24 | RSI-Rücksetzer | AKTIEN | n=3, x=15, exit=rsi50, trend=200 | +0.10 % | -0.0 % | nein |
| robust | 25 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | +0.52 % | -0.4 % | nein |
| rendite | 1 | Hebel + Trendfilter | HEBEL-QQQ | L=3.0, regel=vola-regime, ausweich=IEF | +1.04 % | -4.3 % | ja |
| rendite | 2 | Hebel + Trendfilter | HEBEL-SPY | L=3.0, regel=sma200-band, ausweich=IEF | +1.44 % | -1.2 % | ja |
| rendite | 3 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | +2.59 % | -0.0 % | ja |
| rendite | 4 | Vola-Regime | QQQ | k=1.2 | +0.43 % | -1.4 % | nein |
| rendite | 5 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | +0.52 % | -0.4 % | nein |
| rendite | 6 | Dividende + niedrige Vola | AKTIEN | N=5 | +1.04 % | -1.1 % | ja |
| rendite | 7 | Januar-Barometer | QQQ | - | +0.43 % | -1.4 % | nein |
| rendite | 8 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | +2.25 % | -0.0 % | ja |
| rendite | 9 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | +0.43 % | -1.4 % | nein |
| rendite | 10 | Momentum-Rotation | AKTIEN | L=189, skip=21, N=5, reb=M, filt=spy200 | +1.15 % | -0.7 % | ja |
| rendite | 11 | Momentum-Rotation | SEKTOREN | L=252, skip=21, N=1, reb=W, filt=keiner | -1.34 % | -2.1 % | nein |
| rendite | 12 | Hohe Dividendenrendite | AKTIEN | N=10, reb=M, filt=keiner | +2.11 % | -0.7 % | ja |
| rendite | 13 | Momentum-Rotation | MULTI | L=189, skip=21, N=5, reb=M, filt=keiner | +1.13 % | -0.2 % | ja |
| rendite | 14 | Vola-Regime | IWM | k=1.5 | +2.53 % | -0.0 % | ja |
| rendite | 15 | IBS-Rücksetzer | QQQ | x=0.2, exit=vortageshoch, trend=0 | +0.43 % | -0.0 % | nein |
| rendite | 16 | Kurzfrist-Umkehr | MULTI | L=10, N=1, reb=M, filt=keiner | -2.83 % | -3.8 % | nein |
| rendite | 17 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | +0.52 % | -0.4 % | nein |
| rendite | 18 | Abwärtstage | QQQ | N=2, exit=sma5, trend=0 | +1.67 % | -0.0 % | ja |
| rendite | 19 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=3, filt=spy200 | -0.17 % | -1.2 % | nein |
| rendite | 20 | Momentum-Rotation | ALLE-KLASSEN | L=252, skip=21, N=1, reb=W, filt=spy200 | +1.21 % | -1.4 % | ja |
| rendite | 21 | RSI-Rücksetzer | QQQ | n=2, x=30, exit=rsi70, trend=0 | +1.67 % | -0.0 % | ja |
| rendite | 22 | Dividenden-Wachstum | AKTIEN | wachstum=0.0, reb=M, filt=spy200 | +1.89 % | -0.0 % | ja |
| rendite | 23 | Januar-Barometer | SPY | - | +0.52 % | -0.4 % | nein |
| rendite | 24 | Vola-Regime | SEKTOREN | k=1.5 | +1.17 % | -0.0 % | ja |
| rendite | 25 | Zeitreihen-Momentum | QQQ | n=21, skip=0 | +0.05 % | -0.0 % | nein |
| vergleich | 1 | 60/40 SPY/AGG | MULTI | - | +0.36 % | -0.1 % | nein |
| vergleich | 2 | Kaufen & Halten | QQQ | - | +0.43 % | -1.4 % | nein |
| vergleich | 3 | Kaufen & Halten | SPY | - | +0.52 % | -0.4 % | nein |

## Nach Gruppe

| Gruppe | Varianten | Median-Rendite seit Start | besser als SPY |
|---|---|---|---|
| Dividenden | 27 | +2.11 % | 27 |
| Hebel + Trend | 176 | +0.74 % | 111 |
| Kalender & Saison | 245 | +0.44 % | 94 |
| Long-Short | 646 | +0.05 % | 160 |
| Maschinelles Lernen | 120 | +0.37 % | 24 |
| Paarhandel | 72 | -0.05 % | 16 |
| Quartalszahlen | 33 | +0.18 % | 5 |
| Rotation & Faktoren | 1858 | +0.33 % | 803 |
| Rücksetzer kaufen | 3900 | +0.05 % | 382 |
| Tageshandel & Overnight | 510 | +0.05 % | 17 |
| Taktische Asset-Allokation | 78 | +0.23 % | 8 |
| Trendfolge | 1228 | +0.10 % | 217 |
| Volatilität & VIX | 537 | +0.35 % | 120 |
