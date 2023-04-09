import importlib
import sys
sys.path.append('../')
from model import shadows, geometries, routing, visualizations

import pandas as pd
import sqlite3
from matplotlib import pyplot as plt
from geopy.distance import geodesic as GD
import geopandas as gpd
from geopandas import GeoDataFrame
from shapely.geometry import Polygon, Point, LineString
from shapely.geometry.multipolygon import MultiPolygon
import googlemaps
from datetime import datetime

# -------------------------------------------
# RELOADING MODULES
# -------------------------------------------
importlib.reload(routing)
importlib.reload(geometries)
importlib.reload(visualizations)
# -------------------------------------------


# -------------------------------------------------------
# Read sqlite query results into a pandas DataFrame
# -------------------------------------------------------

def read_sqlite_db(db_path: str) -> (pd.DataFrame, pd.DataFrame):
    con = sqlite3.connect(db_path)
    vehicles = pd.read_sql_query("SELECT * from vehicles", con)
    locations = pd.read_sql_query("SELECT * from log", con)
    con.close()
    return (vehicles, locations)

_, locations = read_sqlite_db("./data/tier_cph.db")
_, locations = read_sqlite_db("./data/tier_cph_3003.db")

# -------------------------------------------------------
# Extract rides
# -------------------------------------------------------

def appnd_distances(gdf: GeoDataFrame) -> GeoDataFrame:
    """
    Returns GeoDataFrame with with distance column from previous point
    in meters.
    """
    gdf = gdf.sort_values(by="timestamp") \
             .to_crs('epsg:25832')

    gdf['dist'] = gdf.distance(gdf.shift())
    gdf = gdf.to_crs('epsg:4326')
    return gdf

def extrapolate_rides(records: GeoDataFrame, min_dist: float = 500) -> GeoDataFrame:
    """
    Returns GeoDataFrame with extrapolated rides as linestring geometries.
    Filter out rides with under certain distance threshold (meters).

    :records: records from a single bike
    """
    records = appnd_distances(records)
    if records.dist.sum() < 500:
        return [None]
    records = records[(records.dist > min_dist) | (records.dist.isna())]
    if len(records) < 2:
        return [None]
    records['from'] = records.geometry
    records['to'] = records.geometry.shift(-1)
    records = records[:-1]
    records['geometry'] = records.apply(lambda x: LineString([x['from'], x['to']]), 1)
    features = ['internal_id', 'timestamp', 'batteryLevel', 'geometry', 'from', 'to']
    return records[features]

records = gpd.GeoDataFrame(locations, geometry=gpd.points_from_xy(locations.lng, locations.lat), crs='epsg:4326')
unique_bike_ids = list(set(records.internal_id))
unique_bike_ids = range(100)

rides = pd.DataFrame()
for id in unique_bike_ids:
    print(f'Current bike-ID: {id}')
    bike_records = records[records.internal_id == id]
    rides_segment = extrapolate_rides(bike_records)
    if len(rides_segment) < 3:
        continue
    rides = pd.concat([rides, rides_segment])

# -------------------------------------------------------
# Calculate routes: Google directions API
# -------------------------------------------------------

def get_route_google(start_point: Point, end_point: Point) -> LineString:
    gmaps = googlemaps.Client(key='')

    route = gmaps.directions((start_point.y, start_point.x), (end_point.y, end_point.x), \
                            mode='bicycling', \ 
                            departure_time=datetime.now())[0]

    legs = route['legs'][0]['steps']
    coords = [googlemaps.convert.decode_polyline(leg['polyline']['points']) for leg in legs]
    coords = [coord for sublist in coords for coord in sublist]  # flatten coords
    coords = [(coord['lng'], coord['lat']) for coord in coords]  
    route = LineString(coords)
    route = gpd.GeoDataFrame(geometry=[route], crs='epsg:4326')
    return route

# OSM sidewalks network
sidewalks = gpd.read_file("../data/cph/bike_paths.geojson")

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def gdf_to_linestring(gdf: GeoDataFrame, crs: str='epsg:4326') -> LineString:
    gdf = gdf.to_crs(crs)
    gdf = gdf.unary_union
    gdf = gpd.GeoDataFrame(geometry=[gdf], crs=crs)
    return gdf


# -------------------------------------------------------
# Interpolate rides
# -------------------------------------------------------

diffs = []

[float(d) for d in diffs]

for i in range(100):
    i = 8
    curr_ride = rides.iloc[i]
    start_point, end_point = curr_ride['from'], curr_ride['to']

    # OSM
    route = routing.interpolate_route(sidewalks, start_point, end_point)
    route_segments = geometries.get_sidewalk_segments(route)

    # Google
    route_google = get_route_google(start_point, end_point)
    route_segments_google = geometries.get_sidewalk_segments(route_google)

    len_osm = gdf_to_linestring(route, "epsg:25832").length
    len_google = gdf_to_linestring(route_google, "epsg:25832").length

    percentage_diff = (len_google - len_osm) / len_osm * 100
    diffs.append(percentage_diff)



# -------------------------------------------------------
# Plot rides
# -------------------------------------------------------

data_sources = [
            # (buildings, 'Buildings'),
            # (buildings_shadows, 'Shadows'),
            # (trees, 'Trees'),
            # (trees_shadows, 'Tree shadows'),
            (route_segments, 'Path'),
            (route_segments_google, 'Path_google'),
            # (sidewalk_segments, 'Sidewalks')
            ]


visualizations.create_html(data_sources)

# -------------------------------------------------------
# Agreement
# -------------------------------------------------------

from shapely.ops import nearest_points

# calculate distance between segments
distances = segments_osm.geometry.apply(lambda geom: segments_gmaps.geometry.distance(nearest_points(geom, segments_gmaps.geometry)[0]))

# find closest segment(s)
closest_segments = distances.apply(lambda s: list(s.nsmallest(1).index))
