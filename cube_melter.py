##
# Module with the CUBEMELTER Tool

import logging
import os
import re
from datetime import datetime

import time
from logging.handlers import RotatingFileHandler

from spectracan.can_enums import LcfAddress

from tkinter import (Tk, Button, LabelFrame, Label, Text, Entry, BooleanVar, IntVar, END, Scrollbar, ttk,
                     font, Checkbutton, DoubleVar)

from AddressDictionary import AddressDictionary, PMM_LUNS

from backend import CanBackend

LOG_NAME = 'CUBEMELTER.log'
VERSION = '1.0.0'

CNUM_CANR = 0
CNUM_CANT = 1

SRC_ADDRESS = LcfAddress.CAN_OPENER.value
PMM_ADDRESS = LcfAddress.PCM_PMM_MAIN.value

# Time in seconds to wait for heartbeat responses during the scan
LISTENING_TIME = 3

DTL_MAX_TEMP = 90


class CUBEMELTER:
    """Class that implements the CUBEMELTER tool"""

    def __init__(self, root, backend):
        """Initializes a CUMEMELTER object

        Args:
            root: Root of the Tkinter display
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info('Creating CUBMELTER display')

        root.title(f'CUBEMELTER {VERSION}')
        root.geometry('')
        root.rowconfigure(2, weight=1)

        root.defaultFont = font.nametofont("TkDefaultFont")
        root.defaultFont.configure(size=7)

        """  Try setting an icon with the window. Won't likely work on Linux though  """
        try:
            root.iconbitmap(resource_path('icon.ico'))
        except Exception:
            pass
        root.resizable(False, False)

        # Updatable GUI Elements
        self.number_of_addresses = IntVar()  # Addresses that have been scanned
        self.number_of_responses = IntVar()  # Number of responses received
        self.lbox_output = None
        self.btn_scan = None
        # TODO: Change relevant dicts to use DoubleVars
        self.dict_present_cbs = dict()      # {int address : BooleanVar present} used to update the checkboxes
        self.dict_12v_fet_set = dict()      # {int address : IntVar fets_to_set}
        self.dict_5v_fet_set = dict()       # {int address : IntVar fets_to_set}
        self.dict_dpm_voltage = dict()      # {int address : DoubleVar dpm_voltage}
        self.dict_dpm_current = dict()      # {int address : DoubleVar dpm_current}
        self.dict_dtl_sensor_temp = dict()  # {int address : IntVar dtl_temp}
        self.dict_dtl_cpu_temp = dict()     # {int address : IntVar dtl_temp}
        self.dict_supply_status = dict()    # {int supplyLUN : IntVar supply_status}
        self.dict_supply_temp = dict()      # {int supplyLUN : IntVar supply_temp}
        self.dict_supply_voltage = dict()   # {int supplyLUN : IntVar supply_voltage}
        self.dict_supply_current = dict()   # {int supplyLUN : IntVar supply_current}
        self.dict_supply_fspeed = dict()    # {int supplyLUN : IntVar supply_fspeed}
        self.dict_supply_ac = dict()        # {int supplyLUN : IntVar supply_ac}
        self.dict_supply_dc = dict()        # {int supplyLUN : IntVar supply_dc}

        # Create the GUI using the tkinter grid layout manager

        for dba_num in [1, 2, 3, 4]:
            self.create_dba_frame(root, dba_num)

        self.create_scan_frame(root)
        self.create_supply_frame(root)
        self.create_output_frame(root)

        # Set up channel manager
        self.can_backend = backend
        self.scan_done = BooleanVar(value=False)

        # Set up the CAN channels
        self.can_ready = False
        self.can_ready = self.can_backend.setup_can_channel(CNUM_CANR, 400_000)
        self.can_ready = self.can_backend.setup_can_channel(CNUM_CANT, 800_000)
        if not self.can_ready:
            self.log_to_output("CAN is not setup, plug in a CAN device and restart the app")
            return

    def create_dba_frame(self, root, dba_num):
        """Creates each DBA Frame"""
        # DBA Frame
        self.logger.info('Creating DBA Frame {}'.format(dba_num))
        self.frame_dba = LabelFrame(root, text="DBA{}".format(dba_num), labelanchor='w')
        self.frame_dba.grid(row=dba_num-1, column=0, sticky='nsew')

        # DPM? Label
        lbl_dpm_present = Label(self.frame_dba, text='DPM?')
        lbl_dpm_present.grid(row=0, column=1)
        # DTL? Label
        lbl_dtl_present = Label(self.frame_dba, text='DTL?')
        lbl_dtl_present.grid(row=0, column=2)
        # V Label
        lbl_volts = Label(self.frame_dba, text='V')
        lbl_volts.grid(row=0, column=4)
        # A Label
        lbl_amps = Label(self.frame_dba, text='A')
        lbl_amps.grid(row=0, column=5)
        # DTL CPU TEMP
        lbl_dtl_temp = Label(self.frame_dba, text='cpu °C')
        lbl_dtl_temp.grid(row=0, column=7)
        # DTL TEMP
        lbl_dtl_temp = Label(self.frame_dba, text='°C')
        lbl_dtl_temp.grid(row=0, column=8)
        # 5VFetSet Label
        lbl_mfg_date = Label(self.frame_dba, text='5VFetSet')
        lbl_mfg_date.grid(row=0, column=9)
        # 12VFetSet Label
        lbl_mfg_date = Label(self.frame_dba, text='12VFetSet')
        lbl_mfg_date.grid(row=0, column=10)

        for i in range(1, 9):
            # Sled Label
            lbl_mfg_date = Label(self.frame_dba, text='Sled{}'.format(i))
            lbl_mfg_date.grid(row=i, column=0)

            # Use CANAddresses for dict keys, look it up in AddressDictionary
            dtl_address = AddressDictionary["DBA{}_DTL{}".format(dba_num, i)]
            dpm_address = AddressDictionary["DBA{}_DPM{}".format(dba_num, i)]
            self.logger.info('dtl_address:{} dpm_address:{}'.format(dtl_address, dpm_address))

            # DPM CheckBox
            dpm_check_var = BooleanVar()
            cb_dpm = Checkbutton(self.frame_dba, variable=dpm_check_var)
            cb_dpm.configure(state='disabled')
            cb_dpm.grid(row=i, column=1)
            self.dict_present_cbs.update({dpm_address: dpm_check_var})

            # DTL CheckBox
            dtl_check_var = BooleanVar()
            cb_dtl = Checkbutton(self.frame_dba, variable=dtl_check_var)
            cb_dtl.configure(state='disabled')
            cb_dtl.grid(row=i, column=2)
            self.dict_present_cbs.update({dtl_address: dtl_check_var})

            # Get DPM Env Button
            btn_get_dpm = Button(self.frame_dba, text='Get DPM ENV:', height=0,
                                 command=lambda address=dpm_address:
                                 self.get_dpm_env(address))
            # set_fet_button.configure(state='disabled')
            btn_get_dpm.grid(row=i, column=3)

            # DPM Voltage Box
            dpm_volts = DoubleVar()
            ent_dpm_volts = Entry(self.frame_dba, background='white', width=5, textvariable=dpm_volts)
            ent_dpm_volts.configure(state='disabled')
            ent_dpm_volts.grid(row=i, column=4)
            self.dict_dpm_voltage.update({dpm_address: dpm_volts})

            # DPM Current Box
            dpm_current = DoubleVar()
            ent_dpm_amps = Entry(self.frame_dba, background='white', width=5, textvariable=dpm_current)
            ent_dpm_amps.configure(state='disabled')
            ent_dpm_amps.grid(row=i, column=5)
            self.dict_dpm_current.update({dpm_address: dpm_current})

            # Get DTL Env Button
            btn_get_dtl = Button(self.frame_dba, text='Get DTL ENV:', height=0,
                                 command=lambda address=dtl_address:
                                 self.get_dtl_env(address))
            # set_fet_button.configure(state='disabled')
            btn_get_dtl.grid(row=i, column=6)

            # DTL CPU Temperature Box
            dtl_cpu_temp = IntVar()
            ent_dtl_cpu_temp = Entry(self.frame_dba, background='white', width=4, textvariable=dtl_cpu_temp)
            ent_dtl_cpu_temp.configure(state='disabled')
            ent_dtl_cpu_temp.grid(row=i, column=7)
            self.dict_dtl_cpu_temp.update({dtl_address: dtl_cpu_temp})

            # DTL Temperature Box
            dtl_temp = IntVar()
            ent_dtl_temp = Entry(self.frame_dba, background='white', width=4, textvariable=dtl_temp)
            ent_dtl_temp.configure(state='disabled')
            ent_dtl_temp.grid(row=i, column=8)
            self.dict_dtl_sensor_temp.update({dtl_address: dtl_temp})

            # 5VFetSetBox
            set5_var = IntVar()
            ent_5v_fets_set = Entry(self.frame_dba, background='white', width=5, textvariable=set5_var)
            # ent_5v_fets_set.configure(state='disabled') # TODO: only enable if dpm and dtl present
            ent_5v_fets_set.grid(row=i, column=9)
            self.dict_5v_fet_set.update({dtl_address: set5_var})

            # 12VFetSet Box
            set12_var = IntVar()
            ent_12v_fets_set = Entry(self.frame_dba, background='white', width=5, textvariable=set12_var)
            # ent_12v_fets_set.configure(state='disabled') # TODO: only enable if dpm and dtl present
            ent_12v_fets_set.grid(row=i, column=10)
            self.dict_12v_fet_set.update({dtl_address: set12_var})

            # Enable DPM Button
            btn_set_fet = Button(self.frame_dba, text='Enable DPM', height=0,
                                 command=lambda address=dpm_address:
                                 self.set_dpm_enable(address))
            # set_fet_button.configure(state='disabled')
            btn_set_fet.grid(row=i, column=11)

            # Disable DPM Button
            btn_set_fet = Button(self.frame_dba, text='Disable DPM', height=0,
                                 command=lambda address=dpm_address:
                                 self.set_dpm_disable(address))
            # set_fet_button.configure(state='disabled')
            btn_set_fet.grid(row=i, column=12)

            # Set Fets Button
            btn_set_fet = Button(self.frame_dba, text='Set Fets', height=0,
                                 command=lambda address=dtl_address:
                                 self.set_dtl_load(address))
            # set_fet_button.configure(state='disabled')
            btn_set_fet.grid(row=i, column=13)

    def create_scan_frame(self, root):
        """Creates the Scan frame where Scan Button and info is displayed"""
        # Scan Frame
        self.logger.info('Creating Scan Frame')
        frame_scan = LabelFrame(root)
        frame_scan.grid(row=0, column=1, sticky='nsew')
        frame_scan.grid_columnconfigure(2, weight=1)

        # Addresses Scanned Label
        lbl_adr_scan = Label(frame_scan, text='Addresses Scanned:')
        lbl_adr_scan.grid(row=0, column=0)
        # Addresses Scanned Var
        box_adr_scan = Label(frame_scan, text='', background='white', width=3, textvariable=self.number_of_addresses)
        box_adr_scan.grid(row=0, column=1)

        # Responses Received Label
        lbl_rsp_rec = Label(frame_scan, text='Responses Received:')
        lbl_rsp_rec.grid(row=1, column=0)
        # Responses Received Var
        self.box_resp_rec = Label(frame_scan, text='', background='white', width=3,
                                  textvariable=self.number_of_responses)
        self.box_resp_rec.grid(row=1, column=1)

        # Scan Button
        self.btn_scan = Button(frame_scan, text='Scan', height=2, width=16, command=self.start_scan)
        self.btn_scan.grid(row=0, column=2, rowspan=2)
        
        # Get All All DTL Environment Button
        self.btn_dtl_env = Button(frame_scan,text='Get All DTL Envs',
                                  height=3, width=20, command=self.click_get_all_dtl_env)
        self.btn_dtl_env.grid(row=6, column=0, rowspan=2)

        # Enable All DPM Button
        self.btn_dtl_env = Button(frame_scan, text='Enable All DPMs', height=3, width=20, command=self.click_enable_dpms)
        self.btn_dtl_env.grid(row=2, column=2, rowspan=2)

        # Get All DPM Environment Button
        self.btn_dpm_env = Button(frame_scan,text='Get All DPM Envs',
                                  height=3, width=20, command=self.click_get_all_dpm_env)
        self.btn_dpm_env.grid(row=2, column=0, rowspan=2)

        # Disable All DPM BUtton
        self.btn_dpm_env = Button(frame_scan, text='Disable All DPMs', height=3, width=20, command=self.click_disable_dpms)
        self.btn_dpm_env.grid(row=6, column=2, rowspan=2)

        # Get PMM ENV Button
        self.btn_pmm_env = Button(frame_scan,text='Get PMM ENV', height=3, width=20, command=self.click_get_pmm_env)
        self.btn_pmm_env.grid(row=10, column=0, rowspan=2)

    def create_supply_frame(self, root):
        """Creates the Supply frame where Supply Environments are displayed"""
        # Scan Frame
        self.logger.info('Creating Supply Frame')
        frame_supply = LabelFrame(root)
        frame_supply.grid(row=1, column=1, sticky='nsew')
        frame_supply.grid_columnconfigure(2, weight=1)

        """Supply Environment headings"""
        # Status Heading
        lbl_supply_status = Label(frame_supply, text='Status')
        lbl_supply_status.grid(row=2, column=2)
        # Temp Heading
        lbl_supply_temp = Label(frame_supply, text='Temp')
        lbl_supply_temp.grid(row=2, column=3)
        # Voltage Heading
        lbl_supply_voltage = Label(frame_supply, text='V')
        lbl_supply_voltage.grid(row=2, column=4)
        # Current Heading
        lbl_supply_current = Label(frame_supply, text='A')
        lbl_supply_current.grid(row=2, column=5)
        # Fan Speed Heading
        lbl_supply_fspeed = Label(frame_supply, text='Fan(%)')
        lbl_supply_fspeed.grid(row=2, column=6)
        # AC Heading
        lbl_supply_ac = Label(frame_supply, text='AC(W)')
        lbl_supply_ac.grid(row=2, column=7)
        # DC Heading
        lbl_supply_dc = Label(frame_supply, text='DC(W)')
        lbl_supply_dc.grid(row=2, column=8)

        for supply_num in [0,1,2]:
            # Supply Label
            lbl_supply_num = Label(frame_supply, text='Supply{}'.format(supply_num))
            lbl_supply_num.grid(row=3+supply_num, column=0)

            supply_lun = PMM_LUNS["Supply{}".format(supply_num)]

            # Get Button
            btn_get_supply_env = Button(frame_supply, text='GET',
                                        command=lambda lun=supply_lun:
                                        self.get_supply_env(lun))
            btn_get_supply_env.grid(row=3+supply_num, column=1)

            # Status Box
            supply_status = IntVar()
            ent_supply_status = Entry(frame_supply, background='white', width=3, textvariable=supply_status)
            ent_supply_status.configure(state='disabled')
            ent_supply_status.grid(row=3+supply_num, column=2)
            self.dict_supply_status.update({supply_lun: supply_status})

            # Temp Box
            supply_temp = IntVar()
            ent_supply_temp = Entry(frame_supply, background='white', width=3, textvariable=supply_temp)
            ent_supply_temp.configure(state='disabled')
            ent_supply_temp.grid(row=3 + supply_num, column=3)
            self.dict_supply_temp.update({supply_lun: supply_temp})

            # Voltage Box
            supply_voltage = IntVar()
            ent_supply_voltage = Entry(frame_supply, background='white', width=5, textvariable=supply_voltage)
            ent_supply_voltage.configure(state='disabled')
            ent_supply_voltage.grid(row=3 + supply_num, column=4)
            self.dict_supply_voltage.update({supply_lun: supply_voltage})

            # Current Box
            supply_current = IntVar()
            ent_supply_current = Entry(frame_supply, background='white', width=5, textvariable=supply_current)
            ent_supply_current.configure(state='disabled')
            ent_supply_current.grid(row=3 + supply_num, column=5)
            self.dict_supply_current.update({supply_lun: supply_current})

            # Fan Speed Box
            supply_fspeed = IntVar()
            ent_supply_fspeed = Entry(frame_supply, background='white', width=3, textvariable=supply_fspeed)
            ent_supply_fspeed.configure(state='disabled')
            ent_supply_fspeed.grid(row=3 + supply_num, column=6)
            self.dict_supply_fspeed.update({supply_lun: supply_fspeed})

            # AC Power Box
            supply_ac = IntVar()
            ent_supply_ac = Entry(frame_supply, background='white', width=3, textvariable=supply_ac)
            ent_supply_ac.configure(state='disabled')
            ent_supply_ac.grid(row=3 + supply_num, column=7)
            self.dict_supply_ac.update({supply_lun: supply_ac})

            # DC Power Box
            supply_dc = IntVar()
            ent_supply_dc = Entry(frame_supply, background='white', width=3, textvariable=supply_dc)
            ent_supply_dc.configure(state='disabled')
            ent_supply_dc.grid(row=3 + supply_num, column=8)
            self.dict_supply_dc.update({supply_lun: supply_dc})

        # All 5V Label
        lbl_all_twelve = Label(frame_supply, text='All 5:')
        lbl_all_twelve.grid(row=8, column=1)

        # All 5 Box
        self.all_fets_five = IntVar()
        ent_all_fets_five = Entry(frame_supply, background='white', width=3, textvariable=self.all_fets_five)
        ent_all_fets_five.grid(row=8, column=2)

        # All 12V Label
        lbl_all_twelve = Label(frame_supply, text='All 12:')
        lbl_all_twelve.grid(row=8, column=3)

        # All 12 Box
        self.all_fets_twelve = IntVar()
        ent_all_fets_twelve = Entry(frame_supply, background='white', width=3, textvariable=self.all_fets_twelve)
        ent_all_fets_twelve.grid(row=8, column=4)

        # Set all fets button
        self.btn_set_all_fets = Button(frame_supply, text='SET ALL FETS', height=2, width=16, command=self.set_all_fets)
        self.btn_set_all_fets.grid(row=9, column=1, rowspan=2)

    def create_output_frame(self, root):
        """Creates the Output frame where Users can see live output of what is happening"""
        self.logger.info('Creating Output Frame')
        frame_output = LabelFrame(root)
        frame_output.grid(row=2, column=1, rowspan=2, sticky='nesw')
        frame_output.grid_columnconfigure(0, weight=1)
        frame_output.grid_rowconfigure(0, weight=1)

        self.lbox_output = Text(frame_output, wrap='word', width=20, height=12)
        self.lbox_output.grid(row=0, column=0, sticky='nesw')
        self.lbox_output.config(font=("Segoe UI", 9))
        self.lbox_output.configure(state='disabled')
        # Setup a scrollbar for the output window
        vsb = Scrollbar(frame_output)
        vsb.grid(row=0, column=1, sticky='ns')
        self.lbox_output.config(yscrollcommand=vsb.set)
        vsb.config(command=self.lbox_output.yview)

    def frame_handler(self, frame):
        """Callback given to SpectraListener.
        Receives a CanFrame, if it is the first heartbeat response from a given address add it to the treeview"""
        # TODO: Improve / Test the check here, maybe use spectracan.cli.parser to do some of the heavy lifting
        if frame.dest == SRC_ADDRESS and frame.is_response:
            # self.logger.info(str(frame))  # For debug purposes
            self.log_to_output("response from: " + str(hex(frame.src)))
            self.dict_present_cbs[frame.src].set(True)
            self.number_of_responses.set(self.number_of_responses.get() + 1)
            self.box_resp_rec.update()
        
    def stop_listener(self):
        """Callback used to stop and cleanup the listener,
        called after LISTENING_TIME expires or manually if there was a CAN error"""
        self.logger.info("Stopping listener...")  # Log only
        self.listener.stop = True
        # Re-enable the scan button
        self.btn_scan["state"] = "normal"
        self.log_to_output("Stopped Listener")
        # self.check_valid_sleds()

    def check_valid_sleds(self):
        self.log_to_output("Checking for valid sleds...")
        # TODO: Only Enable Device Control for Present Devices

    def start_scan(self):
        """Function called on Scan button click"""
        # Don't bother if CAN isn't setup
        if not self.can_ready:
            # TODO: tried to retry self.setup_can_channel() here but couldn't get it working, seems to require a restart
            self.log_to_output("CAN is not setup, plug in a CAN device and restart the app")
            return

        # Disable Scan button
        self.btn_scan["state"] = "disabled"

        self.log_to_output("Starting Scan")

        # Clear the GUI
        self.number_of_addresses.set(0)
        self.number_of_responses.set(0)
        for value in self.dict_present_cbs.values():
            value.set(False)

        # TODO: Clear the rest of the GUI

    def click_get_pmm_env(self):
        self.log_to_output("CLick get PMM")

    def get_dpm_env(self, dpm_address):
        self.log_to_output("Get DPM Env:" + str(hex(dpm_address)))

        dpm_env = self.can_backend.get_environment(CNUM_CANT, dpm_address)
        self.log_to_output(str(dpm_env))
        self.dict_dpm_voltage[dpm_address].set(dpm_env['twelve_volt'])
        self.dict_dpm_current[dpm_address].set(dpm_env['current'])

    def get_dtl_env(self, dtl_address):
        self.log_to_output("Get DTL Env:" + str(hex(dtl_address)))

        dtl_env = self.can_backend.get_environment(CNUM_CANT, dtl_address)
        self.log_to_output(str(dtl_env))
        self.dict_dtl_sensor_temp[dtl_address].set(dtl_env['sensor_temperature'])
        self.dict_dtl_cpu_temp[dtl_address].set(dtl_env['cpu_temperature'])

        dtl_fets = self.can_backend.get_dtl_fets(CNUM_CANT, dtl_address)
        self.log_to_output(str(dtl_fets))
        self.dict_5v_fet_set[dtl_address].set(dtl_fets['num_enabled_fets_5v'])
        self.dict_12v_fet_set[dtl_address].set(dtl_fets['num_enabled_fets_12v'])

        # Adds Temperature Control for Fet Shut off
        """if dtl_temp > DTL_MAX_TEMP:
            fets_to_set_5 = 0
            fets_to_set_12 = 0
            output_string = ("Set DTL:" + str(hex(dtl_address)) + " {#5VFets:" +
                         str(fets_to_set_5) + ", #12VFets:" + str(fets_to_set_12) + "}")
            self.log_to_output(output_string)
            command = ArbitraryCommand.build_command(payload=[0x6f, 0x35, 0x02, 0, 0])
            MsgSender.send_command_no_response(channel_num=CNUM_CANT,
                                           src=SRC_ADDRESS,
                                           dest=dtl_address,
                                           command=command)"""
        
    def click_get_all_dtl_env(self):
        self.log_to_output("Getting all DTL Environments")
        dtl_addresses = [
            0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
            0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97,
            0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
            0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7
            ]

        for i in self.dict_present_cbs:
            t_f = self.dict_present_cbs[i].get()
            if t_f is True and i in dtl_addresses:
                time.sleep(0.02)
                self.get_dtl_env(i)

    def click_get_all_dpm_env(self):
        self.log_to_output("Getting all DPM Environments")
        dpm_addresses = [
            0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,
            0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,
            0x20,0x21,0x22,0x23,0x24,0x25,0x26,0x27,
            0x30,0x31,0x32,0x33,0x34,0x35,0x36,0x37
            ]

        for i in self.dict_present_cbs:
            t_f = self.dict_present_cbs[i].get()
            if t_f is True and i in dpm_addresses:
                time.sleep(0.02)
                self.get_dpm_env(i)

    def click_disable_dpms(self):
        dpm_addresses = [
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
            0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
            0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37
        ]
        for i in self.dict_present_cbs:
            t_f = self.dict_present_cbs[i].get()
            if t_f is True and i in dpm_addresses:
                time.sleep(0.01)
                self.set_dpm_disable(i)
    
    def click_enable_dpms(self):
        dpm_addresses = [
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
            0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
            0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37
        ]
        for i in self.dict_present_cbs:
            t_f = self.dict_present_cbs[i].get()
            if t_f is True and i in dpm_addresses:
                time.sleep(0.01)
                self.set_dpm_enable(i)

    def get_supply_env(self, supply_lun):
        self.log_to_output("Get Supply Env, LUN: " + str(hex(supply_lun)))

        """self.dict_supply_voltage[supply_lun].set(self.round_up(float(supply_volts), 2))
        # self.dict_supply_current[supply_lun].set(self.round_up(float(supply_current), 2))
        self.dict_supply_current[supply_lun].set(float(supply_current))"""

    def set_dpm_enable(self, dpm_address):
        self.log_to_output("Enable DPM:" + str(hex(dpm_address)))

    def set_dpm_disable(self, dpm_address):
        self.log_to_output("Disable DPM:" + str(hex(dpm_address)))

    def set_dtl_load(self, dtl_address):
        fets_to_set_5 = self.dict_5v_fet_set[dtl_address].get()
        fets_to_set_12 = self.dict_12v_fet_set[dtl_address].get()
        output_string = ("Set DTL:" + str(hex(dtl_address)) + " {#5VFets:" +
                         str(fets_to_set_5) + ", #12VFets:" + str(fets_to_set_12) + "}")

        self.log_to_output(output_string)

    def set_dtl_load_spec(self, dtl_address, fets_5, fets_12):
        fets_to_set_5 = fets_5
        fets_to_set_12 = fets_12
        output_string = ("Set DTL:" + str(hex(dtl_address)) + " {#5VFets:" +
                         str(fets_to_set_5) + ", #12VFets:" + str(fets_to_set_12) + "}")

        self.log_to_output(output_string)

    def set_all_fets(self):
        self.log_to_output("Setting all 5V Fets to:" + str(self.all_fets_five.get())
                           + ", 12V Fets to:" + str(self.all_fets_twelve.get()))

        # TODO: these are used multiple places, use broader scope
        dtl_addresses = [
            0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
            0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97,
            0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
            0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7
        ]

        for i in self.dict_present_cbs:
            t_f = self.dict_present_cbs[i].get()
            if t_f is True and i in dtl_addresses:
                time.sleep(0.01)
                self.set_dtl_load_spec(i, self.all_fets_five.get(), self.all_fets_twelve.get())

    def log_to_output(self, info):
        """Add info to the log AND to the output window"""
        self.logger.info(info)
        self.lbox_output.configure(state='normal')
        self.lbox_output.insert(END, info + '\n')
        self.lbox_output.configure(state='disabled')
        self.lbox_output.see(END)
        self.lbox_output.update()


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def main():
    """Start the CUBEMELTER tool"""
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s : %(name)s %(funcName)s() - %(message)s',
        level=logging.INFO,
        handlers=[
            RotatingFileHandler(LOG_NAME, maxBytes=1000000, backupCount=5),  # ~1MB
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    logger.info('Starting the CUBEMELTER tool')
    can_backend = CanBackend(logger)
    # Run the program
    try:
        root = Tk()
        CUBEMELTER(root, can_backend)
        root.mainloop()
    except Exception as err:  # pylint: disable=broad-except
        logger.exception(err)
    finally:
        logger.info('Closing the program')
        logger.info('Shutting down Channel(s)')
        can_backend.shutdown()
        logging.shutdown()


if __name__ == '__main__':
    main()
