import pandas as pd
from update_transform_log import update_transform_log

print('Fetch Mortgage Data')
#Downloaded Data via API, then saved as MORTGAGE30US.csv file
url = r"MORTGAGE30US.csv"
mortgage = pd.read_csv(url, parse_dates=['observation_date'])
mortgage.columns = ['date', 'rate_30yr_fixed']

print('Extract Year and Month from date column')
mortgage['year_month'] = mortgage['date'].dt.to_period('M')
mortgage_monthly = (
    mortgage.groupby('year_month')['rate_30yr_fixed']
    .mean()
    .reset_index()
)

mortgage_monthly['year_month'] = mortgage_monthly['year_month'].astype('str')
mortgage_monthly[['year', 'month']] = mortgage_monthly['year_month'].str.split('-', n=1, expand=True)

print('Load listing and sold datasets')
sold_path = r'cleaned_raw_sold_data.csv'
listing_path = r'cleaned_raw_listing_data.csv'
sold = pd.read_csv(sold_path)
listings = pd.read_csv(listing_path)

print('Merge with mortgage data')
sold['month'] = sold['month'].astype('int64')
listings['month'] = listings['month'].astype('int64')
mortgage_monthly['month'] = mortgage_monthly['month'].astype('int64')
mortgage_monthly['year'] = mortgage_monthly['year'].astype('int64')

sold_with_rates = sold.merge(mortgage_monthly, on=['year','month'], how='left')
listings_with_rates = listings.merge(mortgage_monthly, on=['year','month'], how='left')

print('Drop irrelevant columns')
sold_with_rates.drop(columns='year_month', inplace=True)
listings_with_rates.drop(columns='year_month', inplace=True)

# Check for any unmatched rows (rate should not be null)
print("Check merge results")
print("Sold Number of Rows Unmatched: ")
print(sold_with_rates['rate_30yr_fixed'].isnull().sum())
print("Listings Number of Rows Unmatched: ")
print(listings_with_rates['rate_30yr_fixed'].isnull().sum())
print("Example View Of Rows:")
print('Sold: ')
print(
    sold_with_rates[
        ['CloseDate', 'year','month', 'ClosePrice', 'rate_30yr_fixed']
    ].head()
)
print('Listings:')
print(
    listings_with_rates[
        ['CloseDate', 'year','month', 'ClosePrice', 'rate_30yr_fixed']
    ].head()
)

sold_target_path = r'sold_mortgage_enriched.csv'
listings_target_path = r'listings_mortgage_enriched.csv'
sold_with_rates.to_csv(sold_target_path,index=False)
listings_with_rates.to_csv(listings_target_path,index=False)
print('Saved Enriched Data')

update_transform_log(df = sold_with_rates, name = 'sold data', action = 'cleaned_raw_sold_data enriched with mortgage rates', destination = sold_target_path)
update_transform_log(df = listings_with_rates, name = 'listing data', action = 'cleaned_raw_listing_data enriched with mortgage rates', destination = listings_target_path)
print('Updated log')