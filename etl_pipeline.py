# Import Packages
import pandas as pd
import re

# Import from local files
from data_cleaning import DataCleaner
from extraction import extract_data

### EXTRACT ###
extracted_df = extract_data('2025 Roll - Parcels Export.xlsx', 'Only Delinquent Parcels')

### CLEAN ###

cleaner = DataCleaner()
clean_df = cleaner.clean_data(extracted_df)

print(clean_df.info())