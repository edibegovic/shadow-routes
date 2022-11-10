
import numpy as np
import pandas as pd
import geopandas as gpd
from geopandas import GeoDataFrame
from shapely.geometry import Polygon, Point, LineString
import pybdshadow

trees = gpd.read_file("data/tree_basiss.json")

tree = trees[['geometry']].copy()
tree['lat'] = tree.geometry.y
tree['lon'] = tree.geometry.x

# Helper util
def geodesic_point_buffer(lon, lat, km):
    proj_crs = ProjectedCRS(
        conversion = AzumuthalEquidistantConversion(lat, lon)
    )
    proj_wgs84 = pyproj.Proj('EPSG:4326')
    Trans = pyproj.Transformer.from_proj(
        proj_crs,
        proj_wgs84,
        always_xy=True
    ).transform
    return transform(Trans, Point(0, 0).buffer(km * 1000))

# buffer
d = {'name': ['axel'], 'geometry': [axel_towers]}
gdf = gpd.GeoDataFrame(d, crs="EPSG:4326")
gdf['geometry'] = gdf['geometry'].buffer(0.015)

trees_small = gpd.sjoin(tree, gdf, how='inner', predicate='within')

# Converts popint (location of tree) to polygon (based on radius)
trees_small['geometry'] = trees_small['geometry'].buffer(0.0005)

# Height height in meters
trees_small['height'] = 6

def get_shadows(gdf: GeoDataFrame) -> GeoDataFrame:
    date = pd.to_datetime('2022-10-21 14:45:33.95979')\
        .tz_localize('Europe/Copenhagen')\
        .tz_convert('UTC')

    gdf['building_id'] = gdf.index 
    shadows = pybdshadow.bdshadow_sunlight(gdf, date)
    return shadows

tree_shadows = get_shadows(trees_small)

