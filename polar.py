from bleak import BleakClient, BleakScanner
import argparse
import sys
import asyncio
import math
import logging
import contextlib
import csv
import time
from pathlib import Path
from datetime import datetime

devices = {
    'Polar OH1 85E77F28': '', # 1
    'Polar OH1 6EFADA2E': '', # 2
    'Polar OH1 84BF0B2D': '', # 3
    'Polar OH1 6E85CB22': '', # 4
    'Polar OH1 D025F429': '', # 5
    'Polar OH1 85EA7F2B': '', # 6
    'Polar OH1 84BF1A2F': '', # 7
}

HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

PMD_SERVICE_UUID = "fb005c80-02e7-f387-1cad-8acd2d8df0c8"
PMD_CONTROL_UUID = "fb005c81-02e7-f387-1cad-8acd2d8df0c8"
PMD_DATA_UUID = "fb005c82-02e7-f387-1cad-8acd2d8df0c8"

ELECTRO_SERVICE_UUID = "0000feee-0000-1000-8000-00805f9b34fb"
ELECTRO_CHAR1_UUID = "fb005c51-02e7-f387-1cad-8acd2d8df0c8"
ELECTRO_CHAR2_UUID = "fb005c52-02e7-f387-1cad-8acd2d8df0c8"
ELECTRO_CHAR3_UUID = "fb005c53-02e7-f387-1cad-8acd2d8df0c8"

async def discover(args):
    devices = await BleakScanner.discover()
    for device in devices:
        try:
            async with BleakClient(device) as client:
                print(f"Services found for device")
                print(f"Name: \033[92m{device.name}\033[0m")
                print(f"\tDevice Address:{device.address}")

                print("\tAll Services")
                for service in client.services:
                    print()
                    print(f"\t\tDescription: {service.description}")
                    print(f"\t\tService: {service}")
        except Exception as e:
                print(f"Could not connect to device: {device}")
                print(f"Error: {e}")

def hr_data_conv(data):
    """
    `data` is formatted according to the GATT Characteristic and Object Type 0x2A37 Heart Rate Measurement which is one of the three characteristics included in the "GATT Service 0x180D Heart Rate".
    `data` can include the following bytes:
    - flags
        Always present.
        - bit 0: HR format (uint8 vs. uint16)
        - bit 1, 2: sensor contact status
        - bit 3: energy expenditure status
        - bit 4: RR interval status
    - HR
        Encoded by one or two bytes depending on flags/bit0. One byte is always present (uint8). Two bytes (uint16) are necessary to represent HR > 255.
    - energy expenditure
        Encoded by 2 bytes. Only present if flags/bit3.
    - inter-beat-intervals (IBIs)
        One IBI is encoded by 2 consecutive bytes. Up to 18 bytes depending on presence of uint16 HR format and energy expenditure.
    """
    byte0 = data[0] # heart rate format
    uint8_format = (byte0 & 1) == 0
    energy_expenditure = ((byte0 >> 3) & 1) == 1
    rr_interval = ((byte0 >> 4) & 1) == 1

    first_rr_byte = 2
    if uint8_format:
        hr = data[1]
    else:
        hr = (data[2] << 8) | data[1] # uint16
        first_rr_byte += 1

    if energy_expenditure:
        ee = (data[first_rr_byte + 1] << 8) | data[first_rr_byte]
        first_rr_byte += 2
    else:
        ee = None

    ibis = []
    for i in range(first_rr_byte, len(data), 2):
        ibi = (data[i + 1] << 8) | data[i]
        # Polar H7, H9, and H10 record IBIs in 1/1024 seconds format.
        # Convert 1/1024 sec format to milliseconds.
        # TODO: move conversion to model and only convert if sensor doesn't
        # transmit data in milliseconds.
        ibi = math.ceil(ibi / 1024 * 1000)
        ibis.append(ibi)

    return hr, ee, ibis

async def record_from_device(device_name: str, lock: asyncio.Lock, csv_file_name, time0, properties = {}):
    try:
        async with contextlib.AsyncExitStack() as stack:
            async with lock:
                logging.debug("scanning for %s", device_name)
                device = await BleakScanner.find_device_by_name(device_name)
                logging.debug("stopped scanning for %s", device_name)

                if device is None:
                    logging.error("%s not found", device_name)
                    return

                client = BleakClient(device, timeout=100)

                logging.debug("connecting to %s", device_name)
                await stack.enter_async_context(client)
                stack.callback(logging.info, "disconnecting from %s", device_name)

            with open(csv_file_name, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=['timestamp', 'device', 'subject', 'phase', 'time', 'heartrate'])
                writer.writeheader()

                def hr_data_dump(sender, data):
                    hr, ee, ibis = hr_data_conv(data)

                    writer.writerow({
                        'timestamp': datetime.now().isoformat(),
                        'time': time.time() - time0,
                        'device': device_name,
                        'heartrate': hr
                    } | properties)

                logging.info("recording from %s", device_name)
                await client.start_notify(HEART_RATE_MEASUREMENT_UUID, hr_data_dump)

                try:
                    while True:
                        await asyncio.sleep(10)
                except asyncio.CancelledError:
                    pass

                await client.stop_notify(HEART_RATE_MEASUREMENT_UUID)

        logging.debug("disconnected from %s", device_name)
    except Exception:
        logging.exception("error with %s", device_name)

async def record(args):
    subjects = args.subjects
    phase = args.phase
    output_folder = args.output_folder

    lock = asyncio.Lock()
    t0 = time.time()

    await asyncio.gather(
        *(
            record_from_device(device_name, lock,
                            csv_file_name=output_folder / f"{subject}_{phase}.csv",
                            time0=t0,
                            properties={'subject': subject, 'phase': phase})
            for (subject, device_name) in zip(subjects, devices)
        )
    )

PPG_SETTING = bytearray([0x01, #get settings
                         0x01]) #type PPG

async def test(args):
    for (name, device) in devices.items():
        async with BleakClient(device, timeout=100) as client:
            response = await client.write_gatt_char(PMD_CONTROL_UUID, PPG_SETTING, response=True)
            print(f"{name}: {response}")
            data = await client.read_gatt_char(PMD_DATA_UUID)
            print(f"{name}: {data}")


async def read(args):
    for (name, device) in devices.items():
        async with BleakClient(device, timeout=100) as client:
            response = await client.read_gatt_char(args.uuid)
            print(f"{name}: {response}")

async def check_battery(args):
    for (device_name, device_address) in devices.items():
        logging.info("scanning for %s", device_name)
        device = await BleakScanner.find_device_by_name(device_name)
        logging.info("stopped scanning for %s", device_name)

        if device is None:
            logging.error("%s not found", device_name)
            return

        logging.info("connecting to %s", device_name)

        async with BleakClient(device, timeout=100) as client:
            response = await client.read_gatt_char(BATTERY_LEVEL_UUID)
            level = response[0]
            print(f"{device_name}: {level}")

        logging.info("disconnected from %s", device_name)

def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true", help="sets the log level to debug")

    subparsers = parser.add_subparsers(title='subcommands',
                                       dest="subcommand",
                                       description='valid subcommands',
                                       help='additional help')

    parser_discover = subparsers.add_parser('discover')
    parser_battery = subparsers.add_parser('battery')
    parser_test = subparsers.add_parser('test')

    parser_record = subparsers.add_parser('record')
    parser_record.add_argument('--subjects', "--sub", type=str, nargs='+', default=[])
    parser_record.add_argument('--output_folder', type=Path, default=Path.cwd())
    parser_record.add_argument('--phase', type=str, default="0")

    parser_read = subparsers.add_parser('read')
    parser_read.add_argument('uuid', type=str)

    args = parser.parse_args(args=args)

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )

    try:
        if args.subcommand == 'discover':
            task = discover(args)
        elif args.subcommand == 'record':
            task = record(args)
        elif args.subcommand == 'battery':
            task = check_battery(args)
        elif args.subcommand == 'read':
            task = read(args)
        elif args.subcommand == 'test':
            task = test(args)
        else:
            parser.print_help()
            return 0

        asyncio.run(task)

    except KeyboardInterrupt:
        pass

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
