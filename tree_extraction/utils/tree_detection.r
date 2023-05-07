#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 2) {
  stop("Usage: Rscript tree_extraction.r <input-CHM-path> <output-GEOJSON-path>", call. = FALSE)
}

chm_path <- args[1]
out_path <- args[2]

# Check and install missing packages
required_packages <- c("sf", "raster", "lidR", "terra")
new_packages <- required_packages[!(required_packages %in% installed.packages()[, "Package"])]

if (length(new_packages) > 0) {
  install.packages(new_packages)
}

# Load required libraries
library(sf)
library(raster)
library(lidR)
library(terra)

# Load the CHM raster into memory
chm <- raster(chm_path)
chm <- readAll(chm)

# Detect tree tops
tops <- locate_trees(chm, lmf(7))
tops_sf <- st_as_sf(tops)
tops_sf <- st_set_crs(tops_sf, crs(chm))

# Segment trees
algo <- dalponte2016(chm, tops_sf, th_tree = 1.5, th_seed = 0.28, th_cr = 0.50)
crowns <- algo()

# Vectorize crowns
crowns_spdf <- rasterToPolygons(crowns, dissolve=TRUE)
sf_polygons <- st_as_sf(crowns_spdf)
sf_polygons <- st_as_sf(crowns_spdf, crs = crs(chm))
st_write(sf_polygons, out_path)

