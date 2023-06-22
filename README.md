# Shade Gaps in Copenhagen Bicycle Network
This repository contains the code for identifying shade gaps along the bicycle network of Copenhagen. <br>
The resources are provided as-is and documentation is mostly provided through exemplary notebooks (see `/experiments`). <br>
<br>
Feel free to send a message for further information :)

## Data

| Filename | Description           | Link                |
|----------|-----------------------|-------------------------|
| rides.geojson | Origin-Distination pairs of rentable e-bikes in Copenhagen (TIER). <br> The dataset contains records of rides over a 3 month period in the spring of 2023. | [⬇ Download](https://www.dropbox.com/s/cj1tav4oa22wsrk/rides.geojson?dl=1) |
| trees.geojson | Contains all extracted trees incl. crown radius and height. | [⬇ Download](https://www.dropbox.com/s/ow2c0ozrkbdp82y/trees_CPH.geojson?dl=1) |
| network_simple_norm_traffic.geojson | Simplified bicycle network (OSM) with normalised traffic attribute for segments | [⬇ Download](https://www.dropbox.com/s/bg7i0hmrr0jnne7/network_simple_norm_traffic.geojson?dl=1) |


All other data is available through their original sources: <br>
[Dataforsyningen (LiDAR point clouds and elevation rasters)](https://dataforsyningen.dk/data/926) <br>
[OpenStreetMap (bicycle network and building footprints)](https://www.openstreetmap.org/#map=6/62.994/17.637) <br>

## File tree overview for input data
```
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
```

## Utilities

### Extracting Geometries
Buildings are modeled using the exsisting 2D footprints from OpenStreetMap (OSM) as a base. Since data on building heights is scarce in OSM, we extract them manually. With high-precision elevation maps based on LIDAR scans [(Danmarks Højdemodel - DHM)](https://kortviseren.dk/side/hoejdemodeller.html), we sample the surface elevation for areas overlaid by the building outlines, using the median value as the definitive height for the entire geometry. 

   `setup.py`: works in two modes - *geometries*, the default one, and *shadows*. \
    *Geometries* mode preprocesses specific for working with tiled raster data from [DHM](https://dataforsyningen.dk/data/930) (GeoTIFF) and fetches building geometries from OSM. It estimates buildings height based on local GeoTIFF rasters encoding elevation. It also fetches OSM data and builds a graph representation for routing and retrieves tree models  from [kommunale-traeer dataset](https://www.opendata.dk/city-of-copenhagen/trae-basis-kommunale-traeer).\
    *Shadows* mode generates shadow geometries given extruded 3D geometries, location and timestamp using [pybdshadow](https://github.com/ni1o1/pybdshadow). It allows you to save shade data for later use or analysis purposes.
    
### Shadow Projection, Routing & Visualisation
   `main.py`: generates shadow geometries for a given time and calculates edge weights based on shadow-overlap. Looks for the shortest path between point A and B, using obtained shadow data and preference in avoiding the direct sunlight. Passes GeoDataFrames as sources for a kepler.gl map instance. All plotting properties for layer (color, base map etc.) are defined in `visualization/keplergl_config.json`
   
    
### Demo
![Building shadows central CPH](./misc/demo_gif.gif)

