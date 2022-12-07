from model import shadows, geometries, routing, visualizations
import geopandas as gpd
import pandas as pd
import random


start_point = 8491663725
end_point = 1630693019
# bbox = (55.68, 55.67, 12.59, 12.58)
# start_point = #random point selection in bbox
# end_point = #random point selection in bbox
alpha = 1.0

buildings = gpd.read_file("data/buildings.geojson")
trees = gpd.read_file("data/trees.geojson")
sidewalks = gpd.read_file("data/sidewalks.geojson")

buildings_shadows = shadows.get_buildings_shadows(buildings)
trees_shadows = shadows.get_trees_shadows(trees)
all_shadows = pd.concat([buildings_shadows.geometry, trees_shadows.geometry])

route = routing.get_route(all_shadows, sidewalks, start_point, end_point, alpha)
sidewalks = geometries.get_sidewalk_segments(sidewalks)
route = geometries.get_sidewalk_segments(route)

data_sources = [
            (buildings, 'Buildings'),
            (buildings_shadows, 'Shadows'),
            (trees, 'Trees'),
            (trees_shadows, 'Tree shadows'),
            (route, 'Path'),
            (sidewalks, 'Sidewalks')
            ]


visualizations.create_html(data_sources)