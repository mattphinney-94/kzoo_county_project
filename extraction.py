import pandas as pd

def extract_data(filename, sheet):
    raw_df = pd.read_excel(filename, sheet_name=sheet)

    relevant_columns = [
        'ParcelMaster.parcelnumber',
        'Combined Property Address',
        'ParcelMaster.ownersname',
        'ParcelMaster.ownersname2',
        'ParcelMaster.ownercareof',
        'Combined Owner Address',
        'ParcelMaster.taxpayername',
        'ParcelMaster.taxpayercareof',
        'Combined Taxpayer Address',
        'ParcelMaster.tax_send_to_name',
        'Principal Residence Exemption %',
        'Property Class',
        'Taxable Value',
        'Assessed Value',
        'State Equalized Value (SEV)'
    ]

    df = raw_df[relevant_columns]

    column_mapping = {
        "ParcelMaster.parcelnumber": "parcel_number",
        "Combined Property Address": "property_address",
        "ParcelMaster.ownersname": "owner_name",
        "ParcelMaster.ownersname2": "owner_name_2",
        "ParcelMaster.ownercareof": "owner_care_of",
        "Combined Owner Address": "owner_address",
        "ParcelMaster.taxpayername": "taxpayer_name",
        "ParcelMaster.taxpayercareof": "taxpayer_care_of",
        "Combined Taxpayer Address": "taxpayer_address",
        "ParcelMaster.tax_send_to_name": "tax_send_to_name",
        "Principal Residence Exemption %": "principal_residence_exemption_percentage",
        "Property Class": "property_class",
        "Taxable Value": "tax_value",
        "Assessed Value": "assessed_value",
        "State Equalized Value (SEV)": "state_equalized_value",
    }

    extracted_df = (
        raw_df[list(column_mapping.keys())]
        .rename(columns=column_mapping)
        .copy()
    )

    return extracted_df