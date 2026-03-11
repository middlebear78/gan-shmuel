from app import parse_datetime_param
from datetime import datetime


# --- parse_datetime_param ---

def test_parse_valid_datetime():
    result = parse_datetime_param("20260301130000")
    assert result == datetime(2026, 3, 1, 13, 0, 0)

def test_parse_midnight():
    result = parse_datetime_param("20260301000000")
    assert result == datetime(2026, 3, 1, 0, 0, 0)

def test_parse_invalid_format():
    assert parse_datetime_param("2026-03-01") is None

def test_parse_too_short():
    assert parse_datetime_param("2026030113") is None

def test_parse_too_long():
    assert parse_datetime_param("202603011300001") is None

def test_parse_letters():
    assert parse_datetime_param("abcdefghijklmn") is None

def test_parse_none():
    assert parse_datetime_param(None) is None