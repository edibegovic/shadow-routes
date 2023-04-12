from utils import satellite_imagery
from PIL import Image
import matplotlib.pyplot as plt
from rasterio.transform import from_origin
import numpy as np
import pickle
import os
import rasterio
import pyproj
import rasterio.features
import fiona
from shapely.geometry import shape
from rasterio.mask import mask
import geopandas as gpd

# ----------------------------------------------
# Load CHM Raster (tile)
# ----------------------------------------------

chm_path = "../data/DHM/CHM_617_72_TIF_UTM32-ETRS89/CHM_1km_6173_723.tif"
chm = rasterio.open(chm_path)

bounds = chm.bounds

# ----------------------------------------------
# Get Aerial Image Tile
# ----------------------------------------------

# Convert bounds to WGS84 (without using transformer_model)
bounds_wgs84 = pyproj.transform(
    pyproj.Proj(chm.crs),
    pyproj.Proj(init='epsg:4326'),
    [bounds.left, bounds.right],
    [bounds.top, bounds.bottom]
)


bounds_si = [(bounds_wgs84[1][0], bounds_wgs84[0][0]),
             (bounds_wgs84[1][1], bounds_wgs84[0][1])]

tile_path = satellite_imagery.get_tile(bounds_si, output_dir="./data/si_tiles/")

# ----------------------------------------------
# Extract Vegetetion Mask
# ----------------------------------------------

image = Image.open(tile_path, mode='r')
image = image.convert("RGB")

# Split the image in 4x4 parts
w, h = image.size
w, h = w // 4, h // 4
crop_bounds = [(i*w, j*h, (i+1)*w, (j+1)*h) for j in range(4) for i in range(4)]
images = [image.crop(bounds) for bounds in crop_bounds]


if not os.path.exists("./temp/images"):
    os.makedirs("./temp/images")

# remove all files in ./temp/images
for f in os.listdir("./temp/images"):
    os.remove(os.path.join("./temp/images", f))

for i, img in enumerate(images):
    with open(f"./temp/images/sub_image_{i}.pkl", "wb") as f:
        pickle.dump(img, f)

if not os.path.exists("./temp/masks"):
    os.makedirs("./temp/masks")

# remove all files in ./temp/masks
for f in os.listdir("./temp/masks"):
    os.remove(os.path.join("./temp/masks", f))

masks = []
for i, image in enumerate(images):
    print(f"Processing image {i + 1} of {len(images)}")
    sub_image_path = os.path.join(os.getcwd(), f"./temp/images/sub_image_{i}.pkl")
    os.system(f'python ./utils/transformer_model.py "{sub_image_path}"')
    mask = np.load(f"./temp/masks/mask_{i}.npy")
    masks.append(mask)

# Merge the 4x4 parts into a single image
mask_full = np.zeros((h * 4, w * 4), dtype=np.uint8)
for i, predicted_mask in enumerate(masks):
    x, y = i % 4, i // 4
    mask_full[y * h : (y + 1) * h, x * w : (x + 1) * w] = predicted_mask

mask_full[mask_full > 1] = 0


# ----------------------------------------------
# Export vegetation mask as GeoTIFF
# ----------------------------------------------

# Convert bounds to web mercator (epsg:900913)
bounds_wgs84 = pyproj.transform(
    pyproj.Proj(chm.crs),
    pyproj.Proj(init='epsg:900913'),
    [bounds.left, bounds.right],
    [bounds.top, bounds.bottom]
)

top_left_x = bounds_wgs84[0][0]
top_left_y = bounds_wgs84[1][0]
bottom_right_x = bounds_wgs84[0][1]
bottom_right_y = bounds_wgs84[1][1]

mask_full = mask_full*255

# define the metadata for the output raster
meta = {
    'driver': 'GTiff',
    'dtype': 'uint8',
    'nodata': None,
    'width': mask_full.shape[1],
    'height': mask_full.shape[0],
    'count': 1,
    'crs': 'EPSG:900913',
    'transform': from_origin(top_left_x, top_left_y, (bottom_right_x-top_left_x)/mask_full.shape[1], -(bottom_right_y-top_left_y)/mask_full.shape[0])
}

# write the binary array to a new GeoTIFF file
if not os.path.exists("./data/masks"):
    os.makedirs("./data/masks")

mask_path = './data/masks/mask_' + '_'.join([str(int(x)) for x in list(bounds)]) + '.tif'
with rasterio.open(mask_path, 'w', **meta) as dst:
    dst.write(mask_full, 1)

# ----------------------------------------------
# Export vegetation mask as Shapefile
# ----------------------------------------------

with rasterio.open(mask_path) as src:
    veg_mask = src.read(1)
    veg_meta = src.meta

shapes = list(rasterio.features.shapes(veg_mask, transform=veg_meta['transform']))

schema = {'geometry': 'Polygon', 'properties': {}}
crs = veg_meta['crs']
mask_poly_path = './data/masks/mask_' + '_'.join([str(int(x)) for x in list(bounds)]) + '.geojson'
with fiona.open(mask_poly_path, 'w', driver='GeoJSON', crs=crs, schema=schema) as dst:
    for shp, val in shapes[:-1]:
        geom = shape(shp).buffer(0)
        feature = {'geometry': geom.__geo_interface__, 'properties': {}}
        dst.write(feature)


# ----------------------------------------------
# Clip CHM with vegetation mask
# ----------------------------------------------

mask_gdf = gpd.read_file(mask_poly_path)
mask_geom = mask_gdf.to_crs('epsg:25832').geometry

# Mask the CHM raster with the vegetation mask
masked_chm, out_transform = mask(chm, mask_geom, crop=True, all_touched=True, invert=False, nodata=0)

# Cut everything below 1.5m in the masked CHM raster
masked_chm[masked_chm < 1.5] = 0

# Export the masked CHM raster
out_meta = chm.meta.copy()
out_meta.update({"driver": "GTiff",
                "height": masked_chm.shape[1],
                "width": masked_chm.shape[2],
                "transform": out_transform})

# write the binary array to a new GeoTIFF file
if not os.path.exists("./data/clipped_chm"):
    os.makedirs("./data/clipped_chm")

masked_chm_path = './data/clipped_chm/cchm_' + '_'.join([str(int(x)) for x in list(bounds)]) + '.tif'
with rasterio.open(masked_chm_path, "w", **out_meta) as dest:
    dest.write(masked_chm)

