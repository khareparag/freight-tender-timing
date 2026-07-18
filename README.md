# EU Freight Rate Risk Monitor - Category Manager Edition

This is the category-manager edition of my EU Freight Rate Risk Monitor: the same
analysis, presented for tender-timing and budget decisions. Canonical study repo:
[freight-rate-risk-monitor](https://github.com/khareparag/freight-rate-risk-monitor)
(analysis synced July 2026). Pricing edition:
[freight-pricing-volatility](https://github.com/khareparag/freight-pricing-volatility).
Streaming extension: [freight-rate-stream](https://github.com/khareparag/freight-rate-stream).

Every freight category plan answers two questions, usually by habit: when do we go to
market, and how much room does the budget leave? This study answers both with twenty
years of official EU rate data: air versus road across six EU markets (Germany, Italy,
Spain, Netherlands, Poland, France), built on open Eurostat and INSEE series covering
2003 to 2024. Every claim below is backed by a statistical test in the repo.

## Budget air as a band, not a point
In a typical year air rates move inside a 6.7% band; road moves 2.8%. On 10 million euro
of air spend that band is roughly 670,000 euro of rate movement a budget owner either
plans for or explains later. Road's narrow band is why it holds longer fixed terms
comfortably; air wants shorter agreements, indexation, or both.

## Tender into the trough
Air peaks in Q2, climbing about 3.2% into the spring quarter. Across 85 backtested
market-years, locking air at trough-season levels (Q4 to Q1) beat peak-season locks in
75% of years, average edge 1.8% - in Germany, 8 years of 9. On the same 10 million euro,
timing alone is worth roughly 180,000 euro. Out of sample, the Q2 climb repeated in
10 of 12 market-years across 2024 and 2025.

## Respect the exceptions
The rule is not uniform, and this is the point. In Poland road is the volatile mode, not
air. In France the timing rule fails (44% hit rate on the freight-only series). The study
therefore ships with per-lane validation: segment by market, validate the lane, then
contract.

## The working tool
A self-built, five-tab monitor with a live budget-band what-if: enter an exposure, read
the band in euros. It refreshes each quarter from the public sources.
Live monitor: https://khareparag.github.io/freight-rate-risk-monitor/
Full write-up for category managers: https://rfq.ch/projects/tender-timing/

## Now live as well
Since July 2026 the study also runs in motion: a streaming extension watches the same
bands live and fires a rate-shock alert the moment a market breaks its pattern. Replayed
over 2019-2022, the 2020 air spike fires alerts exactly where the study's charts show it.
The story: https://rfq.ch/projects/freight-rate-stream/

## Reproduce it
```
pip install pandas scipy matplotlib
python code/analysis_fr.py        # six-state pipeline, writes results_6.json
python code/analysis_upgrades.py  # backtest, robustness, out-of-sample
```
results/ holds the machine-readable outputs every number above is checked against.

## Author
Parag Khare. Twelve-plus years in freight pricing, tendering and procurement, seller and
buyer side, including tender platform work for 68+ enterprise shippers. Built to be
reused by freight category managers.

- Site: https://rfq.ch/
- LinkedIn: https://www.linkedin.com/in/khareparag/
- Email: pk@rfq.ch
