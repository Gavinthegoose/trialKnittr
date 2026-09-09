# rate map for trials to apply fertilizer. 
# 2 outputs are given:
	# VR Map of Site
	# GPS Lines for the tractor

# Import Packages
import geopandas as gpd
import pandas as pd
import shapely
from shapely import plotting
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import tkinter 
from tkinter import filedialog

# Define our supporting functions
def grab_bounding_coords(site, verbosity = False, crs = 'EPSG:32613'):

	'''
	site: GeoPandas GeoDataframe of the site 
	verbosity: Do you want to see all plots? Print outs? Then set 'True' at the start
	crs: CRS of the project, defaults to "EPSG:32613"

	Returns: GeoPandas GeoSeries of the lines
	'''

	# Plot site
	if verbosity == True:
		# f, ax = plt.subplots(1, figsize = (9,9))
		site.plot(facecolor = 'none', edgecolor = 'red')
		plt.show()

	# Grab coordinates of this geomety
	coords = site.get_coordinates()
	coords = coords[0:4]

	# Split Coords up
	sw_corn = coords.loc[coords['x'] == min(coords['x']),].iloc[0]
	se_corn = coords.loc[coords['y'] == min(coords['y']),].iloc[0]
	nw_corn = coords.loc[coords['y'] == max(coords['y']),].iloc[0]
	ne_corn = coords.loc[coords['x'] == max(coords['x']),].iloc[0]

	# Make the lines 
	westLine = shapely.LineString([[nw_corn.x,nw_corn.y],[sw_corn.x,sw_corn.y]])
	westLine = gpd.GeoSeries(westLine, crs=crs) 
	northLine = shapely.LineString([[nw_corn.x,nw_corn.y],[ne_corn.x,ne_corn.y]])
	northLine = gpd.GeoSeries(northLine, crs=crs)
	eastLine = shapely.LineString([[ne_corn.x,ne_corn.y],[se_corn.x,se_corn.y]])
	eastLine = gpd.GeoSeries(eastLine, crs=crs)
	southLine = shapely.LineString([[sw_corn.x,sw_corn.y],[se_corn.x,se_corn.y]])
	southLine = gpd.GeoSeries(southLine, crs=crs)

	return westLine, northLine, eastLine, southLine

def createVerticleLines(northLine, southLine, implement_width, verbosity = False):

	'''
	northLine: GeoPandas GeoSeries object given from the grab_bounding_coords function
	southLine: GeoPandas GeoSeries object given from the grab_bounding_coord function
	implement_width: The width of the machine applying the product, in meters
	verbosity: Do you want to see all plots? Print outs? Then set 'True' at the start

	Returns: List of the verticle lines
	'''
	# Segment the lines into the width of the implement
	northLine_seg = northLine.segmentize(max_segment_length=implement_width)
	southLine_seg = southLine.segmentize(max_segment_length=implement_width)

	# Get coordinates from segmentation
	n_coords = northLine_seg.get_coordinates()
	s_coords = southLine_seg.get_coordinates()

	# Grab these verticle lines

	verticleLines = []

	for x in range(0, len(n_coords),1):

		north = n_coords.iloc[x]
		south = s_coords.iloc[x]

		line = shapely.LineString([[north.x,north.y],[south.x,south.y]])

		# Extend the lines for cutting
		extended = shapely.affinity.scale(line, xfact = 1, yfact = 5, origin = line.centroid)

		verticleLines.append(extended)

	if verbosity == True:
		# f,ax = plt.subplots(1, figsize = (8,8))
		gdf = gpd.GeoDataFrame(verticleLines, geometry=0)
		gdf.plot(edgecolor='red')
		plt.show()
	
	return verticleLines

def create_horizontal_lines(westLine,eastLine, plot_length, verbosity = False):

	'''
	westLine: GeoPandas GeoSeries object given from the grab_bounding_coords function
	eastLine: GeoPandas GeoSeries object given from the grab_bounding_coord function
	plot_length: The length of which plots will be
	verbosity: Do you want to see all plots? Print outs? Then set 'True' at the start

	Returns: List of the horizontal lines
	'''
	westLine_seg = westLine.segmentize(max_segment_length=plot_length)
	eastLine_seg = eastLine.segmentize(max_segment_length=plot_length)

	# Get coordinates from segmentation
	w_coords = westLine_seg.get_coordinates()
	e_coords = eastLine_seg.get_coordinates()

	# Grab these verticle lines

	horizonal_lines = []

	for x in range(0, len(w_coords),1):

		west = w_coords.iloc[x]
		east = e_coords.iloc[x]

		line = shapely.LineString([[west.x,west.y],[east.x,east.y]])

		# Extend the lines for cutting
		extended = shapely.affinity.scale(line, xfact = 5, yfact = 1, origin = line.centroid)

		horizonal_lines.append(extended)

	if verbosity == True:
		# f,ax = plt.subplots(1, figsize = (8,8))
		gdf = gpd.GeoDataFrame(horizonal_lines, geometry=0)
		gdf.plot(edgecolor='red')
		plt.show()
	
	return horizonal_lines
	
def create_grid(horizontal_lines, verticleLines, site, verbosity = False):
	
	'''
	horizontal_lines: List of Shapely LineString objects from create_horizontal_lines function
	verticleLines: Line of Shapely LineString objects from createVerticleLines   
	site: GeoPandas GeoDataframe of the site
	verbosity: Do you want to see all plots? Print outs? Then set 'True' at the start

	Returns: GeoPandas GeoDataframe of the grid
	'''

	# Create a union of the shapes
	horizontal_union = shapely.union_all(horizontal_lines)
	verticle_union = shapely.union_all(verticleLines)

	# Rotate the original geometry 
	site_geom = site.geometry.iloc[0]
	site_centroid =  site_geom.centroid.coords.xy
	site_centeroid_coords = (site_centroid[0][0], site_centroid[1][0])
	rotated = shapely.affinity.rotate(site_geom, angle = 1.025, origin = site_centeroid_coords) # Angle chosen as best guess for EPSG:32613, may need to be adjusted for other coordinate reference systems

	# Split site_geom by the horizontal lines first
	h_split = shapely.ops.split(rotated, horizontal_union)

	# Split the horizontal polygons by the verticle lines to obtain our grid
	vSplits = []
	for g in range(len(horizontal_lines)):
		h_geom = h_split.geoms[g] # Grab geometry
		vSplit = shapely.ops.split(h_geom, verticle_union)
		vSplits.append(vSplit)

	# Create a GDF of these splits
	verticle_splits_series = gpd.GeoSeries(vSplits)
	splits_gdf = gpd.GeoDataFrame(verticle_splits_series, geometry=0)

	# Create the grid
	grid = []

	for x in range(1,len(splits_gdf)):
		poly_list = splits_gdf.iloc[x].to_list()
		polygons = list(poly_list[0].geoms)
		row = x # Row number

		split_polys = []
		col = 1
		for i, poly in enumerate(polygons, start = 1):

			if poly.area > 10:
				rotated = shapely.affinity.rotate(poly, angle = -1.025, origin = site_centeroid_coords)
				poly_series = gpd.GeoSeries(rotated)

				split_polys.append({
					"row": row,
					"col": col,
					"geometry": rotated
				})
				col +=1
		
		grid.extend(split_polys)

	poly_gdf = gpd.GeoDataFrame(grid, geometry = 'geometry', crs = CRS)

	if verbosity == True:
		# f, ax = plt.subplots(1, figsize=(9,9))
		poly_gdf.plot(facecolor = 'gold', edgecolor = 'black')
		plt.show()

		# double check coordinates
		plot_0 = poly_gdf.iloc[0]
		coords_0 = plot_0.geometry.bounds
		print(f"Corner coordinate values: {coords_0[0], coords_0[1]}") # usually the first corner drawn from the bounding box creation

		site_geom_coords = site_geom.bounds
		print(f"Corner coordinate values of site bounding box: {site_geom_coords[0], site_geom_coords[1]}") # Should line up, may not be 100% accurate



	return poly_gdf

def input_product_values(poly_gdf, fieldBoundary, siteName, out_dir, vrRates, fieldRate, trialType, savePolyGDF):

	'''
	poly_gdf: GeoPandas GeoDataframe object taken from create_grids function

	Returns: Shapefile of the site grid map in CRS EPSG:4326. Output should be able to placed into agriculture implement controller and work, in theory
	'''
	# Sort dataframe so that columns are presented, in the case of the MORSE Trials performed at the University of Saskatchewan's this is the easiest orientation

	column_first = poly_gdf.sort_values(by = 'col', ascending = True).reset_index().drop(columns='index').copy()
	passes = pd.unique(column_first['col'])
	print("Passes are sorted in order from Left to Right. Keep in mind when inputting values!")

	# Get rates inputted 
	columns = []
	for x, y in zip(passes, vrRates):
		pass_num = column_first.loc[column_first['col'] == x,].copy()
		row_organization= pass_num.sort_values(by = 'row', ascending = False).reset_index().drop(columns = 'index').copy()

		if verbosity ==  True:
			print(f"Pass Number: {pass_num}")
			print(f"Rates: {vrRates[y]}")

		# Add rates to GeoDataframe
		row_organization['rate'] = vrRates[y]

		# Move geometry to the end for asthetic appeal :)
		row_organization = row_organization[[c for c in row_organization.columns if c != 'geometry'] + ['geometry']]

		# Append pass list
		columns.append(row_organization)        

	out_df = pd.concat(columns)

	if verbosity == True:
		print(out_df)
	 
	out_df['rate'] = out_df['rate'].astype(np.float32)
	out_df['rate_lbs'] = out_df['rate'] * 0.8922 # Converts to lbs/ac

	# Save this field grid before dissolving, if User specifies
		# Save poly_gdf if the user would like
	if savePolyGDF == True:
		polyOutFolder = out_dir / "trialGrid"
		polyOutFolder.mkdir(exist_ok=True, parents=True)

		

		polyOutPath = polyOutFolder / "trialGrid.shp"
		if verbosity == True:
			print(f"Folder: {polyOutFolder}")
			print(f"File: {polyOutPath}")

		out_df.to_file(polyOutPath)
	
	# Dissolve geometries on rate
	dissolved = out_df.dissolve('rate').reset_index()

	# Unionize grid and field boundary
	union = dissolved.overlay(fieldBoundary, how = 'union')

	geom2d = union.force_2d()

	union['geometry'] = geom2d    

	out_df_4326 = union.to_crs("EPSG:4326")
	# site_name = input("Name of site to use for file naming: ")
	out_df_4326.iloc[-1,3] = fieldRate
	
	if verbosity == True:
		print(union)

		print(out_df_4326.iloc[-1,2])
	out_dir_site = out_dir / "vrGrid"
	out_dir_site.mkdir(exist_ok = True, parents = True)

	out_path = out_dir_site / f"{siteName}VRGrid.shp"

	# Save to file
	out_df_4326.to_file(out_path)

	# plot end result for user

	# f, ax = plt.subplots(1, figsize = (9,9))

	if trialType == 'Ramp':
		out_df_4326.plot(column='rate',
			cmap='RdYlGn',
			legend=True,
			legend_kwds={'loc': 6, "fancybox": True, 'bbox_to_anchor': (1.05,0.5),
						'title': 'Product Rate'},
			scheme = "EqualInterval",
			# classification_kwds = {'bins': [int(0),int(max(out_df_4326['rate']))]} 
			k = len(pd.unique(out_df_4326['rate']))
			)

	if trialType == 'On/Off':
		f,ax=plt.subplots(1)
		
		for x in range(0,len(columns),1):

			columns[x].plot(ax = ax,
			column='rate',
			cmap='RdYlGn',
			legend=True,
			legend_kwds={'loc': 6, "fancybox": True, 'bbox_to_anchor': (1.05,0.5),
						'title': 'Product Rate','labels': ['0',f"{int(max(out_df_4326['rate']))}"]},
			scheme = "UserDefined",
			classification_kwds = {'bins': [int(0),int(max(out_df_4326['rate']))]} 
			# k = uniquwe5
			)

		plt.show()
	return out_df_4326

def tractor_gps_lines(northLine, southLine, implement_width, out_dir, crs = "EPSG:32613", verbosity = False):

	'''
	northLine: GeoPandas GeoSeries from grab_bounding_coords function
	southLine: GeoPandas GeoSeries from grab_bounding_coords function
	implement_width: int; Width of the implement performing application

	Returns: File of GPS lines which will be used for the application of the product 
	'''

	northLine_seg = northLine.segmentize(max_segment_length=implement_width)
	northLine_seg_gdf = gpd.GeoSeries(northLine_seg, crs = crs)
	southLine_seg = southLine.segmentize(max_segment_length=implement_width)
	southLine_seg_gdf = gpd.GeoSeries(southLine_seg, crs=crs)

	# Get coordinates from segmentation
	n_coords = northLine_seg_gdf.get_coordinates()
	s_coords = southLine_seg_gdf.get_coordinates()

	# Grab coordinates from one swath width
	north = n_coords.iloc[0]
	north_2 = n_coords.iloc[1] 

	south = s_coords.iloc[0]
	south_2 = s_coords.iloc[1]

	# Create lines
	northLine_2 = shapely.LineString([[north.x, north_2.y], [north_2.x, north_2.y]])
	southLine_2 = shapely.LineString([[south.x,south.y],[south_2.x,south_2.y]])

	# Calculate where tractor will be, ideally the center of the swath 
	tractor_position = (implement_width / 2)

	# Segmentize lines again
	northLine_seg_2 = northLine_2.segmentize(max_segment_length=tractor_position)
	southLine_seg_2 = southLine_2.segmentize(max_segment_length=tractor_position)

	if verbosity == True:
		print(northLine_seg_2.coords.xy)

	# Finally, create AB Line
	a_x = northLine_seg_2.coords.xy[0][1]
	a_y = northLine_seg_2.coords.xy[1][1]

	b_x = southLine_seg_2.coords.xy[0][1]
	b_y = southLine_seg_2.coords.xy[1][1]

	ab_line = shapely.LineString([[a_x, a_y], [b_x, b_y]])
	ab_line = gpd.GeoSeries(ab_line).set_crs(crs).to_crs("EPSG:4326")

	out_path = out_dir / "gpsLine"
	out_path.mkdir(exist_ok = True, parents = True)
	out_file = out_path / "gpsLine.shp"

	# Save this is a Shapefile, ready for importation
	ab_line.to_file(out_file)

def onOffHorizontalLines(westLine, eastLine, southEastCoord, southWestCoord, replicates, plotLengths, verbosity=False):

	'''
	westLine: GeoPandas GeoSeries object given from grab_boundary_coords function
	east_line: GeoPandas GeoSeries object given from grab_boundary_coords function
	replicates: (int), number of replicates the trial has
	verbosity: (bool), Do you want to see all of the plots? Print outs? Then set 'True'.

	Returns: List of the horizontal lines
	'''

	# Define our starting variables for the loop
	newWestLine = westLine
	newEastLine = eastLine

	# Define output
	plotLines = []

	# Create the loop to create the horizontal lines
	for x in range(replicates):
		if verbosity == True:
			print(f"Rep #{x+1}")

		for j in plotLengths:

			if verbosity == True:
				print(f"Plot Length: {j}-m")
				print(f"Original length of West line: {newWestLine.length}")
				print(f"Original length of East line: {newEastLine.length}")

			# Interpolate where lines will be
			westPlotPoint = newWestLine.interpolate(j)
			eastPlotPoint = newEastLine.interpolate(j)

			# Create the plot line
			plotLine = shapely.LineString([[westPlotPoint.x, westPlotPoint.y],
											[eastPlotPoint.x,eastPlotPoint.y]
										])
			plotLines.append(plotLine)

			# Recreate the East and West lines for the next cut
			newWestLine = shapely.LineString([[westPlotPoint.x,westPlotPoint.y],
												[southWestCoord[0],southWestCoord[1]]
											])
			newEastLine = shapely.LineString([[eastPlotPoint.x,eastPlotPoint.y],
												[southEastCoord[0],southEastCoord[1]]
											])

			if verbosity == True:
				print(f"Length of West line: {newWestLine.length}")
				print(f"Length of East line: {newEastLine.length}")

	# Create loop to extend all of these lines so that the original shape can be cut
	extendedLines = []
	for line in plotLines:
		extendedLine = shapely.affinity.scale(line,xfact=1.25,yfact=1,origin=line.centroid)
		extendedLines.append(extendedLine)

	if verbosity == True:

		for x in range(len(extendedLines)):
			shapely.plotting.plot_line(extendedLines[x], color='red',alpha=0.75)

		# shapely.plotting.plot_line(north_line[0])

	return extendedLines




def createOnOffGrid(verticleLines, site, verbosity=False, debug=False):	
	# Create a union of the lines
	verticle_union = shapely.union_all(verticleLines)

	# Rotate the original geometry
	site_geom = site.geometry.iloc[0]
	site_centroid =  site_geom.centroid.coords.xy
	site_centeroid_coords = (site_centroid[0][0], site_centroid[1][0])
	rotated = shapely.affinity.rotate(site_geom, angle = 0.954, origin = site_centeroid_coords, use_radians=False) # Angle chosen as best guess for EPSG:32613, may need to be adjusted for other coordinate reference systems

	# Split site_geom by the verticle lines first
	vSplit = shapely.ops.split(rotated, verticle_union)

	if verbosity == True:
		f,ax = plt.subplots(1)

		shapely.plotting.plot_polygon(rotated, ax=ax, color='black')
		for x in range(len(vSplit.geoms)):
			shapely.plotting.plot_polygon(vSplit.geoms[x],ax=ax, color='gold')
		plt.show()
		

	passes = []
	for c in range(len(vSplit.geoms)):

		column = vSplit.geoms[c]

		if column.area > 100:
			passes.append(column)


	if verbosity == True:
		# f,ax = plt.subplots(1)
		shapely.plotting.plot_polygon(passes[0],ax=ax, color="blue", alpha=1)
		shapely.plotting.plot_polygon(passes[1],ax=ax, color="green", alpha=1)
		shapely.plotting.plot_polygon(passes[2],ax=ax, color="red", alpha=1)
		plt.show()
		print(f"Number of Swaths: {len(passes)}")

	# Loop for pass number
	passNum = 1 

	# Get replicates from user
	replicates = int(input("How many replications will take place in each pass? "))
	if debug == True:
		replicates = 2

	# Split each swath first
	splitColumns = []

	for swath in passes:

		# swath = passes[0] # Debugging purposes

		if verbosity == True:
			print(f"Pass #{swath}")
			shapely.plotting.plot_polygon(swath, color = 'black', alpha=0.8)
			plt.show()

		poly_coords = swath.boundary.xy

		# Coordinates of swath
		southWest = (sorted(poly_coords[0])[0], sorted(poly_coords[1])[0])
		northWest = (sorted(poly_coords[0])[2], sorted(poly_coords[1])[3])
		southEast = (sorted(poly_coords[0])[3],sorted(poly_coords[1])[1])
		northEast = (sorted(poly_coords[0])[4], sorted(poly_coords[1])[4])

		# West Line
		westLine = shapely.LineString([northWest,southWest])

		# East Line
		eastLine = shapely.LineString([northEast,southEast])

		# South Line
		southLine_fix = shapely.LineString([southWest,southEast])

		if debug == True:
			shapely.plotting.plot_line(westLine, color='gold', alpha=0.8)
			shapely.plotting.plot_line(eastLine, color='darkblue', alpha=0.8)

		# Get plot lenghts from user 
		plotLengths = input(f"Plot Lengths for swath No.{passNum}: (in meters) ")

		if debug == True:
			plotLengthInt = [60,40,20]


		if verbosity == True:
			print(plotLengths)

		plotLengthsSplit = plotLengths.split(",")
		plotLengthInt= list(map(int,plotLengthsSplit))
		horizontalLines = onOffHorizontalLines(
			westLine,
			eastLine,
			southEast,
			southWest,
			replicates,
			plotLengthInt,
			verbosity=verbosity
		)

		passNum+=1

		union = shapely.union_all(horizontalLines)

		if verbosity == True:
			plotting.plot_line(union)

		hSplit = shapely.ops.split(swath, union)

		if verbosity ==  True:
			f,ax = plt.subplots(1)
			for x in range(len(hSplit.geoms)):
				plotting.plot_polygon(hSplit.geoms[x], ax=ax) 

		splitColumns.append(hSplit)
		

	# Create a geodataframe out of this
	series = []
	for g in splitColumns:
		grid_gdf = gpd.GeoDataFrame(g.geoms)
		series.append(grid_gdf)		

	splitsDf = pd.concat(series).reset_index()
	splitsDf = splitsDf.rename(columns={"index": "row"})
	splitsDf = splitsDf.rename(columns={0: "geometry"})
	splitsDf["col"] = splitsDf.groupby("row").cumcount()

	cols = [c for c in splitsDf.columns if c != "geometry"]
	splitsGdf = splitsDf[cols + ["geometry"]]
	splitsGdf = gpd.GeoDataFrame(splitsGdf, geometry="geometry")

	if verbosity == True:
		splitsGdf.plot(edgecolor='black', facecolor='gold')
	# Rotate geometry back to original position
	rotatedGeoms = []
	for i,geom in splitsGdf.iterrows():

		geometry = geom.geometry
		col = geom.col
		row = geom.row

		if verbosity == True:
			print(f"Column: {col}") 
			print(f"Row: {row}")

		if geometry.area > 1:
			rotat = shapely.affinity.rotate(geometry,angle = -0.954, origin = site_centeroid_coords, use_radians=False)

			# print(type(geom))

			rotatedGeoms.append({
				"row":row,
				"col": col,
				"geometry": rotat})

	# Create GeoDataFrame from this
	geomsGdf = gpd.GeoDataFrame(rotatedGeoms, geometry='geometry', crs=CRS)

	if verbosity == True:
		f,ax = plt.subplots(1)
		geomsGdf.plot(ax=ax, facecolor='none',edgecolor='black')

		print("Showing passes ...")
		for x in range(len(passes)):
			f,ax = plt.subplots(1)
			shapely.plotting.plot_polygon(passes[x],ax=ax, color='purple')
			plt.show()

	return geomsGdf



print("Starting Trial Creation ...")

#Import Data
debug = True

# Debugging parameters
if debug == True:
	project_root = "C:/Users/wrm100/gavinthegoose/trialKnittr"
	selectedSite = f"{project_root}/rawData/rampTestData/hunterWheatRamp.kml"
	selectedField = f"{project_root}/rawData/rampTestData/hunterFieldBoundary/hunterFieldBound.shp"
	rampRatesPath = f"{project_root}/rawData/rampTestData/hunterRampRates.csv"
	onOffRatesPath =f"{project_root}/rawData/onOffTestData/onOffRatesV2.csv"
	crsInput = 1

else:
	root = tkinter.Tk()
	root.withdraw()

	#File directories
	selectedSite = filedialog.askopenfilename(	
		title="Select the bounding box of the trial ...",
		filetypes=[("All Files", "*.*"), (".shp", "*.shp"),(".kml", "*.kml"),(".kmz", "*.kmz"), (".gpkg", "*.gpkg")]
	)
	selectedField = filedialog.askopenfilename(
		title="Select the field boundary for the trial location ...",
		filetypes=[("All Files","*.*"), (".shp", "*.shp"),(".kml", "*.kml"),(".kmz", "*.kmz"), (".gpkg", "*.gpkg")]
	)
	ratesPath = filedialog.askopenfile(
		title="Select rates CSV for the trial ...",
		filetypes=[("CSV", "*.csv")]
	)
	project_root = Path(filedialog.askdirectory(
	title="Select root directory for project ..."
	))

	# CRS for the project
	crsInput = int(input('''
	Choose CRS for the project:

	[1] EPSG:32613 (Most common in Sask)
	[2] EPSG:32612 (Western Sask)
	[3] EPSG:32614 (Eastern Sask)
	[4] Other (Requires further input)
	'''
	))

if crsInput == 1:
	CRS = "EPSG:32613"
elif crsInput == 2:
	CRS = "EPSG:32612"
elif crsInput == 3:
	CRS = "EPSG:32614"
elif crsInput == 4:
	CRS = input("Enter CRS for project: ")

				 
# Get inputs into exportation format
site_path = Path(selectedSite)
site_name = site_path.stem 
fieldBoundary_path = Path(selectedField) 

print(f"Site name: {site_name}")

# Create out directory
out_dir = Path(f"{project_root}/workingFiles/vector/{site_name}")
out_dir.mkdir(exist_ok = True, parents = True)

# Load data
site = gpd.read_file(site_path).to_crs(CRS) 
fieldBoundary = gpd.read_file(fieldBoundary_path).to_crs(CRS)
if debug == False:
	vrRates = pd.read_csv(ratesPath, header = None)
implement_width = int(input("What is the width of the implement in meters? "))
# plot_length = int(input("What is the length of the pl40

# Ask user if they want to see step-by-step building
verbosityInput = int(input('''
Would you like verbose outputs of the process? 
[0] No
[1] Yes
'''
))
verbosity = bool(verbosityInput)


if verbosity == True:
	print("You have chosen a verbose output")


# Gain trial type from user
trial_type = input('''
What type of trial is going in?  
[1] Ramp
[2] On/Off
'''
)

# Poly GDF Save Toggle
savePolyGDF = input(
'''
Would you like to save the grid of the trial?
[0] No
[1] Yes
'''
)

savePolyGDF = bool(savePolyGDF)

if verbosity == True:
	print(savePolyGDF)

# Convert into repsective names for following if statements
if int(trial_type) == 1:
	trialType = 'Ramp'
elif int(trial_type) == 2:
	trialType = 'On/Off'

if verbosity == True:
	print(f"Trial type of '{trialType}' chosen")


# Ramp-Style format
if trialType == 'Ramp':

	# Get plot lengths
	plot_length = int(input("What is the length of the plots in meters? "))

	# Get uniform rate for 
	fieldRate = float(input("What rate of product will be placed outside of the trial area (lbs/ac)? "))
	if debug == True:
		vrRates = pd.read_csv(rampRatesPath, header=None)
	# Parse our bounding box
	westLine, northLine, eastLine, southLine = grab_bounding_coords(site, crs = CRS, verbosity=verbosity)

	# Produce GPS Tractor lines
	tractor_gps_lines(northLine, southLine, implement_width, out_dir, crs = CRS, verbosity=verbosity)

	# Produce lines for plots
	verticleLines = createVerticleLines(northLine, southLine, implement_width, verbosity=verbosity)
	horizontal_lines = create_horizontal_lines(westLine, eastLine, plot_length, verbosity=verbosity)

	# Merge all plots together
	poly_gdf = create_grid(horizontal_lines, verticleLines, site, verbosity=verbosity)

	# # Save poly_gdf if the user would like
	# if savePolyGDF == True:
	# 	polyOutFolder = out_dir / "trialGrid"
	# 	polyOutFolder.mkdir(exist_ok=True, parents=True)

		

	# 	polyOutPath = polyOutFolder / "trialGrid.shp"
	# 	if verbosity == True:
	# 		print(f"Folder: {polyOutFolder}")
	# 		print(f"File: {polyOutPath}")

	# 	poly_gdf.to_file(polyOutPath)

	# Save output as needed
	input_product_values(poly_gdf, fieldBoundary, site_name, out_dir, vrRates, fieldRate, trialType, savePolyGDF)

# On-Off format
if trialType == 'On/Off':
	# Parse our horizontal lines
	westLine, northLine, eastLine, southLine = grab_bounding_coords(site, crs = CRS, verbosity=verbosity)
	# Get the verticle lines of the plots
	verticleLines = createVerticleLines(northLine,southLine,implement_width, verbosity=verbosity)
	
	# Create grid
	poly_gdf = createOnOffGrid(verticleLines, site, verbosity=verbosity)

	if debug == True:
		vrRates = pd.read_csv(onOffRatesPath, header=None)

	# Get field rate input from user
	fieldRate = float(input("What rate of product will be placed outside of the trial area (lbs/ac)? "))

	# Save output as needed
	input_product_values(poly_gdf, fieldBoundary, site_name, out_dir, vrRates, fieldRate, trialType)


