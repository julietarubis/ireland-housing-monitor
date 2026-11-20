# 🏠 Ireland Housing Monitor

**An automated, open-source dashboard for exploring Ireland's residential property market.**

Built with **Python**, **Streamlit**, and **GitHub Actions**, Ireland Housing Monitor brings together official housing statistics and relevant news in one interactive dashboard. A scheduled GitHub workflow checks public datasets each day, stores snapshots in the repository, and makes them available to the deployed Streamlit app.

> **Project status:** The application has been deployed to Streamlit Community Cloud. GitHub Actions workflow run #2 completed successfully, committed snapshot files, and the Streamlit dashboard displayed the scheduled GitHub snapshot. This documents a verified run, not a guarantee that every future update or source will succeed.

## Features

- **House prices:** Explore the CSO Residential Property Price Index (HPM09), select statistical series, filter property categories, and review trends over time.
- **Registered rents:** Explore RTB registered-rent statistics (RIQ02), with interactive filtering and charts.
- **Housing news:** View recent Irish housing-related headlines retrieved from a Google News RSS search.
- **Property research:** Quick links to Daft.ie, MyHome.ie, and Ireland's Property Price Register for manual searches.
- **Data exports:** Inspect the retrieved datasets and download CSV data from the dashboard.
- **Automated refresh:** GitHub Actions checks data sources daily at **07:18 UTC** and commits updated snapshot files.
- **Optional issue alerts:** A configurable threshold can trigger a GitHub Issue for selected published-series changes; disabled by default.

## How it works

```text
CSO PxStat API (HPM09 + RIQ02)      Google News RSS
                 \                     /
                  \                   /
                   Python monitor.py
                          |
                 GitHub Actions schedule
                          |
               data/ CSV and JSON snapshots
                          |
                  GitHub repository
                          |
                 Streamlit dashboard
```

The automation checks for updates daily, **but the underlying government datasets are published on their own schedules**. Running the workflow does not mean a new monthly statistic has been released.

## Tech stack

| Component | Technology | Purpose |
| --- | --- | --- |
| Application | Python, Streamlit | Interactive dashboard |
| Data processing | Python, pandas | Fetch and organise statistics |
| Data sources | CSO PxStat, RTB series, RSS | Public information |
| Automation | GitHub Actions | Scheduled data refresh |
| Data storage | Versioned CSV and JSON files | Persistent snapshots in GitHub |
| Hosting | Streamlit Community Cloud | Publicly accessible app |

## Repository structure

```text
ireland-housing-monitor/
├── .github/
│   └── workflows/
│       └── daily-monitor.yml   # Scheduled monitoring workflow
├── .streamlit/
│   └── config.toml            # Streamlit configuration
├── data/
│   ├── prices.csv             # CSO house-price index snapshot
│   ├── rents.csv              # RTB rent snapshot, if fetch succeeds
│   ├── news.json              # Retrieved housing headlines
│   ├── alerts.json            # Alert deduplication state
│   └── status.json            # Fetch timestamp and source warnings
├── app.py                     # Streamlit dashboard
├── monitor.py                 # Data fetch and alert logic
├── config.json                # Sources and monitoring settings
├── requirements.txt           # Dependencies
└── README.md
```

Some data files are generated only after their respective sources have been successfully fetched. If a source fails, check `data/status.json` and the dashboard's **Latest fetch warnings** section. The dashboard may continue showing an older successful snapshot.

## Run locally

You will need **Python 3.11** and Git.

```bash
git clone https://github.com/julietarubis/ireland-housing-monitor.git
cd ireland-housing-monitor
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Install dependencies, optionally fetch the initial snapshots, and start Streamlit:

```bash
pip install -r requirements.txt
python monitor.py
streamlit run app.py
```

The app opens in your browser, typically at `http://localhost:8501`.

## Deploy to Streamlit Community Cloud

1. Push the repository to GitHub, including the hidden `.github/` and `.streamlit/` folders.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
3. Create an app from repository `julietarubis/ireland-housing-monitor`.
4. Select branch **`main`** and main application file **`app.py`**.
5. Deploy and open the URL provided by Streamlit.
6. In the sidebar, use **Refresh dashboard** to reload the dashboard display. The **Try live API first** switch can be used when an on-demand API fetch is preferred.

The deployed Streamlit app does not serve as the durable storage layer. GitHub stores the snapshots that the scheduled job commits.

## Configure automated monitoring

The workflow lives at `.github/workflows/daily-monitor.yml` and supports:

- **Manual execution** from **Actions → Refresh Ireland housing data → Run workflow**.
- **Scheduled execution** each day at **07:18 UTC**, subject to GitHub scheduling delays or pauses.

The workflow installs Python 3.11 dependencies, executes `python monitor.py`, and commits changed files in `data/` back to the repository using `github-actions[bot]`.

To inspect an execution, open [GitHub Actions](https://github.com/julietarubis/ireland-housing-monitor/actions), select the workflow run, and review the `refresh` job. A **green checkmark** indicates that the job finished, but you should also inspect `data/status.json` for individual fetch failures.

If snapshot commits fail with a permission error, review **Settings → Actions → General → Workflow permissions** and confirm the workflow can write repository contents. Repository and organisation policies may override workflow permissions.

### Customise the monitoring settings

Edit `config.json`:

| Setting | Purpose | Default |
| --- | --- | --- |
| `datasets` | CSO / RTB API endpoints | HPM09 and RIQ02 |
| `news_query` | Keywords used for housing news | Irish housing / rents / market / supply |
| `max_news_items` | Maximum number of news items | `30` |
| `alert_threshold_pct` | Threshold for the monitored series change | `5.0` |
| `enable_github_issues` | Allow GitHub issue alerts | `false` |

To activate issue alerts, set `enable_github_issues` to `true`, ensure GitHub Issues is enabled, and allow the workflow `issues: write` permission. The workflow receives the repository's `GITHUB_TOKEN` automatically. **Do not commit personal access tokens or other credentials to GitHub.**

The built-in alert logic monitors an automatically selected series, not every county, listing, or property. Review the series-selection logic in `monitor.py` before relying on the threshold for decisions.

## Confirm the dashboard is up to date

Use this checklist after a scheduled or manual run:

1. In GitHub **Actions**, verify that the latest monitoring workflow completed successfully.
2. In the repository's `data/` folder, check that the snapshot commit is recent.
3. Open `data/status.json` and inspect `checked_at_utc`, `datasets`, and `errors`.
4. In Streamlit, confirm the sidebar shows **Scheduled refresh** and the main panel says **Scheduled GitHub snapshot**.
5. Expand **Latest fetch warnings** to check whether any feed failed.

During the initial verified run on **17 November 2026**, the repository contained `prices.csv`, `news.json`, `alerts.json`, and `status.json`. The dashboard displayed **20,800 published observations** for the loaded house-price dataset. These are historical observations from that screenshot, **not live figures**.

## Data sources and interpretation

| Source | What it represents | Link |
| --- | --- | --- |
| CSO HPM09 | Residential Property Price **Index** and related measures | [CSO HPM09](https://data.cso.ie/table/HPM09) |
| RTB RIQ02 | Registered-rent statistics | [RTB rent dataset](https://data.gov.ie/en_GB/dataset/riq02-rtb-average-monthly-rent-report) |
| RTB–ESRI Rent Index | Additional context on rental-market trends | [RTB reports](https://rtb.ie/data-insights/rtb-research-reports/rtb-esri-rent-index/) |
| Google News RSS | Housing-related news headlines | [Google News](https://news.google.com/) |
| Property Price Register | Published residential sale transactions; linked for research | [Property Price Register](https://propertypriceregister.ie/) |

**Important limitations:**

- The CSO price index is **not** the average sale price of an Irish home.
- Registered rents are **not** the same as live asking rents on property portals.
- Listing-search links are **not** automated Daft.ie/MyHome.ie scraping or listing alerts.
- News RSS feeds and public APIs can change, fail, or become temporarily unavailable.
- A successful scheduled job does not guarantee every feed refreshed; check warnings and publication periods.
- Dashboard figures are provided for research and should not be treated as financial or property-purchase advice.

## Possible future improvements

County-level comparisons, rental affordability metrics, long-term trend summaries, more precise user-selected alert series, and opt-in email notifications could be added in later versions. These are **not features of the current release**.

## Project purpose

This project makes public Irish housing information easier to find, review, and revisit. It combines a straightforward dashboard with repeatable scheduled data collection, providing an accessible starting point for housing-market research and future analysis.

---

**Built with Python · Streamlit · GitHub Actions**  
**Repository:** [julietarubis/ireland-housing-monitor](https://github.com/julietarubis/ireland-housing-monitor)
