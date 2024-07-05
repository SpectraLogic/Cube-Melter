##
# Module with the CUBEMELTER Tool

import logging
import os

import time
from logging.handlers import RotatingFileHandler

from spectracan.can_enums import LcfAddress

from tkinter import (Tk, Button, LabelFrame, Label, Text, Entry, BooleanVar, IntVar, END, Scrollbar, ttk,
                     font, Checkbutton, DoubleVar)

from AddressDictionary import AddressDictionary, PMM_LUNS

from backend import CanBackend

LOG_NAME = 'CUBEMELTER.log'
VERSION = '1.0.0'

CAN_R = 0
CAN_T = 1

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
        self.root = root

        # Updatable GUI Elements
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

        # PMM Variables
        self.pmm_temp1 = IntVar()
        self.pmm_temp2 = IntVar()
        self.pmm_voltage = DoubleVar()
        self.pmm_current = DoubleVar()

        # Power Supply Dicts
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
        self.create_power_frames(root)
        self.create_output_frame(root)

        # Set up channel manager
        self.can_backend = backend
        self.scan_done = BooleanVar(value=False)

        # Set up the CAN channels
        self.can_ready = False
        self.can_ready = self.can_backend.setup_can_channel(CAN_R, 400_000)
        self.can_ready = self.can_backend.setup_can_channel(CAN_T, 800_000)
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
        # V Label
        lbl_volts = Label(self.frame_dba, text='V')
        lbl_volts.grid(row=0, column=5)
        # A Label
        lbl_amps = Label(self.frame_dba, text='A')
        lbl_amps.grid(row=0, column=6)
        # DTL? Label
        lbl_dtl_present = Label(self.frame_dba, text='DTL?')
        lbl_dtl_present.grid(row=0, column=7)
        # DTL CPU TEMP
        lbl_dtl_temp = Label(self.frame_dba, text='cpu °C')
        lbl_dtl_temp.grid(row=0, column=9)
        # DTL TEMP
        lbl_dtl_temp = Label(self.frame_dba, text='°C')
        lbl_dtl_temp.grid(row=0, column=10)
        # 5VFetSet Label
        lbl_mfg_date = Label(self.frame_dba, text='5VFets')
        lbl_mfg_date.grid(row=0, column=11)
        # 12VFetSet Label
        lbl_mfg_date = Label(self.frame_dba, text='12VFets')
        lbl_mfg_date.grid(row=0, column=12)

        for i in range(0, 8):
            row_num = i+1
            # Sled Label
            lbl_mfg_date = Label(self.frame_dba, text='Sled{}'.format(i))
            lbl_mfg_date.grid(row=row_num, column=0)

            # Use CANAddresses for dict keys, look it up in AddressDictionary
            dtl_address = AddressDictionary["DBA{}_DTL{}".format(dba_num, i)].value
            dpm_address = AddressDictionary["DBA{}_DPM{}".format(dba_num, i)].value
            self.logger.info('dtl_address:{} dpm_address:{}'.format(dtl_address, dpm_address))

            # DPM CheckBox
            dpm_check_var = BooleanVar()
            cb_dpm = Checkbutton(self.frame_dba, variable=dpm_check_var)
            cb_dpm.configure(state='disabled')
            cb_dpm.grid(row=row_num, column=1)
            self.dict_present_cbs.update({dpm_address: dpm_check_var})

            # Enable DPM Button
            btn_set_fet = Button(self.frame_dba, text='Enable DPM', height=0,
                                 command=lambda address=dpm_address:
                                 self.click_dpm_enable(address))
            # set_fet_button.configure(state='disabled')
            btn_set_fet.grid(row=row_num, column=2)

            # Disable DPM Button
            btn_set_fet = Button(self.frame_dba, text='Disable DPM', height=0,
                                 command=lambda address=dpm_address:
                                 self.click_dpm_disable(address))
            # set_fet_button.configure(state='disabled')
            btn_set_fet.grid(row=row_num, column=3)

            # Get DPM Env Button
            btn_get_dpm = Button(self.frame_dba, text='Get DPM ENV:', height=0,
                                 command=lambda address=dpm_address:
                                 self.click_get_dpm_env(address))
            # set_fet_button.configure(state='disabled')
            btn_get_dpm.grid(row=row_num, column=4)

            # DPM Voltage Box
            dpm_volts = DoubleVar()
            ent_dpm_volts = Entry(self.frame_dba, background='white', width=5, textvariable=dpm_volts)
            ent_dpm_volts.configure(state='disabled')
            ent_dpm_volts.grid(row=row_num, column=5)
            self.dict_dpm_voltage.update({dpm_address: dpm_volts})

            # DPM Current Box
            dpm_current = DoubleVar()
            ent_dpm_amps = Entry(self.frame_dba, background='white', width=5, textvariable=dpm_current)
            ent_dpm_amps.configure(state='disabled')
            ent_dpm_amps.grid(row=row_num, column=6)
            self.dict_dpm_current.update({dpm_address: dpm_current})

            # DTL CheckBox
            dtl_check_var = BooleanVar()
            cb_dtl = Checkbutton(self.frame_dba, variable=dtl_check_var)
            cb_dtl.configure(state='disabled')
            cb_dtl.grid(row=row_num, column=7)
            self.dict_present_cbs.update({dtl_address: dtl_check_var})

            # Get DTL Env Button
            btn_get_dtl = Button(self.frame_dba, text='Get DTL ENV:', height=0,
                                 command=lambda address=dtl_address:
                                 self.click_get_dtl_env(address))
            # set_fet_button.configure(state='disabled')
            btn_get_dtl.grid(row=row_num, column=8)

            # DTL CPU Temperature Box
            dtl_cpu_temp = IntVar()
            ent_dtl_cpu_temp = Entry(self.frame_dba, background='white', width=4, textvariable=dtl_cpu_temp)
            ent_dtl_cpu_temp.configure(state='disabled')
            ent_dtl_cpu_temp.grid(row=row_num, column=9)
            self.dict_dtl_cpu_temp.update({dtl_address: dtl_cpu_temp})

            # DTL Temperature Box
            dtl_temp = IntVar()
            ent_dtl_temp = Entry(self.frame_dba, background='white', width=4, textvariable=dtl_temp)
            ent_dtl_temp.configure(state='disabled')
            ent_dtl_temp.grid(row=row_num, column=10)
            self.dict_dtl_sensor_temp.update({dtl_address: dtl_temp})

            # 5VFetSetBox
            set5_var = IntVar()
            ent_5v_fets_set = Entry(self.frame_dba, background='white', width=3, textvariable=set5_var)
            # ent_5v_fets_set.configure(state='disabled') # TODO: only enable if dpm and dtl present
            ent_5v_fets_set.grid(row=row_num, column=11)
            self.dict_5v_fet_set.update({dtl_address: set5_var})

            # 12VFetSet Box
            set12_var = IntVar()
            ent_12v_fets_set = Entry(self.frame_dba, background='white', width=3, textvariable=set12_var)
            # ent_12v_fets_set.configure(state='disabled') # TODO: only enable if dpm and dtl present
            ent_12v_fets_set.grid(row=row_num, column=12)
            self.dict_12v_fet_set.update({dtl_address: set12_var})

            # Set Fets Button
            btn_set_fet = Button(self.frame_dba, text='Set Fets', height=0,
                                 command=lambda address=dtl_address:
                                 self.click_set_dtl_load(address))
            # set_fet_button.configure(state='disabled')
            btn_set_fet.grid(row=row_num, column=13)

    def create_scan_frame(self, root):
        """Creates the Scan frame where Scan Button and info is displayed"""
        # Scan Frame
        self.logger.info('Creating Scan Frame')
        frame_scan = LabelFrame(root)
        frame_scan.grid(row=0, column=1, sticky='nsew')
        frame_scan.grid_columnconfigure(1, weight=1)

        # Scan Button
        self.btn_scan = Button(frame_scan, text='Scan', height=3, width=16, bg='lightgreen',
                               command=self.start_scan)
        self.btn_scan.grid(row=0, column=1, rowspan=2)

        # Get All DPM Environment Button
        btn_all_dpm_env = Button(frame_scan, text='Get All DPM Envs', height=3, width=16,
                                 command=self.click_get_all_dpm_env)
        btn_all_dpm_env.grid(row=4, column=1, rowspan=2)
        
        # Get All All DTL Environment Button
        btn_dtl_env = Button(frame_scan, text='Get All DTL Envs', height=3, width=16,
                             command=self.click_get_all_dtl_env)
        btn_dtl_env.grid(row=6, column=1, rowspan=2)

        # Enable All DPM Button
        btn_enable_all_dpm = Button(frame_scan, text='Enable All DPMs', height=3, width=16,
                                    command=self.click_enable_all_dpms)
        btn_enable_all_dpm.grid(row=4, column=0, rowspan=2)

        # Disable All DPM Button
        btn_disable_all_dpm = Button(frame_scan, text='Disable All DPMs', height=3, width=16,
                                     command=self.click_disable_all_dpms)
        btn_disable_all_dpm.grid(row=6, column=0, rowspan=2)

        # Enable PMM Polling Button
        btn_pmm_polling = Button(frame_scan, text='Enable PMM Polling', height=3, width=16,
                                 command=lambda poll_state=True: self.click_pmm_polling(poll_state))
        btn_pmm_polling.grid(row=4, column=2, rowspan=1)

        # Disable PMM Polling Button
        btn_pmm_polling = Button(frame_scan, text='Disable PMM Polling', height=3, width=16,
                                 command=lambda poll_state=False: self.click_pmm_polling(poll_state))
        btn_pmm_polling.grid(row=6, column=2, rowspan=1)

    def create_power_frames(self, root):
        """Creates the Supply frame where PMM and Supply Environments are displayed"""
        # Scan Frame
        self.logger.info('Creating Power Frames')
        frame_power = LabelFrame(root)
        frame_power.grid(row=1, column=1, sticky='nsew')
        frame_power.grid_columnconfigure(2, weight=1)

        frame_pmm = LabelFrame(frame_power)
        frame_pmm.grid(row=1, column=0, sticky='nsew')
        self.create_pmm_frame(frame_pmm)

        frame_supply = LabelFrame(frame_power)
        frame_supply.grid(row=2, column=0, sticky='nsew')
        self.create_supply_frame(frame_supply)

        frame_dtl_control = LabelFrame(frame_power)
        frame_dtl_control.grid(row=0, column=0, sticky='nsew')
        self.create_dtl_control_frame(frame_dtl_control)

    def create_dtl_control_frame(self, parent_frame):
        # All 5V Label
        lbl_all_twelve = Label(parent_frame, text='All 5:')
        lbl_all_twelve.grid(row=0, column=0)

        # All 5 Box
        self.all_fets_five = IntVar()
        ent_all_fets_five = Entry(parent_frame, background='white', width=3, textvariable=self.all_fets_five)
        ent_all_fets_five.grid(row=0, column=1)

        # All 12V Label
        lbl_all_twelve = Label(parent_frame, text='All 12:')
        lbl_all_twelve.grid(row=1, column=0)

        # All 12 Box
        self.all_fets_twelve = IntVar()
        ent_all_fets_twelve = Entry(parent_frame, background='white', width=3, textvariable=self.all_fets_twelve)
        ent_all_fets_twelve.grid(row=1, column=1)

        # Set all fets button
        btn_set_all_fets = Button(parent_frame, text='SET ALL FETS', height=2, width=16, command=self.click_set_all_fets)
        btn_set_all_fets.grid(row=0, column=2, rowspan=2)

    def create_pmm_frame(self, frame_pmm):
        # PMM Environment headings
        # Backplane Temp1 Heading
        lbl_pmm_temp = Label(frame_pmm, text='Temp1')
        lbl_pmm_temp.grid(row=0, column=2)

        # Backplane Temp2 Heading
        lbl_pmm_temp = Label(frame_pmm, text='Temp2')
        lbl_pmm_temp.grid(row=0, column=3)

        # PMM Voltage Heading
        lbl_pmm_voltage = Label(frame_pmm, text='V')
        lbl_pmm_voltage.grid(row=0, column=4)

        # PMM Current Heading
        lbl_pmm_current = Label(frame_pmm, text='A')
        lbl_pmm_current.grid(row=0, column=5)

        # PMM Label
        lbl_pmm = Label(frame_pmm, text='PMM     ')
        lbl_pmm.grid(row=1, column=0)

        # Get Button
        btn_get_pmm_env = Button(frame_pmm, text='GET', command=self.click_get_pmm_env)
        btn_get_pmm_env.grid(row=1, column=1)

        # Temp1 Box
        ent_pmm_temp1 = Entry(frame_pmm, background='white', width=3, textvariable=self.pmm_temp1)
        ent_pmm_temp1.configure(state='disabled')
        ent_pmm_temp1.grid(row=1, column=2)

        # Temp2 Box
        ent_pmm_temp2 = Entry(frame_pmm, background='white', width=3, textvariable=self.pmm_temp2)
        ent_pmm_temp2.configure(state='disabled')
        ent_pmm_temp2.grid(row=1, column=3)

        # Voltage Box
        ent_pmm_voltage = Entry(frame_pmm, background='white', width=5, textvariable=self.pmm_voltage)
        ent_pmm_voltage.configure(state='disabled')
        ent_pmm_voltage.grid(row=1, column=4)

        # Current Box
        ent_pmm_current = Entry(frame_pmm, background='white', width=5, textvariable=self.pmm_current)
        ent_pmm_current.configure(state='disabled')
        ent_pmm_current.grid(row=1, column=5)

    def create_supply_frame(self, frame_supply):
        # Supply Environment headings
        # Temp Heading
        lbl_supply_temp = Label(frame_supply, text='Temp')
        lbl_supply_temp.grid(row=0, column=4)
        # Voltage Heading
        lbl_supply_voltage = Label(frame_supply, text='V')
        lbl_supply_voltage.grid(row=0, column=5)
        # Current Heading
        lbl_supply_current = Label(frame_supply, text='A')
        lbl_supply_current.grid(row=0, column=6)
        # Fan Speed Heading
        lbl_supply_fspeed = Label(frame_supply, text='Fan(%)')
        lbl_supply_fspeed.grid(row=0, column=7)
        # AC Heading
        lbl_supply_ac = Label(frame_supply, text='AC(W)')
        lbl_supply_ac.grid(row=0, column=8)
        # DC Heading
        lbl_supply_dc = Label(frame_supply, text='DC(W)')
        lbl_supply_dc.grid(row=0, column=9)

        for supply_num in [1, 2, 3]:
            row_num = 0 + supply_num
            # Supply Label
            lbl_supply_num = Label(frame_supply, text='Supply{}'.format(supply_num))
            lbl_supply_num.grid(row=row_num, column=0)

            supply_lun = PMM_LUNS["Supply{}".format(supply_num)].value

            # Get Button
            btn_get_supply_env = Button(frame_supply, text='GET',
                                        command=lambda lun=supply_lun:
                                        self.click_get_supply_env(lun))
            btn_get_supply_env.grid(row=row_num, column=1)

            # Enable Button
            btn_supply_enable = Button(frame_supply, text='EN',
                                        command=lambda lun=supply_lun, state=True:
                                        self.click_supply_set_state(lun, state))
            btn_supply_enable.grid(row=row_num, column=2)

            # Disable Button
            btn_supply_disable = Button(frame_supply, text='DIS',
                                        command=lambda lun=supply_lun, state=False:
                                        self.click_supply_set_state(lun, state))
            btn_supply_disable.grid(row=row_num, column=3)

            # Temp Box
            supply_temp = IntVar()
            ent_supply_temp = Entry(frame_supply, background='white', width=3, textvariable=supply_temp)
            ent_supply_temp.configure(state='disabled')
            ent_supply_temp.grid(row=row_num, column=4)
            self.dict_supply_temp.update({supply_lun: supply_temp})

            # Voltage Box
            supply_voltage = DoubleVar()
            ent_supply_voltage = Entry(frame_supply, background='white', width=6, textvariable=supply_voltage)
            ent_supply_voltage.configure(state='disabled')
            ent_supply_voltage.grid(row=row_num, column=5)
            self.dict_supply_voltage.update({supply_lun: supply_voltage})

            # Current Box
            supply_current = DoubleVar()
            ent_supply_current = Entry(frame_supply, background='white', width=7, textvariable=supply_current)
            ent_supply_current.configure(state='disabled')
            ent_supply_current.grid(row=row_num, column=6)
            self.dict_supply_current.update({supply_lun: supply_current})

            # Fan Speed Box
            supply_fspeed = IntVar()
            ent_supply_fspeed = Entry(frame_supply, background='white', width=3, textvariable=supply_fspeed)
            ent_supply_fspeed.configure(state='disabled')
            ent_supply_fspeed.grid(row=row_num, column=7)
            self.dict_supply_fspeed.update({supply_lun: supply_fspeed})

            # AC Power Box
            supply_ac = IntVar()
            ent_supply_ac = Entry(frame_supply, background='white', width=3, textvariable=supply_ac)
            ent_supply_ac.configure(state='disabled')
            ent_supply_ac.grid(row=row_num, column=8)
            self.dict_supply_ac.update({supply_lun: supply_ac})

            # DC Power Box
            supply_dc = IntVar()
            ent_supply_dc = Entry(frame_supply, background='white', width=3, textvariable=supply_dc)
            ent_supply_dc.configure(state='disabled')
            ent_supply_dc.grid(row=row_num, column=9)
            self.dict_supply_dc.update({supply_lun: supply_dc})

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
        """Callback given to SpectraListener"""
        if frame.dest == SRC_ADDRESS and frame.is_response and frame.src in self.dict_present_cbs.keys():
            # self.logger.info(str(frame))  # For debug purposes
            self.logger.info("response from: " + str(hex(frame.src)))
            self.dict_present_cbs[frame.src].set(True)
        
    def stop_listener(self):
        """Callback used to stop and cleanup the listener,
        called after LISTENING_TIME expires or manually if there was a CAN error"""
        self.scan_done.set(True)
        self.can_backend.stop_listener()

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
        for value in self.dict_present_cbs.values():
            value.set(False)

        # TODO: Clear the rest of the GUI
        self.scan_done.set(False)
        self.can_backend.scan(CAN_T, self.frame_handler, LISTENING_TIME, self.stop_listener)

        self.root.wait_variable(self.scan_done)
        # Re-enable the scan button
        self.btn_scan["state"] = "normal"
        self.log_to_output("Scan Complete")

    def click_get_power_envs(self):
        self.log_to_output("Clicked get Power Envs")
        self.click_get_pmm_env()
        self.click_get_supply_env(1)
        self.click_get_supply_env(2)
        self.click_get_supply_env(3)

    def click_get_pmm_env(self):
        self.log_to_output("Clicked get PMM")
        pmm_env = self.can_backend.get_environment(CAN_R, PMM_ADDRESS)
        self.logger.info(str(pmm_env))

        if pmm_env is None or pmm_env['status'] != 0:
            return
        self.pmm_temp1.set(pmm_env['backplane_temperature_1'])
        self.pmm_temp2.set(pmm_env['backplane_temperature_2'])
        self.pmm_voltage.set(pmm_env['voltage'])
        self.pmm_current.set(pmm_env['current'])

    def click_get_dpm_env(self, dpm_address):
        self.log_to_output("Get DPM Env:" + str(hex(dpm_address)))

        dpm_env = self.can_backend.get_environment(CAN_T, dpm_address)
        self.logger.info(str(dpm_env))
        if dpm_env is None or dpm_env['status'] != 0:
            return
        self.dict_dpm_voltage[dpm_address].set(dpm_env['twelve_volt'])
        self.dict_dpm_current[dpm_address].set(dpm_env['twelve_volt_current'])

    def click_get_dtl_env(self, dtl_address):
        self.log_to_output("Get DTL Env:" + str(hex(dtl_address)))

        dtl_env = self.can_backend.get_environment(CAN_T, dtl_address)
        self.logger.info("Environment: " + str(dtl_env))
        if dtl_env is None or dtl_env['status'] != 0:
            return
        self.dict_dtl_sensor_temp[dtl_address].set(dtl_env['sensor_temperature'])
        cpu_temp = dtl_env['cpu_temperature']
        self.dict_dtl_cpu_temp[dtl_address].set(cpu_temp)
        if cpu_temp > DTL_MAX_TEMP:
            self.log_to_output("DTL CPU Temp is too high: " + str(cpu_temp))
            self.click_set_dtl_load(dtl_address, 0, 0)

        dtl_fets = self.can_backend.get_dtl_fets(CAN_T, dtl_address)
        self.logger.info("Get Fets: " + str(dtl_fets))
        if dtl_fets is None or dtl_fets['status'] != 0:
            return
        self.dict_5v_fet_set[dtl_address].set(dtl_fets['num_enabled_fets_5v'])
        self.dict_12v_fet_set[dtl_address].set(dtl_fets['num_enabled_fets_12v'])

        dtl_mac = self.can_backend.get_dtl_mac(CAN_T, dtl_address)
        self.logger.info("Get MAC: " + str(dtl_mac))

        dtl_ip = self.can_backend.get_dtl_ip(CAN_T, dtl_address)
        self.logger.info("Get IP: " + str(dtl_ip))
        
    def click_get_all_dtl_env(self):
        self.log_to_output("Getting all DTL Environments")
        for address in self.dict_present_cbs:
            if self.dict_present_cbs[address].get() and AddressDictionary.valid_dtl_address(address):
                # time.sleep(0.02)
                self.click_get_dtl_env(address)

    def click_get_all_dpm_env(self):
        self.log_to_output("Getting all DPM Environments")
        for address in self.dict_present_cbs:
            if self.dict_present_cbs[address].get() and AddressDictionary.valid_dpm_address(address):
                # time.sleep(0.02)
                self.click_get_dpm_env(address)

    def click_disable_all_dpms(self):
        self.log_to_output("Disabling All DPMs")
        for address in self.dict_present_cbs:
            if self.dict_present_cbs[address].get() and AddressDictionary.valid_dpm_address(address):
                # time.sleep(0.01)
                self.click_dpm_disable(address)
    
    def click_enable_all_dpms(self):
        self.log_to_output("Enabling All DPMs")
        for address in self.dict_present_cbs:
            if self.dict_present_cbs[address].get() and AddressDictionary.valid_dpm_address(address):
                # time.sleep(0.01)
                self.click_dpm_enable(address)

    def click_pmm_polling(self, poll_state):
        self.log_to_output("Set PMM Polling: " + str(poll_state))
        self.can_backend.set_pmm_polling(poll_state)

    def click_get_supply_env(self, supply_lun):
        self.log_to_output("Get Supply Env, LUN: " + str(supply_lun))
        supply_env = self.can_backend.get_environment(CAN_R, PMM_ADDRESS, supply_lun)
        self.logger.info(str(supply_env))

        if supply_env is None or supply_env['status'] != 0:
            return
        self.dict_supply_temp[supply_lun].set(supply_env['temperature'])
        self.dict_supply_voltage[supply_lun].set(supply_env['voltage'])
        self.dict_supply_current[supply_lun].set(supply_env['current'])
        self.dict_supply_fspeed[supply_lun].set(supply_env['fan_speed'])
        self.dict_supply_ac[supply_lun].set(supply_env['avg_ac_power'])
        self.dict_supply_dc[supply_lun].set(supply_env['avg_dc_power'])

    def click_supply_set_state(self, supply_lun, state):
        self.log_to_output("Set Supply State, LUN: " + str(supply_lun) + " State: " + str(state))
        self.can_backend.set_pmm_device_state(channel=CAN_R, address=PMM_ADDRESS, lun=supply_lun, state=state)

    def click_dpm_enable(self, dpm_address):
        self.log_to_output("Enable DPM:" + str(hex(dpm_address)))
        # TODO: sending directly to each DPM address on CANT for now, could use DPM LUNs via the PMM
        self.can_backend.set_pmm_device_state(channel=CAN_T, address=dpm_address, lun=0, state=True)

    def click_dpm_disable(self, dpm_address):
        self.log_to_output("Disable DPM:" + str(hex(dpm_address)))
        # TODO: sending directly to each DPM address on CANT for now, could use DPM LUNs via the PMM
        self.can_backend.set_pmm_device_state(channel=CAN_T, address=dpm_address, lun=0, state=False)

    def click_set_dtl_load(self, dtl_address, fets_to_set_5=None, fets_to_set_12=None):
        if fets_to_set_5 is None:  # Use individual GUI entries if not specified
            fets_to_set_5 = self.dict_5v_fet_set[dtl_address].get()
            fets_to_set_12 = self.dict_12v_fet_set[dtl_address].get()

        output_string = ("Set DTL:" + str(hex(dtl_address)) + " {#5VFets:" +
                         str(fets_to_set_5) + ", #12VFets:" + str(fets_to_set_12) + "}")

        self.log_to_output(output_string)
        self.can_backend.set_dtl_fets(CAN_T, dtl_address, fets_to_set_5, fets_to_set_12)

    def click_set_all_fets(self):
        self.log_to_output("Setting all 5V Fets to:" + str(self.all_fets_five.get())
                           + ", 12V Fets to:" + str(self.all_fets_twelve.get()))

        for address in self.dict_present_cbs:
            if self.dict_present_cbs[address].get() and AddressDictionary.valid_dtl_address(address):
                self.click_set_dtl_load(address, self.all_fets_five.get(), self.all_fets_twelve.get())

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
