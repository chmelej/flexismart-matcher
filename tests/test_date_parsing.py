from datetime import datetime
import pytest
from src.sync import parse_date

def test_date_parsing_repro():
    date_str = '2025-12-01+01:00'
    # This matches the NEW code in src/sync.py (using parse_date helper)
    parsed = parse_date(date_str)
    assert parsed.year == 2025
    assert parsed.month == 12
    assert parsed.day == 1

def test_date_parsing_simple():
    date_str = '2025-12-01'
    parsed = parse_date(date_str)
    assert parsed.year == 2025
    assert parsed.month == 12
    assert parsed.day == 1

def test_date_parsing_none():
    assert parse_date(None) is None
    assert parse_date("") is None

def test_date_parsing_invalid():
    assert parse_date("invalid-date") is None
