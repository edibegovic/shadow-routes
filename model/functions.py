import os
import geopandas as gpd
from geopandas import GeoDataFrame
import glob
import json
from keplergl import KeplerGl
import numpy as np
import osmnx as ox
import pandas as pd
import pybdshadow
import pyproj
import rasterio
from rasterio.merge import merge
from rasterio.plot import show
from rasterio.warp import calculate_default_transform, reproject, Resampling, transform_bounds
import re
import shapely
from shapely.geometry import Point, Polygon

# --------------------------------------------------------
# Utils
# --------------------------------------------------------

def to_wgs84(point: Point, reverse=False) -> Point:
    """
    Projects points between ETRS89 and WGS84
    """
    projections = (pyproj.Proj('epsg:25832'), 
                   pyproj.Proj('epsg:4326'))
    inProj, outProj = reversed(projections) if reverse else projections
    transformed_coordinates = pyproj.transform(inProj, outProj, point.x, point.y)
    return Point(transformed_coordinates)

def get_shadows(gdf: GeoDataFrame):
    date = pd.to_datetime('2022-10-21 14:45:33.95979')\
        .tz_localize('Europe/Copenhagen')\
        .tz_convert('UTC')

    gdf['building_id'] = gdf.index 
    shadows = pybdshadow.bdshadow_sunlight(gdf, date)
    shadows = shadows.set_crs('epsg:4326')
    return shadows

def get_tree_shadows(gdf: GeoDataFrame):
    date = pd.to_datetime('2022-10-21 14:45:33.95979')\
        .tz_localize('Europe/Copenhagen')\
        .tz_convert('UTC')

    gdf['building_id'] = gdf.index 
    shadows = pybdshadow.bdshadow_sunlight(gdf, date)

    gdf['height'] = 2
    subtract = pybdshadow.bdshadow_sunlight(gdf, date)
    shadows = shadows.difference(subtract)
    
    shadows = shadows.set_crs('epsg:4326')
    return shadows

# --------------------------------------------------------
# Surface data processing
# --------------------------------------------------------

def merge_geotiff(dirpath, search_criteria):
    q = os.path.join(dirpath, search_criteria)

    tif_fps = glob.glob(q)
    files_mosaic = [rasterio.open(fp) for fp in tif_fps]
    mosaic, out_trans = merge(files_mosaic) # adjust output resolution

    src = rasterio.open(tif_fps[-1])
    out_meta = files_mosaic[0].meta.copy()
    out_meta.update({"driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans,
        }
    )

    return mosaic, out_meta

def load_terrain():
    dsm_mosaic, dsm_meta = merge_geotiff(r"./data/DHM/DSM_617_72_TIF_UTM32-ETRS89",  "DSM*.tif")
    dtm_mosaic, dtm_meta = merge_geotiff(r"./data/DHM/DTM_617_72_TIF_UTM32-ETRS89",  "DTM*.tif")
    if dsm_meta == dtm_meta:
        mosaic = dsm_mosaic - dtm_mosaic
        out_meta = dsm_meta
        out_fp = r"./data/cph_10x10km_mosaic.tif"
        with rasterio.open(out_fp, "w", **out_meta) as dest:
            dest.write(mosaic)
        # show(mosaic)
    else:
        raise Exception("Unmatching metadata of subtracted files")

# --------------------------------------------------------
# Trees data processing
# --------------------------------------------------------

def get_tree_geometries(poi):
    trees = gpd.read_file("data/tree_basiss.json")
    tree = trees[['geometry']].copy()
    tree['lat'] = tree.geometry.y
    tree['lon'] = tree.geometry.x
    tree = tree.to_crs(crs=3857)

    # buffer

    d = {'name': ['poi'], 'geometry': [poi]}
    boundary = gpd.GeoDataFrame(d, crs="EPSG:4326").to_crs(crs=3857)
    boundary['geometry'] = boundary['geometry'].buffer(1000)

    tree = tree.overlay(boundary, how="intersection")
    tree['geometry'] = tree['geometry'].buffer(5)
    tree['height'] = 6

    return tree.to_crs(crs="EPSG:4326")

# --------------------------------------------------------
# Buildings geometries data processing
# --------------------------------------------------------

# Some questionable data wrangling going on here..
def extract_building_polygons(building: Polygon) -> Polygon:
    """
    This is a work-around bacause of a syntax mistake in the WKT strings
    returned by osmnx. Extracts all polygons from a single "polygon string"
    from OSM objects tagged 'bulding:part'.

    :building: osmnx multi-polygon representation (either WKT string or Shapely object)
    :return: list of polygons
    """
    wkt_strings = re.findall(r'\(+(.*?)\)', str(building))
    building_polygons = [shapely.wkt.loads(f'POLYGON(({x}))') for x in wkt_strings]
    return building_polygons

def flatten_building_parts(buildings: GeoDataFrame) -> GeoDataFrame:
    """
    Takes a GeoDataFrame of building geometries consisting of multiple
    parts as multi-polygons. Returns a flattend GeoDataFrame with a row
    for each individual building part.
    """
    return buildings.geometry \
            .apply(extract_building_polygons) \
            .explode() \
            .to_frame() \
            .set_geometry('geometry')

def get_building_geometries(_from: Point, radius: int) -> GeoDataFrame:
    """
    Get all building footprints from an area given a point and 
    radius.

    :_from: Point (WGS84 coordinates)
    :radius: radius from point (meters)
    :return: GeoDataFrame containing building geometries
    """

    tags = {"building": True}
    buildings = ox.geometries_from_point((_from.y, _from.x), tags=tags, dist=radius)
    filter_building_type = lambda gdf, _type: gdf[gdf.index.get_level_values('element_type') == _type]

    buildings_whole = filter_building_type(buildings, 'way')
    building_parts = filter_building_type(buildings, 'relation')

    gdf =  pd.concat([
        flatten_building_parts(building_parts), 
        GeoDataFrame(buildings_whole['geometry'])
        ]).set_crs('epsg:4326')

    gdf = gdf.dissolve(by='osmid', aggfunc='max')

    return gdf


# --------------------------------------------------------
# Elevation
# --------------------------------------------------------

def get_elevation(point: Point, mosaic, raster_map) -> float:
    """
    Samples elevation value from raster closest to given point
    :point: ETRS89
    """
    idx = mosaic.index(point.x, point.y, precision=1E-9) 
    return raster_map[idx]

def sample_points_polygon(poly: Polygon, n=10) -> Point:
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

def get_median_elevation(poly: Polygon, mosaic, raster_map) -> float:
    sample_points = sample_points_polygon(poly, n=30)
    return np.median([get_elevation(p, mosaic, raster_map) for p in sample_points])

def get_geometries_for_poi(poi_coords):
    # mosaic = rasterio.open(r"./data/cph_10x10km_mosaic.tif")
    # raster_map = mosaic.read()[0]

    poi = Point(poi_coords[0], poi_coords[1])

    # buildings = get_building_geometries(poi, 500)
    # buildings['height'] = buildings.to_crs('epsg:25832').geometry.apply(get_median_elevation, args=(mosaic, raster_map))
    # buildings.to_file("data/buildings.geojson", driver="GeoJSON")

    # shadows = get_shadows(buildings)
    # shadows.to_file("data/shadows.geojson", driver="GeoJSON")

    tree = get_tree_geometries(poi)
    tree.to_file("data/tree.geojson", driver="GeoJSON")

    tree_shadows = get_tree_shadows(tree)
    tree_shadows.to_file("data/tree_shadows.geojson", driver="GeoJSON")

# --------------------------------------------------------
# Interactive map (using Kepler.gl)
# --------------------------------------------------------

def add_data(_map: KeplerGl, sources):
    """
    This is due to a bug in the latest version on KeplerGL that 
    directly modifies the contents of a provided GeoDataFrame.
    To circumvent this, we instaed provide a copy of the original 
    data source.
    """
    for gdf, name in sources:
        _map.add_data(gdf.copy(), name=name)

def create__html():
    buildings = gpd.read_file("data/buildings.geojson")
    shadows = gpd.read_file("data/shadows.geojson")
    tree = gpd.read_file("data/tree.geojson")
    tree_shadows = gpd.read_file("data/tree_shadows.geojson")

    cph_map = KeplerGl()

    data_sources = [(buildings, 'Buildings'),
                (shadows, 'Shadows'),
                (tree, 'Trees'),
                (tree_shadows, 'Tree shadows'),
                # (path_plot, 'Path'),
                # (sidewalks_plot, 'Sidewalks')
                ]

    with open('./visualisation/keplergl_config.json') as f:
        config = json.load(f)

    add_data(cph_map, data_sources)
    cph_map.config = config
    cph_map.save_to_html(file_name='cph_buildings.html')