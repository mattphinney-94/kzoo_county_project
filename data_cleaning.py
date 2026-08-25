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

# Create a class for cleaning county parcel data
class DataCleaner:

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

        text_columns = df.select_dtypes(include="object").columns

        df[text_columns] = (
            df[text_columns]
            .fillna("")
            .astype(str)
        )

        return df

    # Clean numeric columns
    def clean_numeric_columns(self, df):

        for col in NUMERIC_COLUMNS:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        return df

    # Remove duplicate rows
    def remove_duplicates(self, df):

        return df.drop_duplicates()

    # Clean parcel numbers and convert them to strings
    def clean_parcel_numbers(self, df):

        df["parcel_number"] = (
            df["parcel_number"]
            .astype(str)
            .str.strip()
        )

        return df

    # Perform all data cleaning and standardization
    # Returns a clean, standardized copy of the dataframe
    def clean_data(self, df):

        df = df.copy()

        df = self.clean_text_columns(df)

        df = self.clean_numeric_columns(df)

        df = self.clean_parcel_numbers(df)

        df = self.clean_names(df)

        df = self.clean_addresses(df)

        df = self.remove_duplicates(df)

        return df