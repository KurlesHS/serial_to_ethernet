__author__ = 'alexey'
port = 8000
device = '/dev/ttyUSB0'

import os
from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.internet.protocol import Protocol
from twisted.internet.serialport import SerialPort
from twisted.internet.task import LoopingCall
from twisted.application import service
from twisted.application import internet
from twisted.python import log
from twisted.python.log import ILogObserver, FileLogObserver
from twisted.python.logfile import DailyLogFile

client_list = []
usb_list = []

class USBClient(Protocol):

    def __init__(self, network):
        self.network = network
        self.usb_list = []
        self.lc = LoopingCall(self.timerEvent)
        self.serialBuffer = bytes("")

    def timerEvent(self):
        self.lc.stop()
        for cli in client_list:
            cli.transport.write(self.serialBuffer)
        self.serialBuffer = bytes("")

    def connectionFailed(self):
        log.msg ("Connection Failed:", self)
        reactor.stop()

    def connectionMade(self):
        usb_list.append(self)
        log.msg("Connected to %s device" % device)

    def dataReceived(self, data):
        #log.msg("data resrvr")
        self.serialBuffer += data
        if self.lc.running:
            self.lc.stop()
        self.lc.start(0.2, False)

    def sendLine(self, cmd):
        print cmd
        self.transport.write(cmd + "\r\n")

    def outReceived(self, data):
        self.data = self.data + data


class CommandRx(Protocol):
    def connectionMade(self):
        client_list.append(self)

    def dataReceived(self, data):
        for usb in usb_list:
            usb.transport.write(data)

    def connectionLost(self, reason):
        log.msg('Connection lost', reason)
        if self in client_list:
            print "Removing " + str(self)
            client_list.remove(self)


class CommandRxFactory(Factory):
    protocol = CommandRx
    def init(self):
        self.client_list = []
    def buildProtocol(self, addr):
        log.msg("connection received from %s" % addr)
        return CommandRx()

class SerialService(service.Service):
    def __init__(self, factory, device):
        self.factory = factory
        self.device = device

    def startService(self):
        SerialPort(self.factory, self.device, reactor)

logPath = "/var/log/serialtoethernetd/"
if not os.path.exists(logPath):
    os.mkdir(logPath)

logFile = DailyLogFile("messages.log", logPath, defaultMode=0644)
multiService = service.MultiService()
tcpfactory = CommandRxFactory()
tcpService = internet.TCPServer(port, tcpfactory).setServiceParent(multiService)
serialService = SerialService(USBClient(tcpfactory), device).setServiceParent(multiService)
application = service.Application("serial port to ethernet")
application.setComponent(ILogObserver, FileLogObserver(logFile).emit)
multiService.setServiceParent(application)
#SerialPort(USBClient(tcpfactory), device, reactor)
