import pandas as pd
import os
import re

# Functions for extracting date from filename, checking column consistency, and adding date columns to DataFrames
def extract_date(text):
    pattern = r'(?<!\d)(\d{4})(0[1-9]|1[0-2])'
    match = re.search(pattern, text)
    if match:
        return match.group(1), match.group(2)
    return None, None
def check_columns(columns, final_columns):
    if set(columns) == set(final_columns):
        return True
    else:
        return False
def add_date_columns(df, filename):
    year, month = extract_date(filename)
    df.insert(0, "source", filename)
    df.insert(1, "year", year)
    df.insert(2, "month", month)
    return df

# Initialize final DataFrames and column sets for listing, sold, and sold filled data
folder_path = 'csv'

listing_df = None
listing_final_df = None
listing_col = None

sold_df = None
sold_final_df= None
sold_col = None

sold_filled_df = None
sold_fill_final_df = None
sold_filled_col = None

# Process all CSV files in the specified folder and concatenate them into final DataFrames
for filename in os.listdir(folder_path):
    print("Processing file:", filename)
    if filename.endswith('.csv') and filename.startswith('CRMLSListing'):
        if listing_final_df is not None:
            listing_df = pd.read_csv(folder_path + '/' + filename)
            if check_columns(listing_df.columns, listing_final_df.columns):
                listing_df = add_date_columns(listing_df, filename)
                listing_final_df = pd.concat([listing_final_df, listing_df])
                print("Concatenated listing_final_df with file:", filename)
            else:
                print("Listing columns do not match:", filename, len(listing_df.columns))

        else:
            print("Initializing listing_final_df with file:", filename)
            listing_final_df = pd.read_csv(folder_path + '/' + filename)
            listing_final_df = add_date_columns(listing_final_df, filename)
        
    if filename.startswith('CRMLSSold') and filename.endswith('_filled.csv'):
        if sold_fill_final_df is not None:
            sold_filled_df = pd.read_csv(folder_path + '/' + filename)
            if check_columns(sold_filled_df.columns, sold_fill_final_df.columns):
                sold_filled_df = add_date_columns(sold_filled_df, filename)
                sold_fill_final_df = pd.concat([sold_fill_final_df, sold_filled_df])
                print("Concatenated sold_fill_final_df with file:", filename)
            else:
                print("Sold filled columns do not match:", filename, len(sold_filled_df.columns))
        else:
            print("Initializing sold_fill_final_df with file:", filename)
            sold_fill_final_df = pd.read_csv(folder_path + '/' + filename)
            sold_fill_final_df = add_date_columns(sold_fill_final_df, filename)
            print("Sold filled columns do not match:", filename, len(sold_filled_col))
        
    if filename.startswith('CRMLSSold') and not filename.endswith('_filled.csv'):
        if sold_final_df is not None:
            sold_df = pd.read_csv(folder_path + '/' + filename)
            if check_columns(sold_df.columns, sold_final_df.columns):
                sold_df = add_date_columns(sold_df, filename)
                sold_final_df = pd.concat([sold_final_df, sold_df])
                print("Concatenated sold_final_df with file:", filename)
            else:
                print("Sold columns do not match:", filename, len(sold_final_df.columns))
        else:  # initialize sold_final_df and sold_col
            print("Initializing sold_final_df with file:", filename)
            sold_final_df = pd.read_csv(folder_path + '/' + filename)
            sold_final_df = add_date_columns(sold_final_df, filename)

# Save initial concatenated DataFrames to CSV files
listing_final_df.to_csv('listing_output.csv', index=False)
sold_final_df.to_csv('sold_output.csv', index=False)
sold_fill_final_df.to_csv('sold_fill_output.csv', index=False)

# Identify missing columns between sold_final_df and sold_fill_final_df
sold_filled_col = set(sold_fill_final_df.columns)
sold_col = set(sold_final_df.columns)
not_in_sold = sold_col.difference(sold_filled_col)
not_in_sold_filled = sold_filled_col.difference(sold_col)
print(not_in_sold) # Columns in sold_df but not in sold_fill_final_df
print(not_in_sold_filled) # Columns in sold_fill_final_df but not in sold_final_df

#add missing columns to sold_final_df and sold_fill_final_df before concatenation
sold_fill_final_df['OriginatingSystemSubName'] = ''
sold_fill_final_df['OriginatingSystemName'] = ''
sold_final_df['latfilled'] = ''
sold_final_df['lonfilled'] = ''

# Concatenate the sold_final_df and sold_fill_final_df after adding missing columns
complete_sold_df = pd.concat([sold_final_df, sold_fill_final_df], ignore_index=True)

# Save the complete concatenated DataFrames to CSV files
listing_final_df.to_csv('listing_complete.csv', index=False)
complete_sold_df.to_csv('sold_complete.csv', index=False)

#Residential Only
residential_sold_df = complete_sold_df[complete_sold_df['PropertyType'] == 'Residential']
residential_sold_df.to_csv('residential_sold_output.csv', index=False)
residential_listing_df = listing_final_df[listing_final_df['PropertyType'] == 'Residential']
residential_listing_df.to_csv('residential_listing_output.csv', index=False)
