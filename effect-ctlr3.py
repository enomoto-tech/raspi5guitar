# coding: utf-8

import smbus
from time import sleep
import struct
import socket
import subprocess

# MPU9250 I2C address
MPU9250_ADDR = 0x68

# MPU9250 register addresses for gyroscope data
GYRO_XOUT_H = 0x43
GYRO_YOUT_H = 0x45
GYRO_ZOUT_H = 0x47

# UDP settings for OSC communication
OSC_IP = "127.0.0.1"
OSC_PORT = 9002

# Function to send OSC messages
def send_osc(address, value):
    """Send an OSC message over UDP."""
    # Build the OSC message
    msg = b"," + struct.pack(">f", value)
    data = b"\x00".join([address.encode("utf-8"), b",f", msg])
    # Send via UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(data, (OSC_IP, OSC_PORT))

# Function to read gyroscope data from MPU9250
def read_gyro(bus, addr, reg_h):
    """Read gyroscope data from MPU9250."""
    high = bus.read_byte_data(addr, reg_h)
    low = bus.read_byte_data(addr, reg_h + 1)
    value = (high << 8) | low
    # Handle negative values
    if value > 32767:
        value -= 65536
    return value

# Main process
if __name__ == "__main__":
    try:
        # Launch Pure Data with the specified patch hcmpl_lt1.pdのフルパスは各自編集してください
        pd_process = subprocess.Popen(["puredata", "/home/pi/pd/hcmpl_lt1.pd"])

        bus = smbus.SMBus(1)  # Initialize I2C bus
        bus.write_byte_data(MPU9250_ADDR, 0x6B, 0)  # Wake up MPU9250

        state = 0
        prev_gyro_x = 0
        wah_value = 0
        wah_min = 10
        wah_max = 127

        while True:
            # Read gyroscope data
            gyro_x = read_gyro(bus, MPU9250_ADDR, GYRO_XOUT_H)
            gyro_z = read_gyro(bus, MPU9250_ADDR, GYRO_ZOUT_H)

            wah_delta = (prev_gyro_x - gyro_x) / 2
            if abs(wah_delta) > 5:
                if wah_delta > 0:
                    wah_value = min(wah_value + wah_delta, wah_max)
                else:
                    wah_value = max(wah_value + wah_delta, wah_min)
                send_osc("/wah", wah_value)

            if gyro_z > 10000:
                state += 1
            else:
                if state >= 1:
                    send_osc("/effect", 1.0)
                state = 0

            prev_gyro_x = gyro_x
            sleep(0.1)

    except KeyboardInterrupt:
        print("Exiting...")
        if pd_process:
            pd_process.terminate()  # Terminate the Pure Data process
