from tkinter import *
from tkinter import filedialog as fd
from tkinter import messagebox
from tkinter import ttk
from tkinter import scrolledtext
import numpy as np
from PIL import Image, ImageTk, ImageOps
import string, time, os, sys, math

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Suppress Tk deprecation warning on macOS
if sys.platform == 'darwin':
    os.environ['TK_SILENCE_DEPRECATION'] = '1'

platform = "win"
if any(key for key in os.environ if key.startswith('ANDROID_')) == True:
	platform = "and"
	from usb4a import usb
	from usbserial4a import serial4a
else:
	import serial
	import serial.tools.list_ports

ser = None
serialConnected = False
availablePorts = []

root = Tk()
root.geometry('800x1200')  # Increased height further
root.minsize(800, 1200)    # Set minimum window size
root.title('Neurotech Hub Hyperspectral Imager')

# Modern color scheme
COLORS = {
    'bg': '#e5e5e5',           # Consistent light gray background
    'fg': '#1d1d1f',           # Dark text
    'accent': '#007AFF',       # Native blue accent
    'accent_fg': 'white',      # White text on accent buttons
    'input_bg': 'white',       # White input background
    'input_fg': '#1d1d1f',     # Dark text for inputs
    'input_border': '#d2d2d7', # Light gray border
    'disabled': '#86868b',     # Disabled text/controls
    'success': '#34c759',      # Green for success states
    'error': '#ff3b30',        # Red for error states
    'warning': '#ff9500',      # Orange for warnings
    'plot_bg': 'white',        # White plot background
    'label_fg': '#1d1d1f',     # Dark text for labels
}

# Configure ttk styles for a modern look
from tkinter import ttk
style = ttk.Style()

if sys.platform == 'darwin':  # macOS specific styling
    style.theme_use('aqua')
else:
    style.theme_use('clam')  # Modern theme for Windows/Linux

# Configure ttk styles
style.configure('TButton', 
    padding=(6, 4),  # Reduced horizontal padding
)
style.configure('TEntry', 
    padding=4
)
style.configure('TFrame', 
    background=COLORS['bg']
)
style.configure('TLabel', 
    padding=2,
    background=COLORS['bg']
)
style.configure('TCombobox', 
    padding=4
)
style.configure('Horizontal.TScale',
    sliderrelief='flat'
)

# Configure root window
root.configure(bg=COLORS['bg'])
root.option_add('*Font', ('System', 10))  # Use system font

# Configure root grid weights for vertical spacing - matching GUI_old.py
root.rowconfigure(0, weight=0)  # Serial frame - fixed
root.rowconfigure(1, weight=0)  # Top frame - fixed  
root.rowconfigure(2, weight=0)  # Frame2 - fixed
root.rowconfigure(3, weight=0)  # Frame3 - fixed
root.rowconfigure(4, weight=1)  # Image display - main expansion
root.rowconfigure(5, weight=0)  # Spectral plot - fixed
root.rowconfigure(6, weight=0)  # Controls - fixed
root.columnconfigure(0, weight=1)

# Update matplotlib style for native look
plt.style.use('default')
matplotlib_style = {
    'figure.facecolor': COLORS['plot_bg'],
    'axes.facecolor': COLORS['plot_bg'],
    'axes.edgecolor': COLORS['input_border'],
    'axes.labelcolor': COLORS['fg'],
    'axes.spines.top': False,
    'axes.spines.right': False,
    'grid.alpha': 0.3,
    'grid.color': COLORS['input_border'],
}
plt.rcParams.update(matplotlib_style)

np.set_printoptions(suppress=False, precision=3, threshold=sys.maxsize, linewidth=sys.maxsize)

cieWav = []
chlA = []
chlB = []
nIR = []
cieX = []
cieY = []
cieZ = []
nUV = []


pixels = int(288)
baseInt = int(550) # specifies the minimum hardware integration time in microseconds. 
wavCoef = []
radSens = []
linCoefs = []
wavelength = []
wavelengthBins = []
wavelengthBoxcar = []
unitNumber = int(0)
cieXt = [0.0] * pixels
cieYt = [0.0] * pixels
cieZt = [0.0] * pixels
chlAt = [0.0] * pixels
chlBt = [0.0] * pixels
nIRt = [0.0] * pixels
nUVt = [0.0] * pixels
saveLabel = StringVar()
dataString = ""
output = ""
serialName = ""
visSystems = []
receptorNames = []
receptorVals = []
baudrate = 115200

# Add serial logging
def logSerial(message, direction="OUT"):
    """Log serial communication for debugging"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {direction}: {message}")

def safeSerialWrite(data):
    """Safely write to serial with logging and error handling"""
    if ser is None:
        print("ERROR: Serial connection not available")
        return False
    try:
        logSerial(data, "OUT")
        ser.write(str.encode(data))
        return True
    except Exception as e:
        print(f"ERROR writing to serial: {e}")
        return False

def safeSerialRead():
    """Safely read from serial with logging and error handling"""
    if ser is None:
        print("ERROR: Serial connection not available")
        return None
    try:
        data = ser.readline()
        if data:
            decoded = data.decode('utf-8', 'replace').strip()
            logSerial(decoded, "IN")
            return decoded
        return None
    except Exception as e:
        print(f"ERROR reading from serial: {e}")
        return None

def scanSerialPorts():
    """Scan for available serial ports and update the dropdown"""
    global availablePorts
    availablePorts = []
    
    if platform == 'and':
        usb_device_list = usb.get_usb_device_list()
        device_name_list = [device.getDeviceName() for device in usb_device_list]
        availablePorts = device_name_list
    else:
        ports = serial.tools.list_ports.comports()
        availablePorts = [p.device for p in ports]
    
    # Update the dropdown
    serialPortVar.set('')  # Clear current selection
    serialPortDropdown['values'] = availablePorts
    
    if availablePorts:
        updateStatus(f"Found {len(availablePorts)} port(s)")
        # Auto-select the last port (often the most recently connected device)
        serialPortVar.set(availablePorts[-1])
    else:
        updateStatus("No serial ports found")
    
    print(f"Available ports: {availablePorts}")

def connectSerial():
    """Connect to the selected serial port"""
    global ser, serialName, serialConnected
    
    selectedPort = serialPortVar.get()
    if not selectedPort:
        updateStatus("Please select a serial port")
        return
    
    try:
        if ser and serialConnected:
            disconnectSerial()
        
        if platform == 'and':
            deviceName = usb.get_usb_device(selectedPort)
            while not usb.has_usb_permission(deviceName):
                usb.request_usb_permission(deviceName)
                time.sleep(1)
            ser = serial4a.get_serial_port(selectedPort, baudrate, 8, 'N', 1, timeout=1)
        else:
            ser = serial.Serial(selectedPort, baudrate, timeout=1)
        
        serialName = selectedPort
        serialConnected = True
        updateStatus(f"Connected to {selectedPort}")
        
        # Update button states
        btConnect.config(state="disabled")
        btDisconnect.config(state="normal")
        btScan.config(state="disabled")
        serialPortDropdown.config(state="disabled")
        
        # Enable the Start button
        btStart.config(state="normal")
        
        print(f"Successfully connected to {selectedPort}")
        
    except Exception as e:
        updateStatus(f"Connection failed: {str(e)}")
        print(f"Failed to connect to {selectedPort}: {e}")
        ser = None
        serialConnected = False

def disconnectSerial():
    """Disconnect from the current serial port"""
    global ser, serialConnected
    
    if ser:
        try:
            ser.close()
        except:
            pass
        ser = None
    
    serialConnected = False
    updateStatus("Disconnected")
    
    # Update button states
    btConnect.config(state="normal")
    btDisconnect.config(state="disabled")
    btScan.config(state="normal")
    serialPortDropdown.config(state="readonly")
    
    # Disable the Start button
    btStart.config(state="disabled")
    
    print("Disconnected from serial port")

def connect():
	global ser, serialName
	# This function is now called during initial setup
	# Actual connection is handled by connectSerial()
	scanSerialPorts()  # Scan ports on startup

try:
	connect()
except:
	print("Initial port scan failed")
	print("Use the Scan button to find available ports")
	
print(ser)

def readLine(ta):
	ta.pop(0)
	ta.pop(0)
	ta = list(filter(None, ta))
	ta = [float(i) for i in ta]
	#print(ta)
	return ta
	


def unitSetup():
	global unitNumber, wavCoef, radSens, linCoefs, wavelength, wavelengthBins, wavelengthBoxcar, cieXt, cieYt, cieZt, chlAt, chlBt, nIRt, nUVt, cieWav, chlA, chlB, nIR, cieX, cieY, cieZ, nUV, receptorNames, receptorVals


	if(len(wavCoef) != pixels or len(radSens) != pixels): # only load values from file the first time the code runs (to work out unit number)
		for line in open("./calibration_data.txt"):
			row = line.split(',')
			#print(row)
			try:
				int(row[0])
			except:
				print(" ")
			else:
				if(int(row[0]) == unitNumber):
##					print(row)
					if(row[1] == "wavCoef"):
						wavCoef = row
						wavCoef.pop(0)
						wavCoef.pop(0)
						wavCoef = list(filter(None, wavCoef))
						wavCoef.pop(len(wavCoef)-1)
##						print("waveCoef: " + str(len(wavCoef)))
						wavCoef = [float(i) for i in wavCoef]
					if(row[1] == "radSens"):
						radSens = row
						radSens.pop(0)
						radSens.pop(0)
						radSens = list(filter(None, radSens))
						radSens.pop(len(radSens)-1)
##						print("radSens: " + str(len(radSens)))
						radSens = [float(i) for i in radSens]
##						print(radSens)
					if(row[1] == "linCoefs"):
						linCoefs = row
						linCoefs.pop(0)
						linCoefs.pop(0)
						linCoefs = list(filter(None, linCoefs))
						linCoefs.pop(len(linCoefs)-1)
##						print("linCoefs: " + str(len(linCoefs)))
						linCoefs = [float(i) for i in linCoefs]
						
		for line2 in open("./sensitivity_data.csv"):
			row = line2.split(',')
			# ~ print(row)
			if(row[0] == "base"):
				if(row[1] == "cieWav"):
					cieWav = row
					cieWav.pop(0)
					cieWav.pop(0)
					cieWav = list(filter(None, cieWav))
					cieWav = [int(i) for i in cieWav]
	##				print(cieWav)
				elif(row[1] == "chlA"):
					chlA = readLine(row)
				elif(row[1] == "chlB"):
					chlB = readLine(row)
				elif(row[1] == "nIR"):
					nIR = readLine(row)
				elif(row[1] == "cieX"):
					cieX = readLine(row)
				elif(row[1] == "cieY"):
					cieY = readLine(row)
				elif(row[1] == "cieZ"):
					cieZ = readLine(row)
				elif(row[1] == "nUV"):
					nUV = readLine(row)
			else:
					receptorNames.append(row[0] +"_" + row[1])
					floatVals = row[2:]
					floatVals = [float(value) for value in floatVals if value.replace('.', '', 1).isdigit()]
					receptorVals.append(floatVals)

	
	# COMMENTED OUT WITH RECEPTOR FUNCTIONALITY
	# receptorListbox.delete(0, "end")  # Clear current listbox
	# for item in receptorNames:  # Insert new options
	# 	# ~ print(item)
	# 	receptorListbox.insert("end", item)


	
	if(len(wavCoef) != 6 or len(radSens) != pixels or len(linCoefs) != 2):
		#settingsLabel.config(text="error - calibration data not found\nEnsure calibration_data.txtis present\nand has data for unit #" + str(unitNumber))
		#return
		updateStatus("Missing calibration data")
		print("error - calibration data not found\nEnsure calibration_data.txt is present\nand has data for unit #" + str(unitNumber))
		print("waveCoef: " + str(len(wavCoef)))
		print("radSens: " + str(len(radSens)))
		print("linCoefs: " + str(len(linCoefs)))


	wavelength = []
	for i in range(0,pixels):
		wavelength.append(wavCoef[0]+wavCoef[1]*i+wavCoef[2]*i**2+wavCoef[3]*i**3+wavCoef[4]*i**4+wavCoef[5]*i**5)

	#---set up wavelength bin widths array-------
	wavelengthBins = []
	for i in range(0,pixels-1):
		wavelengthBins.append(wavelength[i+1]-wavelength[i])
	wavelengthBins.append(wavelength[pixels-1]-wavelength[pixels-2])

	# creare array of wavelengths matching boxcar scale for plotting
	wavelengthBoxcar = []
	for i in range(0, pixels, boxcarN): #increment in boxcar size
		wavelengthBoxcar.append(wavCoef[0]+wavCoef[1]*i+wavCoef[2]*i**2+wavCoef[3]*i**3+wavCoef[4]*i**4+wavCoef[5]*i**5)


	#------resample spectral sensitivities at spectrometer wavelengths---------
	for i in range(0,pixels):
		for j in range(0, len(cieWav)):
			if(round(wavelength[i]) == cieWav[j]):
				cieXt[i] = cieX[j]
				cieYt[i] = cieY[j]            
				cieZt[i] = cieZ[j]
				chlAt[i] = chlA[j]
				chlBt[i] = chlB[j]            
				nIRt[i] = nIR[j]
				nUVt[i] = nUV[j]


panFrom = StringVar()
panTo = StringVar()
panResolution = StringVar()
tiltFrom = StringVar()
tiltTo = StringVar()
tiltResolution = StringVar()
maxIntTime = StringVar()
boxcarVal = StringVar()
darkRepVal = StringVar()
reflVal = StringVar()
specOutVal = StringVar()

panFrom.set("-60")  # Degrees (-90 to 90)
panTo.set("60")     # Degrees (-90 to 90)
panResolution.set("30")  # Degrees between positions
tiltFrom.set("-60")  # Degrees (-90 to 90)
tiltTo.set("60")     # Degrees (-90 to 90)
tiltResolution.set("30")  # Degrees between positions
maxIntTime.set("2000") # max int time microseconds
boxcarVal.set("2")
darkRepVal.set("120")
tt = time.time()
reflVal.set("99")
specOutVal.set("")

reflFlag = 0

darkTimes = []
darkVals = []

## RGB image
imLum = []
imR = []
imG = []
imB = []
imCol = []
maxRGB = 1E-10
imSatR = []
imSatB = []


## extreme spectral range image
imI = []
imGG = []
imU = []
maxIGU = 1E-10

## NDVI image
imChlA = []
imChlB = []
imNDVI = []


## hspec image - le values in array
hspec = []
hspecPan = []
hspecTilt = []



panStart = int(0)
panStop = int(0)
pan_Res = int(0)
panDim = int(11) ## initially 11 based on other start settings
tiltStart = int(0)
tiltStop = int(0)
tilt_Res = int(0)
tiltDim = int(11)

scanningFlag = int(0)
stopFlag = int(0)
fileImportFlag = int(0);
loadPath = ""
loadLine = 0
lines = ("")
ct = '' # savepath


boxcarN = int(1)
focusPos = 0
preview = 1
plotImX = 100
plotImY = 100
selX = -1
selY = -1
refs = [] #100% reflectance vals
wbR = 1.0
wbG = 1.0
wbB = 1.0
wbI = 1.0
wbGG = 1.0
wbU = 1.0

def updateStatus(ts):
    statusLabel.config(text=ts)

def plotGraph(status):
	global plotImX, plotImY, wbR, wbG, wbB, wbI, wbGG, wbU
##        print("plotting")
	# normalise to max=1 and non-linearise with power function
	if len(imR) > 0:
		
		br = 100/brightnessScale.get()
		if preview <= 2:
                        ## avoid raising negative numbers to power (numpy doesn't like it)
			nImR = np.sign(imR) * ((np.abs(imR * wbR)/maxRGB)**0.42) * 255 * br
			nImG = np.sign(imG) * ((np.abs(imG * wbG)/maxRGB)**0.42) * 255 * br
			nImB = np.sign(imB) * ((np.abs(imB * wbB)/maxRGB)**0.42) * 255 * br
			
			nImR = np.clip(nImR, 0, 255)
			nImG = np.clip(nImG, 0, 255)
			nImB = np.clip(nImB, 0, 255)

			if preview <= 1: ## RGB images
				imCol = np.dstack((nImR, nImG, nImB))
			else: ## saturation image

				nImR = nImG ## where saturated turn red, otherwise grey (match green)
				nImB = nImG - imSatR ## where saturated turn red
				nImG = nImG - imSatR ## where saturated turn red
				nImB = np.clip(nImB, 0, 255)
				nImB = nImB + (imSatB * 5) ## add blue to show degere of saturation across wavelengths, so magenta will be fully saturated
				nImR = np.clip(nImR, 0, 255)
				nImG = np.clip(nImG, 0, 255)
				nImB = np.clip(nImB, 0, 255)
				imCol = np.dstack((nImR, nImG, nImB))

		if preview == 3:  ## IGU (extreme spectral range image)
			nImI = np.sign(imI) * ((np.abs(imI * wbI)/maxIGU)**0.42) * 255 * br
			nImGG = np.sign(imGG) * ((np.abs(imGG * wbGG)/maxIGU)**0.42) * 255 * br
			nImU = np.sign(imU) * ((np.abs(imU * wbU)/maxIGU)**0.42) * 255 * br
						
			nImI = np.clip(nImI, 0, 255)
			nImGG = np.clip(nImGG, 0, 255)
			nImU = np.clip(nImU, 0, 255)

			imCol = np.dstack((nImI, nImGG, nImU))

		if preview == 4:  ## NDVI
			nImB = imChlB * 255
			nImR = ((255-nImB)*2)* imChlA
			nImG = ((255-nImB)*2)* (1-imChlA)

			imCol = np.dstack((nImR, nImG, nImB))

		# width: plot_frame.bbox(plot)[2] height: plot_frame.bbox(plot)[3]
		
##		widgetDims = root.bbox(0, 3)
		if(plot_frame.bbox(plot)[2] < plot_frame.bbox(plot)[3]):
			plotSize = plot_frame.bbox(plot)[2]
		else: plotSize = plot_frame.bbox(plot)[3]

		plotSize -= 2 ## padding

		if(plotSize < 50):
			plotSize = 50 ## set min plot size to avoid drawing errors
			
		tImCol = imCol.astype(np.uint8)
		plotIm = Image.fromarray(tImCol, "RGB")
##		plotImt = ImageOps.contain(plotIm, (plotSize,plotSize), method=0)
		plotImt = ImageOps.contain(plotIm, (plotImX,plotImY), method=0)
		plotImResized = ImageTk.PhotoImage(plotImt)
		plot.config(image=plotImResized)
		plot.image = plotImResized

		#statusLabel.config(text=status)
	   # print(root.bbox(0, 1))

	else:
		
		if(serialName == 0):
			statusLabel.config(text="Disconnected")
			btStart["state"] = "disabled"
##		else:
##			statusLabel.config(text="Ready")
		
	
def updatePlotRes(event):
        global plotImX, plotImY
        plotImX = plot_frame.bbox(plot)[2]
        plotImY = plot_frame.bbox(plot)[3]
        plotGraph("Ready")

def getSpec():
	global tt, unitNumber, imLum, imR, imG, imB, imCol, imSatR, imSatB, panStart, panStop, pan_Res, panDim, tiltDim, tiltStart, tiltStop, tilt_Res, tiltRes, scanningFlag, dataString, boxcarN, maxRGB, output, focusPos
	global imI, imU, imGG, imChlA, imChlB, imNDVI, maxIGU, hspec, hspecPan, hspecTilt, fileImportFlag, loadPath, loadLine, lines, selX, selY, wavelengthBoxcar, stopFlag, ct
	if(scanningFlag == 0 and fileImportFlag == 0): # start scanning
		# Validate and convert degree inputs to steps
		pan_left_deg = panLeft.get()
		pan_right_deg = panRight.get()
		tilt_bot_deg = tiltBot.get()
		tilt_top_deg = tiltTop.get()
		
		# Validate all inputs
		valid, pan_left_val = validateDegreeRange(pan_left_deg, "Pan Left")
		if not valid: return
		valid, pan_right_val = validateDegreeRange(pan_right_deg, "Pan Right")
		if not valid: return
		valid, tilt_bot_val = validateDegreeRange(tilt_bot_deg, "Tilt Bottom")
		if not valid: return
		valid, tilt_top_val = validateDegreeRange(tilt_top_deg, "Tilt Top")
		if not valid: return
		
		# Convert to steps
		pan_left_steps = degreesToSteps(pan_left_val)
		pan_right_steps = degreesToSteps(pan_right_val)
		tilt_bot_steps = degreesToSteps(tilt_bot_val)
		tilt_top_steps = degreesToSteps(tilt_top_val)
		
		# Convert resolution from degrees to steps
		pan_res_deg = float(panRes.get())
		tilt_res_deg = float(tiltRes.get())
		pan_res_steps = degreesToSteps(pan_res_deg)
		tilt_res_steps = degreesToSteps(tilt_res_deg)
		
		# note addition of 000 to convert max int to microseconds
		ts = "h" + str(pan_left_steps) + "," + str(pan_right_steps) + "," + str(pan_res_steps) + "," + str(tilt_bot_steps) + "," + str(tilt_top_steps) + "," + str(tilt_res_steps) + "," + str(maxInt.get()) + "000," + str(boxcar.get()) + "," + str(darkRep.get()) + "000," # note addition of three zeros for darkRep as it's expecing milliseconds
		#print(ts)
		if(pan_right_steps > pan_left_steps and tilt_top_steps > tilt_bot_steps): # check pan & tilt coords make sense
			boxcarN = int(boxcar.get())
			#updateStatus(ts)
			statusLabel.config(text="Starting")
			safeSerialWrite( ts )
			#btStart["state"] = "disabled"
			btLoad["state"] = "disabled"
			btStart["text"] = "Stop"
			print("starting")
			scanningFlag = 1
			tt = time.time()
			maxRGB = 1E-10
			maxIGU = 1E-10
		else:
			statusLabel.config(text="Invalid pan/tilt")
			return

##	specLength = math.ceil(pixels/int(boxcar.get()))
		
	serFlag = 0

	if(fileImportFlag == 1 and loadLine == 0):
##		print("loading spec")
		f=open(loadPath)
		lines=f.readlines()

	while (serFlag == 0 or fileImportFlag == 1):
		if(stopFlag == 1):
			output = "x"
			dataString += output
			# Set serFlag to 1 to exit the loop when stopping
			serFlag = 1
		else:
			if(fileImportFlag == 0):
				output = safeSerialRead()
				if output:
					dataString += output + "\n"
				else:
					output = "0"
					print(f"No data received from serial (got: {output})")
			else:
				output = lines[loadLine]
	##			print(output)
	##			print(loadLine)
				loadLine +=1
			
			### load file & read first line

		if(output.startswith('x')):
##			print("a")
			if stopFlag == 1:
				statusLabel.config(text="Stopped")
			else:
				statusLabel.config(text="Done")
			## loop to add hspec le values
			hspec = np.nan_to_num(hspec)# convert NaNs to zeros
			if(fileImportFlag == 0):
##				print("b")
				dataString2 = "le values\npan,tilt,wavelength\n,"
				for i in range(0, len(wavelengthBoxcar)):
					dataString2 += "," + str(int(wavelengthBoxcar[i]))
##				print("c") ## FAILS after this point... WHY!?
##				dataString2 += str(hspec)
				for i in range(0, len(hspecTilt)):
					for j in range(0, len(hspecPan)):
						dataString2 += '\n' + str(hspecPan[j]) + ',' + str(hspecTilt[i]) + ','
						dataString3 = str(hspec[i, j])
##						dataString3 = dataString3.replace('\n', ',')
						dataString3 = dataString3.replace(' ', ',')
						dataString3 = dataString3.replace('[', '')
						dataString3 = dataString3.replace(']', '')
						dataString3 = dataString3.replace('0.000e+00', '0')

						dataString2 += dataString3

##			print("d")
			#-------save output file--------
			if(fileImportFlag == 0 and stopFlag == 0):  # Only save if not stopped early
				ts = saveLabel.get()
				t = time.localtime()
				ct = "./scans/" + str(t.tm_year) + "-" + str(t.tm_mon) + "-" + str(t.tm_mday) + "_" + time.strftime("%H-%M-%S", t) + "_" + ts
				ctt = ct + ".csv"
##				print("e")
				file_object = open(ctt, 'a')
				file_object.write(dataString)
				file_object.write(dataString2)
				file_object.close()
##				print("f")
				statusLabel.config(text="Ready")
				plotGraph("")
				ctf = ct + "_sRGB.png"
	##            plt.imsave(ctf, imCol)

				#save image
				nImR = ((imR/maxRGB)**0.42) * 255
				nImG = ((imG/maxRGB)**0.42) * 255
				nImB = ((imB/maxRGB)**0.42) * 255
				imCol = np.dstack((nImR, nImG, nImB))
				
				tImCol = imCol.astype(np.uint8)
				img = Image.fromarray(tImCol, "RGB")
				#img.show()
				img.save(ctf)
##				print("g")
			
			dataString = ""
			scanningFlag = 0
			btStart["text"] = "Start"
			btStart["state"] = "active"
			btLoad["state"] = "active"
			focusPos = 0 # reset focus position in case it was previously up
			#statusLabel.config(text="Ready")
			serFlag = 1
			#fileImportFlag = 0
			loadLine = 0
			selX = -1
			selY = -1 # reset these values to clear reflectance too
			
			wasStopped = stopFlag == 1
			stopFlag = 0
			if wasStopped:
				print("Scan stopped by user")
			else:
				print("h - done")
			return
		#output = output.decode('utf-8')
		output = output.split(',')
##		specLength = math.ceil(pixels/boxcarN)
		if(output[0] == 'h'):
			unitNumber = int(output[1])
			#print("unit: " + str(unitNumber))
			
			# Store the steps internally but don't update GUI fields
			panStart = int(output[2])
			panStop = int(output[3])
			pan_Res = int(output[4])
			panDim = int(0)
			
			boxcarN = int(output[9])
			boxcarVal.set(str(boxcarN))
			specLength = math.ceil(pixels/boxcarN)
##			specLength = math.ceil(pixels/boxcarN)
			if(reflFlag == 1):
				clearRefl()
			unitSetup()

			tiltStart = int(output[5])
			tiltStop = int(output[6])
			tilt_Res = int(output[7])
			panDim = int(1+(panStop-panStart)/pan_Res)
			tiltDim = int(1+(tiltStop-tiltStart)/tilt_Res)
			print("Hyperspec " + str(panDim) + " by " + str(tiltDim))
			imLum = np.zeros([tiltDim, panDim])
			imR = np.zeros([tiltDim, panDim])
			imG = np.zeros([tiltDim, panDim])            
			imB = np.zeros([tiltDim, panDim])
			imCol = np.zeros([tiltDim, panDim, 3])
			imSatR = np.zeros([tiltDim, panDim])
			imSatB = np.zeros([tiltDim, panDim])

			imI = np.zeros([tiltDim, panDim])
			imGG = np.zeros([tiltDim, panDim]) 
			imU = np.zeros([tiltDim, panDim])
			
			imChlA = np.zeros([tiltDim, panDim])            
			imChlB = np.zeros([tiltDim, panDim])
			imNDVI = np.zeros([tiltDim, panDim, 3])
			
			hspec = np.zeros([tiltDim, panDim, specLength])
			hspecPan = np.zeros([panDim])
			hspecTilt = np.zeros([tiltDim])


		if(len(hspec) > 0 and hasattr(hspec, 'shape') and len(output) == hspec.shape[2]+5):
			if(int(output[2]) == 0 or int(output[2]) == 1 or int(output[2]) == 2 ):
				#time.sleep(0.01)
				#processSpec()
				if(preview > 0): ## live update
						root.after(1, processSpec) # 10 seems to work
				else:
						processSpec()
				#statusLabel.config(text="Running")
				return
		

def processSpec():
	global tt, darkTimes, darkVals, panStart, panStop, pan_Res, panDim, tiltDim, tiltStart, tiltStop, tilt_Res, tiltRes, linCoefs,  wavelength, wavelengthBins, maxRGB, boxcarN, output, maxIGU, hspec
	boxedLength = len(output) - 5
	updateDuringDark = 0
	if(int(output[2]) == 0): # start or restart dark measurement
		#if(int(output[3]) <= minIntTime): # start of new dark measurement when int time = 1 (might be better to comapre to previous value)
		if(len(darkTimes) == 0 or int(output[3]) < darkTimes[len(darkTimes)-1]):
			darkTimes = []
			darkVals = []
			#print("new dark measurements")

		if int(output[3]) > 100000:
				updateDuringDark = 1
		darkTimes.append(int(output[3]))
		#for i in range(0,pixels):
		for i in range(5,boxedLength+5):
			darkVals.append(output[i])

		  

	if(int(output[2]) == 1): # light measurement
		for j in range(0, len(darkTimes)): # search through dark integration times
			tempTime = int(output[3])
##            if(tempTime < 0):
##                    tempTime = 1
			if(tempTime == darkTimes[j]): # found corresponding integration time, microsecond values assumed to be equal to 1ms
				#print("int " + row[3])

			   #-----------calculate radiance-----------------
				lum = 0.0
				intTime = float(output[3])
##                if(intTime < 0):
##                        intTime = float(intTime/-1000.0)
				#if(intTime < 0):
				#        intTime = 0.032 # intTime of -1 = 32 microseconds
				intTime += baseInt #was 550 # compensation for minimum microsecond exposure  0.382, 1200 makes the butterfly scan gradients look most smooth (implying it must be close)
##				le = [0] * pixels
				cieXval = 0.0
				cieYval = 0.0
				cieZval = 0.0
				chlAval = 0.0
				chlBval = 0.0
				nIRval = 0.0
				nUVval = 0.0
				
				#ts = "Radiance W/(sr*sqm*nm)\nInt.: "  + str(intTime)  + "ms Scans: " +  str(nScans)
				pan = int((int(output[0]) - panStart) / pan_Res)
				tilt = int((int(output[1]) - tiltStart) / tilt_Res)
				hspecPan[pan] = int(output[0])
##				hspecTilt[tiltDim-1-tilt] = int(output[1])
				hspecTilt[tilt] = int(output[1])
				loc = 0;
				for i in range(0, pixels, boxcarN): #increment in boxcar size
					xSum = 0
					for k in range(0, boxcarN): #repeat boxcar window
						if(i+k < pixels):
							if radSens[i+k] > 0 and len(output) > loc+5 :

								x = (float(output[loc+5])-float(darkVals[loc+boxedLength*j])) / boxcarN # subtract corresponding dark value
								if(x > 0):
										#linMultiplier = linCoefs[0]*math.log((x+1)*linCoefs[1])
									x = math.exp(math.log(x)*linCoefs[0] + linCoefs[1])
								if(x < 0):
									x = -1 * math.exp(math.log(-x)*linCoefs[0] + linCoefs[1])

								x = (x) / (radSens[i+k] * intTime)		

								xSum += x
##								if loc == 0 or loc == 1 or loc ==2:
##								if loc == pixels-1:
##									print("dark:" + darkVals[loc+boxedLength*j] + " light:" + output[loc+5] + " sens:" + str(radSens[i+k]) + " x:"+ str(x))
								x = x * wavelengthBins[i+k] # the following values are adjusted for namometer bin width
								cieXval += x * cieXt[i+k]
								cieYval += x * cieYt[i+k]
								cieZval += x * cieZt[i+k]
								chlAval += x * chlAt[i+k]
								chlBval += x * chlBt[i+k]
								nIRval += x * nIRt[i+k]
								nUVval += x * nUVt[i+k]
								
								lum += x * cieYt[i+k]
					hspec[tilt, pan, loc-1] += xSum/boxcarN # this is watts per nanometer (i.e. not controlled for AUC)
					loc += 1
				lum = lum * 683 * 117.159574150716 #luminance: W/(sr*sqm*nm), scaling factor calculated by comaring JETI to HOSI - the input isn't scaled to the same as OSpRad
				#ts = "Scanning " +  str(float(pan + (tilt * panDim)) / float(tiltDim * panDim) + "% done")
				#print(str(tiltDim) + ", " + str(panDim))
				ts = str(round(float(pan + (tilt * panDim)) / float(tiltDim * panDim) * 100.0)) + "% done"
				#print(ts)
				imLum[tiltDim-1-tilt, pan] = lum

				# convert to sRGB * set white balance to match computer screen
				imRt = 3.24*cieXval -1.54*cieYval - 0.50*cieZval
				imGt = (-0.97*cieXval + 1.88*cieYval + 0.04*cieZval) * 1.44
				imBt = (0.06*cieXval -0.20*cieYval + 1.06*cieZval) *  1.71

				imR[tiltDim-1-tilt, pan] = imRt
				imG[tiltDim-1-tilt, pan] = imGt
				imB[tiltDim-1-tilt, pan] = imBt

				if(imRt > maxRGB):
					maxRGB = imRt
				if(imGt > maxRGB):
					maxRGB = imGt
				if(imBt > maxRGB):
					maxRGB = imBt

				if int(output[4]) > 0:
					imSatR[tiltDim-1-tilt, pan] = 255
				imSatB[tiltDim-1-tilt, pan] = int(output[4])

				imI[tiltDim-1-tilt, pan] = nIRval
				imGG[tiltDim-1-tilt, pan] = cieYval
				imU[tiltDim-1-tilt, pan] = nUVval

				if(nIRval > maxIGU):
					maxIGU = nIRval
				if(cieYval > maxIGU):
					maxIGU = cieYval
				if(nUVval > maxIGU):
					maxIGU = nUVval

				imChlA[tiltDim-1-tilt, pan] = chlAval / (chlAval+nIRval)
				imChlB[tiltDim-1-tilt, pan] = chlBval / (chlBval+nIRval)

				

				ct = time.time()
				#print("time: " + str(tt-ct))
				if ct > tt:
					tt = ct + 1 # time to next plot in seconds
					statusLabel.config(text=ts)
					plotGraph("")
					#root.after(1, plotGraph(ts))

	if updateDuringDark == 1:
		root.after(1, getSpec)
	else:
		getSpec()
		


def togglePreview():
	global preview
	preview += 1
	if preview > 4:
		preview = 1 #reset set to zero if you want to retain delayed plotting

	if preview == 0:
		btPreview.config(text="Delay")
	if preview == 1:
		btPreview.config(text="RGB")
	if preview == 2:
		btPreview.config(text="Sat.")
	if preview == 3:
		btPreview.config(text="IGU")
	if preview == 4:
		btPreview.config(text="NDVI")

	plotGraph("")
		


def goTL():
	if(scanningFlag == 0):
		btTL["state"] = "disabled"
		
		# Convert tilt degrees to steps
		tilt_deg = tiltTop.get()
		valid, tilt_val = validateDegreeRange(tilt_deg, "Tilt Top")
		if not valid:
			btTL["state"] = "active"
			return
		tilt_steps = degreesToSteps(tilt_val)
		
		ts = "l" + str(tilt_steps)
		if not safeSerialWrite(ts):
			btTL["state"] = "active"
			return
		serFlag = 0
		while serFlag == 0: # wait for tilt to get to where it's going
			output = safeSerialRead()
			if output and output.startswith('tilt:'):
				serFlag = 1
		time.sleep(0.1)
		
		# Convert pan degrees to steps
		pan_deg = panLeft.get()
		valid, pan_val = validateDegreeRange(pan_deg, "Pan Left")
		if not valid:
			btTL["state"] = "active"
			return
		pan_steps = degreesToSteps(pan_val)
		
		ts = "p" + str(pan_steps)
		if not safeSerialWrite(ts):
			btTL["state"] = "active"
			return
		serFlag = 0
		while serFlag == 0: # wait for pan to get to where it's going
			output = safeSerialRead()
			if output and output.startswith('pan:'):
				serFlag = 1
		btTL["state"] = "active"

def goTR():
	if(scanningFlag == 0):
		btTR["state"] = "disabled"
		
		# Convert tilt degrees to steps
		tilt_deg = tiltTop.get()
		valid, tilt_val = validateDegreeRange(tilt_deg, "Tilt Top")
		if not valid:
			btTR["state"] = "active"
			return
		tilt_steps = degreesToSteps(tilt_val)
		
		ts = "l" + str(tilt_steps)
		if not safeSerialWrite(ts):
			btTR["state"] = "active"
			return
		serFlag = 0
		while serFlag == 0: # wait for tilt to get to where it's going
			output = safeSerialRead()
			if output and output.startswith('tilt:'):
				serFlag = 1
		time.sleep(0.1)
		
		# Convert pan degrees to steps
		pan_deg = panRight.get()
		valid, pan_val = validateDegreeRange(pan_deg, "Pan Right")
		if not valid:
			btTR["state"] = "active"
			return
		pan_steps = degreesToSteps(pan_val)
		
		ts = "p" + str(pan_steps)
		if not safeSerialWrite(ts):
			btTR["state"] = "active"
			return
		serFlag = 0
		while serFlag == 0: # wait for pan to get to where it's going
			output = safeSerialRead()
			if output and output.startswith('pan:'):
				serFlag = 1
		btTR["state"] = "active"

def goBL():
	if(scanningFlag == 0):
		btBL["state"] = "disabled"
		
		# Convert tilt degrees to steps
		tilt_deg = tiltBot.get()
		valid, tilt_val = validateDegreeRange(tilt_deg, "Tilt Bottom")
		if not valid:
			btBL["state"] = "active"
			return
		tilt_steps = degreesToSteps(tilt_val)
		
		ts = "l" + str(tilt_steps)
		if not safeSerialWrite(ts):
			btBL["state"] = "active"
			return
		serFlag = 0
		while serFlag == 0: # wait for tilt to get to where it's going
			output = safeSerialRead()
			if output and output.startswith('tilt:'):
				serFlag = 1
		time.sleep(0.1)
		
		# Convert pan degrees to steps
		pan_deg = panLeft.get()
		valid, pan_val = validateDegreeRange(pan_deg, "Pan Left")
		if not valid:
			btBL["state"] = "active"
			return
		pan_steps = degreesToSteps(pan_val)
		
		ts = "p" + str(pan_steps)
		if not safeSerialWrite(ts):
			btBL["state"] = "active"
			return
		serFlag = 0
		while serFlag == 0: # wait for pan to get to where it's going
			output = safeSerialRead()
			if output and output.startswith('pan:'):
				serFlag = 1
		btBL["state"] = "active"

def goBR():
	if(scanningFlag == 0):
		btBR["state"] = "disabled"
		
		# Convert tilt degrees to steps
		tilt_deg = tiltBot.get()
		valid, tilt_val = validateDegreeRange(tilt_deg, "Tilt Bottom")
		if not valid:
			btBR["state"] = "active"
			return
		tilt_steps = degreesToSteps(tilt_val)
		
		ts = "l" + str(tilt_steps)
		if not safeSerialWrite(ts):
			btBR["state"] = "active"
			return
		serFlag = 0
		while serFlag == 0: # wait for tilt to get to where it's going
			output = safeSerialRead()
			if output and output.startswith('tilt:'):
				serFlag = 1
		time.sleep(0.1)
		
		# Convert pan degrees to steps
		pan_deg = panRight.get()
		valid, pan_val = validateDegreeRange(pan_deg, "Pan Right")
		if not valid:
			btBR["state"] = "active"
			return
		pan_steps = degreesToSteps(pan_val)
		
		ts = "p" + str(pan_steps)
		if not safeSerialWrite(ts):
			btBR["state"] = "active"
			return
		serFlag = 0
		while serFlag == 0: # wait for pan to get to where it's going
			output = safeSerialRead()
			if output and output.startswith('pan:'):
				serFlag = 1
		btBR["state"] = "active"
	
def goZero():
	if(scanningFlag == 0):
		btZero["state"] = "disabled"
		if not safeSerialWrite("l0"):
			btZero["state"] = "active"
			return
		serFlag = 0
		while serFlag == 0: # wait for tilt to get to where it's going
			output = safeSerialRead()
			if output and output.startswith('tilt:'):
				serFlag = 1
		if not safeSerialWrite("p0"):
			btZero["state"] = "active"
			return
		serFlag = 0
		while serFlag == 0: # wait for pan to get to where it's going
			output = safeSerialRead()
			if output and output.startswith('pan:'):
				serFlag = 1
		btZero["state"] = "active"

def setServoAngle(angle):
	"""Set servo to specific angle (0-180)"""
	if(scanningFlag == 0):
		if 0 <= angle <= 180:
			cmd = f"s{angle}"
			safeSerialWrite(cmd)
		else:
			print("Invalid servo angle. Must be between 0 and 180.")

def openShutter():
	"""Open the shutter (servo angle 90)"""
	print(f"openShutter() called - scanningFlag: {scanningFlag}")
	if(scanningFlag == 0):
		print("Sending 'open' command to Arduino")
		safeSerialWrite("open")
	else:
		print("Cannot open shutter - system is currently scanning")

def closeShutter():
	"""Close the shutter (servo angle 60)"""
	print(f"closeShutter() called - scanningFlag: {scanningFlag}")
	if(scanningFlag == 0):
		print("Sending 'close' command to Arduino")
		safeSerialWrite("close")
	else:
		print("Cannot close shutter - system is currently scanning")

def degreesToSteps(degrees):
	"""Convert degrees (-90 to 90) to steps (-512 to 512)"""
	# Linear conversion: -90° = -512 steps, 90° = 512 steps
	return int(degrees * 512 / 90)

def validateDegreeRange(value, name):
	"""Validate that degree value is within -90 to 90 range, clamp if out of range"""
	deg = float(value)
	# Clamp values to -90 to 90 range
	if deg < -90:
		deg = -90
	elif deg > 90:
		deg = 90
	return True, deg

def showRes(a,b,c):
	if(scanningFlag == 0):
		try:
			# Validate degree inputs first
			pan_from_deg = panFrom.get()
			pan_to_deg = panTo.get()
			tilt_from_deg = tiltFrom.get()
			tilt_to_deg = tiltTo.get()
			
			valid, pan_from_val = validateDegreeRange(pan_from_deg, "Pan From")
			if not valid: return
			valid, pan_to_val = validateDegreeRange(pan_to_deg, "Pan To")
			if not valid: return
			valid, tilt_from_val = validateDegreeRange(tilt_from_deg, "Tilt From")
			if not valid: return
			valid, tilt_to_val = validateDegreeRange(tilt_to_deg, "Tilt To")
			if not valid: return
			
			# Get resolution in degrees and convert to steps
			pan_res_deg = float(panResolution.get())
			tilt_res_deg = float(tiltResolution.get())
			pan_res_steps = degreesToSteps(pan_res_deg)
			tilt_res_steps = degreesToSteps(tilt_res_deg)
			
			# Convert range to steps for calculation
			pan_from_steps = degreesToSteps(pan_from_val)
			pan_to_steps = degreesToSteps(pan_to_val)
			tilt_from_steps = degreesToSteps(tilt_from_val)
			tilt_to_steps = degreesToSteps(tilt_to_val)
			
			pan = math.floor( (pan_to_steps - pan_from_steps) / pan_res_steps ) +1
			tilt = math.floor( (tilt_to_steps - tilt_from_steps) / tilt_res_steps ) +1
			ts = str(pan) + "x" + str(tilt)
			statusLabel.config(text=ts)
##			print(ts)
		except:
			return
		


# detect when pan and tilt variables change and show resolution
panTo.trace_add('write', showRes)
panFrom.trace_add('write', showRes)
panResolution.trace_add('write', showRes)
tiltTo.trace_add('write', showRes)
tiltFrom.trace_add('write', showRes)
tiltResolution.trace_add('write', showRes)



def onmouse(event):
	global panDim, tiltDim, hspec, wavelengthBoxcar
	global plotImX, plotImY, selX, selY, refs
	clickX = event.x
	clickY = event.y
##	print("mouse event")
##	print('x:' + str(event.x) + ' y:' + str(event.y))
##	print(  plot_frame.bbox(plot) )
	imAR = panDim/tiltDim # aspect ratio h/w y/x
	frameAR = plotImX/plotImY # width is 2, height is 3
	padding = 2
	if(imAR > frameAR): ## frame narrower than image, image width scales with frame width
		scale = (panDim)/(plotImX)
	else: ## frame wider than image, image height scales with frame height
		scale = (tiltDim)/(plotImY)

	centreX = plotImX/2
	centreY = plotImY/2
	selX = int(math.floor( (panDim/2) + scale*(clickX-centreX)  )) ## offsets between click and centre of image
	selY = int(math.floor( (tiltDim/2) + scale*(clickY-centreY) ))
	selY = tiltDim-selY-1


##	print("Selection:" + str(selX) + ", " + str(selY))
	#---ensure selected coordinates match image dimensions---
	if(selX < 0):
		selX = 0
	if(selX > panDim-1):
		selX = panDim-1
	if(selY < 0):
		selY = 0
	if(selY > tiltDim-1):
		selY = tiltDim-1
		

	if(len(hspec)>0 and hasattr(hspec, 'shape')):
		# Update position label
		posLabel.config(text=f"Position: x:{selX} y:{selY} (pan:{panStart+pan_Res*selX}° tilt:{tiltStart+tilt_Res*selY}°)")
		
		# Update luminance label
		if(imLum[selY, selX] > 0.1):
			lumLabel.config(text=f"Luminance: {imLum[selY, selX]:.3f} cd/m²")
		else:
			lumLabel.config(text=f"Luminance: {imLum[selY, selX]:.3e} cd/m²")
##		print("plot update")
		le = hspec[selY][selX]
		if(reflFlag == 1):
			with np.errstate(invalid='ignore'):
				le = le*100*refs
		[ax[i].clear() for i in range(1)]
		
		# Find peak wavelength
		peak_idx = np.argmax(le)
		peak_wavelength = wavelengthBoxcar[peak_idx]
		peak_value = le[peak_idx]
		
		# Create the main plot
		ax[0].plot(wavelengthBoxcar, le, 'b-', linewidth=2, label='Spectrum')
		
		# Mark the peak
		ax[0].plot(peak_wavelength, peak_value, 'ro', markersize=8, label=f'Peak: {peak_wavelength:.1f} nm')
		
		# Set labels and title
		ax[0].set_xlabel('Wavelength (nm)', fontsize=10, fontweight='bold')
		if(reflFlag == 1):
			ax[0].set_ylabel('Reflectance (%)', fontsize=10, fontweight='bold')
			ax[0].set_title(f'Reflectance Spectrum - Pixel ({selX}, {selY})', fontsize=11, fontweight='bold')
		else:
			ax[0].set_ylabel('Radiance (W·sr⁻¹·m⁻²·nm⁻¹)', fontsize=10, fontweight='bold')
			ax[0].set_title(f'Radiance Spectrum - Pixel ({selX}, {selY})', fontsize=11, fontweight='bold')
		
		# Add grid
		ax[0].grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
		ax[0].grid(True, alpha=0.2, linestyle='--', linewidth=0.3, which='minor')
		
		# Set axis limits
		ax[0].set_ylim(ymin=0)
		ax[0].set_xlim(min(wavelengthBoxcar), max(wavelengthBoxcar))
		
		# Add legend
		ax[0].legend(loc='upper right', fontsize=9)
		
		# Improve tick formatting
		ax[0].tick_params(axis='both', which='major', labelsize=9)
		ax[0].tick_params(axis='both', which='minor', labelsize=8)
		
		# Add minor ticks
		ax[0].minorticks_on()
		
		canvas.draw()
		btSpecOut["state"] = "active"




def loadFile():
	global fileImportFlag, loadPath, maxRGB, maxIGU
	filetypes = (
		('Hyperspec Files', '*.csv'),
		('All files', '*.*')
	)

	try:
		loadPath = fd.askopenfilename(
			title='Open a file',
			initialdir='./scans/',
			filetypes=filetypes)
		print('Loading: ' + loadPath)
		fileImportFlag = 1
		maxRGB = 1E-10
		maxIGU = 1E-10
		getSpec()
	except:
		fileImportFlag = 0
		return

def setReflVal():
	global reflVal, reflFlag, selX, selY, refs, hspec, imR, imG, imB, maxRGB, wbR, wbG, wbB, wbI, wbGG, wbU, maxIGU, tiltDim
	if(reflFlag == 0):
		reflVal = setRefl.get()
		print("Reflectance standard set to " + reflVal + "%")
		typeLabel.config(text=f"Mode: Reflectance ({reflVal}%)")
##		try:
		try:
			if(float(reflVal) > 0 and len(hspec) > 0 and hasattr(hspec, 'shape') and selX != -1 and selY != -1):
				refs = hspec[selY][selX]

				with np.errstate(divide='ignore', invalid='ignore'):
					refs = (float(reflVal)/100)/refs # can't deal with zeros
										
				btRefl.config(text="Clear Ref.")
				reflFlag = 1
				setRefl["state"] = "disabled"

				# adjust image white-balance
				wbR = imR[tiltDim-1-selY, selX]
				wbG = imG[tiltDim-1-selY, selX]
				wbB = imB[tiltDim-1-selY, selX]
				wbI = imI[tiltDim-1-selY, selX]
				wbGG = imGG[tiltDim-1-selY, selX]
				wbU = imU[tiltDim-1-selY, selX]
##				print("Raw R:"+str(wbR)+" G:"+str(wbG)+" B:"+str(wbB))

				tmaxRGB = wbR
				if(wbG > tmaxRGB):
					tmaxRGB = wbG
				if(wbB > tmaxRGB):
					tmaxRGB = wbB
					
				wbR = tmaxRGB/wbR
				wbG = tmaxRGB/wbG
				wbB = tmaxRGB/wbB

				tmaxIGU = wbI
				if(wbGG > tmaxIGU):
					tmaxIGU = wbGG
				if(wbU > tmaxIGU):
					tmaxIGU = wbU
					
				wbI = tmaxIGU/wbI
				wbGG = tmaxIGU/wbGG
				wbU = tmaxIGU/wbU
##				print("Multiplier R:"+str(wbR)+" G:"+str(wbG)+" B:"+str(wbB))
##					
				plotGraph("Reflectance set")

			else:
				clearRefl()
				typeLabel.config(text="Mode: Radiance")
				# clear reflectance
		except ValueError:
			print("Invalid reflectance value entered")
			clearRefl()



def clearRefl():
	global reflFlag, wbR, wbG, wbB, wbI, wbGG, wbU, hspec, le
	btRefl.config(text="Set Ref.%")
	reflFlag = 0
	setRefl["state"] = "normal"
	typeLabel.config(text="Mode: Radiance")
	wbR = 1.0 # reset white balance
	wbG = 1.0
	wbB = 1.0
	wbI = 1.0
	wbGG = 1.0
	wbU = 1.0
	if(len(hspec)>0 and hasattr(hspec, 'shape')):
##		print("plot update")
		le = hspec[selY][selX]
		[ax[i].clear() for i in range(1)]
		
		# Find peak wavelength
		peak_idx = np.argmax(le)
		peak_wavelength = wavelengthBoxcar[peak_idx]
		peak_value = le[peak_idx]
		
		# Create the main plot
		ax[0].plot(wavelengthBoxcar, le, 'b-', linewidth=2, label='Spectrum')
		
		# Mark the peak
		ax[0].plot(peak_wavelength, peak_value, 'ro', markersize=8, label=f'Peak: {peak_wavelength:.1f} nm')
		
		# Set labels and title
		ax[0].set_xlabel('Wavelength (nm)', fontsize=10, fontweight='bold')
		ax[0].set_ylabel('Radiance (W·sr⁻¹·m⁻²·nm⁻¹)', fontsize=10, fontweight='bold')
		ax[0].set_title(f'Radiance Spectrum - Pixel ({selX}, {selY})', fontsize=11, fontweight='bold')
		
		# Add grid
		ax[0].grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
		ax[0].grid(True, alpha=0.2, linestyle='--', linewidth=0.3, which='minor')
		
		# Set axis limits
		ax[0].set_ylim(ymin=0)
		ax[0].set_xlim(min(wavelengthBoxcar), max(wavelengthBoxcar))
		
		# Add legend
		ax[0].legend(loc='upper right', fontsize=9)
		
		# Improve tick formatting
		ax[0].tick_params(axis='both', which='major', labelsize=9)
		ax[0].tick_params(axis='both', which='minor', labelsize=8)
		
		# Add minor ticks
		ax[0].minorticks_on()
		
		canvas.draw()
	plotGraph("Reflectance cleared")

def showInfo():
	"""Display information window with usage instructions and tool details"""
	info_window = Toplevel(root)
	info_window.title("HOSI Scanner - Information")
	info_window.geometry("800x600")
	info_window.resizable(True, True)
	
	# Create scrolled text widget
	text_widget = scrolledtext.ScrolledText(info_window, wrap=WORD, font=('Arial', 11), padx=10, pady=10)
	text_widget.pack(fill=BOTH, expand=True, padx=10, pady=10)
	
	# Information content
	info_text = """HOSI Scanner - Hyperspectral Imaging System
Version 2.0

🔬 OVERVIEW
This is a hyperspectral imaging system designed for spectral data acquisition and analysis using the Hamamatsu C12880MA spectrometer. The system provides real-time spectral visualization, reflectance calibration, and patient safety monitoring.

📋 FEATURES
• Hyperspectral scanning with pan/tilt gimbal control
• Real-time spectral data visualization with peak detection
• Interactive spectral plot with crosshair wavelength identification
• Multiple image preview modes (RGB, Saturation, IGU, NDVI)
• Reflectance calibration using white reference standards
• Luminance monitoring for patient safety (cd/m²)
• Spectral data export to CSV format
• Serial port management for Arduino control

🚀 QUICK START GUIDE

1. CONNECT HARDWARE:
   • Connect Arduino via USB
   • Upload HOSI_Scanner.ino firmware to Arduino
   • Ensure gimbal and spectrometer are properly connected

2. ESTABLISH CONNECTION:
   • Click "Scan" to find available serial ports
   • Select your Arduino port from dropdown
   • Click "Connect" to establish communication
   • "Start" button will enable when connected

3. CONFIGURE SCAN PARAMETERS:
   • Pan/Tilt ranges: Set angular limits in degrees (-90° to +90°)
   • Resolution: Set step size in degrees (e.g., 2° for fine scans)
   • Integration time: Adjust for lighting conditions (ms)
   • Boxcar: Spectral averaging parameter
   • Dark repeat: Background measurement interval

4. PERFORM SCAN:
   • Set file label for data organization
   • Click "Start" to begin hyperspectral acquisition
   • Monitor progress and preview in real-time
   • Click "Stop" to halt scan if needed

5. ANALYZE DATA:
   • Click on any pixel in the scanned image to view spectrum
   • Peak wavelength is automatically identified and marked
   • Click on spectral plot to get precise wavelength readings
   • Position and luminance information displayed at bottom

📊 REFLECTANCE CALIBRATION

For quantitative reflectance measurements:
1. Include a white reference standard (e.g., 99% Spectralon) in your scene
2. Complete a full radiance scan
3. Click on the white reference pixel in the image
4. Enter the known reflectance value (e.g., "99")
5. Click "Set Ref.%" to calibrate
6. All subsequent measurements show relative reflectance

The mode indicator will change from "Radiance" to "Reflectance (99%)" when active.

⚕️ PATIENT SAFETY

The luminance display shows brightness in cd/m² for safety monitoring:
• Values update in real-time when clicking pixels
• Critical for ophthalmic applications
• Typical safety thresholds:
  - Class 1 LED: <100 cd/m² (no time limit)
  - Photochemical hazard: <10,000 cd·s/m² (blue weighted)

🎯 INTERFACE CONTROLS

• Corner Buttons (┌┐└┘): Move gimbal to scan area corners
• Center Button (○): Return gimbal to home position
• RGB Button: Toggle between display modes
• Brightness Slider: Adjust image display intensity
• Shutter Controls: Open/close optical shutter

💾 DATA EXPORT

• Export Spectrum: Save selected pixel spectrum to CSV
• Automatic Saving: Complete scans auto-save with timestamp
• File Organization: All data saved to ./scans/ directory

🔧 SERIAL COMMANDS

Manual control via serial terminal (115200 baud):
• p<value>: Pan control (e.g., p100)
• l<value>: Tilt control (e.g., l500)  
• t<microseconds>: Set integration time
• r: Single measurement
• open/close: Shutter control
• stop: Emergency stop

⚠️ TROUBLESHOOTING

• Connection Issues: Use "Scan" button to refresh ports
• Missing Data: Ensure calibration_data.txt is present
• UI Problems: Requires Python 3.11+ on macOS
• Serial Errors: Check Arduino firmware upload

📁 FILES STRUCTURE

• GUI.py: Main application
• calibration_data.txt: Spectrometer calibration
• sensitivity_data.csv: Spectral response functions
• ./scans/: Output directory for data files

This tool is designed for research and educational use in spectral imaging applications."""

	# Insert text and make it read-only
	text_widget.insert(1.0, info_text)
	text_widget.config(state=DISABLED)
	
	# Add close button
	close_button = ttk.Button(info_window, text="Close", command=info_window.destroy)
	close_button.pack(pady=10)



def startStop():
	global fileImportFlag
	fileImportFlag = 0
	global stopFlag, scanningFlag
	if(scanningFlag == 0 and stopFlag == 0):
		# Start scanning
		getSpec()
		return
	if(scanningFlag == 1 and stopFlag == 0):
		# Stop scanning
		print("Stopping")
		stopFlag = 1
		# Send stop command to Arduino
		safeSerialWrite("stop")
		# Change button text back to Start
		btStart["text"] = "Start"
		# Re-enable Load button
		btLoad["state"] = "active"
		return
	

# COMMENTED OUT FOR LATER USE - RECEPTOR-BASED IMAGE OUTPUT FUNCTION
# def imageOutput():
# 	print("Outputting selected cone-catch images");
# 	for item in receptorListbox.curselection():
# 		#print("item: "+ str(item))
# 		print(receptorNames[item])
# 	
# 		#------resample spectral sensitivities at spectrometer wavelengths---------
# 		recept = [0.0] * pixels
# 		rSum = 0.0
# 		for i in range(0,pixels):
# 			# ~ for j in range(0, len(cieWav)):
# 			for j in range(0, len(receptorVals[item])):
# 				if(round(wavelength[i]) == cieWav[j]):
# 					recept[i] = receptorVals[item][j]
# 					rSum += recept[i]
# 					
# 		# ~ for i in range(0,pixels):
# 			# ~ recept[i] = recept[i]/rSum #  normalise to area under curve = 1
# 		
# 		# ~ print(recept)
# 		imOut = np.zeros([tiltDim, panDim])
# 		
# 		# ~ pes = [(6.626E-34 * 2.998E8) / (x*1E-9) for x in wavelengthBoxcar] # energy per photon at each wavelength
# 		pes = [(1E18 * 6.626E-34 * 2.998E8) / (x*1E-9) for x in wavelengthBoxcar] # energy per photon at each wavelength - SCALED (multiplied by 1E18 to give more sensible ouput given 32-bit floating point range limits
# 		#print(pes)
# 		
# 		for y in range(0, tiltDim):
# 			for x in range(0, panDim):
# 				leSum = 0.0
# 				le = hspec[y][x]
# 				if(reflFlag == 1):
# 					with np.errstate(invalid='ignore'):
# 						le = le*100*refs
# 				# ~ print(str(len(le)))
# 				
# 				for z in range(0, len(le)):
# 					for b in range(0, boxcarN):
# 						# ~ leSum += le[z] * recept[b + z*boxcarN] * wavelengthBins[b + z*boxcarN] # correct for differences in bin-width (area-under curve)
# 						leSum += (le[z]/pes[z]) * recept[b + z*boxcarN] * wavelengthBins[b + z*boxcarN] # correct for differences in bin-width (area-under curve)
# 
# 				imOut[tiltDim-y-1, x] = leSum
# 
# 				# ~ print("x: "+ str(x) + " y: " + str(y) + " val: " + str(leSum))
# 		# ~ print(imOut)
# 		img = Image.fromarray(imOut)
# 		
# 		if fileImportFlag == 1:
# 			ts = loadPath.replace('.csv', '')
# 		else:
# 			ts = ct
# 		print(ts)
# 		ts = ts + "_" + receptorNames[item] + ".tif"
# 		img.save(ts)

		
def specOutput():
	if len(hspec)>0 and hasattr(hspec, 'shape') and selX > -1:
		print("x:" + str(selX) + " y:" + str(selY))
		##		print("plot update")
		le = hspec[selY][selX]
		tts = "radiance"
		if(reflFlag == 1):
			tts = "reflectance"
			with np.errstate(invalid='ignore'):
				le = le*100*refs
				
		if fileImportFlag == 1:
			ts = loadPath.replace('.csv', '')
		else:
			ts = ct
		# ~ print(ts)
		ts = ts + "_" + tts + ".csv"

		specOutVal = specOutLabel.get()
		
		if os.path.exists(ts):
			# If the file exists, read the lines, append new data, and rewrite
			with open(ts, 'r') as file_object:
				lines = file_object.readlines()
			
			# Ensure the number of lines matches the length of wavelengthBoxcar
			if len(lines[1:]) != len(le):
				print("Error: Mismatch between file lines and spectrum length.")
				return
				
			header = lines[0].strip()  # Remove any trailing newlines or spaces
			header = header + ",x" + str(selX) + "_y" + str(selY) + "_" + specOutVal + "\n"  # Append the new header label

			# Rewrite the file with updated lines
			with open(ts, 'w') as file_object:
				file_object.write(header)
				for i, line in enumerate(lines[1:]):
					# Strip newline and append the new wavelengthBoxcar value
					line = line.strip() + f",{le[i]}\n"
					file_object.write(line)
	
		else:
			# If the file does not exist, create it and write both columns
			with open(ts, 'w') as file_object:
				file_object.write("Wavelength," + "x" + str(selX) + "_y" + str(selY) + "_" + specOutVal + "\n")
				for wb, le_value in zip(wavelengthBoxcar, le):
				    file_object.write(f"{wb},{le_value}\n")
		# btSpecOut["state"] = "disabled" # disable button to stop repeated saves



##updatePlotRes() # run at start to set image size

##------------TOP FRAME-------------
## ┌ ┐└ ┘ ╬ □ ○
	
frame1 = ttk.Frame(root)
frame1.grid(row=1, column=0, sticky=N+E+W, padx=8, pady=4)
for i in range(5):
    frame1.columnconfigure(i, weight=1)  # Make all columns expand equally

btStart = ttk.Button(frame1, text='Start', width=8, command=lambda: startStop(), state="disabled")  # Increased width
btStart.grid(row=0, column=0, padx=(0,2), pady=2, sticky=N+S+E+W)

btTL = ttk.Button(frame1, text="┌", width=4, command=lambda: goTL())
btTL.grid(row=0, column=1, padx=2, pady=2, sticky=N+S+E+W)

tiltTop = ttk.Entry(frame1, textvariable=tiltTo)
tiltTop.grid(row=0, column=2, padx=2, pady=2, sticky=N+S+E+W)

btTR = ttk.Button(frame1, text="┐", width=4, command=lambda: goTR())
btTR.grid(row=0, column=3, padx=2, pady=2, sticky=N+S+E+W)

resMsg = ttk.Label(frame1, text="Res.(°)")
resMsg.grid(row=0, column=4, padx=(2,0), pady=2, sticky=S+W)

btLoad = ttk.Button(frame1, text="Load", width=8, command=lambda: loadFile())  # Added width
btLoad.grid(row=1, column=0, padx=2, pady=2, sticky=N+S+E+W)

panLeft = ttk.Entry(frame1, textvariable=panFrom)
panLeft.grid(row=1, column=1, padx=2, pady=2, sticky=N+W)

btZero = ttk.Button(frame1, text="○", command=lambda: goZero())
btZero.grid(row=1, column=2, padx=2, pady=2, sticky=N+S+E+W)

panRight = ttk.Entry(frame1, textvariable=panTo)
panRight.grid(row=1, column=3, padx=2, pady=2, sticky=N+W)

panRes = ttk.Entry(frame1, textvariable=panResolution)
panRes.grid(row=1, column=4, padx=2, pady=2, sticky=N+W)

btPreview = ttk.Button(frame1, text="RGB", width=8, command=lambda: togglePreview())  # Added width
btPreview.grid(row=2, column=0, padx=2, pady=2, sticky=N+S+E+W)

btBL = ttk.Button(frame1, text="└", command=lambda: goBL())
btBL.grid(row=2, column=1, padx=2, pady=2, sticky=N+S+E+W)

tiltBot = ttk.Entry(frame1, textvariable=tiltFrom)
tiltBot.grid(row=2, column=2, padx=2, pady=2, sticky=N+W)

btBR = ttk.Button(frame1, text="┘", command=lambda: goBR())
btBR.grid(row=2, column=3, padx=2, pady=2, sticky=N+S+E+W)

tiltRes = ttk.Entry(frame1, textvariable=tiltResolution)
tiltRes.grid(row=2, column=4, padx=2, pady=2, sticky=N+W)

##---------------FRAME2-----------------
frame2 = ttk.Frame(root)
frame2.grid(row=2, column=0, sticky=N+E+W, padx=8, pady=4)

# Configure columns to expand equally
for i in range(4):
    frame2.columnconfigure(i, weight=1)

saveMessage = ttk.Label(frame2, text="File Label")
saveMessage.grid(row=0, column=0, padx=2, pady=2, sticky=N+W)

maxIntMessage = ttk.Label(frame2, text="MaxInt(ms)")
maxIntMessage.grid(row=0, column=1, padx=2, pady=2, sticky=N+W)

boxcarMessage = ttk.Label(frame2, text="Boxcar")
boxcarMessage.grid(row=0, column=2, padx=2, pady=2, sticky=N+W)

darkRepMessage = ttk.Label(frame2, text="DarkRep(s)")
darkRepMessage.grid(row=0, column=3, padx=2, pady=2, sticky=N+W)

saveInput = ttk.Entry(frame2, textvariable=saveLabel)
saveInput.grid(row=1, column=0, padx=2, pady=2, sticky=N+S+E+W)

maxInt = ttk.Entry(frame2, textvariable=maxIntTime)
maxInt.grid(row=1, column=1, padx=2, pady=2, sticky=N+S+E+W)

boxcar = ttk.Entry(frame2, textvariable=boxcarVal)
boxcar.grid(row=1, column=2, padx=2, pady=2, sticky=N+S+E+W)

darkRep = ttk.Entry(frame2, textvariable=darkRepVal)
darkRep.grid(row=1, column=3, padx=2, pady=2, sticky=N+S+E+W)

##---------------FRAME3-----------------

frame3 = Frame(root)
frame3.grid(row=3, column=0, sticky=N+E+W)

frame3.columnconfigure(0, weight=1)
frame3.rowconfigure(0, weight=1)

brightnessScale = Scale(frame3, from_=1, to=100, orient='horizontal',command= plotGraph)
brightnessScale.set(100)
brightnessScale.grid(row=0, column=0, padx=2, pady=2, sticky=N+W+E)

statusLabel = Label(frame3, text = "Status", fg="gray", justify="left")
statusLabel.grid(row=0, column=0, padx=2, pady=2, sticky=N+W)

##------------IMAGE FRAME-------------

plot_frame = Frame(root)
plot_frame.grid(row=4, column=0, sticky=N+S+E+W)
plot_frame.columnconfigure(0, weight=1)
plot_frame.rowconfigure(0, weight=1)

plotWidth=400
try:
    gridIm = Image.open("grid.png")
    gridImt = ImageOps.contain(gridIm, (plotWidth,plotWidth), method=0)
    gridImResized = ImageTk.PhotoImage(gridImt)
except:
    # If grid.png doesn't exist, create a simple checkerboard pattern
    import numpy as np
    checkerboard = np.zeros((plotWidth, plotWidth, 3), dtype=np.uint8)
    # Create checkerboard pattern
    square_size = 20
    for i in range(0, plotWidth, square_size):
        for j in range(0, plotWidth, square_size):
            if (i // square_size + j // square_size) % 2 == 0:
                checkerboard[i:i+square_size, j:j+square_size] = [200, 200, 200]  # Light gray
            else:
                checkerboard[i:i+square_size, j:j+square_size] = [100, 100, 100]  # Dark gray
    gridIm = Image.fromarray(checkerboard)
    gridImt = ImageOps.contain(gridIm, (plotWidth,plotWidth), method=0)
    gridImResized = ImageTk.PhotoImage(gridImt)

plot = Label(plot_frame, image=gridImResized, fg="gray", justify="left", cursor="hand2")
plot.grid(row=0, column=0, padx=0, pady=0, sticky=N+W+E+S)
plot.bind('<1>', onmouse) ## mouse click event
plot_frame.grid_propagate(False)

##------------SPEC PLOT FRAME-------------
spec_frame = Frame(root)
spec_frame.grid(row=5, column=0, sticky=N+S+E+W)

figure = plt.Figure(figsize=(6,3), facecolor='#d9d9d9', tight_layout=True) #figsize=(3,1.5)
canvas = FigureCanvasTkAgg(figure, spec_frame)
canvas.get_tk_widget().grid(row=0, column=0, padx=2, pady=2, sticky=N+S+E+W)
ax = [figure.add_subplot(1, 1, x+1) for x in range(1)]

# Global variables for crosshair
crosshair_vline = None
crosshair_text = None

def on_plot_click(event):
	"""Handle clicks on the spectral plot to show wavelength crosshair"""
	global crosshair_vline, crosshair_text
	
	if event.inaxes == ax[0] and len(hspec) > 0 and hasattr(hspec, 'shape'):
		# Clear previous crosshair by removing from axes lines and texts collections
		if crosshair_vline:
			try:
				crosshair_vline.remove()
			except:
				# If remove fails, clear from lines collection
				if crosshair_vline in ax[0].lines:
					ax[0].lines.remove(crosshair_vline)
		
		if crosshair_text:
			try:
				crosshair_text.remove()
			except:
				# If remove fails, clear from texts collection
				if crosshair_text in ax[0].texts:
					ax[0].texts.remove(crosshair_text)
		
		# Get clicked wavelength
		wavelength_clicked = event.xdata
		
		if wavelength_clicked is not None:
			# Find closest wavelength in our data
			closest_idx = np.argmin(np.abs(np.array(wavelengthBoxcar) - wavelength_clicked))
			closest_wavelength = wavelengthBoxcar[closest_idx]
			
			# Get the spectrum value at this wavelength
			le = hspec[selY][selX]
			if(reflFlag == 1):
				with np.errstate(invalid='ignore'):
					le = le*100*refs
			spectrum_value = le[closest_idx]
			
			# Add vertical line at clicked wavelength
			crosshair_vline = ax[0].axvline(x=closest_wavelength, color='red', linestyle='--', alpha=0.8, linewidth=2)
			
			# Add text annotation
			crosshair_text = ax[0].annotate(
				f'{closest_wavelength:.1f} nm\n{spectrum_value:.3e}',
				xy=(closest_wavelength, spectrum_value),
				xytext=(10, 10), textcoords='offset points',
				bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8),
				fontsize=9, fontweight='bold'
			)
			
			canvas.draw()
			print(f"Clicked wavelength: {closest_wavelength:.1f} nm, Value: {spectrum_value:.3e}")

# Connect the click event to the plot
canvas.mpl_connect('button_press_event', on_plot_click)

spec_frame.columnconfigure(0, weight=1)
spec_frame.rowconfigure(0, weight=1)




root.bind("<Configure>", updatePlotRes) ## resizing the window calls this function

# Serial port selection variables
serialPortVar = StringVar()

##------------SERIAL CONNECTION FRAME-------------
serial_frame = ttk.Frame(root)
serial_frame.grid(row=0, column=0, sticky=N+E+W, padx=8, pady=4)
serial_frame.columnconfigure(1, weight=1)  # Make dropdown expand

serialLabel = ttk.Label(serial_frame, text="Serial Port:")
serialLabel.grid(row=0, column=0, padx=(0,2), pady=2, sticky=W)

serialPortDropdown = ttk.Combobox(serial_frame, textvariable=serialPortVar, state="readonly", width=25)
serialPortDropdown.grid(row=0, column=1, padx=2, pady=2, sticky=W+E)

btScan = ttk.Button(serial_frame, text="Scan", width=6, command=lambda: scanSerialPorts())
btScan.grid(row=0, column=2, padx=2, pady=2, sticky=W)

btConnect = ttk.Button(serial_frame, text="Connect", width=8, command=lambda: connectSerial())
btConnect.grid(row=0, column=3, padx=2, pady=2, sticky=W)

btDisconnect = ttk.Button(serial_frame, text="Disconnect", width=10, command=lambda: disconnectSerial(), state="disabled")
btDisconnect.grid(row=0, column=4, padx=(2,0), pady=2, sticky=W)

##------------CONTROLS FRAME-------------
controls_frame = ttk.Frame(root)
controls_frame.grid(row=6, column=0, sticky=N+S+E+W, padx=8, pady=8)
controls_frame.configure(height=300)  # Increased minimum height

# Configure the main grid for controls
for i in range(6):  # 6 columns for better organization
    controls_frame.columnconfigure(i, weight=1)

# Initialize control variables

# Row 0: Reflectance and Export controls
ttk.Label(controls_frame, text="Reflectance:").grid(row=0, column=0, padx=4, pady=4, sticky=W)
setRefl = ttk.Entry(controls_frame, textvariable=reflVal, width=8)
setRefl.grid(row=0, column=1, padx=4, pady=4, sticky=W+E)
btRefl = ttk.Button(controls_frame, text="Set Ref.%", command=lambda: setReflVal(), width=10)
btRefl.grid(row=0, column=2, padx=4, pady=4, sticky=W+E)

ttk.Label(controls_frame, text="Column Label:").grid(row=0, column=3, padx=4, pady=4, sticky=W)
specOutLabel = ttk.Entry(controls_frame, textvariable=specOutVal, width=10)
specOutLabel.grid(row=0, column=4, padx=4, pady=4, sticky=W+E)
btSpecOut = ttk.Button(controls_frame, text="Export Spectrum", command=lambda: specOutput(), width=10)
btSpecOut.grid(row=0, column=5, padx=4, pady=4, sticky=W+E)

# Row 1: Shutter and Info controls
ttk.Label(controls_frame, text="Shutter:").grid(row=1, column=0, padx=4, pady=4, sticky=W)
btOpenShutter = ttk.Button(controls_frame, text="Open", command=lambda: openShutter(), width=8)
btOpenShutter.grid(row=1, column=1, padx=4, pady=4, sticky=W+E)
btCloseShutter = ttk.Button(controls_frame, text="Close", command=lambda: closeShutter(), width=8)
btCloseShutter.grid(row=1, column=2, padx=4, pady=4, sticky=W+E)

# Info button
ttk.Label(controls_frame, text="Help:").grid(row=1, column=3, padx=4, pady=4, sticky=W)
btInfo = ttk.Button(controls_frame, text="Info", command=lambda: showInfo(), width=12)
btInfo.grid(row=1, column=4, columnspan=2, padx=4, pady=4, sticky=W+E)

# Export Images button spanning two columns for better balance - COMMENTED OUT (USES RECEPTORS)
# btImOut = ttk.Button(controls_frame, text="Export Images", command=lambda: imageOutput(), width=15)
# btImOut.grid(row=1, column=4, columnspan=2, padx=4, pady=4, sticky=W+E)

# Row 2: Status display (properly formatted, always visible)
status_frame = ttk.Frame(controls_frame)
status_frame.grid(row=2, column=0, columnspan=6, padx=4, pady=(16,4), sticky=N+S+E+W)
status_frame.columnconfigure(0, weight=1)
status_frame.columnconfigure(1, weight=1)
status_frame.columnconfigure(2, weight=1)

# Position and measurement type
posLabel = ttk.Label(status_frame, text="Position: --", font=('System', 12, 'bold'))
posLabel.grid(row=0, column=0, padx=4, pady=2, sticky=N)

typeLabel = ttk.Label(status_frame, text="Mode: Radiance", font=('System', 12, 'bold'))
typeLabel.grid(row=0, column=1, padx=4, pady=2, sticky=N)

# Luminance display
lumLabel = ttk.Label(status_frame, text="Luminance: --", font=('System', 12, 'bold'))
lumLabel.grid(row=0, column=2, padx=4, pady=2, sticky=N)

# Row 4: Receptor list (full width) - COMMENTED OUT FOR LATER USE
# ttk.Label(controls_frame, text="Receptors:").grid(row=4, column=0, columnspan=6, padx=4, pady=(8,2), sticky=W)
# receptorListbox = Listbox(controls_frame, selectmode="multiple", bg=COLORS['input_bg'], fg=COLORS['input_fg'])
# receptorListbox.grid(row=5, column=0, columnspan=6, padx=4, pady=(2,8), sticky=E+W+N+S)

# Make the listbox row expandable and give the controls frame some height - COMMENTED OUT WITH RECEPTORS
# controls_frame.rowconfigure(5, weight=1)
controls_frame.configure(height=350)  # Increase height to give more room for receptors

root.mainloop()