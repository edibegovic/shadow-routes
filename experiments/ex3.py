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

small = gpd.read_file('./data/backup/sidewalks_small.geojson')
sidewalks = gpd.read_file('./data/backup/sidewalks_hourly_06_18_01072022.geojson')
nodes = list(pd.concat([sidewalks['u'], sidewalks['v']]).unique())

sidewalk_segments = geometries.get_sidewalk_segments(small)


def get_routes(sidewalks_gdf, endpoints, hour='06', alpha=0.0):
    sidewalks_weighted = sidewalks_gdf
    sidewalks_weighted['meters_covered'] = sidewalks_gdf[hour].apply(lambda x: x['total'], 1)
    G = nx.from_pandas_edgelist(sidewalks_weighted.reset_index(), 'u', 'v', edge_attr=True, edge_key='osmid')
    routes = []
    for i, (start_point, end_point) in enumerate(endpoints):
        print(i)
        route = routing.route(G, start_point, end_point, alpha)
        routes.append(route)
    return routes


# ----------------------------------------------------------------
# For hours
# ----------------------------------------------------------------
hours = ['{:02d}'.format(num) for num in range(6, 19)]
mean_shade_cover = []
for hour in hours:
    print(f'Hour: {hour}')
    routes = get_routes(sidewalks, endpoints, hour, 0.0)
    length_list = [(r['length'].sum(), r['meters_covered'].sum()) for r in routes]
    sc = np.array([cover/length*100 for length, cover in length_list]).mean()
    print("Mean length")
    print(np.array([length for length, cover in length_list]).mean())
    mean_shade_cover.append(sc)


# ----------------------------------------------------------------
# For alpha
# ----------------------------------------------------------------
n = 1000
samples = random.sample(nodes, k=n*2)
endpoints = list(zip(samples[::2], samples[1::2]))

endpoints_dist = {'short': [], 'medium': [], 'long': []}

G = nx.from_pandas_edgelist(sidewalks.reset_index(), 'u', 'v', edge_attr=True, edge_key='osmid')
for i, (start_point, end_point) in enumerate(endpoints):
    route = routing.route(G, start_point, end_point, 0.0)
    length = route['length'].sum()
    print(length)
    if length < 1000:
        endpoints_dist['short'].append((start_point, end_point))
    elif length < 4000:
        endpoints_dist['medium'].append((start_point, end_point))
    else:
        endpoints_dist['long'].append((start_point, end_point))

alphas = [x/15 for x in range(0, 16)]
stats = {'09': {'mean_shade_cover': [], 'mean_length': []}, 
         '13': {'mean_shade_cover': [], 'mean_length': []},
         '17': {'mean_shade_cover': [], 'mean_length': []}
         }

for hour in ['09', '13', '17']:
    for alpha in alphas:
        print(f'Alpha: {alpha}')
        routes = get_routes(sidewalks, endpoints, hour, alpha)
        length_list = [(r['length'].sum(), r['meters_covered'].sum()) for r in routes]
        shade_coverage = np.array([cover/length*100 for length, cover in length_list]).mean()
        mean_length = np.array([length for length, cover in length_list]).mean()
        stats[hour]['mean_shade_cover'].append(shade_coverage)
        stats[hour]['mean_length'].append(mean_length)

# -----------------------------------------------
# Seaborn plot
# -----------------------------------------------

data = pd.DataFrame({'alpha': alphas,
                     '09_msc': stats['09']['mean_shade_cover'],
                     '09_ml': stats['09']['mean_length'],
                     '09_prc_incr': [x/stats['09']['mean_length'][0] for x in stats['09']['mean_length']],
                     '09_shade_incr': [(stats['09']['mean_length'][0]*(1-stats['09']['mean_shade_cover'][0]*0.01) \
                                      - stats['09']['mean_length'][i]*(1-stats['09']['mean_shade_cover'][i]*0.01)) \
                                      / abs(stats['09']['mean_length'][0]*(1-stats['09']['mean_shade_cover'][0]*0.01))*100 \
                                     for i in range(len(alphas))],
                     '13_msc': stats['13']['mean_shade_cover'],
                     '13_ml': stats['13']['mean_length'],
                     '13_prc_incr': [x/stats['13']['mean_length'][0] for x in stats['13']['mean_length']],
                     '13_shade_incr': [(stats['13']['mean_length'][0]*(1-stats['13']['mean_shade_cover'][0]*0.01) \
                                      - stats['13']['mean_length'][i]*(1-stats['13']['mean_shade_cover'][i]*0.01)) \
                                      / abs(stats['13']['mean_length'][0]*(1-stats['13']['mean_shade_cover'][0]*0.01))*100 \
                                     for i in range(len(alphas))],
                     '17_msc': stats['17']['mean_shade_cover'],
                     '17_ml': stats['17']['mean_length'],
                     '17_prc_incr': [x/stats['17']['mean_length'][0] for x in stats['17']['mean_length']],
                     '17_shade_incr': [(stats['17']['mean_length'][0]*(1-stats['17']['mean_shade_cover'][0]*0.01) \
                                      - stats['17']['mean_length'][i]*(1-stats['17']['mean_shade_cover'][i]*0.01)) \
                                      / abs(stats['17']['mean_length'][0]*(1-stats['17']['mean_shade_cover'][0]*0.01))*100 \
                                     for i in range(len(alphas))]
                     })

plt.figure(figsize=(7, 6))

enmax_palette = ["#585858", "#75B2CC", "#918BC3", "#F1E51D", "#228D8D", "#482878"]
color_codes_wanted = ['grey', 'blue', 'purple', 'morning', 'noon', 'evening']
c = lambda x: enmax_palette[color_codes_wanted.index(x)]

# sns.lineplot(x='alpha', y='09_shade_incr', data=data, label='09:00', color=c('morning'), linewidth=3)
# sns.lineplot(x='alpha', y='13_shade_incr', data=data, label='13:00', color=c('noon'), linewidth=3)
# sns.lineplot(x='alpha', y='17_shade_incr', data=data, label='17:00', color=c('evening'), linewidth=3)

sns.lineplot(x='alpha', y='09_prc_incr', data=data, label='09:00', color=c('morning'), linewidth=3)
sns.lineplot(x='alpha', y='13_prc_incr', data=data, label='13:00', color=c('noon'), linewidth=3)
sns.lineplot(x='alpha', y='17_prc_incr', data=data, label='17:00', color=c('evening'), linewidth=3)
# plt.fill_between(data['alpha'], [50]*len(data['alpha']), alpha=0.8, color=c('grey'), edgecolor=None)

ax = plt.gca()
plt.tight_layout()
plt.margins(x=0.02, y=0.045)
plt.legend(fontsize=14)
plt.xlabel('Shade factor (α)', size=15)
# plt.ylabel('Decrease in sun-exposure (%)', size=15)
plt.ylabel('Increase in total route length', size=15)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)
ax.yaxis.set_major_formatter(FormatStrFormatter('%.2fx'))
plt.savefig('/Users/edibegovic/Desktop/teest.png', dpi=300, bbox_inches='tight')
# plt.show()

