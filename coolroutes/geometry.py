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

class Geometry(object):
    def __init__(self, bbox=None):
        if bbox:
            self.bbox = bbox
        else:
            self.bbox = (
                55.67510033526866, 
                55.68521434273881, 
                12.579297227774566, 
                12.564148112833434,
                ) # central Copenhagen
        self.crs = 4326
        self.gdf = None

    def save_geojson(self, out_path=None):
        if out_path:
            self.geometry.to_file(out_path, driver="GeoJSON")
            print(f"Saved to: {out_path}")
        else:
            raise Exception("No output path provided!")
    
    def get_geometry(self):
        return self.geometry

    def __get_shadows(self, hour):
        date = pd.to_datetime(date)\
            .tz_localize('Europe/Copenhagen')\
            .tz_convert('UTC')

        gdf_copy = self.gdf.copy()
        gdf_copy['building_id'] = gdf_copy.index 
        shadows = pybdshadow.bdshadow_sunlight(gdf_copy, date)
        shadows = shadows.set_crs('epsg:4326')
        return shadows        

class Trees(Geometry):
    def __init__(self, bbox=None):
        super().__init__(bbox)
        self.load()
    
    def load(self, in_path):
        pass

    def get_shadows(self, hour):
        return super().__get_shadows(hour)

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
        return super().__get_shadows(hour)

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