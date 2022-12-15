
from model import terrain, geometries, shadows, routing, visualizations
import geopandas as gpd
import pandas as pd
import random
import sys
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
import networkx as nx

import importlib
importlib.reload(routing)

sidewalks = gpd.read_file('./data/backup/sidewalks_hourly_06_18_01072022.geojson')
small = gpd.read_file('./data/backup/sidewalks_small.geojson')

sidewalk_segments = geometries.get_sidewalk_segments(small)

def get_routes(sidewalks_gdf, n=50, hour='06', alpha=0.0):
    nodes = list(pd.concat([sidewalks_gdf['u'], sidewalks_gdf['v']]).unique())
    samples = random.sample(nodes, k=n*2)
    endpoints = list(zip(samples[::2], samples[1::2]))
    sidewalks_weighted = sidewalks_gdf
    sidewalks_weighted['meters_covered'] = sidewalks_gdf[hour].apply(lambda x: x['total'], 1)
    G = nx.from_pandas_edgelist(sidewalks_weighted.reset_index(), 'u', 'v', edge_attr=True, edge_key='osmid')
    routes = []
    for i, (start_point, end_point) in enumerate(endpoints):
        print(i)
        route = routing.route(G, start_point, end_point, alpha)
        routes.append(route)
    return routes


hours = ['{:02d}'.format(num) for num in range(6, 19)]
mean_shade_cover = []
for hour in hours:
    print(f'Hour: {hour}')
    routes = get_routes(sidewalks, 100, hour, 0.0)
    length_list = [(r['length'].sum(), r['meters_covered'].sum()) for r in routes]
    sc = np.array([cover/length*100 for length, cover in length_list]).mean()
    print("Mean length")
    print(np.array([length for length, cover in length_list]).mean())
    mean_shade_cover.append(sc)


# -----------------------------------------------
# Seaborn plot
# -----------------------------------------------

data = pd.DataFrame({'hour': hours,
                     'mean_shade': mean_shade_cover
                     })

plt.figure(figsize=(12, 5))

enmax_palette = ["#585858", "#75B2CC", "#918BC3"]
color_codes_wanted = ['grey', 'blue', 'purple']
c = lambda x: enmax_palette[color_codes_wanted.index(x)]

# Create the line plot
sns.lineplot(x='hour', y='mean_shade', data=data, label='Combined', color=c('grey'))

plt.fill_between(data['hour'], data['mean_shade'], alpha=0.8, color=c('grey'), edgecolor=None)

# Add a title and axis labels
plt.xlabel('Hour')
plt.ylabel('Shade coverage (%)')

ax = plt.gca()

plt.legend(fontsize=14)
plt.tight_layout()
plt.margins(x=0)
plt.margins(y=0)
ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f%%'))
# ax.set_xticklabels([f'{x}:00' for x in hours])

plt.show()
