import os
import glob
import rasterio
from rasterio.merge import merge

# --------------------------------------------------------
# Merge GeoTIFF tiles
# --------------------------------------------------------

# Path to directory containing GeoTIFF files
dirpath = r"../data/DHM/DSM_617_72_TIF_UTM32-ETRS89"
search_criteria = "DSM*.tif"
q = os.path.join(dirpath, search_criteria)

tif_fps = glob.glob(q)
files_mosaic = [rasterio.open(fp) for fp in tif_fps]
mosaic, out_trans = merge(files_mosaic, res=25000) # adjust output resolution

out_meta = src.meta.copy()
out_meta.update({"driver": "GTiff",
    "height": mosaic.shape[1],
    "width": mosaic.shape[2],
    "transform": out_trans,
    }
)

out_fp = r"../data/cph_10x10km_mosaic.tif"
with rasterio.open(out_fp, "w", **out_meta) as dest:
    dest.write(mosaic)

# --------------------------------------------------------
# Subtract terrain elevation from surface level elevation
# --------------------------------------------------------

## TODO
# DANMARKS HØJDEMODEL TERRÆN 
# DANMARKS HØJDEMODEL OVERFLADE 

