# 🏠 Ireland Housing Monitor

A ready-to-deploy **Python + Streamlit** housing dashboard for Ireland, connected to **CSO residential price index**, **RTB registered rents**, and housing-news RSS. **GitHub Actions** refreshes public-data snapshots daily so the Streamlit app can read stable files from GitHub.

## Features

- 📈 Monthly CSO Residential Property Price Index (HPM09); filter series and compare periods
- 🏘️ RTB average registered rent (RIQ02); filter dimensions
- 📰 Irish housing headlines from Google News RSS
- 🔎 Links to Daft.ie, MyHome.ie and the official Property Price Register
- 📥 CSV export and CSV inspection
- 🔄 Scheduled snapshot updates via GitHub Actions, daily at **07:18 UTC**
- 🔔 Optional GitHub issue alerts when newly published datapoints cross a threshold

## Deploy on GitHub + Streamlit Community Cloud

1. Create a **new GitHub repository** named `ireland-housing-monitor` (public repository is easiest for Streamlit Community Cloud).
2. Upload **all these files**, including `.github/workflows/daily-monitor.yml` and `.streamlit/config.toml`, preserving directories. Or unzip locally and use `git init`, `git add .`, `git commit`, `git remote add origin ...`, `git push -u origin main`.
3. Open the repository's **Actions** tab, enable workflows if prompted, select **Refresh Ireland housing data** and **Run workflow**. This writes CSV/JSON snapshots to `data/`. For a public repository, scheduled workflows run on the default branch, and may be disabled after inactivity.
4. Visit [share.streamlit.io](https://share.streamlit.io/), sign in with GitHub, choose **Create app**, select your repository and main branch, and enter `app.py` as the main file. Deploy.
5. Open the dashboard URL supplied by Streamlit. GitHub Actions refreshes stored files on its daily schedule; Streamlit Cloud redeploys when repo files change. The app can also fetch live data on demand via the sidebar toggle.

### Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python monitor.py          # optional: get initial snapshots
streamlit run app.py
```

### Configure

Edit `config.json`:

- `news_query`: RSS search terms
- `max_news_items`: count of recent stories
- `alert_threshold_pct`: percentage movement between **consecutive observations** for the monitored series
- `enable_github_issues`: default `false`. When set to `true`, the scheduled workflow can open GitHub Issues for new period changes above the threshold. Ensure **Settings → Actions → General → Workflow permissions** allows read/write access, and that Issues are enabled for the repository.

The issue-alert logic uses a single automatically selected dataset series for each source and is only suitable as an *illustrative* alert; it does not monitor all regions or properties. You can adapt `numeric_latest` in `monitor.py` for a precise index/rent series. There are **no automated emails, SMS alerts, or individual listing notifications** in this version.

## Data / reliability notes

- **CSO HPM09**: price **index**, not the average euro property price or all property transactions.
- **RTB RIQ02**: registered rents, not live advertised rental listings. The CSO PxStat series and formats can change; a failed refresh retains last successful snapshot and displays a warning.
- News via Google News RSS may change or throttle requests. News headlines are third-party content.
- Data sources do not update daily; a daily job only checks for new publications.
- No web scraping of Daft.ie/MyHome.ie or bypass of listing website protections.
- Streamlit Community Cloud has an ephemeral filesystem, so snapshots are **committed by GitHub Actions** instead of written by the deployed Streamlit process.
- GitHub Actions schedules may execute late or be paused; check the Actions tab to confirm last execution.

Sources: https://data.cso.ie/table/HPM09 · https://data.gov.ie/en_GB/dataset/riq02-rtb-average-monthly-rent-report · https://rtb.ie/data-insights/rtb-research-reports/rtb-esri-rent-index/ · https://propertypriceregister.ie/

## File map

```text
app.py                         Streamlit UI
monitor.py                     CSV + RSS downloader and alert logic
config.json                    Public-source URLs and parameters
requirements.txt               Python dependencies
.github/workflows/daily-monitor.yml  Daily GitHub Actions job
.streamlit/config.toml         Dashboard theme
data/                          Latest public-source snapshots (populated by job)
```
