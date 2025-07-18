# Polar Heart Rate Monitor Data Collection

A Python script for collecting heart rate and PPG sensor data from Polar heart rate monitors via Bluetooth Low Energy (BLE).

## Installation

```bash
pip install bleak
```

## Usage

```bash
python polar.py [OPTIONS] COMMAND [ARGS]
```

### Global Options

- `-d`, `--debug`: Enable debug logging with detailed output
- `-v`, `--verbose`: Enable verbose logging with informational messages

### Commands

#### `discover`
Scan for and list available Polar heart rate monitors.

```bash
python polar.py discover
```

#### `battery`
Check battery level of connected Polar devices.

```bash
python polar.py battery
```

#### `test`
Test connectivity and responsiveness of Polar devices.

```bash
python polar.py test
```

#### `record`
Record heart rate and PPG sensor data from Polar devices to CSV files.

```bash
python polar.py record [OPTIONS]
```

**Options:**
- `--subjects`, `--sub`: List of subject identifiers (space-separated). Subjects are assigned in order to the predefined Polar device IDs in the script
- `--output_folder`: Directory to save CSV data files (default: current directory)
- `--phase`: Recording phase identifier (default: "0")

**Example:**
```bash
python polar.py record --subjects sub1 sub2 --output_folder ./data --phase experiment1
```

**Note:** The script contains a predefined list of Polar device IDs. When recording, subjects are assigned to devices in the order they appear in both the subjects list and the device ID list. For example, if you have 3 devices configured and specify `--subjects A B C`, subject A will be assigned to the first device, B to the second, and C to the third.

#### `read`
Read data from a specific service UUID across all Polar devices in the predefined list.

```bash
python polar.py read <service_uuid>
```

**Arguments:**
- `service_uuid`: The UUID of the service to read from (e.g., battery service, device information service)

**Example:**
```bash
python polar.py read 0000180f-0000-1000-8000-00805f9b34fb
```

**Note:** This command will attempt to read the specified service from all Polar devices configured in the script's device list.

## Examples

```bash
# Enable debug logging and discover Polar devices
python polar.py --debug discover

# Record heart rate data from multiple subjects
python polar.py record --subjects participant1 participant2 --output_folder ./experiment_data

# Read service info from all devices with verbose output
python polar.py --verbose read 0000180f-0000-1000-8000-00805f9b34fb
```

## Requirements

- Python 3.7+
- bleak library
- Polar heart rate monitor (compatible with BLE)
- Bluetooth adapter with BLE support

## Setup

1. Install the required dependencies:
   ```bash
   pip install bleak
   ```

2. Configure your Polar devices:
   - The script includes a predefined list of Polar device IDs
   - Ensure your devices match the IDs configured in the script
   - Some systems may require pairing the devices first through system Bluetooth settings
   - Put your Polar devices in pairing/discoverable mode if needed

3. Verify device connectivity:
   ```bash
   python polar.py discover
   ```

## Data Output

The `record` command saves timestamped sensor data (heart rate or PPG) to CSV files in the specified output folder. Each file contains:
- Timestamp
- Heart rate or PPG readings
- Subject identifier (assigned to devices in order)
- Phase information

Data is collected from multiple Polar devices simultaneously, with each subject identifier mapped to a specific device based on the predefined device list in the script.

## Troubleshooting

**Device not found:**
- Ensure your Polar device is powered on and in range
- Try pairing the device through your system's Bluetooth settings first
- Use the `discover` command to verify the device is visible

**Connectivity issues:**
- Check that your Bluetooth adapter supports BLE
- Restart the Bluetooth service on your system
- Move closer to the device to improve signal strength
- Use `--debug` flag for detailed error information

**Permission errors:**
- On Linux, you may need to run with elevated privileges or add your user to the `bluetooth` group
- On Windows, ensure Bluetooth permissions are enabled for the application

## License

This project is licensed under the MIT License.
