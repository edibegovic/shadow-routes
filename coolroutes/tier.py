import importlib
import sys
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
import numpy as np
import networkx as nx

import osmnx as ox
import time
from coolroutes import terrain, geometry, visualization

def read_sqlite_db(db_path: str):
    con = sqlite3.connect(db_path)
    vehicles = pd.read_sql_query("SELECT * from vehicles", con)
    locations = pd.read_sql_query("SELECT * from log", con)
    con.close()
    return (vehicles, locations)

def extract_valid_rides(df, min_distance=500, max_battery_change=10):
    df = df.sort_values(by="timestamp").reset_index(drop=True)

    df.geometry = df.apply(lambda row: LineString([df.iloc[row.name-1].geometry, row.geometry]), axis=1)
    df["length"] = df.geometry.length

    battery_change =  df.iloc[1:].batteryLevel - df[:-1].batteryLevel.values
    df["battery_change"] = battery_change

    df = df[df.length > min_distance]
    df = df[df.battery_change < max_battery_change]
    return df

def save_rides():
    _, locations = read_sqlite_db("./data/tier/tier_cph.db")
    records = gpd.GeoDataFrame(locations, geometry=gpd.points_from_xy(locations.lng, locations.lat), crs=4326)
    unique_bike_ids = list(set(records.internal_id))

    records_mercator = records.to_crs(25832)

    rides = pd.DataFrame()
    for bike_id in unique_bike_ids:
        bike_records = records_mercator[records_mercator.internal_id == bike_id]
        bike_rides = extract_valid_rides(bike_records)
        rides = pd.concat([rides, bike_rides])

    base_point = Point(707075.1489904693, 6171947.488004295)
    rides = rides[rides.geometry.distance(base_point) > 1000]

    rides = rides.to_crs(4326)
    rides = rides[["timestamp", "geometry"]]
    rides.to_file("./model/rides.geojson", driver="GeoJSON")