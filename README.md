# ACOM

This application is desiged to control and monitor the ACOM 600S/700S/1200S series amplifiers.
This application is modeled after Björn Ekelund system described on his web site, https://sm7iun.se/station/acom/
source code is avalible on his github page here: https://github.com/bjornekelund

![image](https://user-images.githubusercontent.com/4152473/150659748-a0e6b7bc-7f7e-4099-ba83-7fefab24fa18.png)

This application was developed for two reasons:

     - The need to run on both PCs and MACs 
     - The need to set the CAT interface parameters

This applicatoin is written in python using the pycharm IDE

     - python 3.7   
     - pySerial 3.5

The system is modeled after Björn Ekelund work and has a minimal UI, this UI is close to Björn Ekelund
system but some of the details are different and a few visual features are missing. I developed this app
for cross platform use and the ability to switch the CAT interface using this application. In my application
I have a ICOM 7610 and a Flex 6400 that I switch between. The ICOM system is PC based and the Flex is on a MAC.
The ACOM amp is connected to both computers through an automatic serial switch. When this app starts it
configures the ACOM cat interface properly based on the computer where is was started.


The port from the orginal C# application to python required a number of changes, I am using the tkinter
UI. All the python code is in this file. There are three main classes defined:

       Comm            Serial interface class, has open/close and message sending methods
       ACOM            Defines the UI with methodes to update values, display message, etc
       Configuration   The class references Comm and ACOM and has the methods to set the system
                       parameters. On start up this class will load the save settings and configure
                       the CAT interface.
                       
An additional class called FIFO is used for the peak detection capability. The structure and design matches
Björn Ekelund original system.
In my application I have a ACOM 700S with a remote tuner connected to a ICOM-7610 and a Flex 6400.
The ACOM accessory connector goes to a A/B switch with a CAT cable to the ICOM in position A and to
the Fex in position B. The ACOM RS232 control port is connected to a RS232 comm automatic switch that
also connects to the PC controlling the ICOM and the MAC controlling the Flex. A copy of this application
is on the MAC and the PC. Thr apps are configured to set the CAT interface as needed. So all I have to do is
set the A/B switch then start the app on the proper computer and the CAT interface is configured automatically.
The A/B switch can be removed and a custom cable constructed becasue the two CAT interfaces use different
pin in the ACOM accessory connector.

This application will set the flow control lines on the serial interfaces active, these lines can be used to power the ACOM amplifier on and off. This requires the addition of a couple diodes in the RS232 automatic switch because this switch does not pass the flow control signals, only the communications signals. With the diodes in place I can just start the application to turn on the amplifier and press off then exit the application to turn the amplifier off. The PC and MAC both require a USB to RS232 interface cable that plugs into the automaic switch. All of this hardware is avalible on amazon and no amplifier modifications are required.

The Dist folder has both a MAC and PC standalone program you can dowload and run. There were built using py installer. When running on a PC you will get virus warnings from windows defender. This is a know issue with py installer. You can and should create an exclusion for ACOM.exe in defender to resolve the issue.

Please contact me if you find any bugs or would like to see additional features added to this application.

  Revision history
  
  1.0, Dec 23, 2021
  
     - Orginal release

Gordon Anderson

KG7YU

gaa@owt.com

509.628.6851
