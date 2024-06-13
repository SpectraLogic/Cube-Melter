from spectracan import ChannelManager, MsgSender
from spectracan.can_commands import (LCFCmd_HeartBeat, PMM_DeviceEnableCmd, PMM_DeviceDisableCmd,
                                     LCFCmd_GetEnvironment, CanCommand)

from spectracan.error import CanTimeoutError, ChannelNotSetUpError
from spectracan.can_enums import LcfAddress

CNUM_CANR = 0
CNUM_CANT = 1

SRC_ADDRESS = LcfAddress.CAN_OPENER.value
PMM_ADDRESS = LcfAddress.PCM_PMM_MAIN.value

class ArbitraryCommand(CanCommand):
    @classmethod
    def build_command(cls, *, payload, ack=False):
        return cls._start_command(payload[0], ack) + payload[1:]


def setup_can_channels(logger):
    """Try to set up kvaser return true if setup successfully"""
    try:
        logger.info("Trying to setup CANR...")
        ChannelManager.setup_channel(channel_num=CNUM_CANR, device_type='kvaser', bit_rate=400_000)
        logger.info("Kvaser is ready on CANR")
    except Exception as ex:
        logger.info("Unable to set up CANR. Exception: " + str(ex))
        return False

    try:
        logger.info("Trying to setup CANT...")
        ChannelManager.setup_channel(channel_num=CNUM_CANT, device_type='kvaser', bit_rate=800_000)
        logger.info("Kvaser is ready on CANT")
    except Exception as ex:
        logger.info("Unable to set up CANT. Exception: " + str(ex))
        return False
    return True


def check_pmm(logger):
    command = LCFCmd_HeartBeat.build_command()

    try:
        response_bytes = MsgSender.send_command_sync(channel_num=CNUM_CANT,
                                                     src=SRC_ADDRESS,
                                                     dest=PMM_ADDRESS,
                                                     command=command,
                                                     timeout=1)
    except CanTimeoutError:
        logger.warning(f'Timed out waiting for a response from PMM')
        return None
    else:
        return LCFCmd_HeartBeat.parse_response(response_bytes)


def set_pmm_polling(logger, enable=False):
    enable_byte = 0x10 if enable else 0x00
    command = ArbitraryCommand.build_command(payload=[0x4f, 0x00, 0x10, enable_byte])

    try:
        response_bytes = MsgSender.send_command_sync(channel_num=CNUM_CANR,
                                                     src=SRC_ADDRESS,
                                                     dest=PMM_ADDRESS,
                                                     command=command,
                                                     timeout=1)
    except CanTimeoutError:
        logger.warning(f'Timed out waiting for a response from PMM')
        return None
    else:
        return response_bytes

def parse_pmm_env(response_bytes):
    STATUS = 'status'
    PRESENT_SUPPLIES = 'present_supplies'
    env = {}
    env[STATUS] = response_bytes[5]
    env[PRESENT_SUPPLIES] = response_bytes[6]


def get_pmm_env(logger, supply_lun):
    logger.info("Get PMM Env, LUN: " + str(hex(supply_lun)))

    command = LCFCmd_GetEnvironment.build_command(lun=supply_lun)
    try:
        response_bytes = MsgSender.send_command_sync(channel_num=CNUM_CANR,
                                                     src=SRC_ADDRESS,
                                                     dest=PMM_ADDRESS,
                                                     command=command,
                                                     timeout=1)
    except Exception as err:
        logger.info("Failed to get environment:" + str(err))
        return None
    return response_bytes

