# Hyperspectral Results

Our device utilizes independent pan and roll stepper motors with a resolution of 2048 steps per revolution. An internal servo-controlled shutter enables in-place black point correction every 30s.

<img src="hosi_render.jpg" alt="HOSI Render" width="100%">

<img src="hosi.gif" alt="HOSI In Action" width="100%">

## Scanning Results

The HOSI device was used to create a 137 x 91 hyperspectral data by panning 120° and rolling 80° at 1° increments.

<img src="hosi.jpg" alt="HOSI Device" width="100%">

Within the GUI, each x-y 'pixel' can be clicked to reveal the full spectrum (320–880 nm) with reporting for radiance and luminance. Once clicked, the spectrum is displayed for that pixel and the peak will be automatically plotted (red arrow). Clicking other points on the plot will draw a vertical line and present data for that wavelength.

<img src="hosi_gui.png" alt="HOSI GUI Interface" width="100%">

**Exported RGB Image**

<img src="scan_output.png" alt="Spectral Output Display" width="100%">

**Actual Scene (from iPhone)**

<img src="scan_photo.jpg" alt="Original Scene Photo" width="100%">

**Blue LED Strip in View**

<img src="scan_leds.jpg" alt="Blue LEDs in Scene" width="100%">

## Conclusion

In conclusion, our device captures spectral data for an entire scene which can be analyzed in realtime or posthoc; all data is exported via CSV as well as the RGB image below.