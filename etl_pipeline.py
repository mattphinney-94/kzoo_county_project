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
from entity_resolution import EntityResolver

### EXTRACT ###
extracted_df = extract_data('2025 Roll - Parcels Export.xlsx', 'Only Delinquent Parcels')

### CLEAN ###
cleaner = DataCleaner()
clean_df = cleaner.clean_data(extracted_df)

# print(clean_df.info())

### ENTITY RESOLUTION ###
(
    entity_occurrences,
    entities,
    parcel_entity_roles,
    association_evidence,
    entity_associations
) = EntityResolver().build(clean_df)

### Entity occurrences table check
print(entity_occurrences.head(20))
print()

print(f"Total entity occurrences: {len(entity_occurrences):,}")

print("\nEntity types:")
print(entity_occurrences["entity_type"].value_counts())

print("\nOrganization types:")
print(entity_occurrences["organization_type"].value_counts(dropna=False))

### Entities table check
print(entities.head(20))
print()

print(f"Total entities: {len(entities):,}")