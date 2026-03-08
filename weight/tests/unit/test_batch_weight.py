import pytest
from app import parse_csv, parse_json


# --- parse_csv: valid input ---

def test_csv_kg(tmp_path):
    f = tmp_path / "test.csv"
    f.write_text('"id","kg"\nC-123,300\nC-456,250\n')
    result = parse_csv(str(f))
    assert result == [("C-123", 300), ("C-456", 250)]


def test_csv_lbs(tmp_path):
    f = tmp_path / "test.csv"
    f.write_text('"id","lbs"\nK-100,1000\n')
    result = parse_csv(str(f))
    assert result == [("K-100", 453)]


# --- parse_csv: validation errors ---

def test_csv_wrong_first_column(tmp_path):
    f = tmp_path / "test.csv"
    f.write_text('"name","kg"\nAlice,300\n')
    with pytest.raises(ValueError, match="expected 'id'"):
        parse_csv(str(f))


def test_csv_bad_unit(tmp_path):
    f = tmp_path / "test.csv"
    f.write_text('"id","tons"\nC-123,300\n')
    with pytest.raises(ValueError, match="unsupported unit"):
        parse_csv(str(f))


def test_csv_missing_column(tmp_path):
    f = tmp_path / "test.csv"
    f.write_text('"id","kg"\nC-123\n')
    with pytest.raises(ValueError, match="expected 2 columns"):
        parse_csv(str(f))


def test_csv_empty_id(tmp_path):
    f = tmp_path / "test.csv"
    f.write_text('"id","kg"\n,300\n')
    with pytest.raises(ValueError, match="missing container id"):
        parse_csv(str(f))


def test_csv_missing_weight(tmp_path):
    f = tmp_path / "test.csv"
    f.write_text('"id","kg"\nC-123,\n')
    with pytest.raises(ValueError, match="missing weight value"):
        parse_csv(str(f))


# --- parse_json: valid input ---

def test_json_kg(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('[{"id":"C-123","weight":300,"unit":"kg"}]')
    result = parse_json(str(f))
    assert result == [("C-123", 300)]


def test_json_lbs(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('[{"id":"K-100","weight":1000,"unit":"lbs"}]')
    result = parse_json(str(f))
    assert result == [("K-100", 453)]


def test_json_default_unit(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('[{"id":"C-123","weight":300}]')
    result = parse_json(str(f))
    assert result == [("C-123", 300)]


# --- parse_json: validation errors ---

def test_json_not_array(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('{"id":"C-123","weight":300}')
    with pytest.raises(ValueError, match="expected a JSON array"):
        parse_json(str(f))


def test_json_missing_id(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('[{"weight":300}]')
    with pytest.raises(ValueError, match="missing 'id' or 'weight'"):
        parse_json(str(f))


def test_json_missing_weight(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('[{"id":"C-123"}]')
    with pytest.raises(ValueError, match="missing 'id' or 'weight'"):
        parse_json(str(f))


def test_json_empty_id(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('[{"id":"","weight":300}]')
    with pytest.raises(ValueError, match="empty 'id' field"):
        parse_json(str(f))


def test_json_null_weight(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('[{"id":"C-123","weight":null}]')
    with pytest.raises(ValueError, match="missing weight value"):
        parse_json(str(f))