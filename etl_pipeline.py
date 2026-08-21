# Import Packages
import pandas as pd
import re

# Set pandas display width to match monitor and prevent line wraps
pd.set_option('display.width', 1000)

# Tell pandas to print all dataframe columns
pd.set_option('display.max_columns', None)


# Import from local files
from data_cleaning import DataCleaner
from extraction import extract_data

### EXTRACT ###
extracted_df = extract_data('2025 Roll - Parcels Export.xlsx', 'Only Delinquent Parcels')

### CLEAN ###
cleaner = DataCleaner()
clean_df = cleaner.clean_data(extracted_df)

# print(clean_df.info())

### ENTITY RESOLUTION ###
# Define the columns where an entity can be found
entity_columns = [
    "owner_name",
    "owner_name_2",
    "owner_care_of",
    "taxpayer_name",
    "taxpayer_care_of",
    "tax_send_to_name"
]

# Create a dictionary associating entity columns with their role and the address associated with them.
role_mapping = {
    "owner_name": {
        "role": "Owner",
        "address_column": "owner_address"
    },
    "owner_name_2": {
        "role": "Owner",
        "address_column": "owner_address"
    },
    "owner_care_of": {
        "role": "Owner Care Of",
        "address_column": "owner_address"
    },
    "taxpayer_name": {
        "role": "Taxpayer",
        "address_column": "taxpayer_address"
    },
    "taxpayer_care_of": {
        "role": "Taxpayer Care Of",
        "address_column": "taxpayer_address"
    },
    "tax_send_to_name": {
        "role": "Tax Send To",
        "address_column": "taxpayer_address"
    }
}

# Build the occurrence table
entity_occurrences = []

for column, info in role_mapping.items():

    temp = (
        clean_df[
            [
                "parcel_number",
                column,
                info["address_column"]
            ]
        ]
        .copy()
    )

    temp.columns = [
        "parcel_number",
        "entity_name",
        "associated_address"
    ]

    temp["role"] = info["role"]

    entity_occurrences.append(temp)

entity_occurrences = (
    pd.concat(entity_occurrences, ignore_index=True)
)

# Remove rows with blank entities
entity_occurrences = entity_occurrences[
    entity_occurrences["entity_name"] != ""
].copy()

# The list below defines what words to search for to determine what counts as an organization
# along with a confidence level that it is an organization, based on its keyword(s).
organization_patterns = {
    r"\bLLC\b":               ("LLC", "High"),
    r"\bL\.L\.C\b":           ("LLC", "High"),

    r"\bINC\b":               ("Corporation", "High"),
    r"\bINC\.\b":             ("Corporation", "High"),
    r"\bCORP\b":              ("Corporation", "High"),
    r"\bCORPORATION\b":       ("Corporation", "High"),

    r"\bLP\b":                ("Limited Partnership", "High"),
    r"\bLTD\b":               ("Limited Company", "High"),

    r"\bBANK\b":              ("Bank", "High"),

    r"\bTRUST\b":             ("Trust", "Medium"),

    r"\bCHURCH\b":            ("Church", "High"),

    r"\bCOUNTY\b":            ("Government", "High"),
    r"\bCITY\b":              ("Government", "High"),
    r"\bTOWNSHIP\b":          ("Government", "High"),
    r"\bVILLAGE\b":           ("Government", "High"),

    r"\bUNIVERSITY\b":        ("University", "High"),

    r"\bFOUNDATION\b":        ("Foundation", "High"),

    r"\bESTATE\b":            ("Estate", "Medium"),
    r"\bESTATES\b":           ("Estate", "Medium"),

    r"\bHOLDINGS\b":          ("Holding Company", "Medium"),

    r"\bCOMPANY\b":           ("Other Organization", "Medium"),
    r"\bCO\b":                ("Other Organization", "Low"),
}

# Default every entity to Person
entity_occurrences["entity_type"] = "Person"

# If an entity matches any organization pattern,
# classify it as an Organization
organization_regex = "|".join(organization_patterns.keys())

entity_occurrences.loc[
    entity_occurrences["entity_name"].str.contains(
        organization_regex,
        regex=True,
        case=False,
        na=False
    ),
    "entity_type"
] = "Organization"

# Define an organization classification function
def classify_organization(name):

    if name == "":
        return (None, None)

    for pattern, (org_type, confidence) in organization_patterns.items():
        if re.search(pattern, name):
            return (org_type, confidence)

    return ("Other Organization", "Low")

# Apply the organization classification function.
mask = entity_occurrences["entity_type"] == "Organization"

organization_info = (
    entity_occurrences.loc[mask, "entity_name"]
    .apply(classify_organization)
)

entity_occurrences.loc[mask, "organization_type"] = (
    organization_info.str[0]
)

entity_occurrences.loc[mask, "classification_confidence"] = (
    organization_info.str[1]
)

# Add address source
address_source_mapping = {
    "Owner": "owner_address",
    "Owner Care Of": "owner_address",
    "Taxpayer": "taxpayer_address",
    "Taxpayer Care Of": "taxpayer_address",
    "Tax Send To": "taxpayer_address"
}

entity_occurrences["address_source"] = (
    entity_occurrences["role"]
    .map(address_source_mapping)
)

# Give every row a primary key
entity_occurrences.insert(
    0,
    "occurrence_id",
    range(1, len(entity_occurrences) + 1)
)

print(entity_occurrences.head(20))
print()

print(f"Total entity occurrences: {len(entity_occurrences):,}")

print("\nEntity types:")
print(entity_occurrences["entity_type"].value_counts())

print("\nOrganization types:")
print(entity_occurrences["organization_type"].value_counts(dropna=False))