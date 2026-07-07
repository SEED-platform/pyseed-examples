from examples.lib.helpers import chunks, clean_up_name, map_months_to_date


def test_clean_up_name_normalizes_spaces_slashes_and_case():
    assert clean_up_name("My / Example Name") == "my___example_name"


def test_chunks_splits_dictionary_into_fixed_sizes():
    data = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}

    result = list(chunks(data, 2))

    assert result == [
        {"a": 1, "b": 2},
        {"c": 3, "d": 4},
        {"e": 5},
    ]


def test_chunks_returns_empty_for_empty_input():
    assert list(chunks({}, 3)) == []


def test_map_months_to_date_returns_all_months_without_values():
    result = map_months_to_date(2023)

    assert len(result) == 12
    assert result[0] == {"start_time": "2023-01-01", "end_time": "2023-01-31"}
    assert result[-1] == {"start_time": "2023-12-01", "end_time": "2023-12-31"}


def test_map_months_to_date_adds_readings_when_values_exist():
    result = map_months_to_date(
        2023,
        {
            "ELECTRICITYUSE_KBTU_JANUARY": 10.5,
            "ELECTRICITYUSE_KBTU_MARCH": 2,
        },
    )

    assert len(result) == 2
    assert result[0] == {
        "start_time": "2023-01-01",
        "end_time": "2023-01-31",
        "reading": 10.5,
        "source_unit": "kBtu (Thousand BTU)",
        "conversion_factor": 1,
    }
    assert result[1] == {
        "start_time": "2023-03-01",
        "end_time": "2023-03-31",
        "reading": 2,
        "source_unit": "kBtu (Thousand BTU)",
        "conversion_factor": 1,
    }


def test_map_months_to_date_returns_empty_when_all_values_are_zero():
    result = map_months_to_date(
        2023,
        {
            "ELECTRICITYUSE_KBTU_JANUARY": 0,
            "ELECTRICITYUSE_KBTU_FEBRUARY": 0,
        },
    )

    assert result == []


def test_map_months_to_date_uses_leap_year_end_date_for_february():
    result = map_months_to_date(2024)

    february = result[1]
    assert february == {"start_time": "2024-02-01", "end_time": "2024-02-29"}


def test_map_months_to_date_handles_non_leap_century_year():
    result = map_months_to_date(2100)

    february = result[1]
    assert february == {"start_time": "2100-02-01", "end_time": "2100-02-28"}
