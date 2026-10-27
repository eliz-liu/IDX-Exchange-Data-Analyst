import pandas as pd
from update_transform_log import update_transform_log
import numpy as np

sold_final_path = r'sold_final.csv'
listings_final_path = r'listings_final.csv'

sold_flags_path = r'sold_stage.csv'
listings_flags_path = r'listings_stage.csv'

sold_target_path = r'sold_mortgage_enriched.csv'
listings_target_path = r'listings_mortgage_enriched.csv'
sold_df = pd.read_csv(sold_target_path)
listings_df = pd.read_csv(listings_target_path)

print('Start creating staging datasets: ')

#Convert date fields to datetime format (CloseDate, PurchaseContractDate, ListingContractDate, ContractStatusChangeDate)
date_cols = [
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
    "ContractStatusChangeDate",
]

sold_df[date_cols] = sold_df[date_cols].apply(pd.to_datetime, errors="coerce")
listings_df[date_cols] = listings_df[date_cols].apply(pd.to_datetime, errors="coerce")

#Remove unnecessary or redundant columns
sold_df = sold_df.drop_duplicates()
listings_df = listings_df.drop_duplicates()
listings_df = listings_df.drop(columns=['Unnamed: 0'])
sold_df = sold_df.drop(columns=['Unnamed: 0'])

#Handle missing values appropriately
print(sold_df.shape)
sold_df.dropna(axis=1, how='all')
sold_df.dropna(axis=0, how='all')
print(sold_df.shape)
print(listings_df.shape)
listings_df.dropna(axis=0, how='all')
listings_df.dropna(axis=1, how='all')
print(listings_df.shape)

print('Finished cleaning data. Now identifying and removing invalid rows.')
#Remove or flag invalid numeric values: 
# ClosePrice <= 0, LivingArea <= 0, 
# DaysOnMarket < 0, 
# negative Bedrooms or Bathrooms

rules = {
    "ClosePrice":            lambda s: s <= 0,
    "LivingArea":            lambda s: s <= 0,
    "DaysOnMarket":          lambda s: s < 0,
    "BedroomsTotal":         lambda s: s < 0,
    "BathroomsTotalInteger": lambda s: s < 0,
}

def flag_invalid_numeric(df, rules):
    df = df.copy()

    # int64 can't hold missing values, so allow nulls before we blank anything out
    df["DaysOnMarket"] = df["DaysOnMarket"].astype("Int64")

    any_invalid = pd.Series(False, index=df.index)
    for col, is_bad in rules.items():
        if col not in df.columns:
            continue
        bad = is_bad(df[col]).fillna(False).astype(bool)  # NaN is not "invalid"
        df[f"Invalid_{col}"] = bad          # keep a flag for auditing
        df.loc[bad, col] = np.nan           # null out the bad value
        any_invalid |= bad                  #updates where there is invalid numeric

    df["HasInvalidNumeric"] = any_invalid
    return df

listings = flag_invalid_numeric(listings_df, rules)
sold = flag_invalid_numeric(sold_df, rules)

sold_clean = sold[~sold["HasInvalidNumeric"]].copy()
listings_clean = listings[~listings["HasInvalidNumeric"]].copy()

update_transform_log(df = sold_clean, name = 'sold data', action = 'Remove invalid numeric values', destination = sold_flags_path)
update_transform_log(df = listings_clean, name = 'listing data', action = 'Remove invalid numeric values', destination = listings_flags_path)
print('Removed invalid numeric data, and updated transform log')
'''
Validate the logical order of date fields: ListingContractDate should precede PurchaseContractDate, which should precede CloseDate. 
Create boolean flag columns to mark records that violate these rules:
•	listing_after_close_flag
•	purchase_after_close_flag
•	negative_timeline_flag
'''

def add_date_order_flags(df):
    df = df.copy()

    listing  = df["ListingContractDate"]
    purchase = df["PurchaseContractDate"]
    close    = df["CloseDate"]

    # Comparisons involving NaT evaluate to False, so incomplete records are not flagged
    df["listing_after_close_flag"]  = listing > close
    df["purchase_after_close_flag"] = purchase > close

    # Any break in the Listing -> Purchase -> Close chain
    df["negative_timeline_flag"] = (
        (listing > purchase) |
        (purchase > close) |
        (listing > close)
    )
    return df

listings = add_date_order_flags(listings_clean)
sold = add_date_order_flags(sold_clean)


update_transform_log(df = sold, name = 'sold data', action = 'add_date_order_flags', destination = sold_flags_path)
update_transform_log(df = listings, name = 'listing data', action = 'add_date_order_flags', destination = listings_flags_path)
print('Added date order flags, and updated transform log')

# (lat_min, lat_max, lon_min, lon_max), keyed by StateOrProvince abbreviation
STATE_BOUNDS = {
    "CA": (32.5, 42.0, -124.5, -114.1),
    # "TX": (25.8, 36.5, -106.7, -93.5),   # add other states if your data has them
}
DEFAULT_BOUNDS = (24.5, 49.5, -125.0, -66.9)  # continental US fallback for unlisted states

def add_geo_flags(df, state_bounds=STATE_BOUNDS, default_bounds=DEFAULT_BOUNDS):
    df = df.copy()
    lat, lon = df["Latitude"], df["Longitude"]

    # 1. Missing coordinates
    df["missing_coords_flag"] = lat.isna() | lon.isna()

    # 2. Zero used as a sentinel for "unknown"
    df["zero_coords_flag"] = (lat == 0) | (lon == 0)

    # 3. Positive longitude (sign error; US longitudes are negative)
    df["positive_longitude_flag"] = lon > 0

    # 4. Outside the expected state's bounding box
    state = df["StateOrProvince"].astype("string").str.strip().str.upper()

    def bound(i):
        lookup = {k: v[i] for k, v in state_bounds.items()}
        return state.map(lookup).astype(float).fillna(default_bounds[i])

    lat_min, lat_max, lon_min, lon_max = (bound(i) for i in range(4))

    has_coords = lat.notna() & lon.notna()
    outside = (lat < lat_min) | (lat > lat_max) | (lon < lon_min) | (lon > lon_max)
    df["out_of_state_flag"] = has_coords & outside

    # Any geographic problem
    geo_flags = ["missing_coords_flag", "zero_coords_flag",
                 "positive_longitude_flag", "out_of_state_flag"]
    df["invalid_geo_flag"] = df[geo_flags].any(axis=1)
    return df

listings = add_geo_flags(listings)
sold = add_geo_flags(sold)

listings.to_csv(listings_flags_path)
sold.to_csv(sold_flags_path)

update_transform_log(df = sold, name = 'sold data', action = 'add_geo_flags', destination = sold_flags_path)
update_transform_log(df = listings, name = 'listing data', action = 'add_geo_flags', destination = listings_flags_path)
print('Added geo flags, Saved Staging datasets, and Updated transform log')

def flag_summary(df, filename):
    flag_cols = df.columns[df.columns.str.contains('flag')].tolist()
    flag_count = [df[f"{col}"].sum() for col in flag_cols]
    df_summary = pd.DataFrame({
        'flag_name': flag_cols,
        'flag_count': flag_count
    })
    df_summary.to_csv(filename,index=False)


for name, df in [('listing_flag_summary.csv', listings), ('sold_flag_summary.csv', sold)]:
    flag_summary(df, name)
    
print('Remove flags and Save final dataset')
sold_flag_cols = sold.columns[sold.columns.str.contains('flag')].tolist()
listings_flag_cols = listings.columns[listings.columns.str.contains('flag')].tolist()


sold_final = sold[sold[sold_flag_cols].any(axis=1)]
listings_final = listings[listings[listings_flag_cols].any(axis=1)]

print(len(sold_final),len(listings_final))

sold_final = sold_final.drop(columns=sold_flag_cols)
listings_final = listings_final.drop(columns=listings_flag_cols)

sold_final.to_csv(sold_final_path,index=False)
listings_final.to_csv(listings_final_path,index=False)

update_transform_log(df = sold_final, name = 'sold data', action = 'remove_flagged', destination = sold_final_path)
update_transform_log(df = listings_final, name = 'listing data', action = 'remove_flagged', destination = listings_final_path)

print('Saved final dataset. Updated log')


    

    
