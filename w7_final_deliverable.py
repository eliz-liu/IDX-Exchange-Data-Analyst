# %%
import pandas as pd
import os
import numpy as np
from update_transform_log import update_transform_log

# %%
df = pd.read_csv('sold_and_listings_school_districts_view.csv')

# %%
def flag_outliers(df, col='ClosePrice'):
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1

    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    
    result = ((df[col] < lower) | (df[col] > upper)).astype(int)
    
    return result

# %%
df['ClosePrice_is_outlier'] = flag_outliers(df, col='ClosePrice')
df['LivingArea_is_outlier'] = flag_outliers(df, col='LivingArea')
df['DaysOnMarket_is_outlier'] = flag_outliers(df, col='DaysOnMarket')
df['is_outlier'] = (
    (df['ClosePrice_is_outlier'] == 1) |
    (df['LivingArea_is_outlier'] == 1) |
    (df['DaysOnMarket_is_outlier'] == 1)
).astype(int)

# %%
update_transform_log(df = df, name = 'sold_and_listings_school_districts_view', action = 'flag_outliers', destination = 'sold_and_listings_view_flagged.csv')

# %%
df.to_csv('sold_and_listings_view_flagged.csv',index=False)

# %%
outlier_columns = ['ClosePrice_is_outlier','LivingArea_is_outlier','DaysOnMarket_is_outlier','is_outlier']
df_clean = df[df['is_outlier'] == 0].drop(columns=outlier_columns)

# %%
update_transform_log(df = df_clean, name = 'sold_and_listings_school_districts_view', action = 'remove_outliers', destination = 'sold_and_listings_view_cleaned.csv')

# %%
df_clean.to_csv('sold_and_listings_view_cleaned.csv',index=False)

# %% [markdown]
# IQR filtering to key numeric fields (ClosePrice, LivingArea, DaysOnMarket). Add outlier flag columns rather than deleting records outright. Save both a full flagged dataset and a clean filtered dataset. Include a written comparison of dataset size and median values before and after filtering.


