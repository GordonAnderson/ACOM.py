# ACOM RF amplifier control program
#
#   This application is desiged to control and monitor the ACOM 600S/700S/1200S series amplifiers.
#   This application is modeled after Björn Ekelund system described on his web site, https://sm7iun.se/station/acom/
#   source code is avalible on his github page here: https://github.com/bjornekelund
#
#   This application was developed for two reasons:
#       - The need to run on both PCs and MACs
#       - The need to set the CAT interface parameters
#
#   This applicatoin is written in python using the pycharm IDE
#       - python 3.7
#       - pySerial 3.5
#
#   The system is modeled after Björn Ekelund work and has a minimal UI, this UI is close to Björn Ekelund
#   system but some of the details are different and a few visual features are missing. I developed this app
#   for cross platform use and the ability to switch the CAT interface using this application. In my application
#   I have a ICOM 7610 and a Flex 6400 that I switch between. The ICOM system is PC based and the Flex is on a MAC.
#   The ACOM amp is connected to both computers through an automatic serial switch. When this app starts it
#   configures the ACOM cat interface properly based on the computer where is was started.
#
#   The port from the orginal C# application to python required a number of changes, I am using the tkinter
#   UI. All the python code is in this file. There are three main classes defined:
#       Comm            Serial interface class, has open/close and message sending methods
#       ACOM            Defines the UI with methodes to update values, display message, etc
#       Configuration   The class references Comm and ACOM and has the methods to set the system
#                       parameters. On start up this class will load the save settings and configure
#                       the CAT interface.
#   An additional class called FIFO is used for the peak detection capability. The structure and design matches
#   Björn Ekelund original system.
#   In my application I have a ACOM 700S with a remote tuner connected to a ICOM-7610 and a Flex 6400.
#   The ACOM accessory connector goes to a A/B switch with a CAT cable to the ICOM in position A and to
#   the Fex in position B. The ACOM RS232 control port is connected to a RS232 comm automatic switch that
#   also connects to the PC controlling the ICOM and the MAC controlling the Flex. A copy of this application
#   is on the MAC and the PC. Thr apps are configured to set the CAT interface as needed. So all I have to do is
#   set the A/B switch then start the app on the proper computer and the CAT interface is configured automatically.
#   The A/B switch can be removed and a custom cable constructed becasue the two CAT interfaces use different
#   pin in the ACOM accessory connector.
#
#   Please contact me if you find any bugs or would like to see additional features added to this application.
#
#   Revision history
#   1.0, Dec 23, 2021
#       - Orginal release
#
# Gordon Anderson
# KG7YU
# gaa@owt.com
# 509.628.6851

# system imports
from __future__ import absolute_import
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog
import os
import sys
import time
import serial

# Used for peak detection. Values are entered into this FIFO and are never removed.
# When the FIFO fills the oldest value is over written. The max function will return
# the largest value in the FIFO. A get function is provided but never used in this
# application.
class FIFO:
    def __init__(self, size):
        self.values = [0.0] * size
        self.head = 0
        self.tail = 0
    def put(self,val):
        self.values[self.head] = val
        self.head += 1
        if self.head >= len(self.values): self.head = 0
    def get(self):
        val = self.values[self.head]
        self.head -= 1
        if self.head > 0: self.head =  len(self.values) - 1
    def max(self):
        m = self.values[0]
        for v in self.values:
            if v > m: m = v
        return m

# Peak detection variables
DrivePowerPeak = FIFO(8)
ReflectedPowerPeak = FIFO(8)
swrPeak = FIFO(8)
PApowerPeak = FIFO(8)
# Link status variable
linkIsAlive = False

# This class supports the RS232 communications with methods to open/close the port
#  as well as send messages to the ACOM
class Comm:
    def __init__(self, parent):
        self.master = parent
        self.isOpen = False
        self.isError = False
        self.ErrorMessage = ""
        self.statusbar = None
        self.stopbits = 1
        self.bytesize = 8
        self.baudrate = 9600
        self.flowcontrol = "None"
        self.port = ""
        self.parity = 'N'
        self.cp = None
    def open(self):
        if self.port == "": return
        xonxoff = False
        rtscts = False
        if self.flowcontrol == "RTS/CTS": rtscts = True
        if self.flowcontrol == "XON/XOFF": xonxoff = True
        try:
            self.cp = serial.Serial(self.port,self.baudrate,self.bytesize,self.parity,self.stopbits,None,xonxoff,rtscts,None,False,None,None)
            self.isError = False
            self.isOpen = True
            self.cp.rts = True
            self.cp.dtr = True
            self.ErrorMessage = "Connected: " + self.port
        except Exception as e:
            self.isError = True
            self.isOpen = False
            self.ErrorMessage = e
    def close(self):
        if self.cp == None:
            self.ErrorMessage = 'Nothing to disconnect!'
            return
        if self.cp.isOpen():
            self.cp.close()
        else:
            self.ErrorMessage = self.port + ' all ready disconnected!'
            return
        while self.cp.isOpen():
            self.master().update()
        self.isOpen = False
        self.ErrorMessage = 'Disconnected: ' + self.port
    def enable(self):
        if self.cp.isOpen():
            self.cp.rts = True
            self.cp.dtr = True
    def disable(self):
        if self.cp.isOpen():
            self.cp.rts = False
            self.cp.dtr = False
    def findPorts(self):
        from serial.tools.list_ports import comports
        ports = []
        for n, (port, desc, hwid) in enumerate(sorted(comports()), 1):
            ports.append(port)
        return ports
    def avaliable(self):
        if (self.isOpen == False): return 0
        return self.cp.inWaiting()
    def getByte(self):
        if (self.isOpen == False): return 0
        if (self.cp.inWaiting() <= 0): return 0
        try:
            return self.cp.read(1)
        except Exception as e:
            self.isError = True
            self.ErrorMessage = e
    def sendMessage(self, message):
        if (self.isOpen == False): return
        try:
            self.cp.flush()
            self.cp.write(message)
            self.isError = False
        except Exception as e:
            self.isError = True
            self.ErrorMessage = e
    def sendString(self, message):
        if(self.isOpen == False): return
        try:
            self.cp.flush()
            self.cp.write(message.encode('utf-8'))
            self.isError = False
        except Exception as e:
            self.isError = True
            self.ErrorMessage = e

# This class creates the UI with methodes to set parameters. Callbacks allow the button
# actions to signal the main program process.
class ACOM:
    def __init__(self, parent):
        self.master = parent
        self.master.geometry('650x180')
        self.master.resizable(0, 0)
        self.Model = "700S"
        self.maxPower = 800
        self.maxRpower = 170
        self.maxTemp = 100
        self.Version = ""
        self.setModel("700S")
        # determine if application is a script file or frozen exe
        if getattr(sys, 'frozen', False):
            self.application_path = os.path.dirname(sys.executable)
        elif __file__:
            self.application_path = os.path.dirname(__file__)
        self.last_path = self.application_path
        if os.name == "posix": self.isPC = False
        else: self.isPC = True
        # font sizes based on os.
        self.pbText = 18        # Progress bar text values
        self.statusSize = 20    # Text size used in status box
        self.boxText = 18       # Text size used in band and drive boxes
        self.messageText = 24   # Text size used for warning and error messages
        self.fromText = 14      # Text size for misc text on the form, SWR and Fan for example
        if self.isPC:
            self.pbText = 12
            self.statusSize = 16
            self.boxText = 12
            self.messageText = 20
            self.fromText = 10
        # callback functions
        self.callbackStandby = None
        self.callbackOperate = None
        self.callbackOff = None
        self.callbackOffRC = None
        self.callbackMessageRC = None
        # styles
        self.s = ttk.Style()
        self.s.theme_use('clam')
        self.s.configure("red.Horizontal.TProgressbar", foreground='red', background='red')
        self.s.configure("blue.Horizontal.TProgressbar", foreground='blue', background='blue')
        self.s.configure("green.Horizontal.TProgressbar", foreground='green', background='green')
        self.s.configure("blue.TButton", foreground='white', background='blue')
        self.s.configure("green.TButton", foreground='white', background='green')
        self.s.configure("gray.TButton", foreground='white', background='gray')
        # Setup all the buttons
        self.btStandby = ttk.Button(self.master, style="blue.TButton", text="Standby", command = self.onStandby)
        self.btStandby.place(x=10, y=10, width=100)
        self.btOperate = ttk.Button(self.master, style="green.TButton", text="Operate", command = self.onOperate)
        self.btOperate.place(x=130, y=10, width=100)
        self.btOff = ttk.Button(self.master, style="gray.TButton", text="Off", command = self.onOff)
        self.btOff.place(x=250, y=10, width=100)
        self.btOff.bind("<Button-2>", self.onOffclick)
        self.btOff.bind("<Button-3>", self.onOffclick)
        # Setup all progress bars
        self.pbPower = ttk.Progressbar(self.master, style="blue.Horizontal.TProgressbar", orient='horizontal',  mode='determinate')
        self.pbPower.configure(maximum = self.maxPower)
        self.pbPower.place(x=370, y=10, width=200, height = 24)
        self.pbPower.step(0)
        self.Power = tk.StringVar()
        self.lblPower = tk.Label(self.master, textvariable=self.Power)
        self.lblPower.place(x=580,y=12,width = 60, height = 20)
        self.lblPower.configure(fg = 'gray', font = ("",self.pbText), anchor="e")
        self.Power.set("0W")
        self.pbRpower = ttk.Progressbar(self.master, style="red.Horizontal.TProgressbar", orient='horizontal',  mode='determinate')
        self.pbRpower.configure(maximum = self.maxRpower)
        self.pbRpower.place(x=370, y=43, width=200, height = 24)
        self.pbRpower.step(0)
        self.Rpower = tk.StringVar()
        self.lblRpower = tk.Label(self.master, textvariable=self.Rpower)
        self.lblRpower.place(x=580,y=45,width = 60, height = 20)
        self.lblRpower.configure(fg = 'gray', font = ("",self.pbText), anchor="e")
        self.Rpower.set("0R")
        self.pbTemp = ttk.Progressbar(self.master, style="green.Horizontal.TProgressbar", orient='horizontal',  mode='determinate')
        self.pbTemp.configure(maximum = self.maxTemp)
        self.pbTemp.place(x=370, y=76, width=200, height = 24)
        self.pbTemp.step(0)
        self.Temp = tk.StringVar()
        self.lblTemp = tk.Label(self.master, textvariable=self.Temp)
        self.lblTemp.place(x=580,y=78,width = 60, height = 20)
        self.lblTemp.configure(fg = 'gray', font = ("",self.pbText), anchor="e")
        self.Temp.set("0C")
        # Status box
        self.frmStatus = tk.LabelFrame(self.master, text="Status")
        self.frmStatus.place(x=10, y=50, width=150, height=50)
        self.Status = tk.StringVar()
        self.lblStatus = tk.Label(self.frmStatus, textvariable=self.Status)
        self.lblStatus.place(x=0, y=1, width=140, height=20)
        # Band box
        self.frmBand = tk.LabelFrame(self.master, text="Band")
        self.frmBand.place(x=170, y=50, width=80, height=50)
        self.Band = tk.StringVar()
        self.lblBand = tk.Label(self.frmBand, textvariable=self.Band)
        self.lblBand.place(x=0, y=1, width=70, height=20)
        self.lblBand.configure(fg='gray', font=("", self.boxText))
        # Drive box
        self.frmDrive = tk.LabelFrame(self.master, text="Drive")
        self.frmDrive.place(x=260, y=50, width=80, height=50)
        self.Drive = tk.StringVar()
        self.lblDrive = tk.Label(self.frmDrive, textvariable=self.Drive)
        self.lblDrive.place(x=0, y=1, width=70, height=20)
        self.lblDrive.configure(fg='gray', font=("", self.boxText))
        # SWR and Fan status
        self.lblLabel = tk.Label(self.master, text="SWR:")
        self.lblLabel.place(x=10, y=120, width=40, height=20)
        self.lblLabel.configure(fg='gray', font=("", self.fromText))
        self.SWR = tk.StringVar()
        self.lblSWR = tk.Label(self.master, textvariable=self.SWR)
        self.lblSWR.place(x=50,y=120,width = 50, height = 20)
        self.lblSWR.configure(fg = 'gray', font = ("",self.fromText), anchor="e")

        self.lblLabel = tk.Label(self.master, text="Fan:")
        self.lblLabel.place(x=10, y=150, width=40, height=20)
        self.lblLabel.configure(fg='gray', font=("", self.fromText))
        self.Fan = tk.StringVar()
        self.lblFan = tk.Label(self.master, textvariable=self.Fan)
        self.lblFan.place(x=50,y=150,width = 50, height = 20)
        self.lblFan.configure(fg = 'gray', font = ("",self.fromText), anchor="e")
        # Error and warning message box
        self.Message = tk.StringVar()
        self.lblMessage = tk.Label(self.master, textvariable=self.Message)
        self.lblMessage.place(x=200,y=120,width = 400, height = 40)
        self.lblMessage.bind("<Button-1>", self.onMessageclick)
    # Events functions
    def onOffclick(self,event):
        #Here when you right click on the off button
        if(self.callbackOffRC != None): self.callbackOffRC()
    def onMessageclick(self,event):
        #Here when you right click on the error box
        if(self.callbackMessageRC != None): self.callbackMessageRC()
    def onStandby(self):
        if(self.callbackStandby != None): self.callbackStandby()
    def onOperate(self):
        if(self.callbackOperate != None): self.callbackOperate()
    def onOff(self):
        if(self.callbackOff != None): self.callbackOff()
    # Functions
    def setPower(self, pwr):
        self.pbPower['value'] = pwr
        self.Power.set(str(int(pwr))+'W')
    def setRpower(self, pwr):
        self.pbRpower['value'] =pwr
        self.Rpower.set(str(int(pwr))+'R')
    def setTemp(self, temp):
        self.pbTemp['value'] = temp
        self.Temp.set(str(int(temp))+'C')
    def setStatus(self,mess, color):
        self.lblStatus.configure(fg=color, font=("", self.statusSize))
        self.Status.set(mess)
    def setStandby(self):
        self.lblStatus.configure(fg='blue', font=("", self.statusSize))
        self.Status.set("STANDBY")
    def setReceive(self):
        self.lblStatus.configure(fg='green', font=("", self.statusSize))
        self.Status.set("RECEIVE")
    def setTransmit(self):
        self.lblStatus.configure(fg='red', font=("", self.statusSize))
        self.Status.set("TRANSMIT")
    def setBand(self,band):
        self.Band.set(band)
    def setDrive(self,drive):
        self.Drive.set(str(int(drive)) + "W")
    def setSWR(self,mess):
        self.SWR.set(str(mess))
    def setFan(self,mess):
        self.Fan.set(str(mess))
    def setWarning(self, mess):
        self.lblMessage.configure(fg='black', bg = 'yellow', font=("", self.messageText))
        self.Message.set(mess)
    def setError(self, mess):
        self.lblMessage.configure(fg='white', bg = 'red', font=("", self.messageText))
        self.Message.set(mess)
    def setMessageClear(self):
        self.lblMessage.configure(fg='black', bg = 'white', font=("", self.messageText))
        self.Message.set("")
    def isMessage(self):
        if self.Message.get() != "": return True
        else: return False
    def setDown(self):
        self.Power.set("--W")
        self.pbPower['value'] = 0
        self.Rpower.set("--R")
        self.pbRpower['value'] = 0
        self.Temp.set("--C")
        self.pbTemp['value'] = 0
        self.setBand("--m")
        self.setSWR("")
        self.setFan("")
        self.Drive.set("")
        self.setMessageClear()
    def setModel(self,PAmodel):
        if PAmodel == "600S":
            self.maxPower = 700
            self.maxRpower = 150
        elif PAmodel == "700S":
            self.maxPower = 800
            self.maxRpower = 170
        elif PAmodel == "1000S":
            self.maxPower = 1200
            self.maxRpower = 250
        elif PAmodel == "1200S":
            self.maxPower = 1400
            self.maxRpower = 300
        else: return
        self.Model = PAmodel
        self.Version = "ACOM " + self.Model + ", Version 1.0, Dec 22, 2021"
        self.master.title(self.Version)
    def setStandbyCallback(self,function):
        self.callbackStandby = function
    def setOperateCallback(self,function):
        self.callbackOperate = function
    def setOffCallback(self,function):
        self.callbackOff = function
    def setOffRCCallback(self,function):
        self.callbackOffRC = function
    def setMessageCallback(self,function):
        self.callbackMessageRC = function

# This class loads the saved settings and allows the user to change the system
# configuration.
class Configure:
    def __init__(self, parent, comm, acom):
        self.master = parent
        self.cp = comm
        self.acom = acom
        self.isError = False
        self.ErrorMessage = ""
        self.PAmodels = "600S", "700S", "1000S", "1200S"
        self.CATports = "None", "RS232", "TTL", "BDC", "Analog"
        self.CATmodes = "None", "ICOM", "YEASU FT-450", "YEASU FT-817...", "YEASU FT-1000MP...", "ELECRAFT/KENWOOD"
        self.CATbauds = "None", "1200", "4800", "9600", "19200", "38400", "57600"
        # CAT setup message template, bytes 5 and 6 and checksum are filled based on selected
        # settings
        self.catMessage = [0x55, 0x81, 0x08, 0x05, 0x00, 0x00, 0x00, 0x00]
        # Application configuration parameters
        self.port    = ""
        self.PAmodel = "700S"
        self.CATport = "TTL"
        self.CATmode = "ICOM"
        self.CATbaud = "4800"
        self.loadSettings(os.path.dirname(sys.executable) + "/ACOM.settings")
        self.configure()
    def configure(self):
        self.acom.setModel(self.PAmodel)
        self.cp.port = self.port
        self.updateCATmessage()
        try:
            self.cp.close()
            self.cp.open()
            # Send CAT setup message
            self.cp.sendMessage(self.catMessage)
        except Exception as e:
            self.isError = True
            self.ErrorMessage = e
    def saveSettings(self, fileName):
        try:
            f = open(fileName, "wt")
            f.write("Model," + self.PAmodel + "\n")
            f.write("Port," + self.port + "\n")
            f.write("CATport," + self.CATport + "\n")
            f.write("CATmode," + self.CATmode + "\n")
            f.write("CATbaud," + self.CATbaud + "\n")
            f.close()
        except Exception as e:
            self.isError = True
            self.ErrorMessage = e
    def loadSettings(self, fileName):
        try:
            f = open(fileName, "rt")
            for x in f:
                y = x.split(",")
                arg = ""
                if len(y) >= 2: arg = y[1].strip()
                if y[0] == "Model": self.PAmodel = arg
                elif y[0] == "Port": self.port = arg
                elif y[0] == "CATport": self.CATport = arg
                elif y[0] == "CATmode": self.CATmode = arg
                elif y[0] == "CATbaud": self.CATbaud = arg
            f.close()
        except Exception as e:
            self.isError = True
            self.ErrorMessage = e
    def getPAmodel(self):
        return self.PAmodel
    def getPort(self):
        return self.port
    def updateCATmessage(self):
        i = self.CATports.index(self.CATport) << 4
        try: i |= self.CATmodes.index(self.CATmode)
        except: pass
        try: self.catMessage[4] = i
        except: pass
        try: i = self.CATbauds.index(self.CATbaud) << 4
        except: pass
        self.catMessage[5] = i
        self.catMessage[7] = 0
        # Calculate the checksum
        checksum = 0
        for c in self.catMessage:
            checksum += c & 0xff
        checksum &= 0xFF
        self.catMessage[7] = (0 - checksum) & 0xFF
    def settings(self):
        def portSelected(event):
            self.port = portsel.get()
        def modelSelected(event):
            self.PAmodel = PAmodel.get()
            self.acom.setModel(self.PAmodel)
        def catPortSelected(event):
            self.CATport = CATport.get()
        def catModeSelected(event):
            self.CATmode = CATmode.get()
        def catBaudSelected(event):
            self.CATbaud = CATbaud.get()
        def acceptPressed():
            self.configure()
            self.saveSettings(os.path.dirname(sys.executable) + "/ACOM.settings")
            settings.destroy()
        settings = tk.Toplevel(self.master)
        settings.title("ACOM configuration")
        settings.geometry('220x300')
        # Comm port selection
        lblLabel = tk.Label(settings, text="Comm port", anchor="w")
        lblLabel.place(x=10, y=5, width=100, height=10)
        portsel = ttk.Combobox(settings, width=20)
        portsel['values'] = [""] + self.cp.findPorts()
        portsel.bind("<<ComboboxSelected>>", portSelected)
        portsel.set(self.port)
        portsel.place(x=10, y=25, width =200)
        # Power amplifier selection
        lblLabel = tk.Label(settings, text="Amplifier model", anchor="w")
        lblLabel.place(x=10, y=50, width=100, height=20)
        PAmodel = ttk.Combobox(settings, width=20)
        PAmodel['values'] = self.PAmodels
        PAmodel.place(x=10, y=75, width =200)
        PAmodel.bind("<<ComboboxSelected>>", modelSelected)
        PAmodel.set(self.PAmodel)
        # Cat port selection
        lblLabel = tk.Label(settings, text="CAT port", anchor="w")
        lblLabel.place(x=10, y=100, width=100, height=20)
        CATport = ttk.Combobox(settings, width=20)
        CATport['values'] = self.CATports
        CATport.place(x=10, y=125, width =200)
        CATport.bind("<<ComboboxSelected>>", catPortSelected)
        CATport.set(self.CATport)
        # Cat mode
        lblLabel = tk.Label(settings, text="CAT mode", anchor="w")
        lblLabel.place(x=10, y=150, width=100, height=20)
        CATmode = ttk.Combobox(settings, width=20)
        CATmode['values'] = self.CATmodes
        CATmode.place(x=10, y=175, width =200)
        CATmode.bind("<<ComboboxSelected>>", catModeSelected)
        CATmode.set(self.CATmode)
        # Cat baudrate
        lblLabel = tk.Label(settings, text="CAT baudrate", anchor="w")
        lblLabel.place(x=10, y=200, width=100, height=20)
        CATbaud = ttk.Combobox(settings, width=20)
        CATbaud['values'] = self.CATbauds
        CATbaud.place(x=10, y=225, width =200)
        CATbaud.bind("<<ComboboxSelected>>", catBaudSelected)
        CATbaud.set(self.CATbaud)
        # Accept button
        btAccept = ttk.Button(settings, text="Accept", command = acceptPressed)
        btAccept.place(x=60, y=260, width=100)
        settings.mainloop()

# ACOM main
def main():
    #ACOM message strings
    commandEnableTelemetry  = 0x55, 0x92, 0x04, 0x15
    commandDisableTelemetry = 0x55, 0x91, 0x04, 0x16

    messageOperate = 0x55, 0x81, 0x08, 0x02, 0x00, 0x06, 0x00, 0x1A
    messageStandby = 0x55, 0x81, 0x08, 0x02, 0x00, 0x05, 0x00, 0x1B
    messageOff     = 0x55, 0x81, 0x08, 0x02, 0x00, 0x0A, 0x00, 0x16
    restartMessage = 0x55, 0x81, 0x08, 0x02, 0x00, 0x02, 0x00, 0x1E

    BandName = "?m", "160m", "80m", "40/60m", "30m", "20m","17m", "15m", "12m", "10m", "6m", "?m", "?m", "?m", "?m", "?m"

    #Callback functions
    def StandbyPressed():
        # Turn on the AMP
        comm.enable()
        comm.sendMessage(messageStandby)
    def OperatePressed():
        comm.sendMessage(messageOperate)
    def OffPressed():
        comm.sendMessage(messageOff)
        #Turn off the amp
        comm.disable()
    def MessageCB():
        if acom.isMessage(): comm.sendMessage(messageOperate)
    def OffRC():
        config.settings()

    # Called when the app closes
    def on_closing():
        comm.sendMessage(commandDisableTelemetry)
        root.destroy()

    # Process Telemetry data and update dialog. This function runs continously looking for received
    # messages.
    def ProcessTelemerty():
        global DrivePowerPeak,ReflectedPowerPeak,swrPeak,PApowerPeak,linkIsAlive
        # Message starts with 0x55, 0x2F
        msgLen = 72
        msg = bytearray(0)
        if(comm.avaliable() < msgLen):
            root.after(20, ProcessTelemerty)
            return
        while(comm.avaliable() > 0):
            linkIsAlive = True
            b = bytes(comm.getByte())
            if len(msg) == 0:
                if b[0] == 0x55: msg.append(b[0])
            elif len(msg) == 1:
                if b[0] == 0x2f: msg.append(b[0])
            elif len(msg) > 1: msg.append(b[0])
            if len(msg) == msgLen:
                # Now decode the message
                chksum = 0
                for c in msg:
                    chksum += c & 0xFF
                    chksum &= 0xFF
                if (chksum & 0xff) == 0:
                    # Valid checksum
                    PAstatus = (msg[3] & 0xF0) >> 4
                    if PAstatus == 1: acom.setStatus("RESET", 'black')
                    elif PAstatus == 2: acom.setStatus("INIT", 'black')
                    elif PAstatus == 3: acom.setStatus("DEBUG", 'black')
                    elif PAstatus == 4: acom.setStatus("SERVICE", 'black')
                    elif PAstatus == 5: acom.setStandby()
                    elif PAstatus == 6: acom.setReceive()
                    elif PAstatus == 7: acom.setTransmit()
                    elif PAstatus == 9: acom.setStatus("SYSTEM", 'black')
                    elif PAstatus == 10: acom.setStatus("OFF", 'gray')
                    else: acom.setStatus("UNKNOWN", 'gray')
                    #Tmperature bar with fan status
                    PAtemp = msg[16] + msg[17] * 256 - 273  # extract data from message
                    PAfan = (msg[69] & 0xF0) >> 4
                    if (PAstatus != 10): # PAstatus == 10 means in powering down mode
                        if (PAtemp >= 0 & PAtemp <= 100): # safety for corrupted reads
                            acom.setTemp(PAtemp)
                        if PAfan == 1: acom.setFan("Fan 1")
                        elif PAfan == 2: acom.setFan("Fan 2")
                        elif PAfan == 3: acom.setFan("Fan 3")
                        elif PAfan == 4: acom.setFan("Fan 4")
                        else: acom.setFan("")
                        DrivePowerCurrent = msg[20] + msg[21] * 256.0
                        DrivePowerPeak.put(DrivePowerCurrent)
                        ReflectedPowerCurrent = msg[24] + msg[25] * 256.0
                        ReflectedPowerPeak.put(ReflectedPowerCurrent)
                        swrCurrent = (msg[26] + msg[27] * 256) / 100.0
                        swrPeak.put(swrCurrent)
                        PApowerCurrent = 1.02 * (msg[22] + msg[23] * 256)
                        PApowerPeak.put(PApowerCurrent)
                        #display the parameters
                        acom.setPower(PApowerPeak.max())
                        acom.setRpower(ReflectedPowerPeak.max())
                        acom.setSWR("{:.1f}".format(swrPeak.max()))
                        acom.setDrive(DrivePowerPeak.max()/10.0)
                        acom.setBand(BandName[msg[69] & 0x0F])
                        errorCode = msg[66]
                        if errorCode == 0xff:
                            acom.setMessageClear()
                        else:
                            if (errorCode == 0x0) or (errorCode == 0x8): acom.setError("Hot switching")
                            elif (errorCode == 0x3): acom.setError("Drive power at wrong time")
                            elif (errorCode == 0x4) or (errorCode == 0x5): acom.setError("Reflected power warning")
                            elif (errorCode == 0x6) or (errorCode == 0x7): acom.setError("Drive power too high")
                            elif (errorCode == 0xc): acom.setError("RF power at wrong time")
                            elif (errorCode == 0xe): acom.setError("Stop transmission first")
                            elif (errorCode == 0xf): acom.setError("Remove drive power")
                            elif (errorCode == 0x24) or (errorCode == 0x25) or (errorCode == 0x39): acom.setError("Excessive PAM current")
                            elif (errorCode == 0x44) or (errorCode == 0x45) or (errorCode == 0x59): acom.setError("Excessive PAM current")
                            elif (errorCode == 0x70): acom.setWarning("CAT error")
                            else: acom.setWarning("ERROR - See display")
                    else:
                        #PA is powering down
                        acom.setDown()
        root.after(20,ProcessTelemerty)

    # This function runs every 500mS to make sure the telemetry is running, if
    # not a message is sent to start telemetry
    def RequestTelemetry():
        global linkIsAlive
        if linkIsAlive == False:
            comm.sendMessage(commandEnableTelemetry)
            acom.setDown()
        root.after(500, RequestTelemetry)
        linkIsAlive = False

    #System setup
    root = tk.Tk()
    # Create the three system objects
    comm = Comm(root)
    acom = ACOM(root)
    acom.setDown()  # Set default state to shutdown
    config = Configure(root, comm, acom)
    # Setup all the callbacks from the acom object
    acom.setStandbyCallback(StandbyPressed)
    acom.setOperateCallback(OperatePressed)
    acom.setOffCallback(OffPressed)
    acom.setOffRCCallback(OffRC)
    acom.setMessageCallback(MessageCB)
    # Start telemetry
    RequestTelemetry()
    ProcessTelemerty()
    # Paint the UI and lets go!
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
