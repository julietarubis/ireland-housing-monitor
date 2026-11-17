"""Fetch and snapshot public Irish housing datasets; suitable for GitHub Actions."""
from __future__ import annotations

import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import feedparser
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CONFIG = ROOT / "config.json"
TIMEOUT = 35


def config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def fetch_csv(url: str) -> pd.DataFrame:
    resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "IrelandHousingMonitor/1.0 (public-data dashboard)"})
    resp.raise_for_status()
    df = pd.read_csv(io.BytesIO(resp.content), low_memory=False, encoding="utf-8-sig")
    if df.empty or "VALUE" not in [c.upper() for c in df.columns]:
        raise ValueError("Unexpected CSV response: missing VALUE column or no rows")
    return df


def news_feed(query: str, max_items: int = 30) -> list[dict]:
    url = "https://news.google.com/rss/search?q=" + quote(query) + "&hl=en-IE&gl=IE&ceid=IE:en"
    resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0 IrelandHousingMonitor/1.0"})
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    return [{"title": str(x.get("title", "")), "link": str(x.get("link", "")),
             "published": str(x.get("published", "")),
             "source": str(x.get("source", {}).get("title", ""))}
            for x in feed.entries[:max_items] if x.get("title") and x.get("link")]


def slug(label: str) -> str:
    if "HPM09" in label:
        return "prices"
    if "RIQ02" in label:
        return "rents"
    return hashlib.sha1(label.encode()).hexdigest()[:10]


def numeric_latest(df: pd.DataFrame) -> dict | None:
    """Find most recent time period, and first series for change detection only.

    Display filters in the app, not this function, control what users chart.
    """
    time_cols = [c for c in df.columns if c.casefold() in ("month", "quarter", "year")]
    if not time_cols:
        return None
    time_col = time_cols[0]
    vcol = next(c for c in df.columns if c.upper() == "VALUE")
    table = df.copy()
    table[vcol] = pd.to_numeric(table[vcol], errors="coerce")
    table = table.dropna(subset=[vcol])
    # Values may include multiple statistics, regions, property types. Compare one
    # *identical series* at consecutive periods; never compare mixed series.
    other = [c for c in table.columns if c != time_col and c != vcol and not c.endswith(" Code") and c.casefold() not in ("tlists(m1)", "tlists(q1)")]
    if table.empty:
        return None
    table["_period"] = table[time_col].astype(str)
    for _, group in table.groupby(other, dropna=False, sort=False) if other else [(None, table)]:
        group = group.sort_values("_period").drop_duplicates("_period")
        if len(group) >= 2:
            a, b = group.iloc[-2], group.iloc[-1]
            if float(a[vcol]) == 0:
                continue
            return {"series": " | ".join(str(b[c]) for c in other), "previous_period": str(a[time_col]),
                    "latest_period": str(b[time_col]), "previous_value": float(a[vcol]),
                    "latest_value": float(b[vcol]),
                    "change_pct": round((float(b[vcol]) / float(a[vcol]) - 1) * 100, 3)}
    return None


def create_issue(title: str, body: str, token: str, repository: str) -> bool:
    r = requests.post(f"https://api.github.com/repos/{repository}/issues",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"title": title, "body": body, "labels": []}, timeout=TIMEOUT)
    r.raise_for_status()
    return True


def run():
    DATA.mkdir(parents=True, exist_ok=True)
    cfg = config()
    previous = json.loads((DATA / "status.json").read_text()) if (DATA / "status.json").exists() else {}
    status = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "datasets": {}, "errors": {}}
    for name, url in cfg["datasets"].items():
        key = slug(name)
        try:
            df = fetch_csv(url)
            # Preserve last valid snapshot if this run fails.
            df.to_csv(DATA / f"{key}.csv", index=False)
            latest = numeric_latest(df)
            status["datasets"][key] = {"label": name, "source_url": url,
                "rows": len(df), "latest": latest, "refreshed_at_utc": status["checked_at_utc"]}
        except Exception as exc:
            status["errors"][key] = f"{type(exc).__name__}: {exc}"
            if key in previous.get("datasets", {}):
                status["datasets"][key] = previous["datasets"][key]

    try:
        news = news_feed(cfg["news_query"], int(cfg.get("max_news_items", 30)))
        (DATA / "news.json").write_text(json.dumps(news, indent=2, ensure_ascii=False), encoding="utf-8")
        status["news_items"] = len(news)
    except Exception as exc:
        status["errors"]["news"] = f"{type(exc).__name__}: {exc}"
        status["news_items"] = previous.get("news_items", 0)

    # Optional alert: changes from the last successful fetch, not arbitrary series.
    # Avoid creating an issue for every scheduled run by storing the alert fingerprint.
    alerts_file = DATA / "alerts.json"
    alerts_state = json.loads(alerts_file.read_text()) if alerts_file.exists() else {}
    for key, current in status["datasets"].items():
        old = previous.get("datasets", {}).get(key, {}).get("latest")
        new = current.get("latest")
        if not old or not new or old.get("latest_period") == new.get("latest_period"):
            continue
        if old.get("series") != new.get("series") or not new.get("change_pct"):
            continue
        if abs(new["change_pct"]) < float(cfg.get("alert_threshold_pct", 5)):
            continue
        finger = f"{key}:{new['series']}:{new['latest_period']}"
        if alerts_state.get(key) == finger:
            continue
        if cfg.get("enable_github_issues") and os.getenv("GITHUB_TOKEN") and os.getenv("GITHUB_REPOSITORY"):
            try:
                create_issue(f"Housing monitor: {key} moved {new['change_pct']:+.1f}%",
                  f"Series: {new['series']}\n\nPeriod: {new['latest_period']}\nChange: {new['change_pct']:+.2f}%\n\nSource: {current['source_url']}",
                  os.environ["GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"])
                alerts_state[key] = finger
            except Exception as exc:
                status["errors"]["alert"] = str(exc)
    alerts_file.write_text(json.dumps(alerts_state, indent=2), encoding="utf-8")
    (DATA / "status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(status, indent=2))
    return status


if __name__ == "__main__":
    run()
