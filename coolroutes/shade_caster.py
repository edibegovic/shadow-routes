import math
import geopandas as gpd
from shapely.geometry import Point, LineString
from shapely import affinity
from suncalc import get_position
import shapely
import datetime
import pybdshadow

def get_sun_position(date, gdf):
    lon1, lat1, lon2, lat2  = gdf.bounds.mean()
    lon = (lon1+lon2)/2
    lat = (lat1+lat2)/2
    sun_position = get_position(date, lon, lat)
    if (sun_position['altitude']<0):
        raise ValueError("Given time before sunrise or after sunset")
    azimuth_p = sun_position["azimuth"]
    altitude_p = sun_position["altitude"]
    return azimuth_p, altitude_p

def inner_tree(poly, shrink_factor=0.5):
    xs = list(poly.exterior.coords.xy[0])
    ys = list(poly.exterior.coords.xy[1])
    x_center = 0.5 * min(xs) + 0.5 * max(xs)
    y_center = 0.5 * min(ys) + 0.5 * max(ys)
    min_corner = Point(min(xs), min(ys))
    center = Point(x_center, y_center)
    shrink_distance = center.distance(min_corner)*shrink_factor
    my_polygon_resized = poly.buffer(-shrink_distance)
    return my_polygon_resized

def layer_shade(geom, height, azimuth, altitude):
    distance = height/math.tan(altitude)
    lon_distance = distance*math.sin(azimuth)
    lat_distance = distance*math.cos(azimuth)
    shade = affinity.translate(geom, lon_distance, lat_distance)
    return shade

def tree_shade(row, azimuth, altitude):
    geom = row.geometry
    height = row.height
    crown_ratio = row.crown_ratio

    inner_tree_g = inner_tree(geom, shrink_factor=0.2)

    l1 = (inner_tree_g, height)
    l2 = (geom, (1 - crown_ratio/2) * height)
    l3 = (inner_tree_g, (1-crown_ratio) * height)
    layers = [l1, l2, l3]

    shades = [layer_shade(g, h, azimuth, altitude) for g, h in layers]

    trunk = LineString([
        geom.centroid,
        layer_shade(geom.centroid, height, azimuth, altitude)
    ]).buffer(0.3)

    shade = shapely.ops.unary_union(shades)
    shade = shade.convex_hull
    shade = shapely.ops.unary_union([shade, trunk])
    return shade

def get_tree_shadows(date, gdf, precision=4, details=0.4):
    sun_pos_gdf = gdf.copy().to_crs(epsg=4326)
    azimuth, altitude = get_sun_position(date, sun_pos_gdf)
    crs = gdf.crs
    trees_mercator = gdf.to_crs(epsg=3857)
    shadows_geom = trees_mercator.apply(lambda row: tree_shade(row, azimuth, altitude), axis=1)
    shadows_gdf = gpd.GeoDataFrame(
        crs='epsg:3857', 
        geometry=gpd.GeoSeries(shadows_geom)
        ).to_crs(crs)
    return shadows_gdf

def get_building_shadows(date, gdf):
    gdf_copy = gdf.copy().to_crs(epsg=4326)
    crs = gdf.crs
    gdf_copy['building_id'] = gdf_copy.index 
    shadows = pybdshadow.bdshadow_sunlight(gdf_copy, date)
    shadows = shadows.set_crs(crs=gdf_copy.crs).to_crs(crs)
    return shadows
