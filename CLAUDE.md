# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based intelligent sarcopenia detection system (智能肌少症检测系统) that processes real-time pressure sensor data through serial communication and visualizes it as heatmaps. The system is specifically designed for Weihai Juqiao Industrial Technology Co., Ltd. pressure sensor arrays.

## Development Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Testing and Validation
```bash
# Test all module imports and basic functionality
python test_modules.py

# Test performance benchmarks
python test_performance.py

# Command-line data acquisition (testing serial connection)
python date.py
```

### Running the Application
```bash
# Standard version (20 FPS)
python run_ui.py
# or directly
python pressure_sensor_ui.py

# High-performance version (100 FPS)
python run_ui_fast.py

# Ultra-optimized version (200 FPS, 5ms latency)
python run_ui_ultra.py

# Windows users can use batch files
启动UI.bat        # Ultra-optimized version
start.bat         # Standard version
```

## Architecture Overview

The codebase follows a modular architecture with clear separation of concerns:

### Core Modules
- **`serial_interface.py`** - Serial communication module that handles COM port detection, data acquisition threads, and frame parsing
- **`data_processor.py`** - Data processing module implementing the JQ transform algorithm and statistical analysis
- **`visualization.py`** - Heatmap visualization module with 16-level color mapping and real-time updates
- **`pressure_sensor_ui.py`** - Main UI controller coordinating all modules

### Data Flow Architecture
```
Serial Device → serial_interface.py → data_processor.py → visualization.py → UI Display
```

### Key Technical Details

#### Serial Communication Protocol
- **Baud Rate**: 1,000,000 bps
- **Frame Header**: AA 55 03 99
- **Data Format**: Variable length frames (max 1024 bytes)
- **Supported Arrays**: 32x32, 32x64, 32x96 sensor configurations

#### JQ Transform Algorithm
The system implements a proprietary data transformation algorithm for Weihai Juqiao Industrial Technology:
1. **Mirror Flip**: Rows 1-15 are mirror-flipped (row 0 ↔ row 14, row 1 ↔ row 13, etc.)
2. **Row Reordering**: First 15 rows are moved to the end ([1-15][16-32] → [16-32][1-15])
3. **Condition**: Only applies to 32x32 (1024 byte) arrays

#### Performance Variants
The system offers three performance tiers:
- **Standard** (`run_ui.py`): 20 FPS, ~50ms latency
- **Fast** (`run_ui_fast.py`): 100 FPS, ~10ms latency  
- **Ultra** (`run_ui_ultra.py`): 200 FPS, <5ms latency with frame dropping

## Development Guidelines

### Module Dependencies
- Each module is designed to be independently testable
- Serial interface reuses functions from `date.py` for port detection
- Data processor uses NumPy vectorization for 10x performance improvement
- UI components are thread-safe for real-time data updates

### Code Conventions
- All files use UTF-8 encoding with proper Chinese comment support
- Threading is used for serial data acquisition vs. UI updates
- Error handling includes detailed logging with timestamps
- Memory management includes automatic buffer size limiting

### Testing Strategy
- Use `test_modules.py` to verify all module imports before development
- Use `test_performance.py` to benchmark changes affecting real-time performance
- Test serial communication with `date.py` before UI testing

## File Structure Context

- **Runtime files**: `run_ui*.py` - Different performance variants of the main application
- **Test files**: `test_*.py` - Module validation and performance testing
- **Batch files**: `*.bat` - Windows convenience launchers
- **Documentation**: `模块说明.md` - Detailed Chinese documentation of the modular refactor