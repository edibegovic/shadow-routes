
import os
import sys
import glob

# CHMs path
chms_path = "../data/DHM/CHM_617_72_TIF_UTM32-ETRS89"

# List all CHMs
chms = glob.glob(os.path.join(chms_path, "*.tif"))
chms = sorted(chms)

# Run the script for each CHM
for idx, chm in enumerate(chms[96:100]):
    print('---------------------------------------------')
    print('---------------------------------------------')
    print(f"Processing CHM {idx+1}/{len(chms)}")
    print(f"File:{chm}")
    print('---------------------------------------------')
    print('---------------------------------------------')
    os.system(f"python main.py {chm}")

# ----------------------------------------------
# Merge all masks
# ----------------------------------------------

# Merge all masks
import geopandas as gpd
import pandas as pd

# Get all masks
masks = glob.glob("./data/canopies/*.geojson")
masks = sorted(masks)

df = pd.concat([gpd.read_file(mask) for mask in masks], ignore_index=True)

# make new df where the geometry is the centroid of the polygons
df_centroid = df.copy()
df_centroid["geometry"] = df_centroid.centroid

# save the new df
df_centroid.to_file("./data/canopies/trees_CPH.geojson", driver="GeoJSON")

