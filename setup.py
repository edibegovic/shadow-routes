from model import terrain, geometries
# bbox = (55.69468513531616, 55.66707153061302, 12.597097109876165, 12.544356607371874)
bbox = (55.68, 55.67, 12.59, 12.58)

terrain.load_terrain()
geometries.save_buildings_geojson(bbox)
geometries.save_trees_geojson(bbox)
geometries.save_sidewalks_geojson(bbox)