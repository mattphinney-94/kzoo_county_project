import pandas as pd
import pytest

from data_cleaning import DataCleaner


def _valid_input_dataframe():
    """
    Return one valid source row containing every column
    required by DataCleaner.
    """

    return pd.DataFrame(
        {
            "parcel_number": [
                " 09-14-410-056 "
            ],
            "property_address": [
                "123 North Main Street"
            ],
            "owner_name": [
                "smith, john"
            ],
            "owner_name_2": [
                ""
            ],
            "owner_care_of": [
                ""
            ],
            "owner_address": [
                "456 West Elm Road"
            ],
            "taxpayer_name": [
                "smith, john"
            ],
            "taxpayer_care_of": [
                ""
            ],
            "taxpayer_address": [
                "456 West Elm Road"
            ],
            "tax_send_to_name": [
                ""
            ],
            "principal_residence_exemption_percentage": [
                100
            ],
            "property_class": [
                "401"
            ],
            "tax_value": [
                1000
            ],
            "assessed_value": [
                50000
            ],
            "state_equalized_value": [
                50000
            ]
        }
    )


def test_valid_input_is_cleaned():
    cleaner = DataCleaner()

    result = cleaner.clean_data(
        _valid_input_dataframe()
    )

    assert len(result) == 1

    assert (
        result.iloc[0]["parcel_number"]
        ==
        "09-14-410-056"
    )

    assert (
        result.iloc[0]["owner_name"]
        ==
        "SMITH, JOHN"
    )

    assert (
        result.iloc[0]["property_address"]
        ==
        "123 N MAIN ST"
    )

    assert (
        result.iloc[0]["owner_address"]
        ==
        "456 W ELM RD"
    )


def test_empty_input_is_rejected():
    cleaner = DataCleaner()

    df = _valid_input_dataframe().iloc[0:0]

    with pytest.raises(
        ValueError,
        match="Input parcel DataFrame is empty"
    ):
        cleaner.clean_data(df)


def test_missing_required_column_is_rejected():
    cleaner = DataCleaner()

    df = (
        _valid_input_dataframe()
        .drop(
            columns=[
                "owner_name"
            ]
        )
    )

    with pytest.raises(
        ValueError,
        match="missing required columns"
    ):
        cleaner.clean_data(df)


def test_duplicate_column_names_are_rejected():
    cleaner = DataCleaner()

    df = _valid_input_dataframe()

    df["duplicate_owner_name"] = (
        df["owner_name"]
    )

    df = df.rename(
        columns={
            "duplicate_owner_name":
                "owner_name"
        }
    )

    with pytest.raises(
        ValueError,
        match="duplicate column names"
    ):
        cleaner.clean_data(df)


def test_missing_parcel_number_is_rejected():
    cleaner = DataCleaner()

    df = _valid_input_dataframe()

    df.loc[
        0,
        "parcel_number"
    ] = None

    with pytest.raises(
        ValueError,
        match="Missing parcel numbers"
    ):
        cleaner.clean_data(df)


@pytest.mark.parametrize(
    (
        "column",
        "bad_value",
        "message"
    ),
    [
        (
            "tax_value",
            "NOT A NUMBER",
            "contains non-numeric values"
        ),
        (
            "assessed_value",
            100.5,
            "contains non-integer values"
        ),
        (
            "principal_residence_exemption_percentage",
            101,
            "must be between 0 and 100"
        ),
        (
            "state_equalized_value",
            -1,
            "cannot contain negative values"
        )
    ]
)
def test_invalid_numeric_values_are_rejected(
        column,
        bad_value,
        message
):
    cleaner = DataCleaner()

    df = _valid_input_dataframe()

    # Allow the test to inject deliberately malformed
    # source values into an otherwise numeric column.
    df[column] = df[column].astype(object)

    df.loc[
        0,
        column
    ] = bad_value

    with pytest.raises(
        ValueError,
        match=message
    ):
        cleaner.clean_data(df)