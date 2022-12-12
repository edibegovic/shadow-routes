from model import terrain, geometries, shadows, routing
import geopandas as gpd
import pandas as pd
import sys

def get_terrain():
    terrain.load_terrain()

def get_geometries(bbox):
    geometries.save_buildings_geojson(bbox, path="./data/buildings.geojson")
    geometries.save_trees_geojson(bbox, path="./data/trees.geojson")
    geometries.save_sidewalks_geojson(bbox, path="./data/sidewalks.geojson")

def get_shadows(hour):
    # function to be cleaned
    timestamp = "2022-10-21 " + hour + ":45:33.95979"
    buildings = gpd.read_file("./data/buildings.geojson")
    trees = gpd.read_file("./data/trees.geojson")
    sidewalks = gpd.read_file("./data/sidewalks.geojson")

    buildings_shadows = shadows.get_buildings_shadows(buildings, date=timestamp)
    trees_shadows = shadows.get_trees_shadows(trees, date=timestamp)
    all_shadows = pd.concat([buildings_shadows.geometry, trees_shadows.geometry]).reset_index(drop=True)

    sidewalks_weighted = routing.apply_shadow_to_sidewalks(all_shadows, sidewalks)

    buildings_shadows.to_file("data/buildings_shadows.geojson", driver="GeoJSON")
    trees_shadows.to_file("data/trees_shadows.geojson", driver="GeoJSON")
    sidewalks_weighted.to_file("data/sidewalks_weighted.geojson", driver="GeoJSON")

def main():
    bbox = (55.69468513531616, 55.66707153061302, 12.597097109876165, 12.544356607371874)
    mode = sys.argv[1] if len(sys.argv) > 1 else "geometries"

    if mode == "terrain":
        get_terrain()
    elif mode == "geometries":
        get_geometries(bbox)
    elif mode == "shadows":
        hour = str(sys.argv[2]) if len(sys.argv) > 2 else "14"
        get_shadows(hour)
    else:
        raise Exception("Wrong mode selected")

if __name__ == "__main__":
    main()