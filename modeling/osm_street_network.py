
import numpy as np
import pandas as pd
import geopandas as gpd
from geopandas import GeoDataFrame
from shapely.geometry import Polygon, Point, LineString, MultiLineString
from shapely.prepared import PreparedGeometry, prep
from shapely.ops import unary_union, union
import networkx as nx
import osmnx as ox
from rtree import index

# --------------------------------------------------------
# Fetch street network from OSM
# --------------------------------------------------------

# axel_towers = Point(12.565886448579562, 55.675641285999056)
# G_walk = ox.graph_from_point((axel_towers.y, axel_towers.x), dist=600, network_type='walk', retain_all=True)
# G_sidewalk = ox.graph_from_point((axel_towers.y, axel_towers.x), dist=600, custom_filter='["sidewalk"]')

G_walk = ox.graph_from_bbox(*dhm_bbox, network_type='walk', retain_all=True)
G_sidewalk = ox.graph_from_bbox(*dhm_bbox, custom_filter='["sidewalk"]')
G_full = nx.compose(G_walk, G_sidewalk)
G = G_full

# --------------------------------------------------------
# Shade coverage
# --------------------------------------------------------

def get_shadow_coverage(segment: LineString, shadow: Polygon) -> float:
    """
    Calculates the total length of a LineString that is covered by
    an overlying polygon. 

    OBS: If the desired unit is meters, make sure the geometries 
    are in an appropriate CRS.
    """
    intersection = segment.intersection(shadow)

    shadow_length = 0
    if isinstance(intersection, LineString):
        shadow_length += intersection.length
    elif isinstance(intersection, MultiLineString):
        for line in intersection:
            shadow_length += line.length

    return shadow_length


shadow_polygon = unary_union(shadows.to_crs('epsg:25832')['geometry'])

_, lines = ox.graph_to_gdfs(G, edges=True)
sidewalks = lines

sidewalks['length'] = sidewalks \
        .to_crs('epsg:25832') \
        .apply(lambda x: x['geometry'].length, 1)

sidewalks['meters_covered'] = sidewalks \
        .to_crs('epsg:25832')['geometry'] \
        .apply(lambda x: get_shadow_coverage(x, shadow_polygon))

sidewalks['percent_covered'] = sidewalks \
        .apply(lambda x: x['meters_covered']/x['length'], 1)

# --------------------------------------------------------
# kepler.gl plotting utils
# --------------------------------------------------------

def extract_line_segments(segments: LineString) -> [Point]:
    points = [list(p) for p in segments.coords]
    return [source+target for source, target in zip(points, points[1:])]

def faltten_sidewalk_segments(sidewalks: GeoDataFrame) -> GeoDataFrame:
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


sidewalks_plot = faltten_sidewalk_segments(sidewalks)

# This is just for keplr.gl
# (it only shows the first 4 fields in the preview box :)
sidewalks_plot = sidewalks_plot[['osmid', 'meters_covered', 'percent_covered', 
    's_lng', 's_lat', 't_lng', 't_lat', 'geometry']]


