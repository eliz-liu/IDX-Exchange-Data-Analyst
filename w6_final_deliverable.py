import geopandas as gpd
import pandas as pd
import numpy as np
import datetime

#Load Datasets
gdf = gpd.read_file("DistrictAreas2425")
df_sold = pd.read_csv("sold_final.csv")
df_listing = pd.read_csv("listings_final.csv")

#tidy up datasets
school_columns = ['CDCode', 'CDSCode', 'CountyName',
       'DistrictNa', 'DistrictTy', 'GradeLow', 'GradeHigh', 'GradeLowCe',
       'GradeHighC', 'AssistStat', 'CongressUS', 'SenateCA', 'AssemblyCA',
       'UpdateNote', 'EnrollTota', 'EnrollChar', 'EnrollNonC', 'AAcount',
       'AApct', 'AIcount', 'AIpct', 'AScount', 'ASpct', 'FIcount', 'FIpct',
       'HIcount', 'HIpct', 'PIcount', 'PIpct', 'WHcount', 'WHpct', 'MRcount',
       'MRpct', 'NRcount', 'NRpct', 'ELcount', 'ELpct', 'FOScount', 'FOSpct',
       'HOMcount', 'HOMpct', 'MIGcount', 'MIGpct', 'SWDcount', 'SWDpct',
       'SEDcount', 'SEDpct','geometry']

school_df = gdf[school_columns]

df_sold['SoldOrListing'] = 'Sold'
df_listing['SoldOrListing'] = 'Listing'
df = pd.concat([df_sold,df_listing])


#add metrics

date_cols = [
    "ListingContractDate",
    "PurchaseContractDate",
    "CloseDate"
]

for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors="coerce")

df["CloseDate"] = pd.to_datetime(df["CloseDate"])
df["CloseDateYear"] = df["CloseDate"].dt.year
df["CloseDateMonth"] = df["CloseDate"].dt.month
df["CloseDateYrMo"] = df["CloseDate"].dt.strftime("%Y-%m")

df["Price Ratio"] = np.where(
    (df["OriginalListPrice"].notna()) & (df["OriginalListPrice"] > 0),
    df["ClosePrice"] / df["OriginalListPrice"],
    np.nan
)

df["Price Per Sq Ft"] = np.where(
    (df["LivingArea"].notna()) & (df["LivingArea"] > 0),
    df["ClosePrice"] / df["LivingArea"],
    np.nan
)

df["CloseToOriginalListRatio"] = np.where(
    df["OriginalListPrice"] > 0,
    df["ClosePrice"] / df["OriginalListPrice"],
    np.nan
)

df["ListingToContractDays"] = (
    df["PurchaseContractDate"] -
    df["ListingContractDate"]
).dt.days

df["ContractToCloseDays"] = (
    df["CloseDate"] -
    df["PurchaseContractDate"]
).dt.days

#add school district

points = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df.Longitude, df.Latitude),
    crs="EPSG:4326"
).to_crs("EPSG:3857")

result = gpd.sjoin(
    points,
    school_df,
    how="left",
    predicate="within"
)

metrics = [
    "ClosePrice",
    "Price Ratio",
    "Price Per Sq Ft",
    "ListingToContractDays",
    "ContractToCloseDays",
    "DaysOnMarket"
]

property_type_summary = (
    result[result['SoldOrListing']=='Sold'].groupby(["PropertyType", "PropertySubType"])[metrics]
      .agg([
          "count",
          "mean",
          "median",
          "min",
          "max",
          "std"
      ])
      .round(2)
      .sort_values(
          ("ClosePrice", "count"),
          ascending=False
      )
)

print(property_type_summary)

location_summary = (
    result[result['SoldOrListing']=='Sold'].groupby(["CountyOrParish", "MLSAreaMajor"])[metrics]
      .agg([
          "count",
          "mean",
          "median",
          "min",
          "max",
          "std"
      ])
      .round(2)
      .sort_values(
          ("ClosePrice", "count"),
          ascending=False
      )
)

print(location_summary)

listing_office_summary = (
    result[result['SoldOrListing']=='Sold'].groupby("ListOfficeName")[metrics]
      .agg([
          "count",
          "mean",
          "median"
      ])
      .round(2)
      .sort_values(
          ("ClosePrice", "count"),
          ascending=False
      )
)

print(listing_office_summary)

buyer_office_summary = (
    result[result['SoldOrListing']=='Sold'].groupby("BuyerOfficeName")[metrics]
      .agg([
          "count",
          "mean",
          "median"
      ])
      .round(2)
      .sort_values(
          ("ClosePrice", "count"),
          ascending=False
      )
)

print(buyer_office_summary)