# Databricks notebook source
# MAGIC %md
# MAGIC # Agentic Travel Planner on Databricks (MakeMyTrip)
# MAGIC
# MAGIC **Goal:** Build an agent that finds the cheapest flights (CCU↔DEL) and hotels near Red Fort for **Sep 1–6, 2026**, generates an itinerary, and writes an output file.
# MAGIC
# MAGIC > ⚠️ Automating/scraping consumer travel websites may be restricted by their Terms. Prefer official/partner APIs, affiliate feeds, or permissioned access.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0) Parameters

# COMMAND ----------

PARAMS = {
    "origin": "Kolkata",
    "origin_iata": "CCU",
    "destination": "New Delhi",
    "destination_iata": "DEL",
    "depart_date": "2026-09-01",
    "return_date": "2026-09-06",
    "travellers": 1,
    "cabin": "Economy",
    "rooms": 1,
    "guests_per_room": 2,
    "poi": "Red Fort, New Delhi",
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1) Install libraries

# COMMAND ----------

# MAGIC %pip install -U selenium==4.15.2 beautifulsoup4 lxml pandas openpyxl

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2) Install headless Chrome + ChromeDriver (example)
# MAGIC You may prefer a cluster init script so this persists across restarts.

# COMMAND ----------

# DBTITLE 1,Cell 7
# MAGIC %pip install playwright
# MAGIC import subprocess
# MAGIC subprocess.run(["playwright", "install", "chromium"], check=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3) Tools

# COMMAND ----------

# DBTITLE 1,Cell 9
from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd

@dataclass
class ToolResult:
    ok: bool
    data: Any
    source: str
    error: str = ""


def build_driver():
    from playwright.sync_api import sync_playwright
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    return context, playwright, browser


def fetch_cheapest_flights_mmt(params: Dict[str, Any]) -> ToolResult:
    """Starter: automate MakeMyTrip flights search and parse results."""
    try:
        context, playwright, browser = build_driver()
        page = context.new_page()
        page.goto("https://www.makemytrip.com/flights/")
        # TODO: Fill From/To, set dates, click Search, parse list sorted by price.
        browser.close()
        playwright.stop()
        df = pd.DataFrame([], columns=[
            "segment","airline","depart","arrive","duration","stops","price_inr","booking_url"
        ])
        return ToolResult(True, df, source="makemytrip.com")
    except Exception as e:
        return ToolResult(False, None, source="makemytrip.com", error=str(e))


def fetch_cheapest_hotels_near_redfort_mmt(params: Dict[str, Any]) -> ToolResult:
    """Starter: automate MakeMyTrip hotel search around Red Fort and parse results."""
    try:
        context, playwright, browser = build_driver()
        page = context.new_page()
        page.goto("https://www.makemytrip.com/hotels/")
        # TODO: Search POI, set dates, sort by price low→high, parse first N.
        browser.close()
        playwright.stop()
        df = pd.DataFrame([], columns=[
            "hotel","area","distance","rating","price_inr","taxes","booking_url"
        ])
        return ToolResult(True, df, source="makemytrip.com")
    except Exception as e:
        return ToolResult(False, None, source="makemytrip.com", error=str(e))


def build_itinerary(params: Dict[str, Any]) -> pd.DataFrame:
    import datetime as dt
    start = dt.date.fromisoformat(params["depart_date"])
    end = dt.date.fromisoformat(params["return_date"])
    days = (end - start).days + 1
    rows = []
    for i in range(days):
        d = start + dt.timedelta(days=i)
        rows.append({"date": d.isoformat(), "day": d.strftime("%A"), "morning": "", "afternoon": "", "evening": ""})
    return pd.DataFrame(rows)


def write_excel_report(flights_df: pd.DataFrame, hotels_df: pd.DataFrame, itinerary_df: pd.DataFrame, out_path: str):
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        flights_df.to_excel(writer, index=False, sheet_name="Cheapest Flights")
        hotels_df.to_excel(writer, index=False, sheet_name="Cheapest Hotels")
        itinerary_df.to_excel(writer, index=False, sheet_name="Itinerary")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4) Orchestrator (agent loop)

# COMMAND ----------

# DBTITLE 1,Cell 11
import os
import shutil

flight_res = fetch_cheapest_flights_mmt(PARAMS)
hotel_res = fetch_cheapest_hotels_near_redfort_mmt(PARAMS)
it_df = build_itinerary(PARAMS)

flights_df = flight_res.data if flight_res.ok else pd.DataFrame()
hotels_df = hotel_res.data if hotel_res.ok else pd.DataFrame()

# Write to /tmp/ first to avoid Volume I/O issues
tmp_path = "/tmp/travel_report.xlsx"
write_excel_report(flights_df, hotels_df, it_df, tmp_path)

# Copy to Volume using shutil
out_path = "/Volumes/workspace/gen_ai/agentic_ai_target/travel_report.xlsx"
shutil.copy(tmp_path, out_path)
print("Wrote:", out_path)

# COMMAND ----------

# MAGIC %sql
# MAGIC create volume workspace.gen_ai.agentic_ai_target
