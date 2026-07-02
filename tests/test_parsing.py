from pipeline.parsing import (
    decode,
    extract_match_name,
    parse_physical_text,
    validate_rows,
)


# The PDF font maps U+E071..U+E07A -> '0'..'9' and U+E094 -> '.'
def enc(s: str) -> str:
    table = {str(i): chr(0xE071 + i) for i in range(10)} | {".": chr(0xE094)}
    return "".join(table.get(c, c) for c in s)


def test_decode_digits_and_dot():
    assert decode(enc("36.8")) == "36.8"


def test_extract_match_name():
    assert extract_match_name("PMSR-M03-CAN-V-BIH-V2") == "CAN V BIH"
    assert extract_match_name("PMSR-M101-NED-V-SWE") == "NED V SWE"


def test_parse_physical_text():
    text = "\n".join([
        "Physical Data Netherlands",
        f"4 Micky VAN DE VEN {enc('10.2')} {enc('1.4')} {enc('36.8')}",
        "some non-player line",
        f"11 Anthony ELANGA {enc('9.9')} {enc('1.1')} {enc('36.5')}",
    ])
    rows = parse_physical_text(text, "NED V SWE")
    assert rows == [
        {"match": "NED V SWE", "team": "Netherlands", "jersey": 4,
         "player": "Micky VAN DE VEN", "top_speed_kmh": 36.8},
        {"match": "NED V SWE", "team": "Netherlands", "jersey": 11,
         "player": "Anthony ELANGA", "top_speed_kmh": 36.5},
    ]


def test_validate_rows_drops_bad_speed_and_empty_fields():
    good = {"match": "A V B", "team": "X", "jersey": 1, "player": "P", "top_speed_kmh": 30.0}
    none_speed = good | {"top_speed_kmh": None}
    too_fast = good | {"top_speed_kmh": 55.0}
    no_player = good | {"player": ""}
    kept, dropped = validate_rows([good, none_speed, too_fast, no_player])
    assert kept == [good, none_speed]
    assert dropped == 2
