import os
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
from shapely.geometry import Point

base_dir = "C:/Users/........./"

# Load cleaned trip data with engineered features
stations_path = os.path.join(base_dir, "stations.csv")
stations_df = pd.read_csv(stations_path, skiprows=1, header=0,
                          usecols=['Number', 'NAME', 'Lat', 'Long',
                                   'Municipality', 'Total Docks'],)

stations_df.head()

# Create GeoDataFrame with station locations
stations_df['geometry'] = stations_df.apply(lambda row: Point(row['Long'], row['Lat']), axis=1)
stations_gdf = gpd.GeoDataFrame(stations_df, geometry='geometry', crs="EPSG:4326")

# Define area of interest around stations
convex_hull = stations_gdf.unary_union.convex_hull.buffer(0.02)

# Get road network from OpenStreetMap
G = ox.graph_from_polygon(convex_hull, network_type='drive')

# Project graph to UTM for distance calculations
G_proj = ox.project_graph(G)

# Project stations to the same CRS as the graph
stations_gdf = stations_gdf.to_crs(G_proj.graph['crs'])

stations_gdf.head()

# Function to calculate a distance matrix
def calculate_distance_matrix(graph, stations_gdf):
    # Get station numbers and coordinates
    station_numbers = stations_gdf['Number'].tolist()
    station_coords = list(zip(stations_gdf.geometry.y, stations_gdf.geometry.x))

    # Initialize an empty DataFrame for the matrix
    distance_matrix = pd.DataFrame(index=station_numbers, columns=station_numbers, dtype=float)

    # Iterate through each pair of stations
    for i, (number1, coord1) in enumerate(zip(station_numbers, station_coords)):
        for j, (number2, coord2) in enumerate(zip(station_numbers, station_coords)):
            if number1 != number2:  # Avoid self-loops
                # Find nearest nodes on the graph
                orig_node = ox.distance.nearest_nodes(graph, coord1[1], coord1[0])
                dest_node = ox.distance.nearest_nodes(graph, coord2[1], coord2[0])

                # Check if a path exists between the nodes
                if nx.has_path(graph, orig_node, dest_node):
                    # Calculate shortest path length
                    path_length = nx.shortest_path_length(graph, orig_node, dest_node, weight='length')
                    distance_matrix.at[number1, number2] = path_length
                else:
                    # No path available
                    distance_matrix.at[number1, number2] = None

    return distance_matrix

# Calculate the distance matrix
distance_matrix = calculate_distance_matrix(G_proj, stations_gdf)

# Display the distance matrix
distance_matrix