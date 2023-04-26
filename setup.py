from coolroutes import terrain, geometry, visualization
import time

# tree structure for input files
# .
# └── data/
#     ├── DHM/
#     │   ├── DSM_617_72_TIF_UTM32-ETRS89/
#     │   │   ├── DSM_1km_<id>.tif
#     │   │   └── ...
#     │   └── DTM_617_72_TIF_UTM32-ETRS89/
#     │       ├── DTM_1km_<id>.tif
#     │       └── ...
#     └── tree_bassis.json

def main():
    t0 = time.time()

    terrain.create_geotiff()
    t1 = time.time()
    print(f"Terrain data loaded in {int(t1-t0)} seconds.")

    geometry.Buildings().load_osm().save_geojson()
    t2 = time.time()
    print(f"Buildings data loaded in {int(t2-t1)} seconds.")

    geometry.Trees().load_municipality_dataset().save_geojson()
    t3 = time.time()
    print(f"Terrain data loaded in {int(t3-t2)} seconds.")

    # loading network data here 

if __name__ == "__main__":
    main()
