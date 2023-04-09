
import mercantile
import rasterio
import pyproj
from pyproj import Transformer
from shapely.geometry import box

# ----------------------------------------------
# Get MERCANTILE bounds (Strava)
# ----------------------------------------------

zoom = 14
x = 8763
y = 5126

tile_bounds = mercantile.bounds(x, y, zoom)
print(f"West: {tile_bounds[0]}, South: {tile_bounds[1]}, East: {tile_bounds[2]}, North: {tile_bounds[3]}")

# ----------------------------------------------
# Get WGS84 bounds from DHM (REF89)
# ----------------------------------------------

def get_tile_bounds(bbox, src_crs='epsg:25832', dst_crs='epsg:4326'):
    transformer = pyproj.Transformer.from_crs(src_crs, dst_crs)

    x_min, y_min, x_max, y_max = bbox
    x_origin, y_origin = transformer.transform(x_min, y_max)
    x_dest, y_dest = transformer.transform(x_max, y_min)

    p_bbox = (x_origin, y_origin, x_dest, y_dest)
    print(p_bbox)

    return p_bbox


# ⭐ Usage
# -----------------------------------------------
with rasterio.open('../data/DHM/vesterbro.tif') as src:
    chm = src.read(1)

bbox = src.bounds
get_tile_bounds(bbox)


# ----------------------------------------------
# WSG84 to REF89
# ----------------------------------------------


def get_ref89(coords: tuple, src_crs='epsg:4326', dst_crs='epsg:25832'):
    transformer = pyproj.Transformer.from_crs(src_crs, dst_crs)
    x_origin, y_origin = transformer.transform(coords[0], coords[1])
    return(x_origin, y_origin)


# ⭐ Usage
# -----------------------------------------------
coords = (55.67430834867186, 12.558920726892632)
get_ref89(coords)

# bb = (723000.0, 6175000.0, 724000.0, 6176000.0)
# coords = (bb[0], bb[1])
# coords = (bb[2], bb[2])
# get_ref89(coords, src_crs='epsg:25832', dst_crs='epsg:900913')



# ----------------------------------------------
# Create CHM raster
# ----------------------------------------------

def make_chm(dtm_path, dsm_path, out_path):
    with rasterio.open(dtm_path) as src:
        dtm = src.read(1)
        dtm_meta = src.meta
        dtm_bounds = src.bounds

    with rasterio.open(dsm_path) as src:
        dsm = src.read(1)

    chm = dsm - dtm

    with rasterio.open(out_path, 'w', **dtm_meta) as dst:
        dst.write(chm, 1)

# ⭐ Usage
# -----------------------------------------------
F_DTM = '../data/DHM/DTM_617_72_TIF_UTM32-ETRS89/DTM_1km_6175_723.tif'
F_DSM = '../data/DHM/DSM_617_72_TIF_UTM32-ETRS89/DSM_1km_6175_723.tif'
F_CHM = '../data/DHM/vesterbro.tif'

make_chm(F_DTM, F_DSM, F_CHM)

# ----------------------------------------------
# Transform raster to web mercator
# ----------------------------------------------

import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import pyproj

# Define the source and target coordinate reference systems
src_crs = 'EPSG:25832'
dst_crs = 'EPSG:900913'

path = '../data/DHM/vesterbro.tif'
with rasterio.open(path) as src:
    # Calculate the transformation parameters to convert the source to the target CRS
    transform, width, height = calculate_default_transform(
        src_crs, dst_crs, src.width, src.height, *src.bounds
    )
    kwargs = src.meta.copy()
    kwargs.update({
        'crs': dst_crs,
        'transform': transform,
        'width': width,
        'height': height
    })
    
    # Reproject the source raster into the target CRS and write it to a new raster file
    with rasterio.open("../data/DHM/vesterbro_project.tif", "w", **kwargs) as dst:
        for i in range(1, src.count + 1):
            reproject(
                source=rasterio.band(src, i),
                destination=rasterio.band(dst, i),
                src_transform=src.transform,
                src_crs=src_crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest
            )



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





