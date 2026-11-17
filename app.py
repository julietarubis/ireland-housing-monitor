"""Ireland Housing Monitor — Streamlit Community Cloud dashboard."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import streamlit as st

from monitor import DATA, config, fetch_csv, news_feed, slug

st.set_page_config(page_title="Ireland Housing Monitor", page_icon="🏠", layout="wide")

st.markdown("""<style>
.block-container {padding-top: 2rem; max-width: 1400px;}
[data-testid='stMetric'] {background: rgba(130,130,130,.07); padding: 1rem; border-radius: 12px;}
</style>""", unsafe_allow_html=True)

cfg = config()
st.title("🏠 Ireland Housing Monitor")
st.caption("Irish property prices, registered rents and housing headlines • CSO / RTB public data")

@st.cache_data(ttl=3600, show_spinner=False)
def load_public_data(label: str, url: str, online: bool):
    cached_file = DATA / f"{slug(label)}.csv"
    if online:
        try:
            return fetch_csv(url), "Live public-data API"
        except Exception as exc:
            if cached_file.exists():
                return pd.read_csv(cached_file, low_memory=False), f"Saved GitHub snapshot (live refresh unavailable: {exc})"
            raise
    if cached_file.exists():
        return pd.read_csv(cached_file, low_memory=False), "Scheduled GitHub snapshot"
    # On a new GitHub project, GitHub Actions may not have run yet.
    return fetch_csv(url), "Live public-data API (first run)"

@st.cache_data(ttl=3600, show_spinner=False)
def load_news(online: bool):
    path = DATA / "news.json"
    if online or not path.exists():
        try:
            return news_feed(cfg["news_query"], int(cfg.get("max_news_items", 30))), "Live RSS feed"
        except Exception:
            if not path.exists():
                return [], "News feed currently unavailable"
    return json.loads(path.read_text(encoding="utf-8")), "Scheduled GitHub snapshot"

status_path = DATA / "status.json"
status = json.loads(status_path.read_text()) if status_path.exists() else {}

with st.sidebar:
    st.header("Settings")
    online = st.toggle("Try live API first", value=False, help="When off, prefer GitHub Action snapshots. First launch still fetches live data.")
    if st.button("Refresh dashboard"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.markdown("**Scheduled refresh**")
    st.write(status.get("checked_at_utc", "Not yet run — launch the GitHub workflow"))
    if status.get("errors"):
        with st.expander("Latest fetch warnings"):
            st.json(status["errors"])
    st.caption("Scheduled data is stored in GitHub. Streamlit's local filesystem is not durable storage.")

price_tab, rent_tab, news_tab, listings_tab, about_tab = st.tabs([
    "📈 House prices", "🏘️ Registered rents", "📰 Housing news", "🔎 Listing searches", "ℹ️ Sources & help"
])

def chart_dataset(label: str, container):
    url = cfg["datasets"][label]
    with container:
        try:
            raw, provenance = load_public_data(label, url, online)
        except Exception as exc:
            st.error(f"Could not load {label}: {exc}")
            st.markdown(f"[View source dataset]({url})")
            return
        df = raw.copy()
        value_col = next((x for x in df.columns if x.upper() == "VALUE"), None)
        if not value_col:
            st.error("The source dataset format has changed (missing VALUE column).")
            return
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        time_col = next((x for x in df.columns if x.casefold() in ("month", "quarter", "year")), None)
        if not time_col:
            st.error("Cannot identify a month, quarter or year column in the source.")
            st.dataframe(df.head(10), use_container_width=True)
            return
        st.caption(f"{provenance} · {len(df):,} published observations · [Original source]({url})")
        ignore = {value_col, time_col, "STATISTIC", "UNIT", "TLIST(M1)", "TLIST(Q1)", "TLIST(A1)"}
        # Exclude code columns and high-cardinality dimensions from default controls.
        dimensions = [c for c in df.columns if c.upper() not in ignore and not c.lower().endswith(" code")
                      and 1 < df[c].nunique(dropna=True) <= 250]
        filtered = df
        with st.expander("Select series and filters", expanded=True):
            cols = st.columns(min(3, max(1, len(dimensions))))
            for idx, dimension in enumerate(dimensions):
                values = sorted(str(x) for x in filtered[dimension].dropna().unique())
                if not values:
                    continue
                # One value per dimension prevents mixing incomparable metrics.
                default_index = 0
                prefer = ("all", "national", "state", "ireland", "total", "index")
                for i, item in enumerate(values):
                    if any(word in item.lower() for word in prefer):
                        default_index = i
                        break
                with cols[idx % len(cols)]:
                    selected = st.selectbox(dimension, values, index=default_index, key=f"{slug(label)}:{dimension}")
                filtered = filtered[filtered[dimension].astype(str) == selected]
        filtered = filtered.dropna(subset=[value_col]).copy()
        if filtered.empty:
            st.warning("No numeric observations match these filters. Change a series selection.")
            return
        filtered["Period"] = filtered[time_col].astype(str)
        filtered = filtered.sort_values("Period").drop_duplicates("Period", keep="last")
        latest = filtered.iloc[-1]
        prev = filtered.iloc[-2] if len(filtered) >= 2 else None
        a, b, c = st.columns(3)
        a.metric("Latest published value", f"{latest[value_col]:,.1f}",
                 delta=f"{latest[value_col]-prev[value_col]:+,.1f} vs previous period" if prev is not None else None)
        b.metric("Latest period", str(latest['Period']))
        c.metric("Data points", f"{len(filtered):,}")
        unit = str(latest.get("UNIT", ""))
        st.caption(f"Unit: {unit or 'See source data'} · Change is an absolute value change, not a percentage.")
        fig = px.line(filtered, x="Period", y=value_col, markers=True, title=f"{label} — selected series")
        fig.update_layout(yaxis_title=unit or "Value", xaxis_title="Period", height=410,
                          margin=dict(l=10, r=10, t=55, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("Download filtered data (CSV)", filtered.to_csv(index=False).encode("utf-8"),
                           file_name=f"ireland_{slug(label)}_filtered.csv", mime="text/csv")
        with st.expander("Preview source records"):
            st.dataframe(filtered.tail(40), use_container_width=True)

chart_dataset("Residential property prices (CSO HPM09)", price_tab)
chart_dataset("Registered rents (RTB RIQ02)", rent_tab)

with news_tab:
    items, provenance = load_news(online)
    st.caption(f"{provenance} · Google News RSS search; publisher reporting is not independently verified")
    if not items:
        st.info("No headlines available. Try live refresh or the scheduled fetch workflow.")
    else:
        for entry in items:
            st.markdown(f"**[{entry['title']}]({entry['link']})**")
            st.caption(" · ".join(x for x in [entry.get("source"), entry.get("published")] if x))
            st.divider()

with listings_tab:
    st.info("Listing portals are linked, not scraped. This avoids fragile scraping and respects the sites' own search and access rules.")
    county = st.selectbox("County", ["All Ireland", "Dublin", "Cork", "Galway", "Limerick", "Waterford", "Kildare",
        "Meath", "Wicklow", "Wexford", "Kilkenny", "Clare", "Kerry", "Mayo", "Sligo", "Donegal", "Louth", "Offaly",
        "Westmeath", "Laois", "Tipperary", "Carlow", "Monaghan", "Cavan", "Roscommon", "Leitrim", "Longford"])
    purpose = st.radio("Looking for", ["Buy", "Rent"], horizontal=True)
    # Use stable portal homepage links; their search parameter formats can change.
    q = quote(f"{county} property for {'sale' if purpose == 'Buy' else 'rent'} Ireland")
    st.link_button("Search Daft.ie", "https://www.daft.ie/", use_container_width=True)
    st.link_button("Search MyHome.ie", "https://www.myhome.ie/", use_container_width=True)
    st.link_button("Search property on Google", f"https://www.google.com/search?q={q}", use_container_width=True)
    st.markdown("### Optional: analyze a Property Price Register CSV")
    uploaded = st.file_uploader("Upload an exported CSV to inspect sales transactions", type=["csv"])
    if uploaded:
        try:
            sales = pd.read_csv(uploaded, encoding="utf-8-sig", low_memory=False)
            st.write(f"{len(sales):,} imported records")
            st.dataframe(sales.head(100), use_container_width=True)
            st.download_button("Download imported CSV", sales.to_csv(index=False).encode(), "imported_sales.csv")
        except Exception as exc:
            st.error(f"CSV could not be parsed: {exc}")
    st.markdown("[Official Residential Property Price Register](https://propertypriceregister.ie/)")

with about_tab:
    st.markdown("""### How it works
- GitHub Actions runs `python monitor.py` daily and commits snapshots in `data/`.
- Streamlit reads the committed snapshots; you can also enable live refresh.
- Prices come from **CSO HPM09**; registered rents come from **RTB RIQ02 on CSO PxStat**.
- News uses an RSS search feed. Listing searches open the relevant property portals.
- Alert issues are **optional**, configured in `config.json`, and require GitHub Actions `issues: write` permission.

**Important:** CSO price indices are not average house sale prices. RTB registered-rent data is not necessarily current advertised asking rent. Sources publish on different schedules; new data may not appear daily. The dashboard is informational, not financial advice.
""")
    st.markdown("**Data sources**")
    st.markdown("[CSO PxStat](https://data.cso.ie/) · [RTB Rent Index](https://rtb.ie/data-insights/rtb-research-reports/rtb-esri-rent-index/) · [Property Price Register](https://propertypriceregister.ie/)")
