
from model import terrain, geometries, shadows, routing, visualizations
import geopandas as gpd
import pandas as pd
import sys
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

sidewalks = gpd.read_file('./data/backup/sidewalks_small.geojson')
sidewalks = gpd.read_file('./data/backup/sidewalks_hourly_06_18_01072022.geojson')

hours = ['{:02d}'.format(num) for num in range(6, 19)]

total_shade_percentages = []
tree_shade_percentages = []
building_shade_percentages = []

for h in hours:
    tree = sidewalks[h].apply(lambda x: x['tree'], 1)
    total = sidewalks[h].apply(lambda x: x['total'], 1)
    total_length = sidewalks['length'].sum()

    total_percent = total.sum()/total_length
    total_shade_percentages.append(total_percent*100)

    tree_percent = tree.sum()/total_length
    tree_shade_percentages.append(tree_percent*100)

    building_percent = (total.sum()-tree.sum())/total_length
    building_shade_percentages.append(building_percent*100)

# -----------------------------------------------
# Analysis
# -----------------------------------------------

np.array(tree_shade_percentages)/np.array(total_shade_percentages)

# -----------------------------------------------
# Seaborn plot
# -----------------------------------------------

data = pd.DataFrame({'hour': hours,
                     'total_shade': total_shade_percentages,
                     'building_shade': building_shade_percentages,
                     'tree_shade': tree_shade_percentages})

plt.figure(figsize=(12, 5))

enmax_palette = ["#585858", "#75B2CC", "#918BC3"]
color_codes_wanted = ['grey', 'blue', 'purple']
c = lambda x: enmax_palette[color_codes_wanted.index(x)]

# Create the line plot
sns.lineplot(x='hour', y='total_shade', data=data, label='Combined', color=c('grey'))
sns.lineplot(x='hour', y='building_shade', data=data, label='Buildings', color=c("blue"))
sns.lineplot(x='hour', y='tree_shade', data=data, label='Vegetation', color='green')

plt.fill_between(data['hour'], data['total_shade'], alpha=0.8, color=c('grey'), edgecolor=None)
plt.fill_between(data['hour'], data['building_shade'], alpha=0.99, color=c("blue"), edgecolor=None)
plt.fill_between(data['hour'], data['tree_shade'], alpha=0.8, color='green', edgecolor=None)

# Add a title and axis labels
plt.xlabel('Hour')
plt.ylabel('Shade coverage (%)')

ax = plt.gca()
ax.axvline('13', linestyle='--', color='goldenrod', alpha=0.8)
ax.text('13', max(data['total_shade']), '\n  Zenith (solar noon)', color='goldenrod', verticalalignment='top', fontsize=12)

plt.legend(fontsize=12)
plt.tight_layout()
plt.margins(x=0)
plt.margins(y=0)
ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f%%'))
# ax.set_xticklabels([f'{x}:00' for x in hours])

plt.show()

# -----------------------------------------------
# Seaborn plot
# -----------------------------------------------

data = pd.DataFrame({'hour': hours,
                     'building_shade': [100] * len(building_shade_percentages),
                     'tree_shade': np.array(tree_shade_percentages)/np.array(building_shade_percentages)*101})

plt.figure(figsize=(12, 2))

enmax_palette = ["#585858", "#75B2CC", "#918BC3"]
color_codes_wanted = ['grey', 'blue', 'purple']
c = lambda x: enmax_palette[color_codes_wanted.index(x)]

# Create the line plot
sns.lineplot(x='hour', y='building_shade', data=data, label='Buildings', color=c("blue"))
sns.lineplot(x='hour', y='tree_shade', data=data, label='Vegetation', color='green')

# make horizonal dashed line at y=36.0
plt.axhline(y=37.3, color='white', linestyle='--', alpha=0.8)

plt.fill_between(data['hour'], data['building_shade'], alpha=0.99, color=c("blue"), edgecolor=None)
plt.fill_between(data['hour'], data['tree_shade'], alpha=0.8, color='green', edgecolor=None)

# Add a title and axis labels
plt.xlabel('Hour')
plt.ylabel('Makeup of shade (%)')

ax = plt.gca()
plt.legend(fontsize=12)
plt.tight_layout()
plt.margins(x=0)
plt.margins(y=0)
ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f%%'))

plt.show()
