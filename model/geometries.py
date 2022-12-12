import numpy as np
import pandas as pd
from geopandas import GeoDataFrame
import geopandas as gpd
import osmnx as ox
import networkx as nx
import rasterio
from shapely.geometry import Polygon, Point, LineString, MultiPoint
import shapely
import re

# --------------------------------------------------------
# Trees
# --------------------------------------------------------

def save_trees_geojson(bbox, out_path="data/trees.geojson", data_path="data/tree_basiss.json"):
    trees = gpd.read_file(data_path)[['geometry']]
    trees['lat'] = trees.geometry.y
    trees['lon'] = trees.geometry.x
    trees = trees

    boundary_points = [(bbox[2], bbox[0]),  (bbox[3], bbox[0]), (bbox[3], bbox[1]), (bbox[2], bbox[1]), (bbox[2], bbox[0])]
    boundary = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[Polygon(boundary_points)])

    trees = trees.overlay(boundary, how="intersection")
    trees['geometry'] = trees['geometry'].to_crs(crs=3857).buffer(5)
    trees['height'] = 6
    trees.to_crs(crs=4326).to_file(out_path, driver="GeoJSON")
    print(f"Saved to: {out_path}")

# --------------------------------------------------------
# Buildings
# --------------------------------------------------------

def get_elevation(point: Point, surface_data, raster_map) -> float:
    """
    Samples elevation value from raster closest to given point
    :point: ETRS89
    """
    idx = surface_data.index(point.x, point.y, precision=1E-9)    
    if (-1 < idx[0] < raster_map.shape[0]) and (-1 < idx[1] < raster_map.shape[1]):
        return raster_map[idx]
    return 0.0

def sample_points_polygon(poly: Polygon, n=10) -> list[Point]:
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

def get_median_elevation(poly: Polygon, surface_data, raster_map) -> float:
    sample_points = sample_points_polygon(poly, n=30)
    return np.median([get_elevation(p, surface_data, raster_map) for p in sample_points])

def extract_polygons(building: Polygon) -> list[Polygon]:
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

def get_building_geometries(bbox: list[float]) -> GeoDataFrame:
    tags = {"building": True}
    buildings = ox.geometries.geometries_from_bbox(*bbox, tags=tags)
    filter_building_type = lambda gdf, _type: gdf[gdf.index.get_level_values('element_type') == _type]

    buildings_whole = filter_building_type(buildings, 'way')
    building_parts = filter_building_type(buildings, 'relation')

    return pd.concat([
        flatten_building_parts(building_parts), 
        GeoDataFrame(buildings_whole['geometry'])
        ]).set_crs('epsg:4326')

def save_buildings_geojson(bbox, out_path="data/buildings.geojson"):
    buildings = get_building_geometries(bbox)
    surface_data = rasterio.open(r"./data/cph_10x10km_mosaic.tif")
    raster_map = surface_data.read()[0]
    buildings['height'] = buildings.to_crs('epsg:25832').geometry.apply(get_median_elevation, args=(surface_data, raster_map))
    buildings.to_file(out_path, driver="GeoJSON")
    print(f"Saved to: {out_path}")

# --------------------------------------------------------
# Sidewalks
# --------------------------------------------------------

def extract_line_segments(segments: LineString) -> list[Point]:
    points = [list(p) for p in segments.coords]
    return [source+target for source, target in zip(points, points[1:])]

def get_sidewalk_segments(sidewalks: GeoDataFrame) -> GeoDataFrame:
    """
    Flattens a LineString representation of edges, such that there is
    only one pair of source and target points per row. 
    We also add seperate columns for each coordinate (needed for kepler.gl plotting)
    """
    sidewalks = sidewalks.copy()
    crs = sidewalks.crs
    sidewalks['geometry'] = sidewalks['geometry'] \
                            .apply(extract_line_segments)

    sidewalks = sidewalks.explode('geometry')
    sidewalks['geometry'] = sidewalks['geometry'] \
            .apply(lambda x: [(x[0], x[1]), (x[2], x[3])]) \
            .apply(lambda x: LineString(x))

    sidewalks[['s_lng', 's_lat', 't_lng', 't_lat']] = pd.DataFrame(
        sidewalks['geometry'].apply(lambda x: (x.coords[0][0], 
                                               x.coords[0][1], 
                                               x.coords[1][0], 
                                               x.coords[1][1])).to_list(), index=sidewalks.index)

    return GeoDataFrame(sidewalks, geometry='geometry', crs=crs)

def get_sidewalks_network(bbox):
    G_walk = ox.graph_from_bbox(*bbox, network_type='walk', retain_all=True)
    G_sidewalk = ox.graph_from_bbox(*bbox, custom_filter='["sidewalk"]')
    G_full = nx.compose(G_walk, G_sidewalk)
    return G_full

def save_sidewalks_geojson(bbox, out_path="data/sidewalks.geojson"):
    G = get_sidewalks_network(bbox)

    _, lines = ox.graph_to_gdfs(G, edges=True)
    sidewalks = lines[["geometry", "highway"]]
    sidewalks = sidewalks[['geometry']]
    sidewalks.to_file(out_path, driver="GeoJSON")
    print(f"Saved to: {out_path}")
