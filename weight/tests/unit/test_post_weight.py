from app import lbs_to_kg, parse_containers, parse_force


# --- lbs_to_kg ---

def test_lbs_to_kg_basic():
    assert lbs_to_kg(1000) == 453

def test_lbs_to_kg_zero():
    assert lbs_to_kg(0) == 0

def test_lbs_to_kg_large():
    assert lbs_to_kg(33000) == int(33000 * 0.453592)


# --- parse_containers ---

def test_parse_containers_multiple():
    assert parse_containers("C-1,C-2,C-3") == ["C-1", "C-2", "C-3"]

def test_parse_containers_single():
    assert parse_containers("C-1") == ["C-1"]

def test_parse_containers_empty():
    assert parse_containers("") == []

def test_parse_containers_None():
    assert parse_containers(None) == []


# --- parse_force ---

def test_parse_force_string_true():
    assert parse_force("true") == True

def test_parse_force_string_True():
    assert parse_force("True") == True

def test_parse_force_boolean_true():
    assert parse_force(True) == True

def test_parse_force_string_false():
    assert parse_force("false") == False

def test_parse_force_boolean_false():
    assert parse_force(False) == False

def test_parse_force_garbage():
    assert parse_force("banana") == False