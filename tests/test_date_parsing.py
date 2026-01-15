from datetime import datetime
import pytest

def test_date_parsing_repro():
    date_str = '2025-12-01+01:00'
    # This matches the NEW code in src/sync.py
    try:
        parsed = datetime.fromisoformat(date_str).date()
        assert parsed.year == 2025
        assert parsed.month == 12
        assert parsed.day == 1
    except ValueError as e:
        pytest.fail(f"Parsing failed: {e}")

def test_date_parsing_simple():
    date_str = '2025-12-01'
    try:
        parsed = datetime.fromisoformat(date_str).date()
        assert parsed.year == 2025
    except ValueError as e:
        pytest.fail(f"Parsing failed: {e}")
