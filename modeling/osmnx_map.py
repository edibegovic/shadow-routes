
import numpy as np
import pandas as pd
import geopandas as gpd
from geopandas import GeoDataFrame
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling, transform_bounds
from shapely.geometry import Polygon, Point, LineString
from shapely import wkt
import shapely
from pyproj import Proj, transform
import re


# --------------------------------------------------------
# OSM utils
# --------------------------------------------------------

# Some questionable data wrangling going on here..
def extract_polygons(building: Polygon) -> [Polygon]:
    """
    This is a work-around bacause of a syntax mistake in the WKT strings
    returned by osmnx. Extracts all polygons from a single "polygon string"
    from OSM objects tagged 'bulding:part'.

    :building: osmnx multi-polygon representation (either WKT string or Shapely object)
    :return: list of polygons
    """
    wkt_strings = re.findall(r'\(+(.*?)\)', str(building))
    polygons = [shapely.wkt.loads(f'POLYGON(({x}))') for x in wkt_strings]
    return polygons

def flatten_building_parts(buildings: GeoDataFrame) -> GeoDataFrame:
    """
    Takes a GeoDataFrame of building geometries consisting of multiple
    parts as multi-polygons. Returns a flattend GeoDataFrame with a row
    for each individual building part.
    """
    return buildings.geometry \
            .apply(extract_polygons) \
            .explode() \
            .to_frame() \
            .set_geometry('geometry')

def get_building_geometries(bbox: [float]) -> GeoDataFrame:
    """
    Get all building footprints from an area given a point and 
    radius.

    :_from: Point (WGS84 coordinates)
    :radius: radius from point (meters)
    :return: GeoDataFrame containing building geometries
    """
    tags = {"building": True}
    buildings = ox.geometries.geometries_from_bbox(*bbox, tags=tags)
    filter_building_type = lambda gdf, _type: gdf[gdf.index.get_level_values('element_type') == _type]

    buildings_whole = filter_building_type(buildings, 'way')
    building_parts = filter_building_type(buildings, 'relation')

    return pd.concat([
        flatten_building_parts(building_parts), 
        GeoDataFrame(buildings_whole['geometry'])
        ]).set_crs('epsg:4326')

# --------------------------------------------------------
# Rastorio utils
# --------------------------------------------------------

def to_wgs84(point: Point, reverse=False) -> Point:
    """
    Projects points between ETRS89 and WGS84
    """
    projections = (Proj('epsg:25832'), 
            Proj('epsg:4326'))
    inProj, outProj = reversed(projections) if reverse else projections
    transformed_coordinates = transform(inProj, outProj, point.x, point.y)
    return Point(transformed_coordinates)

dat = rasterio.open(r"./data/cph_10x10km_mosaic.tif")
raster_map = dat.read()[0]
def get_elevation(point: Point) -> float:
    """
    Samples elevation value from raster closest to given point
    :point: ETRS89
    """
    idx = dat.index(point.x, point.y, precision=1E-9)    
    return raster_map[idx]

def sample_points_polygon(poly: Polygon, n=10) -> [Point]:
    """
    Uniformly sample n points within a polygon
    """
    min_x, min_y, max_x, max_y = poly.bounds
    points = []
    while len(points) < n:
        random_point = Point([np.random.uniform(min_x, max_x), np.random.uniform(min_y, max_y)])
        if (random_point.within(poly)):
            points.append(random_point)
    return points

def get_median_elevation(poly: Polygon) -> float:
    sample_points = sample_points_polygon(poly, n=30)
    return np.median([get_elevation(p) for p in sample_points])


# --------------------------------------------------------
# --------------------------------------------------------
# [TEMP] Copenhagen: reference locations
# --------------------------------------------------------

# København (Axel Towers)
axel_towers = Point(12.565886448579562, 55.675641285999056)

# København (SAS Radison)
sas_radison = Point(12.563763249599585, 55.675006335236190)

dhm_bbox = transform_bounds(dat.crs, {'init': 'epsg:4326'}, *dat.bounds)
buildings = get_building_geometries(dhm_bbox)
buildings['height'] = buildings.to_crs('epsg:25832').geometry.apply(get_median_elevation)

