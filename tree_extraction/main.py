
from utils import satellite_imagery
from PIL import Image
import matplotlib.pyplot as plt
from rasterio.transform import from_origin
import numpy as np
import pickle
import sys
import os
import rasterio
import pyproj
import rasterio.features
import fiona
from shapely.geometry import shape
from shapely.geometry import MultiPoint, Point
from itertools import combinations
from rasterio.mask import mask
import geopandas as gpd

# ----------------------------------------------
# Load CHM Raster (tile)
# ----------------------------------------------
chm_path = "../data/DHM/CHM_617_72_TIF_UTM32-ETRS89/CHM_1km_6174_726.tif"
chm_path = sys.argv[1]

chm = rasterio.open(chm_path)
bounds = chm.bounds

# ----------------------------------------------
# Get Aerial Image Tile
# ----------------------------------------------

padding = 30 # meters

# Convert bounds to WGS84 (without using transformer_model)
bounds_wgs84 = pyproj.transform(
    pyproj.Proj(chm.crs),
    pyproj.Proj(init='epsg:4326'),
    [bounds.left-padding, bounds.right+padding],
    [bounds.top+padding, bounds.bottom-padding]
)


bounds_si = [(bounds_wgs84[1][0], bounds_wgs84[0][0]),
             (bounds_wgs84[1][1], bounds_wgs84[0][1])]

tile_path = satellite_imagery.get_tile(bounds_si, output_dir="./data/si_tiles/")

# ----------------------------------------------
# Extract Vegetetion Mask
# ----------------------------------------------

image = Image.open(tile_path, mode='r')
image = image.convert("RGB")

# Split the image in 5x5 parts
splits = 5 
w, h = image.size
w, h = w // splits, h // splits
crop_bounds = [(i*w, j*h, (i+1)*w, (j+1)*h) for j in range(splits) for i in range(splits)]
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
    mask_t = np.load(f"./temp/masks/mask_{i}.npy")
    masks.append(mask_t)

# Merge the 4x4 parts into a single image
mask_full = np.zeros((h * splits, w * splits), dtype=np.uint8)
for i, predicted_mask in enumerate(masks):
    x, y = i % splits, i // splits
    mask_full[y * h : (y + 1) * h, x * w : (x + 1) * w] = predicted_mask

mask_full[mask_full > 1] = 0


# ----------------------------------------------
# Export vegetation mask as GeoTIFF
# ----------------------------------------------

# Convert bounds to web mercator (epsg:900913)
bounds_wm = pyproj.transform(
    pyproj.Proj(chm.crs),
    pyproj.Proj(init='epsg:900913'),
    [bounds.left-padding, bounds.right+padding],
    [bounds.top+padding, bounds.bottom-padding]
)

top_left_x = bounds_wm[0][0]
top_left_y = bounds_wm[1][0]
bottom_right_x = bounds_wm[0][1]
bottom_right_y = bounds_wm[1][1]

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

shapes_gdf = gpd.GeoDataFrame([{'geometry': shape(s[0]), 'value': s[1]} for s in shapes], crs=veg_meta['crs'])
shapes_gdf = shapes_gdf[shapes_gdf.area != shapes_gdf.area.max()]['geometry']

schema = {'geometry': 'Polygon', 'properties': {}}
crs = veg_meta['crs']
mask_poly_path = './data/masks/mask_' + '_'.join([str(int(x)) for x in list(bounds)]) + '.geojson'
shapes_gdf.to_file(mask_poly_path, driver='GeoJSON', schema=schema, crs=crs)


# ----------------------------------------------
# Clip CHM with vegetation mask
# ----------------------------------------------

mask_geom = shapes_gdf.to_crs('epsg:25832').geometry

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



# ----------------------------------------------
# Segment trees using R
# ----------------------------------------------

if not os.path.exists("./temp/tree_segments"):
    os.makedirs("./temp/tree_segments")

# remove all files in ./temp/tree_segments
for f in os.listdir("./temp/tree_segments"):
    os.remove(os.path.join("./temp/tree_segments", f))

# get filename of masked_chm_path (OUTPUT path)
segment_fn = os.path.basename(masked_chm_path) \
                    .replace(".tif", ".geojson") \
                    .replace("cchm", "segments_raw")

segment_path = os.path.join(os.getcwd(), f"temp/tree_segments/{segment_fn}")

# Run tree segmentation R script
os.system(f'Rscript ./utils/tree_detection.r "{masked_chm_path}" "{segment_path}"')


# ----------------------------------------------
# Clean tree segmentation
# ----------------------------------------------

# tree_seg = gpd.read_file('/Users/edibegovic/Desktop/crowns_w_height.geojson')

# Load geojson file with tree segmentation
tree_seg = gpd.read_file(segment_path)
tree_seg['geometry'] = tree_seg['geometry'].convex_hull

tree_seg = tree_seg[tree_seg.area > 1.2]

# all geometries whose area:perimeter ratio is less than 3.5 are removed
tree_seg['perimeter'] = tree_seg['geometry'].boundary.length
tree_seg['area'] = tree_seg['geometry'].area

# Ignore non-dense trees (false positives)
tree_seg['ratio'] = (tree_seg['area']*4)/(tree_seg['perimeter']**2)
tree_seg = tree_seg[tree_seg['ratio'] > 0.15]

def calculate_diameter(polygon):
    vertices = MultiPoint(polygon.exterior.coords)
    min_rotated_rect = vertices.minimum_rotated_rectangle
    diameter = max(Point(v1).distance(Point(v2)) for v1, v2 in combinations(min_rotated_rect.exterior.coords, 2))
    return diameter

tree_seg['diameter'] = tree_seg['geometry'].apply(calculate_diameter)
tree_seg['centroid'] = tree_seg['geometry'].centroid

# Get tree height from masked CHM
chm_masked = rasterio.open(masked_chm_path)
def get_highest_value(masked_chm, polygon):
    masked_array, _ = rasterio.mask.mask(masked_chm, [polygon], crop=True, filled=False)
    highest_value = np.nanmax(masked_array)
    return highest_value

tree_seg['height'] = tree_seg['geometry'].apply(lambda polygon: get_highest_value(chm_masked, polygon))

# Make tree_seg_round with replacing polygons geometry (in tree_seg) with circles based on centriod and diameter
tree_seg_round = tree_seg.copy()
tree_seg_round['geometry'] = tree_seg_round.apply(lambda x: Point(x['centroid']).buffer(x['diameter']/2), axis=1)
tree_seg_round = tree_seg_round.drop(columns=['centroid'])

# Misc. cleaning
tree_seg_round = tree_seg_round[tree_seg_round['height'] > 2.6]
tree_seg_round = tree_seg_round[~((tree_seg_round['area'] < 10) & (tree_seg_round['height'] > 16))]
tree_seg_round = tree_seg_round[~((tree_seg_round['area'] < 6) & (tree_seg_round['height'] > 12))]

# ----------------------------------------------
# Export canopies
# ----------------------------------------------
if not os.path.exists("./data/canopies"):
    os.makedirs("./data/canopies")

# export tree segmentation as geojson
canopy_fn = os.path.basename(masked_chm_path) \
            .replace(".tif", ".geojson") \
            .replace("cchm", "canopy")

canopy_path = "./data/canopies/" + canopy_fn

cols = ['geometry', 'height', 'diameter']
tree_seg_round[cols].to_file(canopy_path, driver='GeoJSON')
