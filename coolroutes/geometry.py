import math
import pybdshadow
import geopandas as gpd
import shapely
from shapely import affinity
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import unary_union
import numpy as np
import pandas as pd
import networkx as nx
import rasterio
from rtree import index
from suncalc import get_position
import osmnx as ox
import googlemaps
import datetime
import pathlib
import os

ROOT_DIR = os.path.dirname(__file__)

class Geometry(object):
    def __init__(self, bbox=None):
        if bbox:
            self.bbox = bbox
        else:
            self.bbox = {
                "y_min" : 55.62141308805854, 
                "y_max" : 55.715722643196166, 
                "x_max" : 12.661448679631935, 
                "x_min" : 12.494584296105629,
             } # greater Copenhagen
        # else:
        #     self.bbox = {
        #         "y_min" :55.67510033526866, 
        #         "y_max" : 55.68521434273881, 
        #         "x_max" : 12.579297227774566, 
        #         "x_min" : 12.564148112833434,
        #      } # small Copenhagen
        self.crs = 4326
        self.gdf = None
        self.path = None

    def get_sun_position(self, date):
        lon1, lat1, lon2, lat2  = self.gdf.bounds.mean()
        lon = (lon1+lon2)/2
        lat = (lat1+lat2)/2
        sun_position = get_position(date, lon, lat)
        if (sun_position['altitude']<0):
            raise ValueError("Given time before sunrise or after sunset")
        self.azimuth = sun_position["azimuth"]
        self.altitude = sun_position["altitude"]

    def save_geojson(self, path = None):
        path = path if path else self.path
        self.gdf.to_file(ROOT_DIR+path, driver="GeoJSON")
        
    def load_geojson(self):
        self.gdf = gpd.read_file(ROOT_DIR+self.path)
        return self

class Trees(Geometry):
    def __init__(self, bbox=None):
        super().__init__(bbox)
        self.path = "/../model/trees.geojson"

    def load_municipality_dataset(self, in_path="data/tree_basiss.json"):
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

        gdf["height"] = np.random.randint(15, 60, gdf.shape[0])/10
        gdf["crown_radius"] = np.random.randint(2, 6, gdf.shape[0])
        gdf["crown_ratio"] = np.random.randint(4, 6, gdf.shape[0])/10
        gdf["geometry"] = gdf.apply(lambda row: row.geometry.buffer(row.crown_radius), axis=1)
        
        self.gdf = gdf[["geometry", "height", "crown_ratio", "crown_radius"]].to_crs(epsg=self.crs)
        return self
    
    def load_extraction_dataset(self, in_path=""):
        pass

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
        self.get_sun_position(date)
        trees_mercator = self.gdf.to_crs(epsg=3857)
        shadows_geom = trees_mercator.apply(lambda row: self.tree_shade(row), axis=1)
        shadows_gdf = gpd.GeoDataFrame(
            crs='epsg:3857', 
            geometry=gpd.GeoSeries(shadows_geom)
            ).to_crs(epsg=self.crs)
        return shadows_gdf

class Buildings(Geometry):
    def __init__(self, bbox=None):
        super().__init__(bbox)
        self.path = "/../model/buildings.geojson"

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

    def load_osm(self):
        tags = {"building": True}
        gdf = ox.geometries.geometries_from_bbox(*self.bbox.values(), tags=tags)
        gdf = gdf.reset_index()[["osmid", "geometry"]].set_index("osmid")

        self.CHM_data = rasterio.open("./data/GeoTIFF/CHM.tif")
        gdf["height"] = gdf.apply(self.get_buildings_elevation, axis=1)
    
        self.crs = gdf.crs
        self.gdf = gdf
        return self

    def get_shadows(self, date):
        gdf_copy = self.gdf.copy()
        gdf_copy['building_id'] = gdf_copy.index 
        shadows = pybdshadow.bdshadow_sunlight(gdf_copy, date)
        shadows = shadows.set_crs(crs=self.crs)
        return shadows

class Network(Geometry):
    def __init__(self, bbox=None):
        super().__init__(bbox)
        self.path = r"/../model/bike_network.geojson"

    def load_osm(self):
        bbox = (self.bbox["y_max"],
            self.bbox["y_min"],
            self.bbox["x_max"],
            self.bbox["x_min"],
            )
        
        G_bike = ox.graph_from_bbox(
            *bbox,
            network_type='bike',
            retain_all=True,
            simplify=False)
        
        G_walk = ox.graph_from_bbox(
            *bbox,
            network_type='walk',
            custom_filter='["highway"~"footway|unclassified|pedestrian|living_street|service|path"]',
            retain_all=True,
            simplify=False)
        
        G_car = ox.graph_from_bbox(
            *bbox, 
            network_type='drive',
            retain_all=True,
            simplify=False)
        
        G = nx.compose(G_bike, G_walk)
        G = nx.compose(G, G_car)

        # filter to only public roads connected into giant connected component
        access_restricted = ["no", "private", "permit", "delivery", "destination", "customers"]
        selected_edges = [(u, v, d) for u, v, d in G.edges(data=True) if ("access" in d and not d["access"] in access_restricted) or ("access" not in d)]
        G_filtered = nx.Graph(selected_edges)
        G_filtered = nx.subgraph(G_filtered, list(nx.connected_components(G_filtered))[0])
        G = nx.subgraph(G, G_filtered.nodes())

        _, lines = ox.graph_to_gdfs(G, edges=True)
        lines = lines.reset_index()
        lines = lines[["u", "v", "osmid", "geometry"]]

        lines_mercator = lines.to_crs(25832)
        lines_mercator["length"] = lines_mercator.apply(lambda row: row['geometry'].length + 0.01, axis=1)

        self.gdf = lines_mercator.to_crs(self.crs)
        return self
    
    def get_shortest_route(self, start_point, end_point):
        G = nx.from_pandas_edgelist(self.gdf, 'u', 'v', edge_attr=True, edge_key='osmid')
        start_point, _ = min(G.edges(), key=lambda n: G.edges[n]['geometry'].distance(start_point))
        end_point, _ = min(G.edges(), key=lambda n: G.edges[n]['geometry'].distance(end_point))
        path = nx.shortest_path(G, start_point, end_point, weight=lambda u, v, d: d["length"])

        path_subgraph = nx.subgraph(G, path)
        path_edges = list(path_subgraph.edges())
        path_gdf = gpd.GeoDataFrame([G.get_edge_data(edge[0], edge[1]) for edge in path_edges], geometry='geometry', crs=self.crs)
        return path_gdf
    
    def get_google_route(self, start_point, end_point):
        with open("./data/googlemaps_API") as f:
            API_key = f.readline()
        gmaps = googlemaps.Client(key=API_key)

        route = gmaps.directions((start_point.y, start_point.x), (end_point.y, end_point.x), \
                                mode='bicycling', 
                                departure_time=datetime.now())[0]

        legs = route['legs'][0]['steps']
        coords = [googlemaps.convert.decode_polyline(leg['polyline']['points']) for leg in legs]
        coords = [coord for sublist in coords for coord in sublist]  # flatten coords
        coords = [(coord['lng'], coord['lat']) for coord in coords]  
        route = LineString(coords)
        route = gpd.GeoDataFrame(geometry=[route], crs='epsg:4326')
        return route
