import glob
import os
import rasterio
from rasterio.merge import merge

def merge_files(dirpath, search_criteria):
    q = os.path.join(dirpath, search_criteria)

    files = glob.glob(q)
    rasters = [rasterio.open(file) for file in files]
    dest_raster, transform = merge(rasters) # adjust output resolution

    meta = rasters[0].meta.copy()
    meta.update({
        "driver": "GTiff",
        "height": dest_raster.shape[1],
        "width": dest_raster.shape[2],
        "transform": transform,
        })
    
    return dest_raster, meta

def create_geotiff():
    dsm_raster, dsm_meta = merge_files(r"./data/DHM/DSM_617_72_TIF_UTM32-ETRS89",  "DSM*.tif")
    dtm_raster, dtm_meta = merge_files(r"./data/DHM/DTM_617_72_TIF_UTM32-ETRS89",  "DTM*.tif")

    with rasterio.open(r"./data/GeoTIFF/DSM.tiff", "w", **dsm_meta) as f:
        f.write(dsm_raster)

    with rasterio.open(r"./data/GeoTIFF/DTM.tiff", "w", **dtm_meta) as f:
        f.write(dtm_raster)

    if dsm_meta == dtm_meta:
        chm_raster = dsm_raster - dtm_raster
        chm_meta = dsm_meta
        with rasterio.open(r"./data/GeoTIFF/CHM.tif", "w", **chm_meta) as f:
            f.write(chm_raster)
    else:
        raise Exception("Unmatching metadata of subtracted files")   