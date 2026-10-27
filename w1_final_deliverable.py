import pandas as pd
import os
import re
from update_transform_log import update_transform_log

# Functions for extracting date from filename, checking column consistency, and adding date columns to DataFrames
def extract_date(text):
    pattern = r'(?<!\d)(\d{4})(0[1-9]|1[0-2])'
    match = re.search(pattern, text)
    if match:
        return match.group(1), match.group(2)
    return None, None

def create_df(filename):
    try:
        df = pd.read_csv(filename)
    except:
        df = pd.read_csv(filename, encoding='latin1')
    year, month = extract_date(filename)
    df['filename'] = filename
    df['year'] =  year
    df['month'] = month
    df['download_date'] = pd.Timestamp.now()
    return df

# Initialize final DataFrames and column sets for listing, sold, and sold filled data
folder_path = 'new_extracts'

listing_files = [os.path.join(folder_path,filename) for filename in os.listdir(folder_path) if filename.endswith('.csv') and filename.startswith('CRMLSListing')]
sold_files = [os.path.join(folder_path,filename) for filename in os.listdir(folder_path) if filename.endswith('.csv') and filename.startswith('CRMLSSold')]
print(len(listing_files), ' filepaths found for listing files')
print(len(sold_files), ' filepaths found for sold files')

listing_df_list = [create_df(file) for file in listing_files]
sold_df_list = [create_df(file) for file in sold_files]
print(len(listing_df_list), ' files processed for listing')
print(len(sold_df_list), ' files processed for sold')

listing_final = pd.concat(listing_df_list)
sold_final =  pd.concat(sold_df_list)
print('all files concatenated for listing')
print('all files concatenated for sold')

# Save concatenated DataFrames to CSV files
listing_final.to_csv('raw_data_listing.csv', index=False)
sold_final.to_csv('raw_data_sold.csv', index=False)

print('saved raw_data_listing.csv')
print('saved raw_data_sold.csv')

update_transform_log(df = listing_final, name = 'listing data', action = 'concatenation raw listings data', destination = 'raw_data_listing.csv')
update_transform_log(df = sold_final, name = 'sold data', action = 'concatenation raw sold data', destination = 'raw_data_sold.csv')

print('saved raw_data_listing.csv')
print('saved raw_data_sold.csv')

#Residential Only
residential_sold_df = sold_final[sold_final['PropertyType'] == 'Residential']
residential_listing_df = listing_final[listing_final['PropertyType'] == 'Residential']
print('filtered raw_data_sold on residential type')
print('filtered raw_data_listing on residential type')

residential_sold_df.to_csv('raw_residential_sold.csv', index=False)
residential_listing_df.to_csv('raw_residential_listing.csv', index=False)
print('saved raw_residential_sold.csv')
print('saved raw_residential_listing.csv')

update_transform_log(df = residential_sold_df, name = 'residential sold data', action = 'raw_data_sold filter on residential', destination = 'raw_data_sold.csv')
update_transform_log(df = residential_listing_df, name = 'residential listing data', action = 'raw_data_listing filter on residential', destination = 'raw_data_listing.csv')

print('saved residential listing')
print('saved residential sold')

