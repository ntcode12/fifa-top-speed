from dagster import AssetKey

from pipeline.definitions import defs


def test_definitions_load():
    keys = set(defs.resolve_asset_graph().get_all_asset_keys())
    assert {AssetKey("match_report_urls"), AssetKey("raw_match_pdfs"),
            AssetKey("top_speeds")} <= keys
    assert defs.get_schedule_def("daily_refresh") is not None
