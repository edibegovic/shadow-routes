
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import pickle
import os


fn = "../data/DHM/vesterbro_gm.png"
image = Image.open(fn, mode='r')
image = image.convert("RGB")

# Split the image in 4x4 parts
w, h = image.size
w, h = w // 4, h // 4
crop_bounds = [(i*w, j*h, (i+1)*w, (j+1)*h) for j in range(4) for i in range(4)]
images = [image.crop(bounds) for bounds in crop_bounds]


if not os.path.exists("temp_images"):
    os.makedirs("temp_images")

# remove all files in temp_images
for f in os.listdir("temp_images"):
    os.remove(os.path.join("temp_images", f))

for i, img in enumerate(images):
    with open(f"temp_images/sub_image_{i}.pkl", "wb") as f:
        pickle.dump(img, f)

if not os.path.exists("temp_masks"):
    os.makedirs("temp_masks")

# remove all files in temp_masks
for f in os.listdir("temp_masks"):
    os.remove(os.path.join("temp_masks", f))

masks = []
for i, image in enumerate(images):
    print(f"Processing image {i + 1} of {len(images)}")
    
    os.system(f"python transformer_model_temp.py temp_images/sub_image_{i}.pkl")

    mask = np.load(f"temp_masks/mask_{i}.npy")
    masks.append(mask)

# Merge the 4x4 parts into a single image
mask_full = np.zeros((h * 4, w * 4), dtype=np.uint8)
for i, predicted_mask in enumerate(masks):
    x, y = i % 4, i // 4
    mask_full[y * h : (y + 1) * h, x * w : (x + 1) * w] = predicted_mask

mask_full[mask_full > 1] = 0


fig, ax = plt.subplots(1, 2, figsize=(16, 8))
ax[0].imshow(image)
ax[0].axis("off")
ax[0].set_title("Input image")
ax[1].imshow(mask_full, cmap="gray")
ax[1].axis("off")
ax[1].set_title("Predicted semantic map")
plt.show()

# ----------------------------------------------
# Export mask_full as GeoTIFF
# 
# mask_full: numpy array (1s and 0s)
# ---------------------------------------------- 

from rasterio.transform import from_origin
from rasterio.crs import crs

# # define the top-left and bottom-right corners in epsg:900913
# top_left_x = 1396726.0130126684
# top_left_y = 7494674.58309351
# bottom_right_x = 1398401.9856154057
# bottom_right_y = 7492813.378495169
#
# # define the source and target coordinate reference systems
# src_crs = 'epsg:900913'
# tgt_crs = 'epsg:25832'
#
# # create a transformer object to transform the coordinates
# transformer = pyproj.transformer.from_crs(src_crs, tgt_crs)
#
# # transform the top-left corner coordinates
# x_min, y_max = transformer.transform(top_left_x, top_left_y)
#
# # transform the bottom-right corner coordinates
# x_max, y_min = transformer.transform(bottom_right_x, bottom_right_y)
#
# mask_full = mask_full*255
#
# # define the metadata for the output raster
# meta = {
#     'driver': 'gtiff',
#     'dtype': 'uint8',
#     'nodata': none,
#     'width': mask_full.shape[1],
#     'height': mask_full.shape[0],
#     'count': 1,
#     'crs': crs.from_epsg(25832),
#     'transform': from_origin(x_min, y_max, (x_max-x_min)/mask_full.shape[1], -(y_max-y_min)/mask_full.shape[0])
# }
#
# # invert the y-scale transformation to fix orientation
# meta['transform'] = meta['transform'] * rasterio.affine.scale(1, -1)
#
# # write the binary array to a new geotiff file
# with rasterio.open('output.tif', 'w', **meta) as dst:
    # dst.write(mask_full, 1)


#
# tl = (55.67848008935223, 12.547003252166014)
# br = (55.66905190079341, 12.56205877021406)
#
# #trasorm tl and br to epsg:900913
# tl = pyproj.transform(pyproj.Proj(init='epsg:4326'), pyproj.Proj(init='epsg:3857'), tl[1], tl[0])
# br = pyproj.transform(pyproj.Proj(init='epsg:4326'), pyproj.Proj(init='epsg:3857'), br[1], br[0])
#
# mask_full.shape


# define the top-left and bottom-right corners in epsg:900913
top_left_x = 1396726.0130126684
top_left_y = 7494674.58309351
bottom_right_x = 1398401.9856154057
bottom_right_y = 7492813.378495169

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

# invert the y-scale transformation to fix orientation
# meta['transform'] = meta['transform'] * rasterio.Affine.scale(1, -1)

# write the binary array to a new GeoTIFF file
with rasterio.open('output.tif', 'w', **meta) as dst:
    dst.write(mask_full, 1)
