# Shadow Routes
This repository contains the code for the "shadow routes" research project, which aims to discover low-temperature walking routes in a city by incorporating shade data into routing engines.

## Utilities

### Extracting Geometries
Buildings are modeled using the exsisting 2D footprints from OpenStreetMap (OSM) as a base. Since data on building heights is scarce in OSM, we extract them manually. With high-precision elevation maps based on LIDAR scans [(Danmarks Højdemodel - DHM)](https://kortviseren.dk/side/hoejdemodeller.html), we sample the surface elevation for areas overlaid by the building outlines, using the median value as the definitive height for the entire geometry. 

   `setup.py` \
    Work in two modes - *geometries*, the default one, and *shadows*.

    *Geometries* mode preprocesses specific for working with tiled raster data from [DHM](https://dataforsyningen.dk/data/930) (GeoTIFF) and fetches building geometries from OSM. It estimates buildings height based on local GeoTIFF rasters encoding elevation. It also fetches OSM data and builds a graph representation for routing and retrieves tree models  from [kommunale-traeer dataset](https://www.opendata.dk/city-of-copenhagen/trae-basis-kommunale-traeer).

    *Shadows* mode generates shadow geometries given extruded 3D geometries, location and timestamp using [pybdshadow](https://github.com/ni1o1/pybdshadow). It allows you to save shade data for later use or analysis purposes.
    
### Shadow Projection, Routing & Visualisation
   `main.py` \
    Generates shadow geometries for a given time and calculates edge weights based on shadow-overlap. Looks for the shortest path between point A and B, using obtained shadow data and preference in avoiding the direct sunlight. Passes GeoDataFrames as sources for a kepler.gl map instance. All plotting properties for layer (color, base map etc.) are defined in `visualization/keplergl_config.json`
   
    
### Demo
![Building shadows central CPH](./misc/demo_gif.gif)

