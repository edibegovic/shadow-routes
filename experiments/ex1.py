
from model import terrain, geometries, shadows, routing, visualizations
import geopandas as gpd
import pandas as pd
import sys

# Greater Copenhagen
bbox = (55.62141308805854, 
        55.715722643196166, 
        12.661448679631935, 
        12.494584296105629) 


buildings = gpd.read_file("./data/buildings.geojson")
trees = gpd.read_file("./data/trees.geojson")
sidewalks = gpd.read_file("./data/sidewalks.geojson")

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
alpha = 0.7

route = routing.get_route(sidewalks_weighted, start_point, end_point, alpha)
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


