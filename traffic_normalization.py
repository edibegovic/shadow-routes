
from shapely.ops import nearest_points
import geopandas as gpd
import numpy as np

traffic = gpd.read_file('/Users/edibegovic/Desktop/tt_cykler.geojson').to_crs(epsg=25832)
network = gpd.read_file('./data/models/network_simple.geojson').to_crs(epsg=25832)

traffic['traffic'] = np.nan
traffic['distance'] = np.nan


for idx, row in traffic.iterrows():
    if row.geometry is None or row.geometry.is_empty:
        continue
    
    nearest = network.geometry.distance(row.geometry).idxmin()
    nearest_geom = network.loc[nearest, 'geometry']
    
    distance = row.geometry.distance(nearest_geom)
    
    traffic.loc[idx, 'traffic'] = network.loc[nearest, 'traffic']
    traffic.loc[idx, 'distance'] = distance


traffic['count'] = traffic['cykler_7_19'] 

traffic_np = np.array(traffic['traffic']).astype(float) 
traffic_np = traffic_np[~np.isnan(traffic_np)] + 10
traffic_np = np.log(traffic_np)
count_np = np.array(traffic['count']).astype(float)+1.5
count_np = np.log(count_np)

ratios = count_np / traffic_np
mean_ratio = np.mean(ratios)

traffic['diff'] = ratios - mean_ratio

# save to desktop
traffic.to_file('/Users/edibegovic/Desktop/traffic.geojson', driver='GeoJSON')
