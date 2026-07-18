import json, warnings, os
import numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

BASE="/sessions/zen-vibrant-ritchie/mnt/Claude Application Files/Liora Project"
DATA=BASE+"/Freight_Rate_Data"; RB=BASE+"/Freight_Project_Workspace/Reference_Build"
os.makedirs(RB+"/figures_6", exist_ok=True)
CUT=pd.Timestamp(2024,3,31)

def qend(s):
    y,q=s.split("-Q"); return pd.Timestamp(int(y),int(q)*3,1)+pd.offsets.MonthEnd(0)
def load(path):
    raw=pd.read_csv(path)
    f=raw[(raw.indic_bt=="PRC_PRR")&(raw.unit=="I21")&(raw.s_adj=="NSA")].copy()
    f["date"]=f["TIME_PERIOD"].map(qend); return f
air=load(DATA+"/Air/Eurostat_Air_Transport_Price_Index_SPPI.csv")
road=load(DATA+"/Road/Eurostat_Road_Freight_Price_Index_SPPI.csv")
frair=pd.read_csv(RB+"/data/FR_air_freight_INSEE_010766683.csv", comment="#")
frair["date"]=pd.to_datetime(frair["date"]); frair=frair[["date","geo","mode","value"]]

def tidy(f,mode,geos):
    t=f[f.geo.isin(geos)].dropna(subset=["OBS_VALUE"]).copy(); t["mode"]=mode
    return t[["date","geo","mode","OBS_VALUE"]].rename(columns={"OBS_VALUE":"value"})

def run(geos, inject_fr):
    ta=tidy(air,"air",geos)
    if inject_fr: ta=pd.concat([ta, frair[frair.geo.isin(geos)]], ignore_index=True)
    tr=tidy(road,"road",geos)
    rows,windows=[],{}
    for g in geos:
        a,r=ta[ta.geo==g], tr[tr.geo==g]
        if a.empty or r.empty: continue
        start=max(a.date.min(),r.date.min()); end=min(a.date.max(),r.date.max(),CUT)
        windows[g]=[str(start.date()),str(end.date())]
        for t in (a,r): rows.append(t[(t.date>=start)&(t.date<=end)])
    comp=pd.concat(rows,ignore_index=True).sort_values(["mode","geo","date"])
    comp["value_z"]=comp.groupby(["mode","geo"])["value"].transform(lambda s:(s-s.mean())/s.std())
    comp["roll_std_4q"]=comp.groupby(["mode","geo"])["value_z"].transform(lambda s:s.rolling(4).std())
    comp["pct_qoq"]=comp.groupby(["mode","geo"])["value"].transform(lambda s:s.pct_change())
    comp["quarter"]=comp["date"].dt.quarter; comp["year"]=comp["date"].dt.year
    R={"common_windows":windows}
    cvp=comp.groupby(["mode","geo"])["value"].agg(lambda s:s.std()/s.mean()).rename("cv").reset_index().pivot(index="geo",columns="mode",values="cv").reindex(geos).round(4)
    R["cv_pivot"]=cvp; R["cv_mean_air"]=round(float(cvp["air"].mean()),4); R["cv_mean_road"]=round(float(cvp["road"].mean()),4)
    ac=comp[comp["mode"]=="air"]["pct_qoq"].dropna(); rc=comp[comp["mode"]=="road"]["pct_qoq"].dropna()
    L=stats.levene(ac,rc,center="median")
    R["levene"]={"stat":round(float(L.statistic),4),"p":float(L.pvalue),"air_std":round(float(ac.std()),4),"road_std":round(float(rc.std()),4),"n_air":int(ac.size),"n_road":int(rc.size)}
    def kw(m):
        sub=comp[comp["mode"]==m]; g=[sub[sub.quarter==q]["pct_qoq"].dropna() for q in (1,2,3,4)]; k=stats.kruskal(*g)
        mn={"Q"+str(q):round(float(sub[sub.quarter==q]["pct_qoq"].mean())*100,2) for q in (1,2,3,4)}
        return {"stat":round(float(k.statistic),4),"p":float(k.pvalue),"means":mn,"peak":max(mn,key=mn.get)}
    R["kw_air"]=kw("air"); R["kw_road"]=kw("road")
    def band(m):
        sub=comp[comp["mode"]==m]; v=[(grp["value"].max()-grp["value"].min())/grp["value"].mean()*100 for (_,_),grp in sub.groupby(["geo","year"]) if grp["quarter"].nunique()==4]
        return round(float(np.mean(v)),2)
    R["band_air"]=band("air"); R["band_road"]=band("road")
    def prem(m):
        sub=comp[comp["mode"]==m]; v=[]
        for (_,_),grp in sub.groupby(["geo","year"]):
            if grp["quarter"].nunique()==4:
                mid=grp[grp.quarter.isin([2,3])]["value"].mean(); en=grp[grp.quarter.isin([1,4])]["value"].mean(); mm=grp["value"].mean()
                if mm: v.append((mid-en)/mm*100)
        return round(float(np.mean(v)),2)
    R["prem_air"]=prem("air"); R["prem_road"]=prem("road")
    R["ratio"]=round(max(R["cv_mean_air"],R["cv_mean_road"])/min(R["cv_mean_air"],R["cv_mean_road"]),2)
    R["comp"]=comp
    return R

G5=["DE","IT","ES","NL","PL"]; G6=["DE","IT","ES","NL","PL","FR"]
r5=run(G5,False); r6=run(G6,True)

print("##### BASELINE 5-COUNTRY (should match results.json) #####")
print(r5["cv_pivot"]); print("cv_mean air",r5["cv_mean_air"],"road",r5["cv_mean_road"],"ratio",r5["ratio"])
print("levene",r5["levene"]); print("kw_air",r5["kw_air"]["stat"],r5["kw_air"]["p"],"peak",r5["kw_air"]["peak"]); print("kw_road",r5["kw_road"]["stat"],r5["kw_road"]["p"])
print("band air/road",r5["band_air"],r5["band_road"],"prem air/road",r5["prem_air"],r5["prem_road"])
# compare to stored results.json
try:
    js=json.load(open(RB+"/results/results.json"))
    print("STORED cv_mean_air",js.get("cv_mean_air"),"road",js.get("cv_mean_road"),"levene_p",js["levene_pooled"]["p"],"kw_air_stat",js["kruskal_air"]["stat"])
except Exception as e: print("no stored",e)

print("\n##### 6-COUNTRY (with France) #####")
print(r6["cv_pivot"]); print("cv_mean air",r6["cv_mean_air"],"road",r6["cv_mean_road"],"ratio",r6["ratio"])
print("windows_FR",r6["common_windows"].get("FR"))
print("levene",r6["levene"]); print("kw_air",r6["kw_air"]); print("kw_road",r6["kw_road"])
print("band air/road",r6["band_air"],r6["band_road"],"prem air/road",r6["prem_air"],r6["prem_road"])
print("FR_CV", r6["cv_pivot"].loc["FR"].to_dict())

# write 6-country outputs
comp=r6["comp"]
comp[["date","geo","mode","value"]].to_csv(RB+"/data/processed/prices_tidy_6.csv",index=False)
comp[["date","geo","mode","value","value_z","roll_std_4q","pct_qoq","quarter"]].to_csv(RB+"/data/processed/fact_freight_6.csv",index=False)
OUT={"n_states":6,"states":G6,"common_windows":r6["common_windows"],
 "cv_by_geo":r6["cv_pivot"].reset_index().to_dict("records"),
 "cv_mean_air":r6["cv_mean_air"],"cv_mean_road":r6["cv_mean_road"],"cv_ratio":r6["ratio"],
 "levene_pooled":r6["levene"],"kruskal_air":r6["kw_air"],"kruskal_road":r6["kw_road"],
 "intra_year_band_air":r6["band_air"],"intra_year_band_road":r6["band_road"],
 "seasonal_premium_air":r6["prem_air"],"seasonal_premium_road":r6["prem_road"],
 "baseline_5country":{"cv_mean_air":r5["cv_mean_air"],"cv_mean_road":r5["cv_mean_road"],"cv_ratio":r5["ratio"],"levene_p":r5["levene"]["p"]},
 "france_source":"air=INSEE BDM 010766683 (CPF 51.21, base 2021, NSA); road=Eurostat H494 (I21, NSA)"}
json.dump(OUT,open(RB+"/results/results_6.json","w"),indent=2,default=str)

# figures
def save(fig,n): fig.tight_layout(); fig.savefig(RB+"/figures_6/"+n,dpi=120); plt.close(fig)
w=0.38; cvp=r6["cv_pivot"]
fig,ax=plt.subplots(figsize=(10,4.5)); x=np.arange(len(G6))
ax.bar(x-w/2,cvp["air"],w,label="air",color="#1f77b4"); ax.bar(x+w/2,cvp["road"],w,label="road",color="#d62728")
ax.set_xticks(x); ax.set_xticklabels(G6); ax.set_title("Fig 4. Coefficient of variation by mode and country (6 states, France added)"); ax.set_ylabel("CV (std/mean of level)"); ax.legend(); save(fig,"fig4_cv_ranking.png")
fig,ax=plt.subplots(figsize=(9,4.5)); qx=np.arange(4)
am=[r6["kw_air"]["means"]["Q"+str(q)] for q in (1,2,3,4)]; rm=[r6["kw_road"]["means"]["Q"+str(q)] for q in (1,2,3,4)]
ax.bar(qx-w/2,am,w,label="air",color="#1f77b4"); ax.bar(qx+w/2,rm,w,label="road",color="#d62728")
ax.set_xticks(qx); ax.set_xticklabels(["Q1","Q2","Q3","Q4"]); ax.axhline(0,color="grey",lw=0.8); ax.set_title("Fig 5. Mean QoQ rate change by quarter (%), 6 states"); ax.set_ylabel("Mean QoQ change (%)"); ax.legend(); save(fig,"fig5_quarter_effect.png")
fig,ax=plt.subplots(figsize=(9,4.5))
for m,c in [("air","#1f77b4"),("road","#d62728")]:
    s=comp[(comp["mode"]==m)&(comp.geo=="FR")]; ax.plot(s.date,s.value,label=m,color=c)
ax.set_title("Fig 2b. France air vs road rate index (air INSEE 51.21, road Eurostat, 2021=100)"); ax.set_xlabel("Quarter"); ax.set_ylabel("Index (2021=100)"); ax.legend(); save(fig,"fig2b_FR_air_vs_road_level.png")
print("\nFILES written: fact_freight_6.csv, prices_tidy_6.csv, results_6.json, figures_6/*"); print("DONE")
