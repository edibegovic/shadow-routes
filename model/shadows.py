import pandas as pd 
import pybdshadow
from geopandas import GeoDataFrame
import geopandas as gpd

def get_buildings_shadows(gdf: GeoDataFrame):
    date = pd.to_datetime('2022-10-21 14:45:33.95979')\
        .tz_localize('Europe/Copenhagen')\
        .tz_convert('UTC')

    gdf['building_id'] = gdf.index 
    shadows = pybdshadow.bdshadow_sunlight(gdf, date)
    shadows = shadows.set_crs('epsg:4326')
    return shadows

def get_trees_shadows(gdf: GeoDataFrame):
    date = pd.to_datetime('2022-10-21 14:45:33.95979')\
        .tz_localize('Europe/Copenhagen')\
        .tz_convert('UTC')

    gdf['building_id'] = gdf.index 
    shadows = pybdshadow.bdshadow_sunlight(gdf, date)

    gdf['height'] = 2
    subtract = pybdshadow.bdshadow_sunlight(gdf, date)

    shadows = shadows.difference(subtract)
    return gpd.GeoDataFrame(geometry=shadows, crs='epsg:4326')