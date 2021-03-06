#!/usr/bin/env python
"""
Blocky Talky - User Script (us.py, RabbitMQ client)

The module that works with the program written in the Blocky Talky GUI.
"""
import time
import thread
import logging
import socket
import usercode
import pika
from blockytalky_id import *
from message import *
import urllib2

class UserScript(object):
    def __init__(self):
        self.hostname = BlockyTalkyID()
        self.msgQueue = []
        self.robot = Message.initStatus()
        
        #true if unread data from sensor
        self.sensorStatus= Message.createSensorStatus()
        print self.sensorStatus.values()


    def executeScript(self):
        """
        Resets the robot to its default state and runs the script downloaded
        from Google Blockly via usercode.run().
        """
        # Initialize local image to the default state.
        self.robot = Message.initStatus()
        # Runs the user code generated by Blockly.
        logging.info("Running usercode.py ...")
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.queue_declare(queue="HwCmd")
        connection2 = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel2 = connection2.channel()
        channel2.queue_declare(queue="Message")
        usercode.run(self, channel, channel2)

    def getSensorValue(self, sensorType, port):
        key = sensorType + str(port+1)
        #print key
        self.sensorStatus[key] = False
        return self.robot[sensorType+'s'][port]
        

    def checkContent(self, content):
        """ used with "message that says: ____" blocks.  returns true if first
        element in message queue has the desired content.  otherwise
        returns false
        """
        if self.msgQueue:
            if self.msgQueue[0].getContent() == content:
                del self.msgQueue[0]
                return True
        return False

    def checkSource(self, source):
        """ used with "message from: ____" blocks.  returns true if first
        element in message queue is from the desired client.  otherwise
        returns false
        """
        if self.msgQueue:
            if self.msgQueue[0].getSource() == source:
                del self.msgQueue[0]
                return True
        return False

    def on_connected(self, connection):
        connection.channel(us.on_channel_open)

    def on_channel_open(self, new_channel):
        global channel
        channel = new_channel
        self.channel = new_channel
        channel.queue_declare(queue="HwVal", callback=us.on_queue_declared)

    def on_queue_declared(self, frame):
        channel.basic_consume(us.handle_delivery, queue="HwVal", no_ack=True)

    def handle_delivery(self, channel, method, header, body):
        """
        The incoming message is either a hardware status update, a command sent
        by another Pi or a social media status update.
            # On HW message: update the robot
            # On Pi message: add to message queue
            # On SM message: TBD
        """
        # For testing purposes
        message = Message.decode(body)
        if message.getChannel() == "Message":
            # If it's a "do this" type message ...
            self.msgQueue.append(message)
        elif message.getChannel() == "Subs":
            print str(message)
            usercode.run(self, self.channel)
        else:
            # If it's a robot status update ...
            hwDict = message.getContent()
            # Apply the value changes
            for key, valueList in hwDict.iteritems():
                for index, value in enumerate(valueList):
                    if value is not None:
                        self.robot[key][index] = value
           # logging.debug("Command: " + str(hwDict))
        
            #tells user script that there is unread data on all ports
            for sensor in self.sensorStatus:
                self.sensorStatus[sensor]= True

if __name__ == "__main__":
    # Set the logging level.
    logging.basicConfig(format = "%(levelname)s:\t%(message)s",
                        filename = "/home/pi/blockytalky/logs/user_script.log",
                        level = logging.ERROR)
    us = UserScript()
    thread.start_new(us.executeScript, ())

    parameters = pika.ConnectionParameters()
    connection = pika.SelectConnection(parameters, us.on_connected)
    connection.ioloop.start()
