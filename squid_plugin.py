#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: squid_plugin.py
 Author: longhui
 Created Time: 2018-06-27 11:05:16
"""

from optparse import OptionParser
import time
import socket
import subprocess


class Plugin(object):
    '''
    The base class for plugins
    All you need is just to extend it, overwrite prepare_data() method,
    and call report() method in __main__.
    '''
    def report(self):
        '''
        Report your prepared_data() to destination system
        '''
        data = self.prepare_data()
        self._report_to_graphite(data)

    def console(self):
        '''
        Show the data to the cluster administrators
        '''
        data = self.prepare_data()
        self._report_to_console(data)

    def send_to_carbon(self, server, port):
        """
        :return:
        """
        CARBON_SERVER = server
        CARBON_PORT = port

        data = self.prepare_data()
        data_format = '%s.%s.%s %s %s'
        sock = socket.socket()
        sock.connect((CARBON_SERVER, CARBON_PORT))
        for item in data:
            data_map = item.format_data()
            message = data_format % (data_map["endpoint"],
                                     data_map["metric"],
                                     data_map["type"],
                                     data_map["value"],
                                     data_map["timestamp"])
            sock.sendall(message + "\n") # need to add "\n", otherwise it will give warning: unfinished line
        sock.close()

    def prepare_data(self):
        '''
        Prepare your data. Return a list of DataItem(or its subclass) instances
        '''
        raise NotImplementedError

    def _report_to_graphite(self, data):
        data_format = 'PUTVAL "%s/%s/%s" interval=%s N:%s'
        for item in data:
            data_map = item.format_data()
            print( data_format % (data_map["endpoint"], data_map["metric"],
                                 data_map["type"], data_map["step"],
                                 data_map["value"]))

    def _report_to_console(self, data):
        data_format = '%s.%s.%s %s %s' #'metric:%s type:%s value:%s timestamp:%s'
        for item in data:
            data_map = item.format_data()
            #print data_format % (data_map["endpoint"], data_map["metric"], val)
            print( data_format % (data_map["endpoint"],
                                 data_map["metric"],
                                 data_map["type"],
                                 data_map["value"],
                                 data_map["timestamp"]))

class DataItem(object):
    '''
    The base class of data items.
    If new monitor system is applied, we should support both new and old data
    format. So extend it and overwrite format_data() to satisfy new system, and
    modify old subclasses to make it capatible for old plugins
    '''

    def format_data(self):
        '''
        Formatting the data, return a dict
        '''
        raise NotImplementedError()


class GraphiteData(DataItem):
    _metric = ""
    _endpoint = ""
    _value = ""
    _step = ""
    _type = ""

    def __init__(self, endpoint, metric, type, step, value, timestamp=None):
        '''
        host/plugin-instance/type-instance
        :param endpoint: host
        :param metric: plugin-instance
        :param type: type-instance
        :param step: time interval
        :param value:
        '''
        self._endpoint = endpoint
        self._metric = metric
        self._type = type
        self._step = step
        self._value = value
        if timestamp is None:
            timestamp = time.time()
        self._timestamp = timestamp

    def format_data(self):
        return {
            "metric": self._metric,
            "endpoint": self._endpoint,
            "value": self._value,
            "step": self._step,
            "type": self._type,
            "timestamp": self._timestamp
        }


class SquidPlugin(Plugin):
    _endpoint = socket.gethostname()

    def __init__(self, step=30):
        self.step = step
        self.data = []

    def prepare_data(self ):

        self.data = []
        cmd = 'squidclient -h 127.0.0.1 -p 80 mgr:info | grep "file desc"'
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        pout, perr = p.communicate()
        if perr:
            return self.data

        timestamp = time.time()
        for line in str(pout).splitlines():
            try:
                firstpart, secondpart = line.split(":")
                firstpart = str(firstpart).strip()
                value =  str(secondpart).strip()
            except ValueError:
                continue

            if "Maximum number" in firstpart:
                self.data.append(GraphiteData(endpoint=self._endpoint, metric="squid", type="MaxFileDescNum", step=self.step,value=value, timestamp=timestamp))
            elif "Largest file desc" in firstpart:
                self.data.append(GraphiteData(endpoint=self._endpoint, metric="squid", type="LargestFileDescInUse", step=self.step,value=value, timestamp=timestamp))
            elif "Number of" in firstpart:
                self.data.append(GraphiteData(endpoint=self._endpoint, metric="squid", type="CurrentFileDescInUse", step=self.step,value=value, timestamp=timestamp))
            elif "Available number" in firstpart:
                self.data.append(GraphiteData(endpoint=self._endpoint, metric="squid", type="AvailableFileDesc", step=self.step,value=value, timestamp=timestamp))
            elif "Reserved number" in firstpart:
                self.data.append(GraphiteData(endpoint=self._endpoint, metric="squid", type="ReservedFileDesc", step=self.step,value=value, timestamp=timestamp))

        return self.data

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option('--console', dest="console", action="store_true", help="print the data to console")
    parser.add_option('--collectd-exec', dest="collectd_exec", action="store_true", help="use collectd-exec plugin")
    parser.add_option("--server", dest="server", help="Carbon server ip")
    parser.add_option("--port", dest="port", help="Port on carbon server")
    parser.add_option("--step", dest="step", help="Time interval to send data")

    (options, args) = parser.parse_args()
    if options.step:
        try:
            step = int(options.step)
        except ValueError:
            step = 30
    else:
        step = 30

    squildPlugin = SquidPlugin(step=step)
    if options.console:
        while 1:
            squildPlugin.console()
            time.sleep(step)
    elif options.collectd_exec:
        while 1:
            squildPlugin.report()
            time.sleep(step)
    elif (options.server and options.port):
        server = options.server
        try:
            port = int(options.port)
        except ValueError:
            print("Port need to be an integer, use default 2003")
            port = 2003
        while 1:
            squildPlugin.send_to_carbon(server, port)
            time.sleep(step)
    else:
        parser.print_help()


