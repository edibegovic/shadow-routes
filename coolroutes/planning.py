import sys
sys.path.append('..')
import numpy as np
from coolroutes import geometry, visualization
import geopandas as gpd
import pandas as pd

def possible_to_plant(shade_list, trees_in_row):
    cnt = 0
    possible = []
    for element in shade_list:
        if element == 0:
            cnt+= 1
        else:
            possible.append(cnt) if cnt >= trees_in_row else None
            cnt = 0 
    return possible

def segment_weight(data, a):
    return (1 - a) * data['length'] + a * (data['length'] - data['meters_covered'])

def rank(gdf, a, trees_in_row, min_shade, min_traffic):
    gdf = gdf[gdf.traffic >= min_traffic]
    
    gdf["shade_percent"] = gdf.shade.apply(lambda x: sum(x)/len(x)) 
    gdf = gdf[gdf.shade_percent < min_shade]
    
    gdf["possible_to_plant"] = gdf.shade.apply(lambda x: possible_to_plant(x, trees_in_row))
    gdf = gdf[gdf.possible_to_plant.apply(len) > 0]
    
    gdf["possible_shade_gain"] = gdf.possible_to_plant.apply(sum) / gdf.shade.apply(len)
    gdf["possible_shade_percent"] = gdf.shade_percent + gdf.possible_shade_gain
    gdf = gdf[gdf.possible_shade_percent >= min_shade]
    
    gdf["cost"] = gdf.possible_to_plant.apply(sum)
    gdf["score"] = (1 - a) * gdf.possible_shade_percent + a * gdf.traffic
    
    return gdf

def naive_selection(gdf,
                    budget, 
                    a=0.5, #importance of traffic vs shading, 1.0 is traffic only
                    trees_in_row=5, #min numbers of trees to plant in a row
                    min_shade = 0.75, #motivation for this is that if there is a street which even fully planted will have like 50% of shade, it doesnt really makes sense
                    min_traffic = 0.5 #min traffic on the road to take into account
                    ):
    
    gdf = rank(gdf, a, trees_in_row, min_shade, min_traffic)

    gdf = gdf.sort_values("score", ascending=False)
    gdf["cumulative_cost"] = gdf.cost.cumsum()
    gdf =  gdf[gdf.cumulative_cost <= budget]
    return gdf[["group_id", "possible_to_plant", "possible_shade_gain", "cost", "score"]]