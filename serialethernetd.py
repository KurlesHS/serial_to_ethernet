__author__ = 'alexey'
port = 8000
device = '/dev/ttyUSB0'

import sys
from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.internet.protocol import Protocol
from twisted.internet.serialport import SerialPort
from twisted.internet.task import LoopingCall
from twisted.python import log

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
        log.msg("Connected to %d device" % device)
        USBClient.sendLine(self, 'AT\r\n')

    def dataReceived(self, data):
        self.serialBuffer += data
        if self.lc.running:
            self.lc.stop()
        self.lc.start(0.2, False)
        for cli in client_list:
            cli.transport.write(data)


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


tcpfactory = CommandRxFactory()
reactor.listenTCP(port, tcpfactory)
SerialPort(USBClient(tcpfactory), device, reactor)
reactor.run()
