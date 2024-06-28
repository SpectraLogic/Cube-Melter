from spectracan import ChannelManager, MsgSender
from spectracan.can_commands import (LCFCmd_HeartBeat, LCFCmd_GetFirmwareVersion, LCFCmd_GetManufInfo,
    LCFCmd_SetManufInfo, LCFCmd_GetEnvironment, LCFCmd_GetEEPromData, LCFCmd_SetEEPromData, DTL_SetLoadFetCmd,
                                     DTL_GetLoadFetCmd, DTL_GetMACLinkCmd)

from spectracan.error import CanTimeoutError, ChannelNotSetUpError
from spectracan.can_enums import LcfAddress

from pycan.interfaces.kvaser.canlib import CANLIBError
from spectracan.spectra_listener import SpectraListener

# linters might not like these, but pyinstaller needs 'em
import pycan.interfaces.kvaser          # noqa # pylint: disable=unused-import
import pycan.interfaces.kvaser.canlib   # noqa # pylint: disable=unused-import
import pycan.interfaces.usb2can         # noqa # pylint: disable=unused-import

from datetime import datetime


# CHANNEL_NUM = 0
SRC_ADDRESS = LcfAddress.CAN_OPENER.value

# Time in seconds to wait for heartbeat responses during the scan
LISTENING_TIME = 3

# status byte of CAN commands
GOOD_STATUS = '0'


class CanBackend:
    def __init__(self, logger):
        self.listener = None
        self.logger = logger

    def setup_can_channel(self, channel=0, bitrate=400_000):
        """Try to set up kvaser, return true if setup successfully"""
        try:
            ChannelManager.setup_channel(channel_num=channel, device_type='kvaser', bit_rate=bitrate)
            self.logger.info("Kvaser is Ready")
            return True
        except Exception as ex:
            self.logger.info("Unable to set up Kvaser. Exception: " + str(ex))

        # TODO: Removing USB2CAN for now, need to figure out how to handle multiple usb2can devices

        self.logger.info("CAN is not setup, plug in a CAN device and restart the app")
        return False

    def send_heartbeat(self, channel, address):
        command = LCFCmd_HeartBeat.build_command()

        MsgSender.send_command_no_response(channel_num=channel,
                                           src=SRC_ADDRESS,
                                           dest=address,
                                           command=command)

    def stop_listener(self):
        """Function to stop the listener"""
        self.listener.stop = True  # stop the listener early in case of error

    def scan(self, channel, frame_callback, listen_time, stop_listener):
        # Set up a SpectraListener with custom frame_callback and timeout_callback
        self.listener = SpectraListener(channel)
        # TODO: LCR seems to be taking ~3 seconds to respond
        # TODO: test response times of other devices / set timeout accordingly
        self.listener.start_frame_consumer(frame_callback=frame_callback,
                                           timeout=listen_time,
                                           timeout_callback=stop_listener)
        self.listener.start_timer.set()  # start the timer

        # Scan all the addresses found in LcfAddress
        for device in CubeAddress:
            device_name = device.name
            address = device.value
            if device_name not in IGNORED_DEVICES:
                self.logger.info("Pinging: " + hex(address) + " " + device_name)
                try:
                    self.send_heartbeat(channel, address)
                except CanTimeoutError:
                    # Nothing plugged in with usb2can
                    self.logger.info("Error: Check the CAN bus")
                    self.stop_listener()
                    return
                except CANLIBError:
                    # Nothing plugged in with kvaser
                    self.logger.info("Error: Check the CAN bus")
                    self.stop_listener()
                    return
                except ChannelNotSetUpError as chan:
                    self.logger.info(str(chan))
                    self.stop_listener()
                    return
                except Exception as e:
                    self.logger.info("Exception: " + str(e))
                    self.stop_listener()
                    return

    def get_environment(self, channel, address):
        command = LCFCmd_GetEnvironment.build_command()

        try:
            response_bytes = MsgSender.send_command_sync(channel_num=channel,
                                                         src=SRC_ADDRESS,
                                                         dest=address,
                                                         command=command,
                                                         timeout=2)
        except Exception as err:
            self.logger.info("ERROR: Failed to get environment: " + str(err))
            return
        return LCFCmd_GetEnvironment.parse_response(response_bytes)

    def get_dtl_fets(self, channel, address):
        command = DTL_GetLoadFetCmd.build_command()

        try:
            response_bytes = MsgSender.send_command_sync(channel_num=channel,
                                                         src=SRC_ADDRESS,
                                                         dest=address,
                                                         command=command,
                                                         timeout=2)
        except Exception as err:
            self.logger.info("ERROR: Failed to get DTL FETs: " + str(err))
            return
        return DTL_GetLoadFetCmd.parse_response(response_bytes)


    def shutdown(self):
        ChannelManager.shutdown_channels()