import os
import glob
import rasterio
from rasterio.merge import merge

# --------------------------------------------------------
# Surface data processing
# --------------------------------------------------------

def merge_geotiff(dirpath, search_criteria):
    q = os.path.join(dirpath, search_criteria)

    tif_fps = glob.glob(q)
    files_mosaic = [rasterio.open(fp) for fp in tif_fps]
    mosaic, out_trans = merge(files_mosaic) # adjust output resolution

    src = rasterio.open(tif_fps[-1])
    out_meta = files_mosaic[0].meta.copy()
    out_meta.update({"driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans,
        }
    )

    return mosaic, out_meta

def load_terrain():
    dsm_mosaic, dsm_meta = merge_geotiff(r"./data/DHM/DSM_617_72_TIF_UTM32-ETRS89",  "DSM*.tif")
    dtm_mosaic, dtm_meta = merge_geotiff(r"./data/DHM/DTM_617_72_TIF_UTM32-ETRS89",  "DTM*.tif")
    if dsm_meta == dtm_meta:
        mosaic = dsm_mosaic - dtm_mosaic
        out_meta = dsm_meta
        out_fp = r"./data/cph_10x10km_mosaic.tif"
        with rasterio.open(out_fp, "w", **out_meta) as dest:
            dest.write(mosaic)
        # show(mosaic)
    else:
        raise Exception("Unmatching metadata of subtracted files")