import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from update_transform_log import update_transform_log
from w2_utils import numeric_summary_plots, eda_run

df_listing = pd.read_csv('raw_data_listing.csv')
df_sold = pd.read_csv('raw_data_sold.csv')

print('Data loaded')

# Filter out irrevelant columns

# Columns present in both files
COMMON_DROP = [
    # duplicate IDs (keeping ListingId as the key)
    "ListingKey", "ListingKeyNumeric",

    # agent PII / identifiers / provenance
    "ListAgentEmail", "ListAgentFullName", "ListAgentFirstName", "ListAgentLastName",
    "CoListAgentFirstName", "CoListAgentLastName",
    "BuyerAgentMlsId", "BuyerAgentFirstName", "BuyerAgentLastName",
    "CoBuyerAgentFirstName",
    "filename", "BuyerOfficeAOR", "BusinessType", 'download_date',

    # redundant with kept columns
    "LotSizeArea", "LotSizeDimensions",   # keep LotSizeSquareFeet
    "BuildingAreaTotal", "AboveGradeFinishedArea",        # keep LivingArea
    "CoveredSpaces", "ParkingTotal", "AttachedGarageYN",  # keep GarageSpaces
    "FireplaceYN",                                        # keep FireplacesTotal
    "StreetNumberNumeric", "TaxYear",

    # likely all-NaN (float dtype on a text field)
    "ElementarySchoolDistrict", "MiddleOrJuniorSchoolDistrict",

    # high-cardinality, covered by lat/long, postal code, subdivision
    "ElementarySchool", "MiddleOrJuniorSchool", "HighSchool",
]

# Listings file only
LISTINGS_DROP = COMMON_DROP + [
    # duplicate columns created by a merge/concat (verify they match the originals first)
    "PropertyType.1", "ListAgentFirstName.1", "ListAgentLastName.1",
    "DaysOnMarket.1", "LivingArea.1", "Longitude.1", "Latitude.1",
    "ListPrice.1", "CloseDate.1", "BuyerOfficeName.1", "UnparsedAddress.1",
]

# Sold file only
SOLD_DROP = COMMON_DROP + [
    "OriginatingSystemName", "OriginatingSystemSubName",
    "BuyerAgentAOR", "ListAgentAOR",
    "latfilled", "lonfilled",   # coalesce into Latitude/Longitude first
    "Flooring",                 # free text; keep if you plan to parse it
]

listings_filtered = df_listing.drop(columns=LISTINGS_DROP)
sold_filtered = df_sold.drop(columns=SOLD_DROP)
print('Dropped Irrevelant Columns')

update_transform_log(df = listings_filtered, name = 'listing data', action = 'Filter out irrevelant columns in raw_data_listing.csv', destination = 'cleaned_raw_listing_data.csv')
update_transform_log(df = sold_filtered, name = 'sold data', action = 'Filter out irrevelant columns in raw_data_sold.csv', destination = 'cleaned_raw_sold_data.csv')
print('Updated Transform Log')

# Missing Column DataFrames
print('Started Null Analysis')

listing_null_counts = listings_filtered.isnull().sum().to_frame('Null Counts')
listing_null_counts['Null %'] = round(listing_null_counts['Null Counts'] / df_listing.shape[0] * 100, 2)
listing_null_counts['Column Name'] = listing_null_counts.index

sold_null_counts = sold_filtered.isnull().sum().to_frame('Null Counts')
sold_null_counts['Null %'] = round(sold_null_counts['Null Counts'] / df_sold.shape[0] * 100, 2)
sold_null_counts['Column Name'] = sold_null_counts.index

# Null % Distribution
listing_nulls = listing_null_counts['Null %']
listing_null_count_dist = sns.histplot(data=listing_nulls, bins=40).get_figure()
listing_null_count_dist.savefig(r"week_2_final_deliverables\listing_null_count_dist.png", dpi=300, bbox_inches="tight")


sold_nulls = sold_null_counts['Null %']
sold_null_count_dist = sns.histplot(data=sold_nulls, bins=40).get_figure()
sold_null_count_dist.savefig(r"week_2_final_deliverables\sold_null_count_dist.png", dpi=300, bbox_inches="tight")


# Display Columns with High Null Percentages
listing_nulls_90Plus = listing_null_counts[listing_null_counts['Null %'] >= 90].sort_values(by='Null %', ascending=False)
sold_nulls_90Plus = sold_null_counts[sold_null_counts['Null %'] >= 90].sort_values(by='Null %', ascending=False)
print('~Columns with High Null Percentages (90%+) Results~')
print('Columns with 90%+ nulls in listings:')
print(",".join(listing_nulls_90Plus['Column Name'].tolist()))
print()
print('Columns with 90%+ nulls in sold listings:')
print(",".join(sold_nulls_90Plus['Column Name'].tolist()))

# Drop Columns with High Null Percentages (90%+)
listing_data_final = listings_filtered.drop(columns=listing_nulls_90Plus['Column Name'].tolist())
sold_data_final = sold_filtered.drop(columns=sold_nulls_90Plus['Column Name'].tolist())
print('Dropped Columns with High Null Percentages (90%+)')

listing_data_final.to_csv(r'cleaned_raw_listing_data.csv',index=False)
sold_data_final.to_csv(r'cleaned_raw_sold_data.csv',index=False)
print('Saved Final Dataframes to .csv')

update_transform_log(df = listing_data_final, name = 'listing data', action = 'Drop Columns with High Null Percentages (90%+) in raw_data_listing.csv', destination = 'cleaned_raw_listing_data.csv')
update_transform_log(df = sold_data_final, name = 'sold data', action = 'Drop Columns with High Null Percentages (90%+) in raw_data_sold.csv', destination = 'cleaned_raw_sold_data.csv')
print('Updated Transform Log')


print('Start Numeric Review:')
feature_list = ['ClosePrice', 'ListPrice', 'OriginalListPrice', 'LivingArea', 'LotSizeAcres', 'BedroomsTotal', 'BathroomsTotalInteger', 'DaysOnMarket','YearBuilt']
print('Features: ', ','.join(feature_list))

# Summary Plot for listings and sold MLS data
# Analyze the distribution of key numeric fields: 
# ClosePrice, ListPrice, OriginalListPrice, LivingArea, LotSizeAcres, 
# BedroomsTotal, BathroomsTotalInteger, DaysOnMarket, and YearBuilt. 

target_dir = r"week_2_final_deliverables\sold_figures"
numeric_summary_plots(sold_data_final[feature_list], output_dir=target_dir)

target_dir = r"week_2_final_deliverables\listing_figures"
numeric_summary_plots(listing_data_final[feature_list], output_dir=target_dir)

# EDA for listings and sold MLS data.
eda_run("listings", r'cleaned_raw_listing_data.csv')
eda_run("sold", r'cleaned_raw_sold_data.csv')


# Residential Data: Summary Report & Cleaned Dataset
"""
Filter listings / sold data to residential records and profile the result.

For each dataset this script:
  1. Documents the unique PropertyType values found (with counts) and which are kept
  2. Applies the filters below, logging row counts after every step
  3. Produces a null-count summary table for ALL columns (pre-filter and post-filter)
  4. Flags columns that are more than NULL_FLAG_THRESHOLD null (default 90%)
  5. Summarizes ClosePrice, LivingArea and DaysOnMarket
     (min, max, mean, median, std, 1/5/10/25/75/90/95/99th percentiles)
  6. Saves the filtered dataset as a new CSV

Outputs go to OUTPUT_DIR:
  residential_<name>.csv      filtered dataset
  <name>_null_summary.csv     null counts per column
  <name>_numeric_summary.csv  distribution summary
  <name>_report.txt           full text report (same as printed output)
  
Also saves to final result to transform_log.csv. 

"""

with open("w2_generate_residential_report.py", "r") as file:
    script_content = file.read()
exec(script_content)

