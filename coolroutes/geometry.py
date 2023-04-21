import pybdshadow
import geopandas as gpd
import shapely
from shapely.geometry import Polygon, Point, LineString, MultiPoint, MultiLineString
import numpy as np
import pandas as pd
import networkx as nx
import rasterio
from rtree import index
import osmnx as ox
from keplergl import KeplerGl
from shapely.ops import unary_union, nearest_points
from suncalc import get_position
import math
from shapely import affinity
import random

class Geometry(object):
    def __init__(self, bbox=None):
        if bbox:
            self.bbox = bbox
        else:
            self.bbox = {
                "y_min":55.67510033526866, 
                "y_max": 55.68521434273881, 
                "x_max": 12.579297227774566, 
                "x_min": 12.564148112833434,
             } # central Copenhagen
        self.crs = 4326
        self.gdf = None

    def save_geojson(self, out_path=None):
        if out_path:
            self.gdf.to_file(out_path, driver="GeoJSON")
            print(f"Saved to: {out_path}")
        else:
            raise Exception("No output path provided!") 

class Trees(Geometry):
    def __init__(self, bbox=None):
        super().__init__(bbox)

    def load(self, in_path="data/tree_basiss_small.json"):
        gdf = gpd.read_file(in_path)[["geometry", "torso_hoejde"]]
        gdf = gdf[
            (gdf.geometry.x >= self.bbox["x_min"]) &
            (gdf.geometry.x <= self.bbox["x_max"]) &
            (gdf.geometry.y >= self.bbox["y_min"]) &
            (gdf.geometry.y <= self.bbox["y_max"])
        ]

        gdf["height"] = gdf.torso_hoejde.replace(
            {"0-3 meter":1.5, "3 m": 3, "3":3, "3-6 meter":4.5, "over 6 meter": 6}
        ).fillna(4.5)

        gdf = gdf.to_crs(epsg=3857)
        gdf["crown_radius"] = np.random.randint(2, 6, gdf.shape[0])
        gdf["crown_ratio"] = np.random.randint(4, 6, gdf.shape[0])/10
        gdf["geometry"] = gdf.apply(lambda row: row.geometry.buffer(row.crown_radius), axis=1)
        
        self.gdf = gdf[["geometry", "height", "crown_ratio", "crown_radius"]].to_crs(epsg=self.crs)

    def from_file(self, in_path="data/GeoJSON/trees.geojson"):
        self.gdf = gpd.read_file(in_path)

    def inner_tree(self, poly, shrink_factor=0.5):
        xs = list(poly.exterior.coords.xy[0])
        ys = list(poly.exterior.coords.xy[1])
        x_center = 0.5 * min(xs) + 0.5 * max(xs)
        y_center = 0.5 * min(ys) + 0.5 * max(ys)
        min_corner = Point(min(xs), min(ys))
        center = Point(x_center, y_center)
        shrink_distance = center.distance(min_corner)*shrink_factor
        my_polygon_resized = poly.buffer(-shrink_distance)
        return my_polygon_resized
    
    def layer_shade(self, geom, height):
        distance = height/math.tan(self.altitude)
        lon_distance = distance*math.sin(self.azimuth)
        lat_distance = distance*math.cos(self.azimuth)
        shade = affinity.translate(geom, lon_distance, lat_distance)
        return shade
    
    def tree_shade(self, row):
        geom = row.geometry
        height = row.height
        crown_ratio = row.crown_ratio

        inner_tree = self.inner_tree(geom, shrink_factor=0.2)

        l1 = (inner_tree, height)
        l2 = (geom, (1 - crown_ratio/2) * height)
        l3 = (inner_tree, (1-crown_ratio) * height)
        layers = [l1, l2, l3]

        shades = [self.layer_shade(g, h) for g, h in layers]

        trunk = LineString([
            geom.centroid,
            self.layer_shade(geom.centroid, height)
        ]).buffer(0.3)

        shade = shapely.ops.unary_union(shades)
        shade = shade.convex_hull
        shade = shapely.ops.unary_union([shade, trunk])

        return shade


    def get_shadows(self, date, precision=4, details=0.4):
        lon1, lat1, lon2, lat2  = self.gdf.bounds.mean()
        lon = (lon1+lon2)/2
        lat = (lat1+lat2)/2
        sun_position = get_position(date, lon, lat)
        if (sun_position['altitude']<0):
            raise ValueError("Given time before sunrise or after sunset")
        self.azimuth = sun_position["azimuth"]
        self.altitude = sun_position["altitude"]


        trees_mercator = self.gdf.to_crs(epsg=3857)
        shadows_geom = trees_mercator.apply(lambda row: self.tree_shade(row), axis=1)
        shadows_gdf = gpd.GeoDataFrame(
            crs='epsg:3857', 
            geometry=gpd.GeoSeries(shadows_geom)
            ).to_crs(epsg=4326)
        return shadows_gdf

class Buildings(Geometry):
    def __init__(self, bbox=None):
        super().__init__(bbox)
        self.load()

    def get_buildings_elevation(self, poly, n=100):
        minx, miny, maxx, maxy = poly.geometry.bounds
        x = np.random.uniform(minx, maxx, n)
        y = np.random.uniform(miny, maxy, n)

        df = pd.DataFrame()
        df['points'] = list(zip(x,y))
        df['points'] = df['points'].apply(Point)
        gdf_points = gpd.GeoDataFrame(df, geometry='points').set_crs(4326)
        gdf_poly = gpd.GeoDataFrame(geometry=gpd.GeoSeries(poly))
        
        spatial_join = gpd.tools.sjoin(gdf_points, gdf_poly, predicate="within", how='left')
        sample_points = gdf_points[spatial_join.index_right == "geometry"].to_crs(epsg=25832).points.values
        sample_points = [(p.x, p.y) for p in sample_points]
        heights = list(self.CHM_data.sample(sample_points, 1))
        return np.median(heights)

    def load(self):
        tags = {"building": True}
        gdf = ox.geometries.geometries_from_bbox(*self.bbox, tags=tags)
        gdf = gdf.reset_index()[["osmid", "geometry"]].set_index("osmid")

        self.CHM_data = rasterio.open("./data/GeoTIFF/CHM.tif")
        gdf["height"] = gdf.apply(self.get_buildings_elevation, axis=1)
    
        self.crs = gdf.crs
        self.gdf = gdf

    def get_shadows(self, hour):
        pass

class Sidewalks(Geometry):
    def __init__(self, bbox=None):
        super().__init__(bbox)

    def __build_rtree(gdf: gpd.GeoDataFrame):
        idx = index.Index()
        for i, shape in enumerate(gdf):
            idx.insert(i, shape.bounds)
        return idx

    def __get_shadow_coverage(segment: LineString, shadows: gpd.GeoDataFrame, r_tree=None) -> float:
        """
        Calculates the total length of a LineString that is covered by
        an overlying polygon. 
        OBS: If the desired unit is meters, make sure the geometries 
        are in an appropriate CRS.
        """
        if r_tree is not None:
            shadow_ids = list(r_tree.intersection(segment.bounds))
            intersecting_shadows = unary_union(shadows[shadow_ids])
            intersection = segment.intersection(intersecting_shadows)
        else:
            intersection = segment.intersection(shadows)

        shadow_length = 0
        if isinstance(intersection, LineString):
            shadow_length += intersection.length
        elif isinstance(intersection, MultiLineString):
            for line in intersection:
                shadow_length += line.length

        return shadow_length
    
    def __extract_line_segments(segments: LineString) -> list[Point]:
        points = [list(p) for p in segments.coords]
        return [source+target for source, target in zip(points, points[1:])]

    def __shade_coverage_weight(self, data, a):
        return (1 - a) * data['length'] + a * (data['length'] - data['meters_covered'])

    def load(self):
        G_walk = ox.graph_from_bbox(self.bbox, network_type='walk', simplify=False)
        G_sidewalk = ox.graph_from_bbox(self.bbox, custom_filter='["sidewalk"]', simplify=False)
        G_full = nx.compose(G_walk, G_sidewalk)
        G = ox.simplification.simplify_graph(G_full)
        _, lines = ox.graph_to_gdfs(G, edges=True)
        sidewalks = lines[["geometry", "highway"]]
        sidewalks = sidewalks[['geometry']]
        sidewalks['length'] = sidewalks.to_crs('epsg:25832').apply(lambda x: x['geometry'].length + 0.01, 1)
        self.geometry = sidewalks.to_crs(self.crs)

    def update_shadow(self, shadows):
        sidewalks_25832 =  self.geometry.to_crs('epsg:25832')
        shadows_25832 = shadows.to_crs('epsg:25832')

        r_tree_index = self.__build_rtree(shadows_25832)

        self.geometry['meters_covered'] = sidewalks_25832['geometry'] \
                .apply(lambda x: self.__get_shadow_coverage(x, shadows_25832, r_tree_index))

        self.geometry['percent_covered'] = sidewalks_25832 \
                .apply(lambda x: x['meters_covered']/x['length'], 1)

    def get_segments(self):
        """
        Flattens a LineString representation of edges, such that there is
        only one pair of source and target points per row. 
        We also add seperate columns for each coordinate (needed for kepler.gl plotting)
        """
        sidewalks = self.geometry.copy()
        sidewalks['geometry'] = sidewalks['geometry'] \
                                .apply(self.__extract_line_segments)

        sidewalks = sidewalks.explode('geometry')
        sidewalks['geometry'] = sidewalks['geometry'] \
                .apply(lambda x: [(x[0], x[1]), (x[2], x[3])]) \
                .apply(lambda x: LineString(x))

        sidewalks[['s_lng', 's_lat', 't_lng', 't_lat']] = pd.DataFrame(
            sidewalks['geometry'].apply(lambda x: (x.coords[0][0], 
                                                x.coords[0][1], 
                                                x.coords[1][0], 
                                                x.coords[1][1])).to_list(), index=sidewalks.index)

        return gpd.GeoDataFrame(sidewalks, geometry='geometry', crs=self.crs)

    def get_route(self, start_point, end_point, alpha):
        G = nx.from_pandas_edgelist(self.geometry.reset_index(), 'u', 'v', edge_attr=True, edge_key='osmid')
        path = nx.shortest_path(G, start_point, end_point,
                weight=lambda u, v, d: self.__shade_coverage_weight(d, alpha))

        path_subgraph = nx.subgraph(G, path)
        path_edges = list(path_subgraph.edges())

        route = gpd.GeoDataFrame([G.get_edge_data(edge[0], edge[1]) for edge in path_edges], geometry='geometry')

        return route