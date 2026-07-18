# Power BI Build Guide — Freight Lite dashboard
Mohamed confirmed Power BI. A .pbix is a binary you assemble in Power BI Desktop, so this guide
gives you the exact data source, the model, the DAX, and the four pages. You build and defend it.

Data source: ../data/processed/fact_freight.csv
Columns: date, geo, mode, value, value_z, roll_std_4q, pct_qoq, quarter
Rows: 550 (five states, both modes, common windows). No France (no air data).

> Sanity targets while you build. Mean CV: air 0.149, road 0.099. Q2 mean QoQ: air +3.08%,
> road +1.10%. If a card shows something far off, a filter or a measure is wrong.

## Step 1. Import and type the data
1. Home > Get data > Text/CSV > fact_freight.csv > Load.
2. In Power Query, set types: date = Date, geo = Text, mode = Text, value/value_z/roll_std_4q/pct_qoq = Decimal, quarter = Whole number.
3. Add a Year column from date (Add Column > Date > Year) for the axis. Close and Apply.

> Study note. Type the date as Date, not Text, or the time axis sorts wrong and the rolling line zig-zags.

## Step 2. Measures (DAX)
Create these in a Measures table (Modeling > New measure).
- Mean CV (air) = CALCULATE(AVERAGEX(VALUES(fact[geo]), CALCULATE(DIVIDE(STDEV.P(fact[value]), AVERAGE(fact[value])))), fact[mode]="air")
  Simpler path: precompute CV per geo upstream if DAX feels heavy. The CSV already lets you AVERAGE roll_std_4q for a quick volatility KPI.
- Latest index = CALCULATE(LASTNONBLANK(fact[value], 1), FILTER(fact, fact[date]=MAX(fact[date])))
- Avg rolling volatility = AVERAGE(fact[roll_std_4q])
- Avg QoQ change % = AVERAGE(fact[pct_qoq]) * 100
- Mean CV by mode (display): build a small summary visual on value grouped by mode using STDEV.P / AVERAGE.

> Study note. Define your volatility KPI in one sentence before you build it. Jury question 26 is
> "define your volatility KPI exactly as the dashboard computes it." Use: average of the 4-quarter
> rolling standard deviation of the z-scored level.

## Step 3. The four pages
One country slicer (field: geo), placed on every page and set to Sync slicers across pages.

Page 1 — Overview
- Three KPI cards: Latest index, Avg QoQ change %, Avg rolling volatility.
- Line chart: axis = date, values = value, legend = mode. Title "Air vs road price index".
- Slicer: geo.

Page 2 — Volatility
- Line chart: axis = date, value = roll_std_4q, legend = mode. Title "Rolling 4Q volatility".
- Clustered bar: axis = geo, value = a CV measure, legend = mode. Title "CV by mode and country".
- Read: air bars top road for DE, IT, ES.

Page 3 — Seasonality
- Clustered column: axis = quarter (1-4), value = Avg QoQ change %, legend = mode.
- Caption text box: "Kruskal-Wallis quarter effect: air p approx 4e-16, road p approx 8e-4. Both seasonal, peak Q2."

Page 4 — Context and limits
- Line chart of the EU27 air-only series (load ../data/processed/air_eu_context.csv as a second table). Title "EU27 air index, long history".
- Text panel: three limits (passenger air in H51, road has no EU aggregate, France has no air data).

## Step 4. Formatting and bug-free checks
- Consistent colours: air one colour, road another, used on every page.
- Title every visual, label every axis, no raw column names showing.
- Click each country in the slicer and watch all pages. No visual should blank or error. Poland and Netherlands will show road above air, that is correct, not a bug.
- Spelling and layout pass. Mohamed grades layout, visuals, spelling, clarity.

## Step 5. Demo and export
- For the 3 or 4 August demo: open with page 1, change the slicer to DE live, then walk pages 2 and 3.
- Export a PDF (File > Export > PDF) as a backup in case the live app fails on the day.

> Study note. Always carry a PDF or screenshot backup of a live dashboard to a defence. "The app
> must run bug-free" is graded, and a frozen backup saves you if the laptop or projector misbehaves.
