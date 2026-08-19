import pandas as pd

df = pd.read_excel('2025 Roll - Parcels Export.xlsx')
print(df.head())

print()
print('Parcel number stats')
print(df["ParcelMaster.parcelnumber"].nunique())
print(df.shape[0])

print()
print('Owner stats')
print(df["ParcelMaster.ownersname"].nunique())
print()

print()
print('Taxpayer stats')
print(df["ParcelMaster.taxpayername"].nunique())
print()

print()
print(df.count())

print(df["ParcelMaster.ownersname"].value_counts().head(20))


# address_owner_counts = (
#     df.groupby("Combined Owner Address")["ParcelMaster.ownersname"]
#       .nunique()
#       .reset_index(name="unique_owner_count")
# )
#
# multiple_owners = address_owner_counts[
#     address_owner_counts["unique_owner_count"] > 1
# ]
#
# results = df[
#     df["Combined Owner Address"].isin(
#         multiple_owners["Combined Owner Address"]
#     )
# ].sort_values("ParcelMaster.ownersname")
#
# print(results[
#     [
#         "Combined Owner Address",
#         "ParcelMaster.ownersname",
#         "ParcelMaster.parcelnumber"
#     ]
# ].to_string(index=False))