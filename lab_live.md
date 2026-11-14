# Papier-Test aller Strategien

Start 2026-10-27 (gerechnet ab Schlusskurs des Vortags), Stand 2026-11-13: **14 Handelstage**. Gleiche Regeln, Kosten und Ausfuehrung wie im Backtest, nur mit neuen Kursen.

- S&P 500 halten seit Start: **-1.46 %**
- Varianten mit mehr Rendite als SPY seit Start: 6342 von 9430

## Eingefrorene Liste (am Start festgelegt)

| Liste | Rang | Strategie | Markt | Parameter | Rendite seit Start | Max. Verlust | besser als SPY |
|---|---|---|---|---|---|---|---|
| robust | 1 | VAA (Keller) | TAA | set=G4, top=2, breite=1 | -1.41 % | -2.1 % | ja |
| robust | 2 | Risk-Parity | MULTI | n=126, trend=200 | -0.15 % | -0.9 % | ja |
| robust | 3 | Hebel + Trendfilter | HEBEL-QQQ | L=1.0, regel=vola-regime, ausweich=IEF | -5.66 % | -7.4 % | nein |
| robust | 4 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | +1.10 % | -0.9 % | ja |
| robust | 5 | DAA (Keller) | TAA | top=6, breite=1 | -1.41 % | -2.1 % | ja |
| robust | 6 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | -1.98 % | -2.9 % | nein |
| robust | 7 | Williams-%R | SPY | n=10, x=-90, trend=200 | +0.63 % | -4.4 % | ja |
| robust | 8 | PAA (Keller) | TAA | L=126, schutz=1, top=6, anleihe=IEF | -1.34 % | -2.1 % | ja |
| robust | 9 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | +3.95 % | -2.6 % | ja |
| robust | 10 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | -0.90 % | -1.8 % | ja |
| robust | 11 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | -8.42 % | -10.7 % | nein |
| robust | 12 | Statische Portfolios | TAA | mischung=All-Weather (vereinfacht), trend=200 | -0.94 % | -2.0 % | ja |
| robust | 13 | Williams-%R | SEKTOREN | n=5, x=-95, trend=0 | +0.59 % | -1.6 % | ja |
| robust | 14 | IBS-Rücksetzer | SPY | x=0.15, exit=vortageshoch, trend=0 | +3.53 % | -0.7 % | ja |
| robust | 15 | Williams-%R | IWM | n=5, x=-90, trend=0 | +2.98 % | -1.0 % | ja |
| robust | 16 | GTAA (Faber) | MULTI | n=150 | -0.65 % | -1.2 % | ja |
| robust | 17 | Niedrige-Vola-Auswahl | ALLE-KLASSEN | n=63, N=5, filt=keiner | -0.68 % | -1.1 % | ja |
| robust | 18 | Vola-Regime | QQQ | k=1.2 | -4.02 % | -6.2 % | nein |
| robust | 19 | SMA-Kreuz | MULTI | typ=sma, f=50, s=150 | -0.89 % | -2.3 % | ja |
| robust | 20 | ConnorsRSI | AKTIEN | x=5, exit=sma5, trend=200 | +0.48 % | -0.0 % | ja |
| robust | 21 | HAA (Keller) | TAA | top=4 | -0.91 % | -2.3 % | ja |
| robust | 22 | ConnorsRSI | QQQ | x=10, exit=sma5, trend=0 | +0.22 % | -0.0 % | ja |
| robust | 23 | Hebel + Trendfilter | HEBEL-SPY | L=1.0, regel=sma100, ausweich=IEF | -5.50 % | -6.8 % | nein |
| robust | 24 | RSI-Rücksetzer | AKTIEN | n=3, x=15, exit=rsi50, trend=200 | +0.42 % | -0.4 % | ja |
| robust | 25 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | -1.46 % | -5.1 % | nein |
| rendite | 1 | Hebel + Trendfilter | HEBEL-QQQ | L=3.0, regel=vola-regime, ausweich=IEF | -14.16 % | -18.7 % | nein |
| rendite | 2 | Hebel + Trendfilter | HEBEL-SPY | L=3.0, regel=sma200-band, ausweich=IEF | -5.98 % | -15.6 % | nein |
| rendite | 3 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | +4.67 % | -3.7 % | ja |
| rendite | 4 | Vola-Regime | QQQ | k=1.2 | -4.02 % | -6.2 % | nein |
| rendite | 5 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | -1.98 % | -2.9 % | nein |
| rendite | 6 | Dividende + niedrige Vola | AKTIEN | N=5 | +4.66 % | -2.1 % | ja |
| rendite | 7 | Januar-Barometer | QQQ | - | -4.63 % | -10.9 % | nein |
| rendite | 8 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | -2.31 % | -9.3 % | nein |
| rendite | 9 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | -8.42 % | -10.7 % | nein |
| rendite | 10 | Momentum-Rotation | AKTIEN | L=189, skip=21, N=5, reb=M, filt=spy200 | -9.40 % | -15.1 % | nein |
| rendite | 11 | Momentum-Rotation | SEKTOREN | L=252, skip=21, N=1, reb=W, filt=keiner | -6.74 % | -12.0 % | nein |
| rendite | 12 | Hohe Dividendenrendite | AKTIEN | N=10, reb=M, filt=keiner | +6.26 % | -2.5 % | ja |
| rendite | 13 | Momentum-Rotation | MULTI | L=189, skip=21, N=5, reb=M, filt=keiner | -2.93 % | -6.7 % | nein |
| rendite | 14 | Vola-Regime | IWM | k=1.5 | +0.16 % | -4.6 % | ja |
| rendite | 15 | IBS-Rücksetzer | QQQ | x=0.2, exit=vortageshoch, trend=0 | +2.37 % | -1.7 % | ja |
| rendite | 16 | Kurzfrist-Umkehr | MULTI | L=10, N=1, reb=M, filt=keiner | -9.36 % | -10.3 % | nein |
| rendite | 17 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | -1.46 % | -5.1 % | nein |
| rendite | 18 | Abwärtstage | QQQ | N=2, exit=sma5, trend=0 | -1.73 % | -7.0 % | nein |
| rendite | 19 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=3, filt=spy200 | +7.39 % | -1.2 % | ja |
| rendite | 20 | Momentum-Rotation | ALLE-KLASSEN | L=252, skip=21, N=1, reb=W, filt=spy200 | -12.59 % | -16.4 % | nein |
| rendite | 21 | RSI-Rücksetzer | QQQ | n=2, x=30, exit=rsi70, trend=0 | -1.73 % | -7.0 % | nein |
| rendite | 22 | Dividenden-Wachstum | AKTIEN | wachstum=0.0, reb=M, filt=spy200 | +2.46 % | -3.3 % | ja |
| rendite | 23 | Januar-Barometer | SPY | - | -1.46 % | -5.1 % | nein |
| rendite | 24 | Vola-Regime | SEKTOREN | k=1.5 | -0.69 % | -3.6 % | ja |
| rendite | 25 | Zeitreihen-Momentum | QQQ | n=21, skip=0 | +0.22 % | -0.0 % | ja |
| vergleich | 1 | 60/40 SPY/AGG | MULTI | - | -1.09 % | -2.6 % | ja |
| vergleich | 2 | Kaufen & Halten | QQQ | - | -4.63 % | -10.9 % | nein |
| vergleich | 3 | Kaufen & Halten | SPY | - | -1.46 % | -5.1 % | nein |

## Nach Gruppe

| Gruppe | Varianten | Median-Rendite seit Start | besser als SPY |
|---|---|---|---|
| Dividenden | 27 | +4.44 % | 27 |
| Hebel + Trend | 176 | -6.12 % | 0 |
| Kalender & Saison | 245 | -0.05 % | 162 |
| Long-Short | 646 | -0.69 % | 375 |
| Maschinelles Lernen | 120 | -0.96 % | 61 |
| Paarhandel | 72 | +0.12 % | 72 |
| Quartalszahlen | 33 | +0.46 % | 33 |
| Rotation & Faktoren | 1858 | -3.59 % | 584 |
| Rücksetzer kaufen | 3900 | +0.22 % | 3363 |
| Tageshandel & Overnight | 510 | -0.13 % | 440 |
| Taktische Asset-Allokation | 78 | -1.41 % | 44 |
| Trendfolge | 1228 | -0.55 % | 866 |
| Volatilität & VIX | 537 | -1.02 % | 315 |
