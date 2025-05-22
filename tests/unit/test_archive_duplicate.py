from scripts.archive_duplicated_data import extract_hour_key


def test_extract_hour_key_formats():
    assert extract_hour_key("2025-05-22_pool.jsonl") == "2025-05-22T000000"
    assert extract_hour_key("20250522T090000_pool.jsonl") == "20250522T090000"
    assert extract_hour_key("2025-05-22_pool.jsonl") == "2025-05-22T000000"
    assert extract_hour_key("20250522T090000_pool.jsonl") == "20250522T090000"
