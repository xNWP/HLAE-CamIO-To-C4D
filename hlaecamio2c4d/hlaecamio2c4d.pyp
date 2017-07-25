"""
	file: hlaecamio2c4d.pyp
	author: Brett "xNWP" Anthony
	
	Allows import of HLAE CamIO information to Cinema4D.
	Mappings are:
	
			Without Import for map usage
				X -> Z
				Y -> -X
				Z -> Y

			With Import for map usage
				X -> X
				Y -> Y
				Z -> -Z

"""

""" 		ID LAYOUT

0 - Primary UI
	50 - Header Image
	100 - Group (program information)
		101 - Versioning Info
		102 - Description
		103 - Author
		104 - Website
	200 - Group (Browse for CamIO File)
		201 - Prompt
		250 - Button Group
			251 - Browse Wide
			252 - Browse Tiny
		254 - Import For Map Usage ChkBox
	300 - Group (Import and Close Buttons)
		301 - Import Btn
		302 - Close Btn

1 -	Get Resolution UI
	500 - Group (Main Group)
		501 - Request Info
		502 - "" 2
		503 - "" 3
		550 - Group (Field Group)
			551 - Width Text
			552 - Width Field
			553 - Height Test
			554 - Height Field
		600 - Group (Confirm Group)
			601 - Confirm Button
			602 - Cancel Button
"""

# Imports
import c4d
from c4d import plugins
from c4d import documents
from c4d import gui
from c4d.storage import LoadDialog

import math
import webbrowser

# Global Vars
PLUGIN_VERSION = "v1.0"
PLUGIN_VERSION_FLOAT = 1.0
PLUGIN_NAME = "HLAE CamIO 2 Cinema4D " + PLUGIN_VERSION
PLUGIN_DESCRIPTION = "Converts HLAE CamIO to Cinema4D Camera Data."
PLUGIN_ID = 1000000001 #temp test id
PLUGIN_WEBPAGE = "http://github.com/xNWP"
HLAECAM_VERSION = 1
RECORDING_WIDTH = 0
RECORDING_HEIGHT = 0

# Process Data
def DoWork(file, ForMap):

	c4d.StatusSetSpin()
	CamIOFile = open(file.decode("utf-8"))
	
	# load in our headers and test them
	header = CamIOFile.readline()
	
	if(header != "advancedfx Cam\n"):
		gui.MessageDialog("Not a valid HLAE CamIO File.")
		return False
	
	header = CamIOFile.readline()
	
	if(float(header[8:]) > HLAECAM_VERSION):
		gui.MessageDialog("HLAE CamIO version not supported by this plugin, check releases for a new version that does.")
		return False
	
	c4d.StopAllThreads()
	
	header = CamIOFile.readline()
	
	if(header[9:] == "none\n"):
		ScaleFov = False
		
		global RECORDING_WIDTH
		global RECORDING_HEIGHT
		RECORDING_WIDTH = 0
		RECORDING_HEIGHT = 0
		
		print "%s: CS:GO Scaling Detected, requesting recording resolution from user." % (PLUGIN_NAME)
		GetRes = GetResolution()
		GetRes.Open(c4d.DLG_TYPE_MODAL, PLUGIN_ID, -1, -1, 350, 205, 1)
		
		if(not RECORDING_WIDTH == 0 or not RECORDING_HEIGHT == 0): # catch non set res
			RelatedRatio = (float(RECORDING_WIDTH)/RECORDING_HEIGHT)/(4.0/3.0)
		else:
			return False
	else:
		ScaleFov = True
	
	if (ForMap == True):
		print "%s: Importing for map." % (PLUGIN_NAME)
	
	c4d.StatusSetSpin()
	
	CamIOFile.readline() # skip useless lines
	CamIOFile.readline()
	
	# read all our data into an 8d vector
	RawData = []
	CamData = CamIOFile.readlines()
	CamIOFile.close()
	
	for line in CamData:	# read line by line
		data = line.split()	# split each line into the 8 variables
		RawData.append(data)# add it to our list
		
		# check if the time isn't changing (cannot import)
		if (len(RawData) > 1):
			lastFrameTime = RawData[len(RawData) - 2][0]
			currentFrameTime = RawData[len(RawData) - 1][0]
			if (float(currentFrameTime) == float(lastFrameTime)):
				print "%s: ERROR: Non-Changing Time between frames %s and %s." % (PLUGIN_NAME, len(RawData) - 2, len(RawData) - 1)
				gui.MessageDialog("File has duplicate times (make sure you don't pause while recording).")
				return False
	
	framerate = ((float(RawData[-1][0]) - float(RawData[0][0])) / len(RawData)) ** -1 # Calculate the framerate
	
	CurrentProj = c4d.documents.GetActiveDocument() # the current open project.
	
	CurrentProj.StartUndo()
	
	print "%s: Setting Framerate to %s (r/f %s)" % (PLUGIN_NAME, round(framerate, 0), framerate)	
	CurrentProj.SetFps(int(round(framerate, 0))) # set the fps to match our data, we'll round to the nearest full value
												 # this doesn't account for people recording at weird framerates (such as 29.97)
												 # but this should be a slim margin of people, they may override the fps manually if they choose
	
	C4DProjLength = c4d.BaseTime(len(RawData) - 1,CurrentProj.GetFps()) # c4d is zero indexed, 0 -> n - 1
	print "%s: Setting Number of Frames to %s (%s s)." % (PLUGIN_NAME, (C4DProjLength.GetFrame(CurrentProj.GetFps()) + 1), (C4DProjLength.Get() + (1.0/CurrentProj.GetFps())))
	CurrentProj.SetMaxTime(C4DProjLength) # set the project length accordingly.
	CurrentProj.SetLoopMaxTime(C4DProjLength) # set the preview time as well
	
	# if the user had to choose recording res we'll setup the project for them
	if (not ScaleFov):
		CurrentRenderSettings = CurrentProj.GetActiveRenderData()
		CurrentRenderSettings[c4d.RDATA_XRES] = RECORDING_WIDTH
		CurrentRenderSettings[c4d.RDATA_YRES] = RECORDING_HEIGHT
		c4d.EventAdd()
		print "%s: Set resolution (w: %s, h: %s)." % (PLUGIN_NAME, RECORDING_WIDTH, RECORDING_HEIGHT)
		
	# Create our camera
	Camera = c4d.BaseObject(c4d.Ocamera)
	Camera.SetName("HLAE CamIO Camera")
	Camera[c4d.CAMERAOBJECT_TARGETDISTANCE] = 250
	
	if(ForMap == True): # Null for map import
		RotateNull = c4d.BaseObject(c4d.Onull)
		RotateNull.SetRelRot(c4d.Vector(0, math.pi/2, 0))
		RotateNull.SetName("HLAE CamIO Camera")
		CurrentProj.InsertObject(RotateNull)
		CurrentProj.InsertObject(Camera, RotateNull)
	else:
		CurrentProj.InsertObject(Camera)

	c4d.EventAdd()
	
	# Create Tracks
	trackX = c4d.CTrack(Camera,
                    c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_POSITION,c4d.DTYPE_VECTOR,0),
                               c4d.DescLevel(c4d.VECTOR_X,c4d.DTYPE_REAL,0)))
	trackY = c4d.CTrack(Camera,
                    c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_POSITION,c4d.DTYPE_VECTOR,0),
                               c4d.DescLevel(c4d.VECTOR_Y,c4d.DTYPE_REAL,0)))
	trackZ = c4d.CTrack(Camera,
                    c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_POSITION,c4d.DTYPE_VECTOR,0),
                               c4d.DescLevel(c4d.VECTOR_Z,c4d.DTYPE_REAL,0)))
							   
	trackH = c4d.CTrack(Camera,
                    c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_ROTATION,c4d.DTYPE_VECTOR,0),
                               c4d.DescLevel(c4d.VECTOR_X,c4d.DTYPE_REAL,0)))
	trackP = c4d.CTrack(Camera,
                    c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_ROTATION,c4d.DTYPE_VECTOR,0),
                               c4d.DescLevel(c4d.VECTOR_Y,c4d.DTYPE_REAL,0)))
	trackB = c4d.CTrack(Camera,
                    c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_ROTATION,c4d.DTYPE_VECTOR,0),
                               c4d.DescLevel(c4d.VECTOR_Z,c4d.DTYPE_REAL,0)))
	
	trackFov = c4d.CTrack(Camera,
					c4d.DescID(c4d.DescLevel(c4d.CAMERAOBJECT_FOV,c4d.DTYPE_REAL,0)))
							   
	# Insert Tracks
	Camera.InsertTrackSorted(trackX)
	Camera.InsertTrackSorted(trackY)
	Camera.InsertTrackSorted(trackZ)
	Camera.InsertTrackSorted(trackH)
	Camera.InsertTrackSorted(trackP)
	Camera.InsertTrackSorted(trackB)
	Camera.InsertTrackSorted(trackFov)
	
	# Get Curves
	curveX = trackX.GetCurve()
	curveY = trackY.GetCurve()
	curveZ = trackZ.GetCurve()
	curveH = trackH.GetCurve()
	curveP = trackP.GetCurve()
	curveB = trackB.GetCurve()
	curveFov = trackFov.GetCurve()
	
	fps = CurrentProj.GetFps()
	i = 0
	
	c4d.StatusClear()
	
	for frame in RawData:
		# Status Bar
		c4d.StatusSetText("HLAE CamIO Import: Frame %s of %s" % (i + 1, len(RawData)))
		c4d.StatusSetBar(((i + 1.0) / len(RawData)) * 100)
	
		# X POS
		keyDict = curveX.AddKey(c4d.BaseTime(i, fps))
		key = keyDict["key"]
		if(ForMap == True):
			key.SetValue(curveX, float(frame[1]))
		else:
			key.SetValue(curveX, -1*float(frame[2]))
		
		# Y POS
		keyDict = curveY.AddKey(c4d.BaseTime(i, fps))
		key = keyDict["key"]
		key.SetValue(curveY, float(frame[3]))
		
		# Z POS
		keyDict = curveZ.AddKey(c4d.BaseTime(i, fps))
		key = keyDict["key"]
		if(ForMap == True):
			key.SetValue(curveZ, float(frame[2]))
		else:
			key.SetValue(curveZ, float(frame[1]))
		
		# HEADING
		keyDict = curveH.AddKey(c4d.BaseTime(i, fps))
		key = keyDict["key"]
		if(ForMap == True):
			key.SetValue(curveH, math.radians(float(frame[6])) - math.pi/2)
		else:
			key.SetValue(curveH, math.radians(float(frame[6])))
		
		# PITCH
		keyDict = curveP.AddKey(c4d.BaseTime(i, fps))
		key = keyDict["key"]
		key.SetValue(curveP, -1*math.radians(float(frame[5])))
		
		# BANK
		keyDict = curveB.AddKey(c4d.BaseTime(i, fps))
		key = keyDict["key"]
		key.SetValue(curveB, math.radians(float(frame[4])))
		
		# FoV
		keyDict = curveFov.AddKey(c4d.BaseTime(i, fps))
		key = keyDict["key"]
		
		if not ScaleFov:
			fov = float(frame[7])/2
			fov = math.radians(fov)
			fov = math.tan(fov)
			fov = math.degrees(fov) * RelatedRatio
			fov = math.atan(math.radians(fov))
			fov = math.degrees(fov) * 2
			key.SetValue(curveFov, math.radians(fov))
		else:
			key.SetValue(curveFov, math.radians(float(frame[7])))
		
		i = i + 1
	
	c4d.StatusClear()
	c4d.EventAdd()
	
	CurrentProj.EndUndo()
	
	print "%s: Import Completed." % (PLUGIN_NAME)
	gui.MessageDialog("Successfully imported %s frames." % (len(RawData)))
	c4d.DrawViews(c4d.DRAWFLAGS_FORCEFULLREDRAW)
	
	return True
	
# Banner Definition
class Banner(gui.GeUserArea):
	def GetMinSize(self):
		self.width = 280
		self.height = 100
		return (self.width, self.height)
	
	def DrawMsg(self, x1, y1, x2, y2, msg):
		bmp = c4d.bitmaps.BaseBitmap()
		path = __file__
		path = path.replace("hlaecamio2c4d.pyp", "") # remove plugin name
		path += "res\\banner.png"
		bmp.InitWith(path)
		
		self.DrawBitmap(bmp, 0, 0, bmp.GetBw(), bmp.GetBh(), 0, 0, bmp.GetBw(), bmp.GetBh(), c4d.BMP_NORMALSCALED)
	
	
# UI Definition
class PrimaryUI(gui.GeDialog):
	
	# BANNER
	TopBanner = Banner()
	
	def CreateLayout(self):
		# Creates our layout.
		self.SetTitle(PLUGIN_NAME)
		
		# BANNER
		self.AddUserArea(50, c4d.BFH_CENTER, 280, 100)
		self.AttachUserArea(self.TopBanner, 50)
		self.TopBanner.LayoutChanged()
		self.TopBanner.Redraw()
		
		self.GroupBegin(100, c4d.BFH_SCALE, 1, 5) # PROGRAM INFO GROUP
		
		self.AddStaticText(101, c4d.BFH_RIGHT, 0, 0, PLUGIN_VERSION)
		self.AddStaticText(102, c4d.BFH_CENTER, 0, 0, PLUGIN_DESCRIPTION)
		self.AddStaticText(103, c4d.BFH_CENTER, 0, 0, "Plugin by xNWP")
		self.AddStaticText(104, c4d.BFH_CENTER, 0, 0, PLUGIN_WEBPAGE)
		
		self.GroupEnd()
		
		self.AddStaticText(0, c4d.BFH_CENTER, 0, 3) # spacer
		self.AddSeparatorH(300, c4d.BFH_CENTER)
		self.AddStaticText(0, c4d.BFH_CENTER, 0, 3) # spacer
		
		self.GroupBegin(200, c4d.BFH_SCALE, 1, 3, initw=380) # Browse For CAMIO Group
		self.GroupBorderNoTitle(c4d.BORDER_THIN_IN)
		
		self.AddStaticText(201, c4d.BFH_SCALE, 0, 16, "Select a valid CamIO File...")
		
		self.GroupBegin(250, c4d.BFH_SCALE, 2, 2) # Browse Buttons Group
		self.AddButton(251, c4d.BFH_LEFT, 225, 0) # Wide Button
		self.AddButton(252, c4d.BFH_RIGHT, 0, 0, "...") # Tiny Button
		self.GroupEnd()
		
		self.AddCheckbox(253, c4d.BFH_CENTER, 0, 0, "Import for map usage")
		
		self.AddStaticText(0, c4d.BFH_CENTER, 0, 3) # spacer
		
		
		self.GroupEnd()
		
		self.AddStaticText(0, c4d.BFH_CENTER, 0, 3) # spacer
		
		self.GroupBegin(300, c4d.BFH_SCALE, 2, 1) # Import/Close Group
		
		self.AddButton(301, c4d.BFH_LEFT, 80, 16, "Import")
		self.AddButton(302, c4d.BFH_RIGHT, 80, 16, "Close")
		
		self.GroupEnd()
		
		return True


	# USER CONTROL SECTION
	def Command(self, id, msg):
		
		if(id == 251 or id == 252): # Browse Button Hit
			CamIOFile = LoadDialog(c4d.FILESELECTTYPE_ANYTHING, "Please select the CamIO file for import...")
			
			if(CamIOFile != None): # user didn't cancel the browse
				self.SetString(251, CamIOFile)
				print "%s: File to load set as '%s'" % (PLUGIN_NAME, CamIOFile)
		
			return True
			
		if(id == 253): # Import for Maps option
			return True
		if(id == 302): # Close button
			self.Close()
			return True
			
		if(id == 301): # Import Button
			if(self.GetString(251) == ""): # catch no file
				gui.MessageDialog("Please first specify a CamIO File to import.")
				return False
			else:
				ImportCam = DoWork(self.GetString(251), self.GetBool(253)) # Pass the file to the main proccessing function
				if ImportCam:
					self.Close()
			return True

# Get Resolution UI
class GetResolution(gui.GeDialog):
	def CreateLayout(self):
		c4d.StatusClear()
		self.SetTitle(PLUGIN_NAME + " - CS:GO Scaling Detected")
		
		self.AddStaticText(0, c4d.BFH_CENTER, 0, 3) # spacer

		self.GroupBegin(500, c4d.BFH_SCALE, 1, 7) # Main Group
		self.AddStaticText(501, c4d.BFH_CENTER, 0, 0, "This file was exported without corrective FoV scaling,")
		self.AddStaticText(502, c4d.BFH_CENTER, 0, 0, "please enter the resolution that this file was recorded at.")
		self.AddStaticText(0, c4d.BFH_CENTER, 0, 3) # spacer
		self.AddStaticText(503, c4d.BFH_CENTER, 0, 0, "hint: use FoV Scaling alienSwarm next time to skip this step.")
		
		self.AddStaticText(0, c4d.BFH_CENTER, 0, 8) # spacer
		
		self.GroupBegin(550, c4d.BFH_SCALE, 2, 2) # Field Group
		self.AddStaticText(551, c4d.BFH_CENTER, 0, 0, "Width:")
		self.AddStaticText(552, c4d.BFH_CENTER, 0, 0, "Height:")
		self.AddEditText(553, c4d.BFH_CENTER, 140, 0)
		self.AddEditText(554, c4d.BFH_CENTER, 140, 0)
		self.GroupEnd()
		
		self.GroupBegin(600, c4d.BFH_SCALE, 2, 1) # Confirm Group
		self.AddButton(601, c4d.BFH_LEFT, 80, 16, "Confirm")
		self.AddButton(602, c4d.BFH_RIGHT, 80, 16, "Cancel")
		self.GroupEnd()
		
		self.GroupEnd()
		
		return True
		
	def Command(self, id, msg):
		if (id == 602): # Cancel
			self.Close()
			return False
		
		if (id == 601): # Confirm
			try: # catch non int input
				global RECORDING_WIDTH
				global RECORDING_HEIGHT

				tmp_w = int(self.GetString(553))
				tmp_h = int(self.GetString(554))
				
				if(not tmp_w > 0 or not tmp_h > 0): # catch negative/zero
					raise
				
				RECORDING_WIDTH = tmp_w
				RECORDING_HEIGHT = tmp_h
				
				print "%s: Using width: %s, height: %s." % (PLUGIN_NAME, str(RECORDING_WIDTH), str(RECORDING_HEIGHT))
			
			except:
				gui.MessageDialog("Width and height must both be positive integers.")
				return False
			
			self.Close()
			return True
		
		return False

# Plugin Definition
class HLAECamio2C4d(plugins.CommandData):
	
	def Execute(self, BaseDocument):
	# defines what happens when the user clicks the plugin in the menu
		UI = PrimaryUI()
		UI.Open(c4d.DLG_TYPE_MODAL, PLUGIN_ID, -1, -1, 300, 360, 0) # open ui
		return True
		
# Main Definition
def main():
	# Icon
	icon = c4d.bitmaps.BaseBitmap()
	iconpath = __file__
	iconpath = iconpath.replace("hlaecamio2c4d.pyp", "") # remove plugin name
	iconpath += "res\\icon.png"
	icon.InitWith(iconpath)
	
	# Register the plugin
	plugins.RegisterCommandPlugin(PLUGIN_ID, PLUGIN_NAME, 0, icon, PLUGIN_DESCRIPTION, HLAECamio2C4d())
	
	# Console confirmation
	print "Loaded HLAE CamIO 2 Cinema4D %s" % (PLUGIN_VERSION)

# Main Execution
main()