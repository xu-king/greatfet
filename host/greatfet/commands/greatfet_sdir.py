#!/usr/bin/env python3
#
# Copyright 2016 Dominic Spill <dominicgs@gmail.com)
# Copyright 2016 Jared Boone <jared@sharebrained.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
#  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import argparse
import errno
import sys
import time

import greatfet
from greatfet import GreatFET
from greatfet.protocol import vendor_requests
from greatfet.utils import log_silent, log_verbose


def main():
    logfile = 'log.bin'
#    logfile = '/tmp/fifo'
    # Set up a simple argument parser.
    parser = argparse.ArgumentParser(description="Utility for experimenting with GreatFET's ADC")
    parser.add_argument('-s', dest='serial', metavar='<serialnumber>', type=str,
                        help="Serial number of device, if multiple devices", default=None)
    parser.add_argument('-S', dest='samplerate', metavar='<samplerate>', type=int,
                        help="Sample rate for IR Tx", default=1000000)
    parser.add_argument('-f', dest='filename', metavar='<filename>', type=str, help="File to read or write", default=logfile)
    parser.add_argument('-r', dest='receive', action='store_true', help="Write data to file")
    parser.add_argument('-R', dest='repeat', action='store_true', help="Repeat file data (tx only)")
    parser.add_argument('-v', dest='verbose', action='store_true', help="Increase verbosity of logging")
    args = parser.parse_args()

    log_function = log_verbose if args.verbose else log_silent

    try:
        log_function("Trying to find a GreatFET device...")
        device = GreatFET(serial_number=args.serial)
        log_function("{} found. (Serial number: {})".format(device.board_name(), device.serial_number()))
    except greatfet.errors.DeviceNotFoundError:
        if args.serial:
            print("No GreatFET board found matching serial '{}'.".format(args.serial), file=sys.stderr)
        else:
            print("No GreatFET board found!", file=sys.stderr)
        sys.exit(errno.ENODEV)

    if args.receive:
        device.vendor_request_out(vendor_requests.SDIR_RX_START)
        time.sleep(1)
        with open(args.filename, 'wb') as f:
            try:
                while True:
                    d = device.device.read(0x81, 0x4000, 1000)
                    # print(d)
                    f.write(d)
            except KeyboardInterrupt:
                pass
        device.vendor_request_out(vendor_requests.SDIR_RX_STOP)

    else:
        index = args.samplerate & 0xFFFF
        value = (args.samplerate >> 16) & 0xFFFF
        device.vendor_request_out(vendor_requests.SDIR_TX_START, value=value, index=index)
        time.sleep(1)
        with open(args.filename, 'rb') as f:
            try:
                while True:
                    data = f.read(0x4000)
                    if len(data) != 0x4000:
                        if args.repeat:
                            print("End of file reached. Looping")
                            f.seek(0,0)
                        else:
                            break
                        if len(data) == 0:
                            data = f.read(0x4000)
                    # print(data[:10])
                    device.device.write(0x02, data)
            except KeyboardInterrupt:
                pass
        device.vendor_request_out(vendor_requests.SDIR_TX_STOP)


if __name__ == '__main__':
    main()
