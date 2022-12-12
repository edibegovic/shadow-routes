from model import shadows, geometries, routing, visualizations
import geopandas as gpd
import pandas as pd
import random
from functools import reduce

# -----------------------------------------------
# Load data
# -----------------------------------------------
# bbox = (55.68, 55.67, 12.59, 12.58)
# start_point = #random point selection in bbox
# end_point = #random point selection in bbox
alpha = 1.0

buildings = gpd.read_file("./data/buildings.geojson")
trees = gpd.read_file("./data/trees.geojson")
sidewalks = gpd.read_file("./data/sidewalks.geojson")

# -----------------------------------------------
# Project shade
# -----------------------------------------------
timestamp = '2022-10-21 14:30:00.00000'
buildings_shadows = shadows.get_buildings_shadows(buildings, date=timestamp)
trees_shadows = shadows.get_trees_shadows(trees, date=timestamp)
all_shadows = pd.concat([buildings_shadows.geometry, trees_shadows.geometry]).reset_index(drop=True)

# -----------------------------------------------
# Routing
# -----------------------------------------------
sidewalks_weighted = routing.apply_shadow_to_sidewalks(sidewalks, all_shadows)
sidewalk_segments = geometries.get_sidewalk_segments(sidewalks)

start_point = 8491663725
end_point = 1630693019
alpha = 1.0

route = routing.get_route(sidewalks_weighted, start_point, end_point, alpha)
sidewalk_segments = geometries.get_sidewalk_segments(sidewalks)
route_segments = geometries.get_sidewalk_segments(route)

data_sources = [
            (buildings, 'Buildings'),
            (buildings_shadows, 'Shadows'),
            (trees, 'Trees'),
            (trees_shadows, 'Tree shadows'),
            (route_segments, 'Path'),
            (sidewalk_segments, 'Sidewalks')
            ]


visualizations.create_html(data_sources)

