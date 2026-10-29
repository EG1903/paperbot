# Papier-Test aller Strategien

Start 2026-10-27 (gerechnet ab Schlusskurs des Vortags), Stand 2026-10-28: **2 Handelstage**. Gleiche Regeln, Kosten und Ausfuehrung wie im Backtest, nur mit neuen Kursen.

- S&P 500 halten seit Start: **+0.91 %**
- Varianten mit mehr Rendite als SPY seit Start: 1273 von 9430

## Eingefrorene Liste (am Start festgelegt)

| Liste | Rang | Strategie | Markt | Parameter | Rendite seit Start | Max. Verlust | besser als SPY |
|---|---|---|---|---|---|---|---|
| robust | 1 | VAA (Keller) | TAA | set=G4, top=2, breite=1 | -0.01 % | -0.0 % | nein |
| robust | 2 | Risk-Parity | MULTI | n=126, trend=200 | +0.30 % | -0.0 % | nein |
| robust | 3 | Hebel + Trendfilter | HEBEL-QQQ | L=1.0, regel=vola-regime, ausweich=IEF | +1.88 % | -0.0 % | ja |
| robust | 4 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | +0.19 % | -0.0 % | nein |
| robust | 5 | DAA (Keller) | TAA | top=6, breite=1 | -0.01 % | -0.0 % | nein |
| robust | 6 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | +0.91 % | -0.0 % | nein |
| robust | 7 | Williams-%R | SPY | n=10, x=-90, trend=200 | +0.91 % | -0.0 % | nein |
| robust | 8 | PAA (Keller) | TAA | L=126, schutz=1, top=6, anleihe=IEF | +0.05 % | -0.1 % | nein |
| robust | 9 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | -0.66 % | -0.7 % | nein |
| robust | 10 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | -0.15 % | -0.3 % | nein |
| robust | 11 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | +1.88 % | -0.0 % | ja |
| robust | 12 | Statische Portfolios | TAA | mischung=All-Weather (vereinfacht), trend=200 | +0.29 % | -0.0 % | nein |
| robust | 13 | Williams-%R | SEKTOREN | n=5, x=-95, trend=0 | +0.03 % | -0.0 % | nein |
| robust | 14 | IBS-Rücksetzer | SPY | x=0.15, exit=vortageshoch, trend=0 | +0.03 % | -0.0 % | nein |
| robust | 15 | Williams-%R | IWM | n=5, x=-90, trend=0 | +0.03 % | -0.0 % | nein |
| robust | 16 | GTAA (Faber) | MULTI | n=150 | +0.47 % | -0.0 % | nein |
| robust | 17 | Niedrige-Vola-Auswahl | ALLE-KLASSEN | n=63, N=5, filt=keiner | +0.06 % | -0.1 % | nein |
| robust | 18 | Vola-Regime | QQQ | k=1.2 | +1.88 % | -0.0 % | ja |
| robust | 19 | SMA-Kreuz | MULTI | typ=sma, f=50, s=150 | +0.58 % | -0.0 % | nein |
| robust | 20 | ConnorsRSI | AKTIEN | x=5, exit=sma5, trend=200 | +0.03 % | -0.0 % | nein |
| robust | 21 | HAA (Keller) | TAA | top=4 | +0.02 % | -0.0 % | nein |
| robust | 22 | ConnorsRSI | QQQ | x=10, exit=sma5, trend=0 | +0.03 % | -0.0 % | nein |
| robust | 23 | Hebel + Trendfilter | HEBEL-SPY | L=1.0, regel=sma100, ausweich=IEF | +0.91 % | -0.0 % | nein |
| robust | 24 | RSI-Rücksetzer | AKTIEN | n=3, x=15, exit=rsi50, trend=200 | +0.09 % | -0.0 % | nein |
| robust | 25 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | +0.91 % | -0.0 % | nein |
| rendite | 1 | Hebel + Trendfilter | HEBEL-QQQ | L=3.0, regel=vola-regime, ausweich=IEF | +5.58 % | -0.0 % | ja |
| rendite | 2 | Hebel + Trendfilter | HEBEL-SPY | L=3.0, regel=sma200-band, ausweich=IEF | +2.65 % | -0.0 % | ja |
| rendite | 3 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | +2.04 % | -0.0 % | ja |
| rendite | 4 | Vola-Regime | QQQ | k=1.2 | +1.88 % | -0.0 % | ja |
| rendite | 5 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | +0.91 % | -0.0 % | nein |
| rendite | 6 | Dividende + niedrige Vola | AKTIEN | N=5 | -0.92 % | -1.1 % | nein |
| rendite | 7 | Januar-Barometer | QQQ | - | +1.88 % | -0.0 % | ja |
| rendite | 8 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | +0.94 % | -0.0 % | ja |
| rendite | 9 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | +1.88 % | -0.0 % | ja |
| rendite | 10 | Momentum-Rotation | AKTIEN | L=189, skip=21, N=5, reb=M, filt=spy200 | +1.84 % | -0.0 % | ja |
| rendite | 11 | Momentum-Rotation | SEKTOREN | L=252, skip=21, N=1, reb=W, filt=keiner | -1.72 % | -2.1 % | nein |
| rendite | 12 | Hohe Dividendenrendite | AKTIEN | N=10, reb=M, filt=keiner | -0.02 % | -0.7 % | nein |
| rendite | 13 | Momentum-Rotation | MULTI | L=189, skip=21, N=5, reb=M, filt=keiner | +1.39 % | -0.0 % | ja |
| rendite | 14 | Vola-Regime | IWM | k=1.5 | +1.55 % | -0.0 % | ja |
| rendite | 15 | IBS-Rücksetzer | QQQ | x=0.2, exit=vortageshoch, trend=0 | +0.41 % | -0.0 % | nein |
| rendite | 16 | Kurzfrist-Umkehr | MULTI | L=10, N=1, reb=M, filt=keiner | +0.83 % | -0.2 % | nein |
| rendite | 17 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | +0.91 % | -0.0 % | nein |
| rendite | 18 | Abwärtstage | QQQ | N=2, exit=sma5, trend=0 | +1.66 % | -0.0 % | ja |
| rendite | 19 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=3, filt=spy200 | -1.22 % | -1.2 % | nein |
| rendite | 20 | Momentum-Rotation | ALLE-KLASSEN | L=252, skip=21, N=1, reb=W, filt=spy200 | +0.20 % | -1.4 % | nein |
| rendite | 21 | RSI-Rücksetzer | QQQ | n=2, x=30, exit=rsi70, trend=0 | +1.66 % | -0.0 % | ja |
| rendite | 22 | Dividenden-Wachstum | AKTIEN | wachstum=0.0, reb=M, filt=spy200 | +0.50 % | -0.0 % | nein |
| rendite | 23 | Januar-Barometer | SPY | - | +0.91 % | -0.0 % | nein |
| rendite | 24 | Vola-Regime | SEKTOREN | k=1.5 | +0.56 % | -0.0 % | nein |
| rendite | 25 | Zeitreihen-Momentum | QQQ | n=21, skip=0 | +0.03 % | -0.0 % | nein |
| vergleich | 1 | 60/40 SPY/AGG | MULTI | - | +0.48 % | -0.0 % | nein |
| vergleich | 2 | Kaufen & Halten | QQQ | - | +1.88 % | -0.0 % | ja |
| vergleich | 3 | Kaufen & Halten | SPY | - | +0.91 % | -0.0 % | nein |

## Nach Gruppe

| Gruppe | Varianten | Median-Rendite seit Start | besser als SPY |
|---|---|---|---|
| Dividenden | 27 | +0.48 % | 6 |
| Hebel + Trend | 176 | +1.88 % | 132 |
| Kalender & Saison | 245 | +0.53 % | 67 |
| Long-Short | 646 | +0.04 % | 67 |
| Maschinelles Lernen | 120 | +0.33 % | 24 |
| Paarhandel | 72 | +0.09 % | 0 |
| Quartalszahlen | 33 | +0.05 % | 0 |
| Rotation & Faktoren | 1858 | +0.32 % | 475 |
| Rücksetzer kaufen | 3900 | +0.03 % | 314 |
| Tageshandel & Overnight | 510 | +0.03 % | 2 |
| Taktische Asset-Allokation | 78 | +0.29 % | 7 |
| Trendfolge | 1228 | +0.03 % | 112 |
| Volatilität & VIX | 537 | +0.44 % | 67 |
