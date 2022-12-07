
import numpy as np
import pandas as pd
import geopandas as gpd
from geopandas import GeoDataFrame
from shapely.geometry import Polygon, Point, LineString, MultiLineString
from shapely.ops import unary_union
import networkx as nx
import osmnx as ox
from networkx import Graph
from itertools import combinations
import random

def shade_coverage_weight(data, a):
    return (1 - a) * data['length'] + a * (data['length'] - data['meters_covered'])

def route(G: Graph, _from: int, to: int, alpha=1.0) -> GeoDataFrame:
    path = nx.shortest_path(G, _from, to, 
            weight=lambda u, v, d: shade_coverage_weight(d, alpha))

    path_subgraph = nx.subgraph(G, path)
    path_edges = list(path_subgraph.edges())
    edge_data = GeoDataFrame([G.get_edge_data(edge[0], edge[1]) for edge in path_edges], geometry='geometry')

    l = edge_data['length'].sum()
    m_c = edge_data['meters_covered'].sum()
    p_c = m_c/l

    return p_c, l, edge_data
    return edge_data

G = nx.from_pandas_edgelist(sidewalks.reset_index(), 'u', 'v', edge_attr=True, edge_key='osmid')

route_gdf = route(G, 8118496, 10033485130, alpha=1.0)
path_plot = faltten_sidewalk_segments(route_gdf)
