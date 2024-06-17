import time
import os
import logging
from logging.handlers import RotatingFileHandler

from backend import *

from AddressDictionary import AddressDictionary, PMM_LUNS

LOG_NAME = 'CHASSIS_WIRING.log'

CNUM_CANR = 0
CNUM_CANT = 1

GOOD_STATUS = '0'


def main():
    # Delete existing log
    os.remove(LOG_NAME) if os.path.exists(LOG_NAME) else None

    """Start the Chassis_Wiring test"""
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s : %(name)s %(funcName)s() - %(message)s',
        level=logging.INFO,
        handlers=[
            RotatingFileHandler(LOG_NAME, maxBytes=1000000, backupCount=5),  # ~1MB
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    logger.info('Starting the CHASSIS WIRING TEST')
    # Run the program

    try:
        # SETUP CAN R AND CAN T
        if not setup_can_channels(logger):
            return

        # HEARTBEAT PMM
        logger.info("Sending Heartbeat to PMM")
        response = check_pmm(logger)
        if response is None:
            return
        if f'{response["status"]}' != GOOD_STATUS:
            logger.error("PMM is not ready")
            return
        logger.info("PMM is ready")

        # DISABLE PMM POLLING
        logger.info("Disabling PMM Polling")
        response = set_pmm_polling(logger, enable=False)
        logger.info(f'Received response: {response}')

        # GET A PMM ENVIORNMENT
        logger.info("Getting PMM Enviornment")
        response = get_pmm_env(logger, 0)  # TODO: use PMM_LUNS DICT
        logger.info(f'Received response: {response}')

        # CHECK IF PMM STATUS LOOK GOOD

        # CHECK IF ALL THREE SUPPLIES ARE PRESENT (must all be present to contniue)

        # ENABLE ALL SUPPLIES

        # HEARTBEAT DPMS and DTLS (must all be present to contniue)

        # GET ALL THE DPM/DTLS ENVIORNMENTS

        # TURN ON ALL DPMS

        # TURN ON ALL DTLS (slowly!)

        # GRAB PMM/DPM/DTL ENVIORNMENTS EVERY 3 seconds for 30 seconds

        # TURN OFF ALL DTLS and DPMS

        # ENABLE PMM POLLING

    except Exception as err:  # pylint: disable=broad-except
        logger.exception(err)
    finally:
        logger.info('Closing the program')
        logger.info('Shutting down Channel(s)')
        ChannelManager.shutdown_channels()
        logging.shutdown()


if __name__ == '__main__':
    main()
