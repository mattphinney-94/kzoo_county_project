import pandas as pd
import re

# Define global variables.
ADDRESS_REPLACEMENTS = {
    "AVENUE": "AVE",
    "BOULEVARD": "BLVD",
    "CIRCLE": "CIR",
    "COURT": "CT",
    "DRIVE": "DR",
    "HIGHWAY": "HWY",
    "LANE": "LN",
    "PARKWAY": "PKWY",
    "PLACE": "PL",
    "ROAD": "RD",
    "STREET": "ST",
    "TERRACE": "TER",
    "TRAIL": "TRL",
    "APARTMENT": "APT",
    "SUITE": "STE",
    "BUILDING": "BLDG",
    "FLOOR": "FL",
    "ROOM": "RM",
    "NORTH": "N",
    "SOUTH": "S",
    "EAST": "E",
    "WEST": "W",
    "NORTHEAST": "NE",
    "NORTHWEST": "NW",
    "SOUTHEAST": "SE",
    "SOUTHWEST": "SW",
}

ADDRESS_COLUMNS = [
    "property_address",
    "owner_address",
    "taxpayer_address"
]

NUMERIC_COLUMNS = [
    "principal_residence_exemption_percentage",
    "tax_value",
    "assessed_value",
    "state_equalized_value"
]

ENTITY_COLUMNS = [
    "owner_name",
    "owner_name_2",
    "owner_care_of",
    "taxpayer_name",
    "taxpayer_care_of",
    "tax_send_to_name"
]

REQUIRED_COLUMNS = set(
    ADDRESS_COLUMNS
    + NUMERIC_COLUMNS
    + ENTITY_COLUMNS
    + [
        "parcel_number",
        "property_class"
    ]
)

# Create a class for cleaning county parcel data
class DataCleaner:

    def validate_input(self, df):
        """
        Validate the structure of an incoming parcel DataFrame
        before cleaning begins.
        """

        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                "DataCleaner.clean_data expects "
                "a pandas DataFrame."
            )

        if df.empty:
            raise ValueError(
                "Input parcel DataFrame is empty."
            )

        duplicate_columns = (
            df.columns[
                df.columns.duplicated()
            ]
            .tolist()
        )

        if duplicate_columns:
            raise ValueError(
                "Input DataFrame contains duplicate "
                "column names: "
                f"{duplicate_columns}"
            )

        missing_columns = (
            REQUIRED_COLUMNS
            -
            set(df.columns)
        )

        if missing_columns:
            raise ValueError(
                "Input DataFrame is missing required "
                "columns: "
                f"{sorted(missing_columns)}"
            )

    # Standardise address strings
    def normalize_address(self, address):

        if pd.isna(address):
            return ""

        address = str(address).upper().strip()

        # Remove periods
        address = address.replace(".", "")

        # Collapse multiple spaces
        address = re.sub(r"\s+", " ", address)

        # Standardize PO Box formatting
        address = re.sub(
            r"\bP\s*O\s*BOX\b",
            "PO BOX",
            address
        )

        address = re.sub(
            r"\bPOST OFFICE BOX\b",
            "PO BOX",
            address
        )

        # Remove spaces around hyphens
        address = re.sub(r"\s*-\s*", "-", address)

        for old, new in ADDRESS_REPLACEMENTS.items():
            address = re.sub(rf"\b{old}\b", new, address)

        # Remove repeated commas
        address = re.sub(r",+", ",", address)

        # Remove spaces around commas
        address = re.sub(r"\s*,\s*", ", ", address)

        # Remove leading/trailing commas
        address = address.strip(", ")

        return address

    # Standardize person/organization names.
    def normalize_name(self, name):

        if pd.isna(name):
            return ""

        name = str(name).upper().strip()

        # Collapse repeated whitespace
        name = re.sub(r"\s+", " ", name)

        # Standardize spacing around hyphens
        name = re.sub(r"\s*-\s*", "-", name)

        # Standardize spacing around commas
        name = re.sub(r"\s*,\s*", ", ", name)

        return name

    # Clean name columns
    def clean_names(self, df):

        for col in ENTITY_COLUMNS:
            df[col] = df[col].apply(self.normalize_name)

        return df

    # Clean address columns
    def clean_addresses(self, df):

        for col in ADDRESS_COLUMNS:
            df[col] = df[col].apply(self.normalize_address)

        return df

    # Clean text columns
    def clean_text_columns(self, df):

        text_columns = df.select_dtypes(
            include=[
                "object",
                "string"
            ]
        ).columns

        df[text_columns] = (
            df[text_columns]
            .fillna("")
            .astype(str)
        )

        return df

    # Clean numeric columns
    def clean_numeric_columns(self, df):
        """
        Convert expected numeric columns while rejecting
        unexpected non-numeric source values.
        """

        for col in NUMERIC_COLUMNS:

            original = df[col].copy()

            cleaned = pd.to_numeric(
                original,
                errors="coerce"
            )

            invalid_mask = (
                original.notna()
                & original.astype(str).str.strip().ne("")
                & cleaned.isna()
            )

            if invalid_mask.any():
                bad_values = (
                    original.loc[
                        invalid_mask
                    ]
                    .astype(str)
                    .unique()[:10]
                    .tolist()
                )

                raise ValueError(
                    f"{col} contains non-numeric "
                    f"values: {bad_values}"
                )

            non_null = cleaned.dropna()

            if (
                (
                    non_null % 1
                )
                != 0
            ).any():
                raise ValueError(
                    f"{col} contains non-integer values."
                )

            df[col] = cleaned

        pre_values = (
            df[
                "principal_residence_exemption_percentage"
            ]
            .dropna()
        )

        if (
            (pre_values < 0)
            | (pre_values > 100)
        ).any():
            raise ValueError(
                "principal_residence_exemption_percentage "
                "must be between 0 and 100."
            )

        for col in [
            "tax_value",
            "assessed_value",
            "state_equalized_value"
        ]:
            if (
                df[col]
                .dropna()
                .lt(0)
                .any()
            ):
                raise ValueError(
                    f"{col} cannot contain "
                    "negative values."
                )

        return df

    # Remove duplicate rows
    def remove_duplicates(self, df):

        return df.drop_duplicates()

    # Clean parcel numbers and convert them to strings
    def clean_parcel_numbers(self, df):
        """
        Normalize parcel numbers without converting
        missing values into literal strings.
        """

        df["parcel_number"] = (
            df["parcel_number"]
            .astype("string")
            .str.strip()
        )

        df["parcel_number"] = (
            df["parcel_number"]
            .replace(
                "",
                pd.NA
            )
        )

        if df[
            "parcel_number"
        ].isna().any():

            missing_rows = (
                df.index[
                    df[
                        "parcel_number"
                    ].isna()
                ]
                .tolist()[:10]
            )

            raise ValueError(
                "Missing parcel numbers found "
                "at DataFrame rows: "
                f"{missing_rows}"
            )

        return df

    # Perform all data cleaning and standardization
    # Returns a clean, standardized copy of the dataframe
    def clean_data(self, df):

        self.validate_input(df)

        df = df.copy()

        df = self.clean_text_columns(df)

        df = self.clean_numeric_columns(df)

        df = self.clean_parcel_numbers(df)

        df = self.clean_names(df)

        df = self.clean_addresses(df)

        df = self.remove_duplicates(df)

        return df