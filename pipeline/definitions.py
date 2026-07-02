import dagster as dg

from pipeline.assets import match_report_urls, raw_match_pdfs, top_speeds

refresh_all = dg.define_asset_job("refresh_all", selection="*")

daily_refresh = dg.ScheduleDefinition(
    name="daily_refresh",
    job=refresh_all,
    cron_schedule="0 6 * * *",  # 06:00 daily
)

defs = dg.Definitions(
    assets=[match_report_urls, raw_match_pdfs, top_speeds],
    jobs=[refresh_all],
    schedules=[daily_refresh],
)
