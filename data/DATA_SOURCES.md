# Data sources and provenance

## Eurostat (five states air, six states road)
- Dataflow: sts_sepp_q (Services Producer Prices, quarterly).
- Air: NACE H51 (air transport, passenger included). Road: NACE H49.4 (coded H494).
- Filters: indic_bt = PRC_PRR, unit = I21 (index 2021=100), s_adj = NSA.
- Download (no key): https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/sts_sepp_q?format=SDMX-CSV&compressed=false
  then filter locally. Attribution: (c) European Union, Eurostat, reuse permitted with attribution.

## INSEE (French air)
- Series 010766683, CPF 51.21 air freight, base 2021=100, donnees brutes (NSA),
  2006-Q1 onward. The older base-2015 series 010546277 is discontinued; 010766683
  is its live replacement.
- File: FR_air_freight_INSEE_010766683.csv (provenance header included).
- Cross-validation: Eurostat FR road 2024-Q1 = 114.5 vs INSEE road = 114.7, the two
  sources agree on the overlapping series.
- Attribution: (c) INSEE, open data, reuse permitted with attribution.

## Definitional caveat carried through the project
French air is freight-only (CPF 51.21). The other five markets use the broader H51
division, which includes passenger air. A freight-only series swings more, so part of
France's high volatility ranking reflects the purer definition. Every document states
this wherever France appears.

## Processed files
- data/processed/prices_tidy_6.csv: tidy long table (date, geo, mode, value), common
  windows per market, comparison cut 2024-Q1.
- data/processed/fact_freight_6.csv: the dashboard fact table (adds z-score, rolling
  volatility, quarter-on-quarter change, quarter).
- results/results_6.json and results/results_upgrades.json: machine-readable results;
  every number in the reports and README is checked against these.
