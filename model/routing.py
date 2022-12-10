from shapely.geometry import Polygon, LineString, MultiLineString, Point
from shapely.ops import unary_union, nearest_points
import networkx as nx
from geopandas import GeoDataFrame
from networkx import Graph
from math import trunc


def get_shadow_coverage(segment: LineString, all_shadow: Polygon) -> float:
    """
    Calculates the total length of a LineString that is covered by
    an overlying polygon. 
    OBS: If the desired unit is meters, make sure the geometries 
    are in an appropriate CRS.
    """
    intersection = segment.intersection(all_shadow)

    shadow_length = 0
    if isinstance(intersection, LineString):
        shadow_length += intersection.length
    elif isinstance(intersection, MultiLineString):
        for line in intersection:
            shadow_length += line.length

    return shadow_length

def apply_shadow_to_sidewalks(all_shadows, sidewalks):
    shadow_polygon = unary_union(all_shadows.to_crs('epsg:25832'))
    sidewalks['length'] = sidewalks \
        .to_crs('epsg:25832') \
        .apply(lambda x: x['geometry'].length, 1)

    sidewalks['meters_covered'] = sidewalks \
            .to_crs('epsg:25832')['geometry'] \
            .apply(lambda x: get_shadow_coverage(x, shadow_polygon))

    sidewalks['percent_covered'] = sidewalks \
            .apply(lambda x: x['meters_covered']/x['length'], 1)

    return sidewalks

def shade_coverage_weight(data, a):
    return (1 - a) * data['length'] + a * (data['length'] - data['meters_covered'])

def route(G: Graph, _from: int, to: int, alpha=1.0) -> GeoDataFrame:
    path = nx.shortest_path(G, _from, to, 
            weight=lambda u, v, d: shade_coverage_weight(d, alpha))

    path_subgraph = nx.subgraph(G, path)
    path_edges = list(path_subgraph.edges())

    edge_data = GeoDataFrame([G.get_edge_data(edge[0], edge[1]) for edge in path_edges], geometry='geometry')
    return edge_data

def get_route(all_shadows, sidewalks, start_point, end_point, alpha=1.0):
    G = nx.from_pandas_edgelist(sidewalks.reset_index(), 'u', 'v', edge_attr=True, edge_key='osmid')
    return route(G, start_point, end_point, alpha)
