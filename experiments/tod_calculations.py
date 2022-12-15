
from model import terrain, geometries, shadows, routing, visualizations
import geopandas as gpd
import pandas as pd
import sys

buildings = gpd.read_file("./data/cph/buildings.geojson")
trees = gpd.read_file("./data/cph/trees.geojson")
sidewalks = gpd.read_file("./data/cph/sidewalks.geojson")

final_sidewalks = None
test = gpd.read_file('./data/backup/stor.geojson')

# -----------------------------------------------
# Caclculate shade covrage for TOD
# -----------------------------------------------

hours = ['{:02d}'.format(num) for num in range(15, 19)]
for i, h in enumerate(hours):
    print(f'NEW HOUR: {h}')
    timestamp = f'2022-07-01 {h}:01:00.00000'
    buildings_shadows = shadows.get_buildings_shadows(buildings, date=timestamp)
    trees_shadows = shadows.get_trees_shadows(trees, date=timestamp)
    all_shadows = pd.concat([buildings_shadows.geometry, trees_shadows.geometry]).reset_index(drop=True)

    sidewalks_weighted = routing.apply_shadow_to_sidewalks(sidewalks, all_shadows)
    sidewalks_weighted_trees = routing.apply_shadow_to_sidewalks(sidewalks, trees_shadows['geometry'])
    sidewalks_weighted['tree_meters'] = sidewalks_weighted_trees['meters_covered']

    if i == 0:
        final_sidewalks = sidewalks_weighted

    final_sidewalks[h] = sidewalks_weighted.apply(lambda x: {'total': x['meters_covered'],
                               'tree': x['tree_meters']
                               }, axis=1)

    final_sidewalks.to_file(f'./data/backup/sidewalks_{"_".join(hours)}.geojson', driver="GeoJSON")

