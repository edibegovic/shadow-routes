import geopandas as gpd
import networkx as nx
import itertools
from shapely.ops import unary_union
import hashlib
import math
from shapely.geometry import Point, LineString, MultiLineString, Polygon, MultiPolygon

def calculate_angle(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    angle = math.atan2(dy, dx)
    return angle

# gdf = gpd.read_file('/Users/edibegovic/Desktop/over_5_bike_network_w_traffic.geojson')
gdf_og = gpd.read_file('./data/models/network_simple_norm_traffic.geojson')
gdf = gdf_og[gdf_og['traffic'] > 0.5]
gdf = gdf[~gdf.geometry.duplicated()]

# make 'u' and 'v' columns based on the start and end point of each linestring
gdf['u'] = gdf.geometry.apply(lambda x: hashlib.md5(str(str(x.coords[0][0])[:8] + str(x.coords[0][1])[:8]).encode()).hexdigest()[:10])
gdf['v'] = gdf.geometry.apply(lambda x: hashlib.md5(str(str(x.coords[-1][0])[:8] + str(x.coords[-1][1])[:8]).encode()).hexdigest()[:10])
gdf['unique_id'] = gdf['u'] + gdf['v']

gdf['angle'] = gdf.geometry.apply(lambda x: calculate_angle(x.coords[0][0], x.coords[0][1], x.coords[-1][0], x.coords[-1][1]))
gdf['angle'] = gdf['angle'].apply(lambda x: math.degrees(x))
gdf['angle'] = gdf['angle'].apply(lambda x: x + 360 if x < 0 else x)

# build a non-directed graph from the gdf
G = nx.from_pandas_edgelist(gdf, source='u', target='v', edge_attr=True, create_using=nx.Graph())

checked_edges = {}
current_group_id = 0

checked_edges = {}
current_group_id = 0

edges_in_this_group = []
counter = 0
angle_threshold = 25
for u, v, data in G.edges(data=True):
    counter += 1
    print(counter)
    print("group: ", current_group_id)

    queue = [(u, v)]
    visited_edges = set([(u, v)])
    if (u, v) in checked_edges:
        continue
    else:
        checked_edges[(u, v)] = True

    edges_in_this_group.append((u, v))

    current_angle = data['angle']
    while queue:
        u, v = queue.pop()
        for neighbor in G.neighbors(v):
            if neighbor != u and (v, neighbor) not in checked_edges:
                neighbor_angle = G.edges[v, neighbor]['angle']
                # if either angles is above 180, subtract 180 from it
                if current_angle > 180:
                    current_angle -= 180
                if neighbor_angle > 180:
                    neighbor_angle -= 180
                angle_diff = abs(neighbor_angle - current_angle)
                angle_diff = min(angle_diff, 360 - angle_diff)
                if angle_diff < angle_threshold:
                    current_angle = neighbor_angle
                    if (v, neighbor) not in visited_edges:
                        visited_edges.add((v, neighbor))
                        queue.append((v, neighbor))
                        edges_in_this_group.append((v, neighbor))

        for neighbor in G.neighbors(u):
            if neighbor != v and (neighbor, u) not in checked_edges:
                neighbor_angle = G.edges[u, neighbor]['angle']
                if current_angle > 180:
                    current_angle -= 180
                if neighbor_angle > 180:
                    neighbor_angle -= 180
                angle_diff = abs(neighbor_angle - current_angle)
                angle_diff = min(angle_diff, 360 - angle_diff)
                if angle_diff < angle_threshold:
                    print(angle_diff)
                    current_angle = neighbor_angle
                    if (u, neighbor) not in visited_edges:
                        visited_edges.add((u, neighbor))
                        queue.append((u, neighbor))
                        edges_in_this_group.append((u, neighbor))

        total_length = np.sum([G.edges[x, y]['length'] for x, y in edges_in_this_group])
        if total_length > 3000:
            queue = []

    current_group_id += 1
    if len(edges_in_this_group) > 15:
        for edge in edges_in_this_group:
            G[edge[0]][edge[1]]['group_id'] = current_group_id
        current_group_id += 1
        for edge in edges_in_this_group:
            checked_edges[edge] = True
            checked_edges[(edge[1], edge[0])] = True


    edges_in_this_group = []

# --------------------------------------------------------------------------------
# Remove branches
# --------------------------------------------------------------------------------

# Create a dictionary to store the longest paths for each group_id
longest_paths = {}

# Iterate over all edges in the graph
for u, v, data in G.edges(data=True):
    # Check if the edge has a group_id attribute
    if 'group_id' in data:
        group_id = data['group_id']
        # If the group_id is not already in the dictionary, add it with an empty list
        if group_id not in longest_paths:
            longest_paths[group_id] = []
        # Add the edge to the list for its group_id
        longest_paths[group_id].append((u, v, data))

# Create a new graph to store the longest paths for each group_id
G_longest = nx.Graph()

# Iterate over the longest paths for each group_id
for group_id, edges in longest_paths.items():
    # Sort the edges by their length (assuming length is stored in the 'length' attribute)
    edges.sort(key=lambda x: x[2].get('length', 0), reverse=True)
    # Add the longest edge to the new graph
    G_longest.add_edge(*edges[0][:2], **edges[0][2])


# combine all the sub-graphs (in longests_paths) into one graph
G_longest = nx.compose_all([nx.Graph(edges) for edges in longest_paths.values()])

# --------------------------------------------------------------------------------
# Group all 
# --------------------------------------------------------------------------------

df = nx.to_pandas_edgelist(G_longest)

# export graph as geodataframe
df = nx.to_pandas_edgelist(G)
df = df.drop_duplicates(subset=['source', 'target'])
df = df.dropna(subset=['group_id'])

gdf = gpd.GeoDataFrame(df, geometry='geometry', crs=gdf.crs)
gdf['group_id'] = gdf['group_id'].astype(int)

grouped = gdf.groupby('group_id').agg({'geometry': lambda x: unary_union(x),'traffic': 'mean', 'length': 'sum'})
grouped = gpd.GeoDataFrame(grouped, geometry='geometry', crs=gdf.crs)
grouped = grouped.to_crs(epsg=25832)

grouped = grouped.sort_values(by='traffic', ascending=False).iloc[:400]
# export graph as geojson
grouped.to_file('/Users/edibegovic/Desktop/top_350.geojson', driver='GeoJSON')
