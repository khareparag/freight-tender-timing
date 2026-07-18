"""Upgrade analyses for Freight Lite / EU Freight Rate Risk Monitor.
Adds three analyses on top of analysis_fr.py, six-state scope, comparison rules intact:
  A. Robustness: CV gap pre-COVID (to 2019-Q4) and ex-COVID (drop 2020-2022).
  B. Tender-timing backtest: peak-season lock vs trough-season lock, per market per year.
  C. Out-of-sample seasonal check: air tail beyond the 2024-Q1 comparison cut, to 2026-Q1.
Baseline block reproduces results_6.json before anything new runs. Air #1f77b4, road #d62728.
"""
import json, warnings, os
import numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

BASE = "/sessions/laughing-funny-turing/mnt/Liora Project"
DATA = BASE + "/Freight_Rate_Data"
RB   = BASE + "/Freight_Project_Workspace/Reference_Build"
FIG  = RB + "/figures_6"
os.makedirs(FIG, exist_ok=True)
CUT = pd.Timestamp(2024, 3, 31)
G6 = ["DE", "IT", "ES", "NL", "PL", "FR"]
AIR_C, ROAD_C = "#1f77b4", "#d62728"

def qend(s):
    y, q = s.split("-Q")
    return pd.Timestamp(int(y), int(q) * 3, 1) + pd.offsets.MonthEnd(0)

def load(path):
    raw = pd.read_csv(path)
    f = raw[(raw.indic_bt == "PRC_PRR") & (raw.unit == "I21") & (raw.s_adj == "NSA")].copy()
    f["date"] = f["TIME_PERIOD"].map(qend)
    return f

air  = load(DATA + "/Air/Eurostat_Air_Transport_Price_Index_SPPI.csv")
road = load(DATA + "/Road/Eurostat_Road_Freight_Price_Index_SPPI.csv")
frair = pd.read_csv(RB + "/data/FR_air_freight_INSEE_010766683.csv", comment="#")
frair["date"] = pd.to_datetime(frair["date"])
frair = frair[["date", "geo", "mode", "value"]]

def tidy(f, mode, geos):
    t = f[f.geo.isin(geos)].dropna(subset=["OBS_VALUE"]).copy()
    t["mode"] = mode
    return t[["date", "geo", "mode", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "value"})

# ---- full air panel incl. tail beyond CUT (for out-of-sample only) ----
air_full = pd.concat([tidy(air, "air", G6), frair[frair.geo.isin(G6)]], ignore_index=True)
air_full = air_full.sort_values(["geo", "date"]).reset_index(drop=True)

# ---- comparison panel, identical construction to analysis_fr.py ----
rows, windows = [], {}
ta, tr = air_full.copy(), tidy(road, "road", G6)
for g in G6:
    a, r = ta[ta.geo == g], tr[tr.geo == g]
    start = max(a.date.min(), r.date.min()); end = min(a.date.max(), r.date.max(), CUT)
    windows[g] = [str(start.date()), str(end.date())]
    for t in (a, r):
        rows.append(t[(t.date >= start) & (t.date <= end)])
comp = pd.concat(rows, ignore_index=True).sort_values(["mode", "geo", "date"])
comp["pct_qoq"] = comp.groupby(["mode", "geo"])["value"].transform(lambda s: s.pct_change())
comp["quarter"] = comp["date"].dt.quarter
comp["year"] = comp["date"].dt.year

def cv_table(frame):
    p = (frame.groupby(["mode", "geo"])["value"].agg(lambda s: s.std() / s.mean())
         .rename("cv").reset_index().pivot(index="geo", columns="mode", values="cv")
         .reindex(G6).round(4))
    return p

# ---- baseline check against results_6.json ----
cvp = cv_table(comp)
base_air, base_road = round(float(cvp["air"].mean()), 4), round(float(cvp["road"].mean()), 4)
stored = json.load(open(RB + "/results/results_6.json"))
ok = (abs(base_air - stored["cv_mean_air"]) < 1e-4) and (abs(base_road - stored["cv_mean_road"]) < 1e-4)
print("BASELINE CHECK", "PASS" if ok else "FAIL", base_air, base_road,
      "stored", stored["cv_mean_air"], stored["cv_mean_road"])

# =====================================================================
# A. ROBUSTNESS
# =====================================================================
def variant(frame, label, keep_mask_levels, keep_mask_changes):
    lv = frame[keep_mask_levels(frame)]
    p = cv_table(lv)
    ca = frame[(frame["mode"] == "air") & keep_mask_changes(frame)]["pct_qoq"].dropna()
    cr = frame[(frame["mode"] == "road") & keep_mask_changes(frame)]["pct_qoq"].dropna()
    L = stats.levene(ca, cr, center="median")
    out = {"label": label,
           "cv_by_geo": p.reset_index().round(4).to_dict("records"),
           "cv_mean_air": round(float(p["air"].mean()), 4),
           "cv_mean_road": round(float(p["road"].mean()), 4),
           "cv_ratio": round(float(p["air"].mean() / p["road"].mean()), 2),
           "levene_stat": round(float(L.statistic), 2), "levene_p": float(L.pvalue),
           "chg_std_air": round(float(ca.std()), 4), "chg_std_road": round(float(cr.std()), 4),
           "n_air_levels": int(lv[lv["mode"] == "air"].shape[0]),
           "n_air_changes": int(ca.size), "n_road_changes": int(cr.size)}
    return out

pre_end = pd.Timestamp(2019, 12, 31)
rob_pre = variant(
    comp, "pre_covid_to_2019Q4",
    lambda f: f["date"] <= pre_end,
    lambda f: f["date"] <= pre_end)
# ex-COVID: drop level years 2020-2022; drop changes dated 2020-Q1 through 2023-Q1
chg_lo, chg_hi = pd.Timestamp(2020, 3, 31), pd.Timestamp(2023, 3, 31)
rob_ex = variant(
    comp, "ex_covid_drop_2020_2022",
    lambda f: ~f["year"].isin([2020, 2021, 2022]),
    lambda f: ~((f["date"] >= chg_lo) & (f["date"] <= chg_hi)))

print("\nA. ROBUSTNESS")
for r in (rob_pre, rob_ex):
    print(r["label"], "air", r["cv_mean_air"], "road", r["cv_mean_road"], "ratio", r["cv_ratio"],
          "levene", r["levene_stat"], "p", r["levene_p"],
          "chg_std air/road", r["chg_std_air"], r["chg_std_road"])

# =====================================================================
# B. TENDER-TIMING BACKTEST (air; road for contrast)
# =====================================================================
def backtest(frame, mode):
    sub = frame[frame["mode"] == mode]
    recs = []
    for (g, y), grp in sub.groupby(["geo", "year"]):
        if grp["quarter"].nunique() != 4:
            continue
        mid = grp[grp.quarter.isin([2, 3])]["value"].mean()
        tro = grp[grp.quarter.isin([1, 4])]["value"].mean()
        recs.append({"geo": g, "year": int(y),
                     "edge_pct": (mid - tro) / grp["value"].mean() * 100})
    df = pd.DataFrame(recs)
    pooled = {"n_geo_years": int(len(df)),
              "mean_edge_pct": round(float(df.edge_pct.mean()), 2),
              "median_edge_pct": round(float(df.edge_pct.median()), 2),
              "hit_rate_pct": round(float((df.edge_pct > 0).mean() * 100), 1),
              "worst": {"geo": df.loc[df.edge_pct.idxmin(), "geo"],
                        "year": int(df.loc[df.edge_pct.idxmin(), "year"]),
                        "edge_pct": round(float(df.edge_pct.min()), 2)},
              "best": {"geo": df.loc[df.edge_pct.idxmax(), "geo"],
                       "year": int(df.loc[df.edge_pct.idxmax(), "year"]),
                       "edge_pct": round(float(df.edge_pct.max()), 2)}}
    per_geo = (df.groupby("geo")["edge_pct"]
               .agg(mean="mean", hit=lambda s: (s > 0).mean() * 100, n="count")
               .round(2).reindex(G6).reset_index().to_dict("records"))
    return df, pooled, per_geo

bt_air_df, bt_air, bt_air_geo = backtest(comp, "air")
bt_road_df, bt_road, bt_road_geo = backtest(comp, "road")

# operational variant: lock at (Q4 prev year + Q1) vs (Q2 + Q3)
def backtest_op(frame, mode):
    sub = frame[frame["mode"] == mode]
    recs = []
    for g in G6:
        gg = sub[sub.geo == g].set_index("date").sort_index()
        for y in sorted(gg["year"].unique()):
            yr = gg[gg["year"] == y]
            if yr["quarter"].nunique() != 4:
                continue
            q4_prev = gg[(gg["year"] == y - 1) & (gg["quarter"] == 4)]["value"]
            if q4_prev.empty:
                continue
            tro = (q4_prev.iloc[0] + yr[yr.quarter == 1]["value"].iloc[0]) / 2
            mid = yr[yr.quarter.isin([2, 3])]["value"].mean()
            recs.append({"geo": g, "year": int(y),
                         "edge_pct": (mid - tro) / yr["value"].mean() * 100})
    df = pd.DataFrame(recs)
    return {"n_geo_years": int(len(df)),
            "mean_edge_pct": round(float(df.edge_pct.mean()), 2),
            "hit_rate_pct": round(float((df.edge_pct > 0).mean() * 100), 1)}

bt_air_op = backtest_op(comp, "air")

print("\nB. BACKTEST air pooled", bt_air, "\n   air per geo", bt_air_geo,
      "\n   air operational-lock variant", bt_air_op, "\n   road pooled", bt_road)

# =====================================================================
# C. OUT-OF-SAMPLE (air tail beyond 2024-Q1, to 2026-Q1)
# =====================================================================
tail = air_full[air_full.date > pd.Timestamp(2023, 12, 31)].copy()
tail["quarter"] = tail["date"].dt.quarter
tail["year"] = tail["date"].dt.year
cov = tail.groupby("geo")["date"].agg(["min", "max", "count"])
print("\nC. TAIL COVERAGE\n", cov)

oos = {"coverage": {g: [str(cov.loc[g, "min"].date()), str(cov.loc[g, "max"].date()),
                        int(cov.loc[g, "count"])] for g in cov.index}}
recs = []
for g in G6:
    gg = air_full[air_full.geo == g].sort_values("date").set_index("date")
    gg["pct_qoq"] = gg["value"].pct_change()
    for y in (2024, 2025):
        yr = gg[gg.index.year == y]
        if yr.shape[0] < 4:
            continue
        q2 = yr[yr.index.quarter == 2]["pct_qoq"]
        mid = yr[yr.index.quarter.isin([2, 3])]["value"].mean()
        tro = yr[yr.index.quarter.isin([1, 4])]["value"].mean()
        recs.append({"geo": g, "year": y,
                     "q2_qoq_pct": round(float(q2.iloc[0]) * 100, 2) if len(q2) else None,
                     "midyear_premium_pct": round(float((mid - tro) / yr["value"].mean() * 100), 2)})
oos_df = pd.DataFrame(recs)
oos["per_geo_year"] = oos_df.to_dict("records")
if len(oos_df):
    oos["q2_rise_hit_rate_pct"] = round(float((oos_df.q2_qoq_pct > 0).mean() * 100), 1)
    oos["premium_positive_hit_rate_pct"] = round(float((oos_df.midyear_premium_pct > 0).mean() * 100), 1)
    oos["mean_q2_qoq_pct"] = round(float(oos_df.q2_qoq_pct.mean()), 2)
    oos["mean_midyear_premium_pct"] = round(float(oos_df.midyear_premium_pct.mean()), 2)
# 2026-Q1 softness check where published
q1_26 = []
for g in G6:
    gg = air_full[air_full.geo == g].sort_values("date").set_index("date")
    gg["pct_qoq"] = gg["value"].pct_change()
    v = gg[gg.index == pd.Timestamp(2026, 3, 31)]["pct_qoq"]
    if len(v):
        q1_26.append({"geo": g, "q1_2026_qoq_pct": round(float(v.iloc[0]) * 100, 2)})
oos["q1_2026_softness"] = q1_26
print("OOS pooled:", {k: v for k, v in oos.items() if k not in ("per_geo_year", "coverage")})
print(oos_df)

# =====================================================================
# FIGURES 13-15
# =====================================================================
def save(fig, n):
    fig.tight_layout(); fig.savefig(FIG + "/" + n, dpi=120); plt.close(fig)

# fig13: backtest edge distribution by market
fig, ax = plt.subplots(figsize=(10, 4.5))
data = [bt_air_df[bt_air_df.geo == g]["edge_pct"].values for g in G6]
bp = ax.boxplot(data, labels=G6, patch_artist=True, medianprops=dict(color="black"))
for b in bp["boxes"]:
    b.set_facecolor(AIR_C); b.set_alpha(0.55)
ax.axhline(0, color="grey", lw=0.8)
ax.axhline(bt_air["mean_edge_pct"], color=ROAD_C, lw=1.2, ls="--",
           label=f"pooled mean {bt_air['mean_edge_pct']}%")
ax.set_title("Fig 13. Tender-timing backtest: peak-season lock minus trough-season lock, air, % of year mean")
ax.set_ylabel("Edge of trough-season lock (%)"); ax.legend()
save(fig, "fig13_tender_backtest.png")

# fig14: out-of-sample air tail with Q2 shading
fig, ax = plt.subplots(figsize=(10, 4.8))
show = air_full[air_full.date >= pd.Timestamp(2023, 1, 1)]
cols = {"DE": "#1f77b4", "IT": "#ff7f0e", "ES": "#2ca02c", "NL": "#9467bd", "PL": "#8c564b", "FR": "#e377c2"}
for g in G6:
    s = show[show.geo == g]
    ax.plot(s.date, s.value, label=g, color=cols[g], lw=1.6)
for y in (2024, 2025):
    ax.axvspan(pd.Timestamp(y, 4, 1), pd.Timestamp(y, 6, 30), color=AIR_C, alpha=0.12)
ax.axvline(CUT, color="black", lw=1.0, ls=":", label="comparison cut 2024-Q1")
ax.set_title("Fig 14. Out-of-sample check: air rate index beyond the comparison window (Q2 shaded)")
ax.set_ylabel("Index (2021=100)"); ax.legend(ncol=4, fontsize=8)
save(fig, "fig14_oos_seasonal.png")

# fig15: robustness CV means, full vs pre-COVID vs ex-COVID
fig, ax = plt.subplots(figsize=(9, 4.5))
labels = ["Full window", "Pre-COVID\n(to 2019-Q4)", "Ex-COVID\n(drop 2020-22)"]
airv = [base_air, rob_pre["cv_mean_air"], rob_ex["cv_mean_air"]]
roadv = [base_road, rob_pre["cv_mean_road"], rob_ex["cv_mean_road"]]
x = np.arange(3); w = 0.38
ax.bar(x - w / 2, airv, w, label="air", color=AIR_C)
ax.bar(x + w / 2, roadv, w, label="road", color=ROAD_C)
for i, (a, r) in enumerate(zip(airv, roadv)):
    ax.text(i - w / 2, a + 0.002, f"{a:.3f}", ha="center", fontsize=8)
    ax.text(i + w / 2, r + 0.002, f"{r:.3f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_title("Fig 15. Robustness: mean CV by mode, three windows (6 states)")
ax.set_ylabel("Mean CV (std/mean of level)"); ax.legend()
save(fig, "fig15_robustness_cv.png")

# =====================================================================
OUT = {"built": "2026-07-02",
       "baseline_check": {"pass": bool(ok), "cv_mean_air": base_air, "cv_mean_road": base_road},
       "robustness": {"pre_covid": rob_pre, "ex_covid": rob_ex},
       "backtest_air": {"pooled": bt_air, "per_geo": bt_air_geo,
                        "operational_lock_variant": bt_air_op,
                        "definition": "edge = (mean(Q2,Q3) - mean(Q1,Q4)) / year mean * 100, per geo-year, complete years in the common window"},
       "backtest_road_contrast": bt_road,
       "out_of_sample_air": oos,
       "figures": ["fig13_tender_backtest.png", "fig14_oos_seasonal.png", "fig15_robustness_cv.png"]}
json.dump(OUT, open(RB + "/results/results_upgrades.json", "w"), indent=2, default=str)
bt_air_df.round(3).to_csv(RB + "/results/backtest_air_geo_years.csv", index=False)
print("\nWROTE results_upgrades.json, backtest_air_geo_years.csv, fig13-15. DONE")
