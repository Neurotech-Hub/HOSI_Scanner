# Neurotech Hub Hyperspectral Imager

A hyperspectral open-source imager system with GUI interface for spectral data acquisition and analysis. Based on [Troscianko, 2025](https://bmcbiol.biomedcentral.com/articles/10.1186/s12915-024-02110-w).

See our [results](docs/results.md).

## Features

- Hyperspectral scanning with pan/tilt control
- Real-time spectral data visualization
- Multiple image preview modes (RGB, Saturation, IGU, NDVI)
- Reflectance calibration
- Spectral data export
- Cone-catch image generation
- Cross-platform support (Windows, macOS, Linux)
- Serial port selection and management

## Requirements

- Python 3.11 or higher (3.11+ required for macOS)
- Arduino Nano (for hardware control)
- Serial connection to Arduino

## Installation

1. **Install Python**:
   - **Windows**: Download Python 3.11+ from python.org
   - **macOS**: Install via Homebrew:
   ```bash
   brew install python@3.11
   brew install python-tk@3.11  # Required for macOS
   ```

2. Create a virtual environment:
```bash
# Windows
python -m venv .venv

# macOS/Linux
/opt/homebrew/bin/python3.11 -m venv .venv
```

3. Activate the virtual environment:
```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. **Connect Hardware**: 
   - Connect Arduino via USB
   - Upload the `HOSI_Scanner.ino` sketch

2. **Run the GUI**:
```bash
# Windows
python GUI.py

# macOS
/opt/homebrew/bin/python3.11 GUI.py
```

3. **Connect to Arduino**:
   - Click "Scan" to find available serial ports
   - Select your Arduino port from the dropdown
   - Click "Connect" to establish connection
   - Once connected, the "Start" button will be enabled

### Running in VS Code

1. **Set Python Interpreter**:
   - Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows)
   - Type "Python: Select Interpreter"
   - Choose:
     - macOS: `/opt/homebrew/bin/python3.11`
     - Windows: Your Python installation

2. **Run the GUI**:
   - Open the "Run and Debug" sidebar (`Cmd+Shift+D` or `Ctrl+Shift+D`)
   - Select:
     - macOS: "Python: HOSI GUI (macOS)"
     - Windows: "Python: HOSI GUI (Windows)"
   - Click the play button or press `F5`

## Platform-Specific Notes

### macOS
- Requires Python 3.11+ with Tkinter 8.6 for proper UI compatibility
- Uses native serial port selection to handle port access permissions
- Light mode UI ensures compatibility across macOS versions
- If UI elements are not visible, ensure you're using Python 3.11+

### Windows
- Compatible with Python 3.7+
- Automatically detects COM ports
- Default light mode UI

## Dependencies

- **numpy**: Numerical computing and array operations
- **Pillow**: Image processing and manipulation
- **matplotlib**: Plotting and visualization
- **pyserial**: Serial communication with Arduino
- **tkinter**: GUI framework (included with Python)

## File Structure

```
HOSI_Scanner/
├── GUI.py                    # Main GUI application
├── requirements.txt          # Python dependencies
├── README.md                # This file
├── calibration_data.txt     # Calibration data
├── sensitivity_data.csv     # Spectral sensitivity data
├── grid.png                 # Grid image for GUI
└── Arduino_HOSI_Scanner/
    └── HOSI_Scanner.ino     # Arduino firmware
```

## Serial Commands

The HOSI Scanner can be controlled manually via serial port (default baud rate: 115200). The following commands are available:

### Basic Controls

- `t<microseconds>`: Set manual integration time (e.g., `t100` or `t500`)
- `p<value>`: Pan control, where 0 is straight ahead (e.g., `p100` or `p-1000`)
- `l<value>`: Tilt control, where 0 is straight down (e.g., `l100` or `l500`)
- `r`: Take a single radiance measurement

### Shutter Control

- `open`: Open the shutter
- `close`: Close the shutter
- `shutter`: Report current shutter status

### Hyperspectral Measurement

Format: `h<panLeft>,<panRight>,<panResolution>,<tiltBottom>,<tiltTop>,<tiltResolution>,<maxIntegrationTime>,<boxcar>,<darkRepeatTimer>`

Example: `h-200,200,10,400,600,10,2000000,2,120000`

Parameters:
- `panLeft`: Left pan limit
- `panRight`: Right pan limit
- `panResolution`: Pan step size
- `tiltBottom`: Bottom tilt limit
- `tiltTop`: Top tilt limit
- `tiltResolution`: Tilt step size
- `maxIntegrationTime`: Maximum integration time in microseconds
- `boxcar`: Boxcar width for spectral averaging
- `darkRepeatTimer`: Dark measurement repeat interval in milliseconds

### Emergency Control

- `stop`: Immediately stop any ongoing operation, return to origin, and close shutter

## Troubleshooting

### Common Issues

1. **Serial Connection Failed**
   - Use the "Scan" button to refresh available ports
   - Select the correct port from the dropdown
   - Click "Connect" to establish connection
   - If connection fails, try disconnecting and reconnecting the Arduino

2. **Missing Dependencies**
   - Ensure virtual environment is activated
   - Run: `pip install -r requirements.txt`

3. **UI Elements Not Visible (macOS)**
   - Ensure you're using Python 3.11+ with Tkinter 8.6
   - Install via: `brew install python@3.11 python-tk@3.11`
   - Run with: `/opt/homebrew/bin/python3.11 GUI.py`

4. **Calibration Data Missing**
   - Ensure `calibration_data.txt` and `sensitivity_data.csv` are present
   - Check file format and content

## License

This project is for research and educational use.

## Support

For issues and questions, please check the troubleshooting section above or refer to the code comments for detailed implementation information. 