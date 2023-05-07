# 🌳 Urban Tree Extraction

The following steps are based on processing a single tile (1km x 1km)

### Generate CHM

Surface model: `./data/DSM_617_72_TIF_UTM32-ETRS89/`
Terrain model:  `./data/DTM_617_72_TIF_UTM32-ETRS89/`

Subtract *DTM*  from *DSM*

### Download areal imagery
Using [andolg/satellite-imagery-downloader](https://github.com/andolg/satellite-imagery-downloader) to download Google Maps or Bing areal tiles.
Tiles are based on the same *top-left* and *bottom-right* bounding box as the DHM tiles, specified in WGS84. 

1. Modify `preferences.json` to contain bounding-box coordinates
   * Use ```zoom = 19``` 
   * Set `out_dir = ./areal_images/`

2. Run `Python main.py`

### Extract Vegetation Mask
Use areal imagery to extract a mask over areas containing vegetation.

This uses the [thiagohersan/maskformer-satellite-trees](https://huggingface.co/thiagohersan/maskformer-satellite-trees) transformer-based model (~500mb) to label segments. 

1. Run `./transformer_areal.py`  (IPython session) providing the path to an image tile (`fn`) and its bounding-box in *web mercator* (EPSG:900913)
2. Will export merged raster (incl. projection metadata) as `./*_mask.tif`

### Clip CHM raster with mask

1. Run `./chm_masking.py`  (IPython session) providing the `*_mask.tif` from the precious step. 

This will first generate shapefile/geoJSON for the mask. This is then loaded and transformed to the same CRS as the CHM, then clipped. 

The output will be `./*_masked.tif` containing the clipped CHM (i.e. only areas with vegetation)

### Detect individual trees
Uses [lidR](https://r-lidar.github.io/lidRbook/) R package to extract tree canopies. 

Needs the following packages
* lidR
* sf
* raster
* terra

**Example**
```
# load the CHM raster
chm <- raster("./*_masked.tif")

# Smoothing
# kernel <- matrix(1,3,3)
# chm_smooth <- terra::focal(chm, w = kernel, fun = median, na.rm = TRUE)

tops <- locate_trees(chm, lmf(20))

# write tops to GeoJSON file
tops_sf <- st_as_sf(tops)
st_write(tops_sf, "./*_tops.geojson", driver = "GeoJSON")
### Detect individual trees
Uses [lidR](https://r-lidar.github.io/lidRbook/) R package to extract tree canopies. 

```


### Corrections
Ad-hoc steps applied in QGIS for smoothing, intersecting, visualisation etc.
