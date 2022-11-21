# -*- coding: utf-8 -*-
"""Brooklyn_Arrests_Subway_2019.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/14Vbe4KqWI6fXjqfhxf8z6N1YB-ov4mai
"""

from google.colab.output import eval_js
eval_js('google.colab.output.setIframeHeight("100")') # limits the height of output so it doesn't take up the whole notebook screen

!pip install pygeos census geopandas mapclassify contextily adjustText # Install geopandas and mapclassify (used for interactive mapping)

import pygeos
import os
import pandas as pd
import geopandas as gpd
import matplotlib as mpl
import folium
from matplotlib import pyplot as plt
import matplotlib.patheffects as pe
import mapclassify
from census import Census
import contextily as ctx 
from adjustText import adjust_text

plt.rcParams["figure.figsize"] = (10,10) # set this once for a default plot size

from google.colab import drive # this mounts your Google Drive; you have to authenticate it each time I think unfortunately
drive.mount('/drive')
# executes in 15 seconds for me

#loading in TIGER shapefiles
url_us_county = r'https://www2.census.gov/geo/tiger/TIGER2019/COUNTY/tl_2019_us_county.zip' #loading us counties , for some reason it generated a '404 Not found' error when I directly tried loading New York state's counties
us_county = gpd.read_file(url_us_county)
ny_county = us_county[us_county["STATEFP"] == '36'] #filtering to include only new york state
url_ny_tracts = r'https://www2.census.gov/geo/tiger/TIGER2019/TRACT/tl_2019_36_tract.zip'
ny_tracts = gpd.read_file(url_ny_tracts)

#loading dataset
ny_arrest = gpd.read_file('/drive/MyDrive/Github/Data/Brooklyn_Arrest_2019/nyc_arrest_cov.csv') #loading NY Arrest data
sub_station = gpd.read_file('/drive/MyDrive/Github/Data/Brooklyn_Arrest_2019/Subway Stations.geojson') #loading Subway Station data
sub_line = gpd.read_file('/drive/MyDrive/Github/Data/Brooklyn_Arrest_2019/Subway Lines.geojson') #loading subway lines data

#assigning geometries from lat long
ny_arrest = gpd.GeoDataFrame(ny_arrest, crs='epsg:2263', geometry=gpd.points_from_xy(ny_arrest['X_COORD_CD'], ny_arrest['Y_COORD_CD'])) #setting geometry and coordinate system to arrest data
ny_arrest.head()

#filtering arrests to brooklyn
brooklyn_arrest = ny_arrest[ny_arrest["ARREST_BORO"] == "K"]
brooklyn_arrest.head()

#filtering county data to include only brooklyn
brooklyn = ny_county[ny_county['NAME']=='Kings'] 
brooklyn.to_crs('epsg:2263', inplace=True)

#clipping tracts to brooklyn
ny_tracts.to_crs('epsg:2263', inplace=True)
brooklyn_tracts = ny_tracts.clip(brooklyn)
brooklyn_tracts.to_crs(epsg=2263, inplace=True) #projecting to long island state plane
brooklyn_tracts.explore(height=450)

#clipping subway lines to brooklyn
sub_line.to_crs('epsg:2263', inplace=True)
brooklyn_lines = sub_line.clip(brooklyn)
brooklyn_lines.to_crs(epsg=2263, inplace=True) #projecting to long island state plane
brooklyn_lines.explore(height=450)

#creating quarter mile buffers along all subway stations in brooklyn
sub_station.to_crs('epsg:2263', inplace=True)
brooklyn_sub_stn = sub_station.clip(brooklyn) #clipping to only subway stations in brooklyn
brooklyn_sub_stn = brooklyn_sub_stn.to_crs(epsg=2263) #projecting to the long island state plane
sub_stn_buf = brooklyn_sub_stn.buffer(1320) #creating quater mile buffers around the stations
eval_js('google.colab.output.setIframeHeight("500")')
sub_stn_buf.explore(height = 450)

#making all the buffer polygons into one single multipolygon with Unary Union
eval_js('google.colab.output.setIframeHeight("500")') 
near_sub_stn = gpd.GeoDataFrame(index=[0], crs='epsg:2263', geometry=[sub_stn_buf.unary_union])
near_sub_stn.explore(height = 450)

"""**Overlay Operation- Difference**"""

#creating overlay by employing the Difference method to generate polygon inside Brooklyn with areas other than those within a quater mile of a subway station
far_sub_stn = brooklyn.overlay(near_sub_stn, how='difference')
far_sub_stn.explore(height = 450)

#appending the polygons- near subway and farther away from subway stations with indentifier keys
brook_sub_near_far = near_sub_stn.append(far_sub_stn, ignore_index=True)
brook_sub_near_far['key'] = ""
brook_sub_near_far.loc[0,'key'] = 'Near Subway Stations'
brook_sub_near_far.loc[1,'key'] = 'Away from Subway Stations'
brook_sub_near_far

#spatially joining the appended polygon to the arrest gdf
brooklyn_arrest_sub = brooklyn_arrest.sjoin(brook_sub_near_far, how="left")
brooklyn_arrest_sub

#inspecting the number of arrests that took place in the two regions
brooklyn_arrest_sub['key'].value_counts()

#plotting the arrests by their location- within or outside a quater mile radius around subway stations
plt.figure(figsize = (20,16))

ax1 = plt.subplot(111)

brooklyn_tracts.plot(alpha = 0.3, legend = True, ax=ax1, edgecolor = 'white', linewidth = .3, facecolor = '#D3D3D3')

brooklyn_lines.plot(alpha = 0.9, legend = True, ax=ax1, edgecolor = 'white', linewidth = .8, facecolor = '#fafafc')

brooklyn_arrest_sub.plot('key', alpha = 0.6, ax=ax1, legend=True, cmap = 'autumn', edgecolor = 'white', linewidth = .6, markersize = 2)

plt.title("Arrest Locations in 2019-2020: 1/4-Mile around Subway Stations and Beyond", size = 16);
ctx.add_basemap(ax1,source=ctx.providers.CartoDB.DarkMatterNoLabels, crs = brooklyn_tracts.crs);
ax1.axis('off')

"""So, which subway stations contributed to how many arrests?"""

#adding the buffer geoseries to the subway stations gdf and reassigning its geometry to the buffer (polygon) geometry
brooklyn_sub_stn["Stn_Buf_0.25"] = sub_stn_buf #adding buffer Geoseries to Geodataframe to be able to do spatial join
brooklyn_stn_buf = brooklyn_sub_stn.set_geometry("Stn_Buf_0.25", drop=True, inplace=False, crs="epsg:2263") #reassigning geometry and dropping previous geometry
brooklyn_stn_buf.rename(columns={"Stn_Buf_0.25": "geomtery"}) #renaming to geomtery

# using the pivot table approach to join the points(arrests) to the polygons (buffers) aggregating on the total counts for years 2019 and 2020
brook_sub_arrest = ny_arrest.sjoin(brooklyn_stn_buf, how="left") 
dfpivot = pd.pivot_table(brook_sub_arrest,index='objectid',columns='YEAR',aggfunc={"YEAR": "count"}) #aggregating on yearly arrest counts
dfpivot.columns = dfpivot.columns.droplevel() # drops the header row with "YEAR" and makes each column name one of the types
brook_sub_arrest_counts = brooklyn_stn_buf.merge(dfpivot, how='left', on = 'objectid')
brook_sub_arrest_counts.head()

"""Creating Small Multiples is a nice and simple way for a quick comparision"""

#defining series of total yearly counts
y_2019 = brook_sub_arrest_counts["2019"]
y_2020 = brook_sub_arrest_counts["2020"]

#creating centroids of buffers, essentially the subway station locations
brook_sub_arrest_counts_centroids = gpd.GeoDataFrame(brook_sub_arrest_counts.centroid, columns=["geometry"])
brook_sub_arrest_counts_centroids_19 = brook_sub_arrest_counts_centroids.join(y_2019)
brook_sub_arrest_counts_centroids_20 = brook_sub_arrest_counts_centroids.join(y_2020)

#creating dataframes containing only station areas with more than 1000 arrests for labeling
brook_sub_arrest_counts_high_19 = brook_sub_arrest_counts[brook_sub_arrest_counts['2019'] > 1000]
brook_sub_arrest_counts_high_20 = brook_sub_arrest_counts[brook_sub_arrest_counts['2020'] > 1000]

#plotting small multiples of subway stations which had the most arrests in 2019 and 2020 
plt.figure(figsize = (20,16))

#first plot
ax1 = plt.subplot(121)

brooklyn_tracts.plot(alpha = 0.25, legend = True, ax=ax1, edgecolor = 'white', linewidth = .3, facecolor = '#D3D3D3')

brooklyn_lines.plot(alpha = 0.9, legend = True, ax=ax1, edgecolor = 'black', linewidth = .8, facecolor = '#D3D3D3')

brook_sub_arrest_counts_centroids.plot(alpha = 0.6, ax=ax1, legend=True, color = 'orange', edgecolor = 'white', linewidth = .6, markersize = y_2019)

plt.title("Number of arrests in 2019: 1/4-Mile around Subway Stations", size = 16);
ctx.add_basemap(ax1,source=ctx.providers.CartoDB.DarkMatterNoLabels, crs = brooklyn_tracts.crs);
ax1.axis('off')

brook_sub_arrest_counts_high_19['coords'] = brook_sub_arrest_counts_high_19['geometry'].apply(lambda x: x.centroid.coords[:])
brook_sub_arrest_counts_high_19['coords'] = [coords[0] for coords in brook_sub_arrest_counts_high_19['coords']] # eliminate duplicate points
# labelling
labels = [plt.text(brook_sub_arrest_counts_high_19.iloc[i]['coords'][0], 
                  brook_sub_arrest_counts_high_19.iloc[i]['coords'][1],
                  brook_sub_arrest_counts_high_19.iloc[i]['name'].title(), 
                  horizontalalignment='center', size=10,
                  path_effects=[pe.withStroke(linewidth=0.1, )],
                  color='white') for i in range(len(brook_sub_arrest_counts_high_19))]
adjust_text(labels)

#second plot
ax2 = plt.subplot(122)

brooklyn_tracts.plot(alpha = 0.25, legend = True, ax=ax2, edgecolor = 'white', linewidth = .3, facecolor = '#D3D3D3')

brooklyn_lines.plot(alpha = 0.9, legend = True, ax=ax2, edgecolor = 'black', linewidth = .8, facecolor = '#D3D3D3')

brook_sub_arrest_counts_centroids.plot(alpha = 0.6, ax=ax2, legend=True, color = 'orange', edgecolor = 'white', linewidth = .6, markersize = y_2020)

plt.title("Number of arrests in 2020: 1/4-Mile around Subway Stations", size = 16);
ctx.add_basemap(ax2,source=ctx.providers.CartoDB.DarkMatterNoLabels, crs = brooklyn_tracts.crs);
ax2.axis('off')

brook_sub_arrest_counts_high_20['coords'] = brook_sub_arrest_counts_high_20['geometry'].apply(lambda x: x.centroid.coords[:])
brook_sub_arrest_counts_high_20['coords'] = [coords[0] for coords in brook_sub_arrest_counts_high_20['coords']] # eliminate duplicate points
# labelling
labels = [plt.text(brook_sub_arrest_counts_high_20.iloc[i]['coords'][0], 
                  brook_sub_arrest_counts_high_20.iloc[i]['coords'][1],
                  brook_sub_arrest_counts_high_20.iloc[i]['name'].title(), 
                  horizontalalignment='center', size=10,
                  path_effects=[pe.withStroke(linewidth=0.1, )],
                  color='white') for i in range(len(brook_sub_arrest_counts_high_20))]
adjust_text(labels)

"""Next, we can create an interactive map with folium that helps us publish one or both of these maps. As an example, I've gone ahead with the one showing the arrests in 2019"""

# Create a new Folium map
eval_js('google.colab.output.setIframeHeight("1000")') # limits the height of output so it doesn't take up the whole notebook screen
map = folium.Map(location=[40.635284252514246, -73.96308579690913], tiles=None, zoom_start=11, height = 850, width = '100%') # percentage width makes it responsive for mobile
folium.TileLayer('CartoDB dark_matter', name='Carto DarkMatter').add_to(map)

#plotting brooklyn tracts
brooklyn_tracts_webm = brooklyn_tracts.to_crs('epsg:4326')
brooklyn_tracts_webm_f = folium.FeatureGroup(name='Brooklyn Tracts',control=True)

for _, r in brooklyn_tracts_webm.iterrows():
    # Without simplifying the representation of each borough,
    # the map might not be displayed
    sim_geo = gpd.GeoSeries(r['geometry'])
    geo_j = sim_geo.to_json()
    geo_j = folium.GeoJson(data=geo_j,
                           style_function=lambda x: {'alpha':0.25, 'fillColor': '#D3D3D3', # fill color
                                                     'color': 'white', # line color
                                                     'weight': 0.3}) # line width
    geo_j.add_to(brooklyn_tracts_webm_f)
brooklyn_tracts_webm_f.add_to(map)

#plotting arrests near subway stations
brook_sub_arrest_counts_centroids_webm = brook_sub_arrest_counts_centroids.to_crs('epsg:4326')
brook_sub_arrest_counts_webm = brook_sub_arrest_counts.to_crs('epsg:4326')
# Create a geometry list from the GeoDataFrame
brook_sub_arrest_list = [[point.xy[1][0], point.xy[0][0]] for point in brook_sub_arrest_counts_centroids_webm.geometry]

i = 0 # initialize counter at zero
for coordinates in brook_sub_arrest_list:   # Iterate through list and add a marker for each dispensary, color-coded by type
    map.add_child( # Place the markers with the popup labels and data
        folium.Circle(location = coordinates,
                      popup = folium.Popup("<b>Name:</b> " + str(brook_sub_arrest_counts_webm.name[i]), 
                                           max_width=len(f"name= {brook_sub_arrest_counts_webm.name[i]}")*20),
                      radius=float(brook_sub_arrest_counts_webm.iloc[i]['2019']), 
                      tooltip = str(brook_sub_arrest_counts_webm.name[i]),
                      color="white", 
                      weight = 0.5,
                      fill=True, 
                      fillOpacity = 0.5,
                      fill_color="orange"))
    i = i + 1

#plotting subway lines

brooklyn_lines_webm = brooklyn_lines.to_crs('epsg:4326')
brooklyn_lines_webm_f = folium.FeatureGroup(name='Subway Lines',control=True)

for _, r in brooklyn_lines_webm.iterrows():
    # Without simplifying the representation of each borough,
    # the map might not be displayed
    sim_geo_l = gpd.GeoSeries(r['geometry'])
    geo_j_l = sim_geo_l.to_json()
    geo_j_l = folium.GeoJson(data=geo_j_l,
                          style_function=lambda x: {'alpha':0.9, 'fillColor': '#D3D3D3', # fill color
                                                    'color': 'white', # line color
                                                    'weight': 0.8}) # line width
    geo_j_l.add_to(brooklyn_lines_webm_f)
brooklyn_lines_webm_f.add_to(map)

#initiating layer control
folium.LayerControl().add_to(map)
map

"""Lastly, Saving the map in html """

#Exporting the map
map.save('/drive/My Drive/651 - Command-Line GIS/brooklyn_sub_arrests_2019.html')

"""THE END! Special thanks to Prof. Will B Payne for teaching me this. Check out his awesome work here https://willbpayne.com"""