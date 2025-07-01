# HOSI Scanner

A hyperspectral imaging system with GUI interface for spectral data acquisition and analysis.

## Features

- Hyperspectral scanning with pan/tilt control
- Real-time spectral data visualization
- Multiple image preview modes (RGB, Saturation, IGU, NDVI)
- Reflectance calibration
- Spectral data export
- Cone-catch image generation

## Requirements

- Python 3.7 or higher
- Arduino Nano (for hardware control)
- Serial connection to Arduino

## Installation

1. Create a virtual environment:
```bash
python -m venv .venv
```

2. Activate the virtual environment:
```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. **Connect Hardware**: Ensure your Arduino is connected via USB and upload the `HOSI_Scanner.ino` sketch.

2. **Activate Virtual Environment**:
```bash
# Windows
hosi_venv\Scripts\activate

# Linux/macOS
source hosi_venv/bin/activate
```

3. **Run the GUI**:
```bash
python GUI.py
```

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
├── setup_venv.py            # Python setup script
├── setup_venv.bat           # Windows setup script
├── setup_venv.sh            # Unix/Linux/macOS setup script
├── README.md                # This file
├── calibration_data.txt     # Calibration data
├── sensitivity_data.csv     # Spectral sensitivity data
├── grid.png                 # Grid image for GUI
└── Arduino_HOSI_Scanner/
    └── HOSI_Scanner.ino     # Arduino firmware
```

## Troubleshooting

### Common Issues

1. **Serial Connection Failed**
   - Check if Arduino is properly connected
   - Verify the correct COM port is being used
   - Ensure Arduino firmware is uploaded

2. **Missing Dependencies**
   - Activate the virtual environment before running
   - Reinstall dependencies: `pip install -r requirements.txt`

3. **Calibration Data Missing**
   - Ensure `calibration_data.txt` and `sensitivity_data.csv` are present
   - Check file format and content

### Platform-Specific Notes

- **Windows**: Uses `pyserial` for serial communication

## License

This project is for research and educational use.

## Support

For issues and questions, please check the troubleshooting section above or refer to the code comments for detailed implementation information. 