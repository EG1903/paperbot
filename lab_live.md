# Papier-Test aller Strategien

Start 2026-10-27 (gerechnet ab Schlusskurs des Vortags), Stand 2026-11-16: **15 Handelstage**. Gleiche Regeln, Kosten und Ausfuehrung wie im Backtest, nur mit neuen Kursen.

- S&P 500 halten seit Start: **-3.35 %**
- Varianten mit mehr Rendite als SPY seit Start: 7092 von 9430

## Eingefrorene Liste (am Start festgelegt)

| Liste | Rang | Strategie | Markt | Parameter | Rendite seit Start | Max. Verlust | besser als SPY |
|---|---|---|---|---|---|---|---|
| robust | 1 | VAA (Keller) | TAA | set=G4, top=2, breite=1 | -1.19 % | -2.1 % | ja |
| robust | 2 | Risk-Parity | MULTI | n=126, trend=200 | -0.54 % | -0.9 % | ja |
| robust | 3 | Hebel + Trendfilter | HEBEL-QQQ | L=1.0, regel=vola-regime, ausweich=IEF | -5.45 % | -7.4 % | nein |
| robust | 4 | Williams-%R | AKTIEN | n=5, x=-95, trend=0 | +1.03 % | -0.9 % | ja |
| robust | 5 | DAA (Keller) | TAA | top=6, breite=1 | -1.19 % | -2.1 % | ja |
| robust | 6 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | -1.91 % | -2.9 % | ja |
| robust | 7 | Williams-%R | SPY | n=10, x=-90, trend=200 | -1.30 % | -4.4 % | ja |
| robust | 8 | PAA (Keller) | TAA | L=126, schutz=1, top=6, anleihe=IEF | -1.12 % | -2.1 % | ja |
| robust | 9 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=15, filt=spy200 | +3.27 % | -2.6 % | ja |
| robust | 10 | Niedrige-Vola-Auswahl | MULTI | n=126, N=5, filt=keiner | -0.90 % | -1.8 % | ja |
| robust | 11 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | -10.88 % | -12.5 % | nein |
| robust | 12 | Statische Portfolios | TAA | mischung=All-Weather (vereinfacht), trend=200 | -1.64 % | -2.0 % | ja |
| robust | 13 | Williams-%R | SEKTOREN | n=5, x=-95, trend=0 | +0.61 % | -1.6 % | ja |
| robust | 14 | IBS-Rücksetzer | SPY | x=0.15, exit=vortageshoch, trend=0 | +3.55 % | -0.7 % | ja |
| robust | 15 | Williams-%R | IWM | n=5, x=-90, trend=0 | +3.00 % | -1.0 % | ja |
| robust | 16 | GTAA (Faber) | MULTI | n=150 | -0.90 % | -1.4 % | ja |
| robust | 17 | Niedrige-Vola-Auswahl | ALLE-KLASSEN | n=63, N=5, filt=keiner | -0.80 % | -1.2 % | ja |
| robust | 18 | Vola-Regime | QQQ | k=1.2 | -4.01 % | -6.2 % | nein |
| robust | 19 | SMA-Kreuz | MULTI | typ=sma, f=50, s=150 | -1.44 % | -2.3 % | ja |
| robust | 20 | ConnorsRSI | AKTIEN | x=5, exit=sma5, trend=200 | +0.50 % | -0.0 % | ja |
| robust | 21 | HAA (Keller) | TAA | top=4 | -2.25 % | -2.9 % | ja |
| robust | 22 | ConnorsRSI | QQQ | x=10, exit=sma5, trend=0 | +0.24 % | -0.0 % | ja |
| robust | 23 | Hebel + Trendfilter | HEBEL-SPY | L=1.0, regel=sma100, ausweich=IEF | -5.29 % | -6.8 % | nein |
| robust | 24 | RSI-Rücksetzer | AKTIEN | n=3, x=15, exit=rsi50, trend=200 | +0.44 % | -0.4 % | ja |
| robust | 25 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | -3.35 % | -5.1 % | nein |
| rendite | 1 | Hebel + Trendfilter | HEBEL-QQQ | L=3.0, regel=vola-regime, ausweich=IEF | -13.97 % | -18.7 % | nein |
| rendite | 2 | Hebel + Trendfilter | HEBEL-SPY | L=3.0, regel=sma200-band, ausweich=IEF | -11.48 % | -15.6 % | nein |
| rendite | 3 | Kurzfrist-Umkehr | AKTIEN | L=5, N=15, reb=W, filt=keiner | +2.48 % | -3.7 % | ja |
| rendite | 4 | Vola-Regime | QQQ | k=1.2 | -4.01 % | -6.2 % | nein |
| rendite | 5 | Dual-Momentum GEM | MULTI | L=63, risk=SPY/QQQ/EFA | -1.91 % | -2.9 % | ja |
| rendite | 6 | Dividende + niedrige Vola | AKTIEN | N=5 | +4.71 % | -2.1 % | ja |
| rendite | 7 | Januar-Barometer | QQQ | - | -7.19 % | -10.9 % | nein |
| rendite | 8 | Kurzfrist-Umkehr | SEKTOREN | L=5, N=1, reb=M, filt=keiner | -5.50 % | -9.3 % | nein |
| rendite | 9 | VIX-Filter | QQQ | regel=vix<vix3m, f=0.95 | -10.88 % | -12.5 % | nein |
| rendite | 10 | Momentum-Rotation | AKTIEN | L=189, skip=21, N=5, reb=M, filt=spy200 | -12.39 % | -15.1 % | nein |
| rendite | 11 | Momentum-Rotation | SEKTOREN | L=252, skip=21, N=1, reb=W, filt=keiner | -8.58 % | -12.0 % | nein |
| rendite | 12 | Hohe Dividendenrendite | AKTIEN | N=10, reb=M, filt=keiner | +6.04 % | -2.5 % | ja |
| rendite | 13 | Momentum-Rotation | MULTI | L=189, skip=21, N=5, reb=M, filt=keiner | -5.14 % | -6.7 % | nein |
| rendite | 14 | Vola-Regime | IWM | k=1.5 | -1.50 % | -4.6 % | ja |
| rendite | 15 | IBS-Rücksetzer | QQQ | x=0.2, exit=vortageshoch, trend=0 | +2.38 % | -1.7 % | ja |
| rendite | 16 | Kurzfrist-Umkehr | MULTI | L=10, N=1, reb=M, filt=keiner | -12.95 % | -13.8 % | nein |
| rendite | 17 | Accelerating Dual Momentum | TAA | aktien=SPY/EFA, anleihe=TLT | -3.35 % | -5.1 % | nein |
| rendite | 18 | Abwärtstage | QQQ | N=2, exit=sma5, trend=0 | -3.12 % | -7.0 % | ja |
| rendite | 19 | Niedrige-Vola-Auswahl | AKTIEN | n=21, N=3, filt=spy200 | +6.76 % | -1.2 % | ja |
| rendite | 20 | Momentum-Rotation | ALLE-KLASSEN | L=252, skip=21, N=1, reb=W, filt=spy200 | -15.95 % | -17.3 % | nein |
| rendite | 21 | RSI-Rücksetzer | QQQ | n=2, x=30, exit=rsi70, trend=0 | -1.71 % | -7.0 % | ja |
| rendite | 22 | Dividenden-Wachstum | AKTIEN | wachstum=0.0, reb=M, filt=spy200 | +1.37 % | -3.3 % | ja |
| rendite | 23 | Januar-Barometer | SPY | - | -3.35 % | -5.1 % | nein |
| rendite | 24 | Vola-Regime | SEKTOREN | k=1.5 | -1.43 % | -3.6 % | ja |
| rendite | 25 | Zeitreihen-Momentum | QQQ | n=21, skip=0 | +0.24 % | -0.0 % | ja |
| vergleich | 1 | 60/40 SPY/AGG | MULTI | - | -2.21 % | -2.7 % | ja |
| vergleich | 2 | Kaufen & Halten | QQQ | - | -7.19 % | -10.9 % | nein |
| vergleich | 3 | Kaufen & Halten | SPY | - | -3.35 % | -5.1 % | nein |

## Nach Gruppe

| Gruppe | Varianten | Median-Rendite seit Start | besser als SPY |
|---|---|---|---|
| Dividenden | 27 | +3.85 % | 27 |
| Hebel + Trend | 176 | -7.58 % | 3 |
| Kalender & Saison | 245 | -1.57 % | 170 |
| Long-Short | 646 | -0.57 % | 481 |
| Maschinelles Lernen | 120 | -1.50 % | 84 |
| Paarhandel | 72 | +0.08 % | 72 |
| Quartalszahlen | 33 | +0.45 % | 33 |
| Rotation & Faktoren | 1858 | -5.18 % | 686 |
| Rücksetzer kaufen | 3900 | +0.22 % | 3570 |
| Tageshandel & Overnight | 510 | -0.15 % | 489 |
| Taktische Asset-Allokation | 78 | -1.52 % | 61 |
| Trendfolge | 1228 | -0.85 % | 1000 |
| Volatilität & VIX | 537 | -1.97 % | 416 |
