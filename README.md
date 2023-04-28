# File tree for input datasets
.
└── data/
    └── DHM/
        ├── DSM_617_72_TIF_UTM32-ETRS89/
        │   ├── DSM_1km_id.tif
        │   └── ...
        ├── DTM_617_72_TIF_UTM32-ETRS89/
        │   ├── DTM_1km_id.tif
        │   └── ...
        ├── tier/
        │   └── tier_cph.db
        ├── municipality trees/
        │   └── tree_bassis.json
        └── googlemaps_API


# Shadow Routes
This repository contains the code for the "shadow routes" research project, which aims to discover low-temperature walking routes in a city by incorporating shade data into routing engines.

## Utilities

### Extracting Geometries
Buildings are modeled using the exsisting 2D footprints from OpenStreetMap (OSM) as a base. Since data on building heights is scarce in OSM, we extract them manually. With high-precision elevation maps based on LIDAR scans [(Danmarks Højdemodel - DHM)](https://kortviseren.dk/side/hoejdemodeller.html), we sample the surface elevation for areas overlaid by the building outlines, using the median value as the definitive height for the entire geometry. 

1. `modeling/preprocess_raster_data.py` \
    Preprocessing specific for working with tiled raster data from [DHM](https://dataforsyningen.dk/data/930) (GeoTIFF)
    
2. `modeling/osmnx_map.py` \
    Fetches building geometries from OSM and estimates their height based on local GeoTIFF rasters encoding elevation

3. `modeling/trees.py` \
    Models tree geometries based on the location and estimations of height and crown width\
    (Uses [kommunale-traeer dataset](https://www.opendata.dk/city-of-copenhagen/trae-basis-kommunale-traeer))

3. `modeling/project_shadow.py` \
    Generates shadow geometries given extruded 3D geometries, location and timestamp. See [pybdshadow](https://github.com/ni1o1/pybdshadow)
    
### Street Network & Routing
1. `modeling/osm_street_network.py` \
    Fetches OSM data and builds a graph representation for routing \
    Calculates edge weights based on shadow-overlap
    
### Visualization
1. `visualization/keplergl_plot.py` \
    Passes GeoDataFrames as sources for a kepler.gl map instance \
    Plotting properties for layer (color, base map etc.) are defined in `visualization/keplergl_config.json`
   
    
### Demo
![Building shadows central CPH](./misc/demo_gif.gif)

