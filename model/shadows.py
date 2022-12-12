import pandas as pd 
import pybdshadow
from geopandas import GeoDataFrame
import geopandas as gpd
from rtree import index

def get_buildings_shadows(gdf: GeoDataFrame, date='2022-10-21 14:45:33.95979'):
    date = pd.to_datetime(date)\
        .tz_localize('Europe/Copenhagen')\
        .tz_convert('UTC')

    gdf['building_id'] = gdf.index 
    shadows = pybdshadow.bdshadow_sunlight(gdf, date)
    shadows = shadows.set_crs('epsg:4326')
    return shadows

def get_trees_shadows(gdf: GeoDataFrame, date='2022-10-21 14:45:33.95979'):
    date = pd.to_datetime(date)\
        .tz_localize('Europe/Copenhagen')\
        .tz_convert('UTC')

    gdf['building_id'] = gdf.index 
    shadows = pybdshadow.bdshadow_sunlight(gdf, date)

    gdf['height'] = 2
    subtract = pybdshadow.bdshadow_sunlight(gdf, date)

    shadows = shadows.difference(subtract)
    return gpd.GeoDataFrame(geometry=shadows, crs='epsg:4326')

def build_rtree_index(gdf: GeoDataFrame):
    idx = index.Index()
    for i, shape in enumerate(gdf):
        idx.insert(i, shape.bounds)
    return idx
