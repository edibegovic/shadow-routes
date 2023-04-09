
from skimage.filters import threshold_otsu
import rasterio
import pyproj
from shapely.geometry import box
from shapely.ops import transform
import osmnx as ox
from rasterio.features import rasterize, geometry_mask
from rasterio.warp import calculate_default_transform, reproject, transform_bounds, Resampling
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

# ----------------------------------------------
# Generate mask shapefile
# ----------------------------------------------

import rasterio.features
import fiona
from shapely.geometry import shape

with rasterio.open('../data/DHM/vesterbro_mask.tif') as src:
    veg_mask = src.read(1)
    veg_meta = src.meta

# invert the mask as numpy array (1 = veg, 0 = no veg)
# veg_mask = 1 - veg_mask
    
shapes = list(rasterio.features.shapes(veg_mask, transform=veg_meta['transform']))

schema = {'geometry': 'Polygon', 'properties': {}}
crs = veg_meta['crs']
with fiona.open('vesterbro_mask.geojson', 'w', driver='GeoJSON', crs=crs, schema=schema) as dst:
    for shp, val in shapes[:-1]:
        geom = shape(shp).buffer(0)
        feature = {'geometry': geom.__geo_interface__, 'properties': {}}
        dst.write(feature)
        
# ----------------------------------------------
# Subtract vegetation mask from CHM raster
# ----------------------------------------------

import rasterio
from rasterio.mask import mask
import geopandas as gpd

chm = rasterio.open('../data/DHM/vesterbro.tif')

# Open the vegetation mask file and extract its geometry
mask_gdf = gpd.read_file('../data/DHM/vesterbro_mask.geojson')
mask_geom = mask_gdf.to_crs('epsg:25832').geometry
mask_geom = mask_geom[:-1]

# Mask the CHM raster with the vegetation mask
masked_chm, out_transform = mask(chm, mask_geom, crop=True, all_touched=True, invert=False, nodata=0)

# Cut everything below 1.5m in the masked CHM raster
masked_chm[masked_chm < 1.5] = 0

# Read tops.geojson file
tops = gpd.read_file('../data/DHM/tops.geojson')
tops.set_crs('epsg:25832', allow_override=True, inplace=True)


# plot the og chm, the masked chm and mask_gdf, 
fig, ax = plt.subplots(1, 3, figsize=(15, 5))
ax[0].imshow(chm.read(1), cmap='terrain')
ax[1].imshow(masked_chm[0], cmap='terrain')
mask_gdf.plot(ax=ax[2], facecolor='red', edgecolor='black')
plt.show()

# Export the masked CHM raster
# -----------------------------------------------
out_meta = chm.meta.copy()
out_meta.update({"driver": "GTiff",
                "height": masked_chm.shape[1],
                "width": masked_chm.shape[2],
                "transform": out_transform})

with rasterio.open("../data/DHM/vesterbro_masked.tif", "w", **out_meta) as dest:
    dest.write(masked_chm)






