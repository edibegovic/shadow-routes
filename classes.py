from functools import reduce
import geopandas as gpd
import glob
import json
from keplergl import KeplerGl
from math import trunc
import networkx as nx
import numpy as np
import os
import osmnx as ox
import pandas as pd
import pybdshadow
import random
import rasterio
from rasterio.merge import merge
import re
from rtree import index
import shapely
from shapely.geometry import Polygon, Point, LineString, MultiPoint, MultiLineString
from shapely.ops import unary_union, nearest_points

import sys

class Terrain(object):
    def __init__(self):
        pass

    def __merge_geotiff(dirpath, search_criteria):
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

    def load_terrain(self):
        dsm_mosaic, dsm_meta = self.__merge_geotiff(r"./data/DHM/DSM_617_72_TIF_UTM32-ETRS89",  "DSM*.tif")
        dtm_mosaic, dtm_meta = self.__merge_geotiff(r"./data/DHM/DTM_617_72_TIF_UTM32-ETRS89",  "DTM*.tif")
        if dsm_meta == dtm_meta:
            mosaic = dsm_mosaic - dtm_mosaic
            out_meta = dsm_meta
            out_fp = r"./data/cph_10x10km_mosaic.tif"
            with rasterio.open(out_fp, "w", **out_meta) as dest:
                dest.write(mosaic)
        else:
            raise Exception("Unmatching metadata of subtracted files")   

class Geometry(object):
    def __init__(self, bbox):
        self.bbox = bbox
        self.crs = 4326
        self.geometry = None

    def save(self, out_path="data/trees.geojson"):
        self.geometry.to_file(out_path, driver="GeoJSON")
        print(f"Saved to: {out_path}")
    
    def get(self):
        return self.geometry

    def __get_shadows(self, hour):
        date = pd.to_datetime(date)\
            .tz_localize('Europe/Copenhagen')\
            .tz_convert('UTC')

        gdf_copy = self.geometry.copy()
        gdf_copy['building_id'] = gdf_copy.index 
        shadows = pybdshadow.bdshadow_sunlight(gdf_copy, date)
        shadows = shadows.set_crs('epsg:4326')
        return shadows        

class Trees(Geometry):
    def __init__(self, bbox):
        super().__init__(bbox)
    
    def load(self, in_path):
        trees = gpd.read_file(in_path)[['geometry']]
        trees['lat'] = trees.geometry.y
        trees['lon'] = trees.geometry.x

        boundary_points = [
            (self.bbox[2], self.bbox[0]),  
            (self.bbox[3], self.bbox[0]), 
            (self.bbox[3], self.bbox[1]), 
            (self.bbox[2], self.bbox[1]), 
            (self.bbox[2], self.bbox[0]),
            ]

        boundary = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[Polygon(boundary_points)])

        trees = trees.overlay(boundary, how="intersection")
        trees['geometry'] = trees['geometry'].to_crs(crs=3857).buffer(5)
        trees['height'] = 6

        self.geometry = trees.to_crs(crs=self.crs)

    def get_shadows(self, hour):
        return super().__get_shadows(hour)

class Buildings(Geometry):
    def __init__(self, bbox):
        super().__init__(bbox)

    def __sample_points_polygon(self, poly: Polygon, n=10) -> list[Point]:
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

    def __flatten_building_parts(self, buildings: GeoDataFrame) -> GeoDataFrame:
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

    def __get_elevation(self, point: Point) -> float:
        """
        Samples elevation value from raster closest to given point
        :point: ETRS89
        """
        idx = self.surface.index(point.x, point.y, precision=1E-9)    
        if (-1 < idx[0] < self.raster_map.shape[0]) and (-1 < idx[1] < self.raster_map.shape[1]):
            return self.raster_map[idx]
        return 0.0

    def __get_median_elevation(self, poly: Polygon) -> float:
        sample_points = sample_points_polygon(poly, n=30)
        return np.median([get_elevation(p) for p in sample_points])

    def __load_surface_data(self):
        self.surface = rasterio.open(r"./data/cph_10x10km_mosaic.tif")
        self.raster_map = self.surface.read()[0]

    def load(self):
        tags = {"building": True}
        buildings = ox.geometries.geometries_from_bbox(*bbox, tags=tags)
        filter_building_type = lambda gdf, _type: gdf[gdf.index.get_level_values('element_type') == _type]

        buildings_whole = filter_building_type(buildings, 'way')
        building_parts = filter_building_type(buildings, 'relation')

        buildings = pd.concat([
            self.__flatten_building_parts(building_parts), 
            GeoDataFrame(buildings_whole['geometry'])
            ]).set_crs('epsg:4326')

        __load_surface_data()
        buildings['height'] = buildings.to_crs('epsg:25832').geometry.apply(get_median_elevation)
        self.geometry = buildings

    def get_shadows(self, hour):
        return super().__get_shadows(hour)

class Sidewalks(Geometry):
    def __init__(self, bbox):
        super().__init__(bbox)

    def __build_rtree(gdf: GeoDataFrame):
        idx = index.Index()
        for i, shape in enumerate(gdf):
            idx.insert(i, shape.bounds)
        return idx

    def __get_shadow_coverage(segment: LineString, shadows: GeoDataFrame, r_tree=None) -> float:
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
        G_walk = ox.graph_from_bbox(*bbox, network_type='walk', simplify=False)
        G_sidewalk = ox.graph_from_bbox(*bbox, custom_filter='["sidewalk"]', simplify=False)
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
                                .apply(__extract_line_segments)

        sidewalks = sidewalks.explode('geometry')
        sidewalks['geometry'] = sidewalks['geometry'] \
                .apply(lambda x: [(x[0], x[1]), (x[2], x[3])]) \
                .apply(lambda x: LineString(x))

        sidewalks[['s_lng', 's_lat', 't_lng', 't_lat']] = pd.DataFrame(
            sidewalks['geometry'].apply(lambda x: (x.coords[0][0], 
                                                x.coords[0][1], 
                                                x.coords[1][0], 
                                                x.coords[1][1])).to_list(), index=sidewalks.index)

        return GeoDataFrame(sidewalks, geometry='geometry', crs=self.crs)

    def get_route(self, start_point, end_point, alpha):
        G = nx.from_pandas_edgelist(self.geometry.reset_index(), 'u', 'v', edge_attr=True, edge_key='osmid')
        path = nx.shortest_path(G, start_point, end_point,to, 
                weight=lambda u, v, d: self.__shade_coverage_weight(d, alpha))

        path_subgraph = nx.subgraph(G, path)
        path_edges = list(path_subgraph.edges())

        route = GeoDataFrame([G.get_edge_data(edge[0], edge[1]) for edge in path_edges], geometry='geometry')

        return route

class Visualization(object):
    def __init__(self):
        pass

    def add_data(_map: KeplerGl, sources):
        """
        This is due to a bug in the latest version on KeplerGL that 
        directly modifies the contents of a provided GeoDataFrame.
        To circumvent this, we instaed provide a copy of the original 
        data source.
        """
        for gdf, name in sources:
            _map.add_data(gdf.copy(), name=name)

    def create_html(data_sources):
        cph_map = KeplerGl()

        with open('./visualisation/keplergl_config.json') as f:
            config = json.load(f)

        add_data(cph_map, data_sources)
        cph_map.config = config
        cph_map.save_to_html(file_name='cph_buildings.html')