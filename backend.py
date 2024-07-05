from spectracan import ChannelManager, MsgSender
from spectracan.can_commands import (LCFCmd_HeartBeat, LCFCmd_GetEnvironment, DTL_GetLoadFetCmd, DTL_GetMACLinkCmd,
                                     DTL_GetIPAddrCmd, LCFCmd_RunDiagnostic, PMM_DeviceEnableCmd, PMM_DeviceDisableCmd,
                                     DTL_SetLoadFetCmd)

from spectracan.error import CanTimeoutError, ChannelNotSetUpError
from spectracan.can_enums import LcfAddress, DiagnosticId
from AddressDictionary import AddressDictionary

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

IGNORED_DEVICES = []


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
        self.listener.start_frame_consumer(frame_callback=frame_callback,
                                           timeout=listen_time,
                                           timeout_callback=stop_listener)
        self.listener.start_timer.set()  # start the timer

        # Scan all the addresses found in AddressDictionary
        for device in AddressDictionary:
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

    def get_environment(self, channel, address, lun=0):
        command = LCFCmd_GetEnvironment.build_command(lun=lun)

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

    def set_dtl_fets(self, channel, address, fets_5v, fets_12v):
        command = DTL_SetLoadFetCmd.build_command(fets_5v, fets_12v)

        try:
            MsgSender.send_command_sync(channel_num=channel,
                                        src=SRC_ADDRESS,
                                        dest=address,
                                        command=command,
                                        timeout=2)
        except Exception as err:
            self.logger.info("ERROR: Failed to set DTL FETs: " + str(err))
            return
        return True

    def get_dtl_mac(self, channel, address):
        command = DTL_GetMACLinkCmd.build_command()

        try:
            response_bytes = MsgSender.send_command_sync(channel_num=channel,
                                                         src=SRC_ADDRESS,
                                                         dest=address,
                                                         command=command,
                                                         timeout=2)
        except Exception as err:
            self.logger.info("ERROR: Failed to get DTL MAC: " + str(err))
            return
        return DTL_GetMACLinkCmd.parse_response(response_bytes)

    def get_dtl_ip(self, channel, address):
        command = DTL_GetIPAddrCmd.build_command()

        try:
            response_bytes = MsgSender.send_command_sync(channel_num=channel,
                                                         src=SRC_ADDRESS,
                                                         dest=address,
                                                         command=command,
                                                         timeout=2)
        except Exception as err:
            self.logger.info("ERROR: Failed to get DTL IP: " + str(err))
            return
        return DTL_GetIPAddrCmd.parse_response(response_bytes)

    def set_pmm_polling(self, poll_state):

        command = LCFCmd_RunDiagnostic.build_command(
            diagnostic_id=DiagnosticId.DIAG_ID_BUS_SCAN_MODE.value,
            rsvd=poll_state
        )

        try:
            response_bytes = MsgSender.send_command_sync(channel_num=0,
                                                         src=SRC_ADDRESS,
                                                         dest=AddressDictionary.PMM.value,
                                                         command=command,
                                                         timeout=2)
        except Exception as err:
            self.logger.info("ERROR: Failed to set PMM polling: " + str(err))
            return
        return LCFCmd_RunDiagnostic.parse_response(response_bytes)

    def set_pmm_device_state(self, channel, address, lun=0, state=True):
        if state:
            command = PMM_DeviceEnableCmd.build_command(sub_module=lun)
        else:
            command = PMM_DeviceDisableCmd.build_command(sub_module=lun)

        try:
            MsgSender.send_command_sync(channel_num=channel,
                                        src=SRC_ADDRESS,
                                        dest=address,
                                        command=command,
                                        timeout=2)
        except Exception as err:
            self.logger.info("ERROR: Failed to set PMM device state: " + str(err))
            return
        return True

    def set_supply_state(self, lun, state):
        if state:
            command = PMM_DeviceEnableCmd.build_command(sub_module=lun)
        else:
            command = PMM_DeviceDisableCmd.build_command(sub_module=lun)

        try:
            MsgSender.send_command_sync(channel_num=0,
                                        src=SRC_ADDRESS,
                                        dest=AddressDictionary.PMM.value,
                                        command=command,
                                        timeout=2)
        except Exception as err:
            self.logger.info("ERROR: Failed to set Supply state: " + str(err))
            return
        return True

    def shutdown(self):
        ChannelManager.shutdown_channels()