#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: graphite_plugin.py
 Author: longhui
 Created Time: 2018-04-19 17:20:26
"""
from optparse import OptionParser
import XenAPI
import urllib
import time
import sys
import socket
import logging
from logging import handlers
from xml.dom import minidom

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
        data_format = '%s.%s %s %s'
        sock = socket.socket()
        sock.connect((CARBON_SERVER, CARBON_PORT))
        for item in data:
            data_map = item.format_data()
            message = data_format % (data_map["metric"],
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
            print data_format % (data_map["endpoint"], data_map["metric"],
                                 data_map["type"], data_map["step"],
                                 data_map["value"])

    def _report_to_console(self, data):
        data_format = '%s.%s %s %s' #'metric:%s type:%s value:%s timestamp:%s'
        for item in data:
            data_map = item.format_data()
            #print data_format % (data_map["endpoint"], data_map["metric"], val)
            print data_format % (data_map["metric"],
                                 data_map["type"],
                                 data_map["value"],
                                 data_map["timestamp"])

    def generate_graphite_data(self):
        """
        :return:
        """
        data_format = '%s.%s %s %s' #'metric:%s type:%s value:%s timestamp:%s'
        data = self.prepare_data()
        result_data=[]

        for item in data:
            data_map = item.format_data()
            #print data_format % (data_map["endpoint"], data_map["metric"], val)
            result_data.append(data_format % (data_map["metric"],
                                 data_map["type"],
                                 data_map["value"],
                                 data_map["timestamp"]))
        return result_data


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

class TestPlugin(Plugin):
    def __init__(self, endpoit, step, metric, type, value):
        self._step = step
        self._endpoit = endpoit
        self._metric = metric
        self._type = type
        self._value = value

    def prepare_data(self):
        return [GraphiteData(self._metric, self._endpoit, self._value, self._step, self._type)]


# Per VM dictionary (used by GetRRDUdpates to look up column numbers by variable names)
class VMReport(dict):
    """Used internally by GetRRDUdpates"""
    def __init__(self, uuid):
        self.uuid = uuid


# Per Host dictionary (used by GetRRDUdpates to look up column numbers by variable names)
class HostReport(dict):
    """Used internally by GetRRDUdpates"""
    def __init__(self, uuid):
        self.uuid = uuid


# Fetch and parse data class
class GetRRDUdpates:
    """ Object used to get and parse the output the http://host/rrd_udpates?..."""
    def __init__(self):
        # rrdParams are what get passed to the CGI executable in the URL
        self.rrdParams = dict()
        self.rrdParams['start'] = int(time.time()) - 10
        self.rrdParams['host'] = 'true'   # include data for host (as well as for VMs)
        self.rrdParams['cf'] = 'AVERAGE'  # consolidation function, each sample averages 12 from the 5 second RRD
        self.rrdParams['interval'] = '10'

    def GetRows(self):
        return self.rows

    def GetVMList(self):
        return self.vm_reports.keys()

    def GetVMParamList(self, uuid):
        report = self.vm_reports[uuid]
        if not report:
            return []
        return report.keys()

    def GetVMData(self, uuid, param, row):
        report = self.vm_reports[uuid]
        col = report[param]
        return self.__lookup_data(col, row)

    def GetHostUUID(self):
        report = self.host_report
        if not report:
            return None
        return report.uuid

    def GetHostParamList(self):
        report = self.host_report
        if not report:
            return []
        return report.keys()

    def GetHostData(self, param, row):
        report = self.host_report
        col = report[param]
        return self.__lookup_data(col, row)

    def GetRowTime(self, row):
        return self.__lookup_timestamp(row)

    # extract float from value (<v>) node by col,row
    def __lookup_data(self, col, row):
        # Note: the <rows> nodes are in reverse chronological order, and comprise
        # a timestamp <t> node, followed by self.columns data <v> nodes
        node = self.data_node.childNodes[self.rows - 1 - row].childNodes[col+1]
        return float(node.firstChild.toxml()) # node.firstChild should have nodeType TEXT_NODE

    # extract int from value (<t>) node by row
    def __lookup_timestamp(self, row):
        # Note: the <rows> nodes are in reverse chronological order, and comprise
        # a timestamp <t> node, followed by self.columns data <v> nodes
        node = self.data_node.childNodes[self.rows - 1 - row].childNodes[0]
        return int(node.firstChild.toxml()) # node.firstChild should have nodeType TEXT_NODE

    def Refresh(self, session, override_rrdParams = {}, server = 'http://localhost'):
        rrdParams = dict(self.rrdParams)
        rrdParams.update(override_rrdParams)
        rrdParams['host'] = "true"
        rrdParams['session_id'] = session
        rrdParamstr = "&".join(["%s=%s"  % (k,rrdParams[k]) for k in rrdParams])
        url = "%s/rrd_updates?%s" % (server, rrdParamstr)

        if verboselog:
            verboselog.info("Query: %s" % url)

        # this is better than urllib.urlopen() as it raises an Exception on http 401 'Unauthorised' error
        # rather than drop into interactive mode
        sock = urllib.URLopener().open(url)
        xmlsource = sock.read()
        sock.close()

        #myFile = open('debug.xml','w')
        #myFile.write(xmlsource)
        #myFile.close()

        xmldoc = minidom.parseString(xmlsource)
        self.__parse_xmldoc(xmldoc)
        # Update the time used on the next run
        self.rrdParams['start'] = self.end_time + 1 # avoid retrieving same data twice

    def __parse_xmldoc(self, xmldoc):

        # The 1st node contains meta data (description of the data)
        # The 2nd node contains the data
        self.meta_node = xmldoc.firstChild.childNodes[0]
        self.data_node = xmldoc.firstChild.childNodes[1]

        def LookupMetadataBytag(name):
            return int (self.meta_node.getElementsByTagName(name)[0].firstChild.toxml())

        # rows = number of samples per variable
        # columns = number of variables
        self.rows = LookupMetadataBytag('rows')
        self.columns = LookupMetadataBytag('columns')

        # These indicate the period covered by the data
        self.start_time = LookupMetadataBytag('start')
        self.step_time  = LookupMetadataBytag('step')
        self.end_time   = LookupMetadataBytag('end')
        if verboselog:
            verboselog.info("start_time:%s, step_time:%s, end_time:%s", self.start_time, self.step_time, self.end_time)

        # the <legend> Node describes the variables
        self.legend = self.meta_node.getElementsByTagName('legend')[0]

        # vm_reports matches uuid to per VM report
        self.vm_reports = {}

        # There is just one host_report and its uuid should not change!
        self.host_report = None

        # Handle each column.  (I.e. each variable)
        for col in range(self.columns):
            self.__handle_col(col)

    def __handle_col(self, col):
        # work out how to interpret col from the legend
        col_meta_data = self.legend.childNodes[col].firstChild.toxml()

        # vmOrHost will be 'vm' or 'host'.  Note that the Control domain counts as a VM!
        (cf, vmOrHost, uuid, param) = col_meta_data.split(':')

        if vmOrHost == 'vm':
            # Create a report for this VM if it doesn't exist
            if not self.vm_reports.has_key(uuid):
                self.vm_reports[uuid] = VMReport(uuid)

            # Update the VMReport with the col data and meta data
            vm_report = self.vm_reports[uuid]
            vm_report[param] = col

        elif vmOrHost == 'host':
            # Create a report for the host if it doesn't exist
            if not self.host_report:
                self.host_report = HostReport(uuid)
            elif self.host_report.uuid != uuid:
                raise Exception, "Host UUID changed: (was %s, is %s)" % (self.host_report.uuid, uuid)

            # Update the HostReport with the col data and meta data
            self.host_report[param] = col

        else:
            raise Exception, "Invalid string in <legend>: %s" % col_meta_data

class xenserverPlugin(Plugin):
    def __init__(self, host=None, user="root", passwd="", verbose=False):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.url = None
        self.hostinfo = {}
        self.hostname = None
        self.__verbose = verbose # Set to true to make your logs really fat
        self.graphHost = True
        self.xApiIterCpt = 0
        self.xApiDefaultIterCpt = 60 # Reconnect the API every X polls
        self.rrdParams = {}
        self.rrdParams['cf'] = "AVERAGE"
        self.rrdParams['start'] = int(time.time()) - 10
        self.rrdParams['interval'] = 5
        self.uuid_name_map={} # translate uuid to vm name
        self.data = []
        if self.__verbose:
            self.log = verbose
        self.Connect()

    def prepare_data(self):
        self.data = []
        self.Read()
        return self.data

    def Connect(self):
        ''' This is called at the startup of Collectd '''
        # Called at startup

        if self.host is None:
            self.hostinfo['session'] = XenAPI.xapi_local()  #no __nonzero__, can not use if/not for bool test
            self.url = "http://localhost"
        else:
            self.url = "http://" + str(self.host)
            self.hostinfo['session'] = XenAPI.Session(self.url)
        self._LogVerbose("Conntct to url: %s" %(self.url))
        self.hostinfo['rrdupdates'] = GetRRDUdpates()
        self.hostinfo['session'].xenapi.login_with_password(self.user, self.passwd)
        # host name, uuid translation
        host_ref = self.hostinfo['session'].xenapi.host.get_all()[0]
        uuid = self.hostinfo['session'].xenapi.host.get_uuid(host_ref)
        server_name = self.hostinfo['session'].xenapi.host.get_hostname(host_ref)
        self.uuid_name_map[uuid] = server_name
        self.hostname = server_name
        # VM name, uuid translation
        vm_refs_list = self.hostinfo['session'].xenapi.VM.get_all()
        for vm_ref in vm_refs_list:
            vm_uuid = self.hostinfo['session'].xenapi.VM.get_uuid(vm_ref)
            vm_name = self.hostinfo['session'].xenapi.VM.get_name_label(vm_ref)
            if self.hostinfo['session'].xenapi.VM.get_is_control_domain(vm_ref):
                self.uuid_name_map[vm_uuid] = server_name + "_control-domain"
            else:
                self.uuid_name_map[vm_uuid] = vm_name

    def Read(self):
        ''' This is called by Collectd every $Interval seconds '''

        # If the connection is gone, reconnect
        if self.hostinfo['session'] is None:
            self.Connect()

        # Dirt fix: Reconnect every x reads to prevent unhandled api session timeout.
        self.xApiIterCpt += 1
        if self.xApiIterCpt > self.xApiDefaultIterCpt:
            self.Shutdown()
            self.Connect()
            self.xApiIterCpt = 0

        self._LogVerbose("Read session and handle: %s, %s" % (self.hostinfo['session'], self.hostinfo['session'].handle))
        # Fetch the new http://host/rrd_update?.. and parse the new data
        self.hostinfo['rrdupdates'].Refresh(self.hostinfo['session'].handle, self.rrdParams, self.url)
        # the timestamp only reachable after Refresh
        self.timestamp = self.hostinfo['rrdupdates'].end_time

        # If the option is set, process the host mectrics data
        if self.graphHost:
            isHost = True
            uuid = self.hostinfo['rrdupdates'].GetHostUUID()
            mectricsData = self._GetRows(uuid, isHost)
            self._ToCollectd(uuid, mectricsData, isHost)

        # Process all row w've found so far for each vm
        for uuid in self.hostinfo['rrdupdates'].GetVMList():
            isHost = False
            mectricsData = self._GetRows(uuid, isHost)
            self._ToCollectd(uuid, mectricsData, isHost)

    def Shutdown(self):
        ''' Disconnect all the active sessions - This is called by Collectd on SIGTERM '''
        self._LogVerbose('Disconnecting %s ' % self.hostname)
        try:
            self.hostinfo['session'].logout()
            self.hostinfo['session'] = None
        except Exception:
            pass

    def _ToCollectd(self, uuid, metricsData, isHost):
        ''' This is where the metrics are sent to Collectd '''
        if isHost:
            if uuid in self.uuid_name_map:
                vmid = 'Xenserver_host_%s' % (self.uuid_name_map[uuid])
            else:
                vmid = 'Xenserver_host_%s' % (uuid)
        else:
            if uuid in self.uuid_name_map:
                vmid = 'Xenserver_vm_%s' % (self.uuid_name_map[uuid])
            else:
                vmid = 'Xenserver_vm_%s' % (uuid)

        for key, value in metricsData.iteritems():
            # host / plugin - instance / type - instance
            # 'PUTVAL "%s/%s/%s" interval=%s N:%s'
            self.data.append(GraphiteData(endpoint=vmid, metric=vmid, type=key, step=self.rrdParams['interval'], value=value, timestamp=self.timestamp))
            # type = 'gauge'
            # cltd.host =  vmid #'xenservers' # xenservers/
            # cltd.plugin = vmid # vm-29887edd-6f21-d936-53e5-b4cb2bac3ba0/
            # cltd.type_instance = key # cpu0
            # cltd.values = [ value ]
            # cltd.dispatch()
            #self._LogVerbose('Dispatch() data from %s: %s/%s/%s/%s' % (hostname, cltd.host, cltd.plugin, cltd.type_instance, value))

            #self._LogVerbose('Dispatch() data from %s: %s/%s/%s/%s' % (self.hostname, vmid, vmid, key, value))

    def _GetRows(self, uuid, isHost):
        result = {}
        if isHost:
            paramList = self.hostinfo['rrdupdates'].GetHostParamList()
        else:
            paramList = self.hostinfo['rrdupdates'].GetVMParamList(uuid)
        for param in paramList:
            if param != '':
                max_time=0
                data=''
                for row in range(self.hostinfo['rrdupdates'].GetRows()):
                    epoch = self.hostinfo['rrdupdates'].GetRowTime(row)
                    if isHost:
                        dv = str(self.hostinfo['rrdupdates'].GetHostData(param, row))
                    else:
                        dv = str(self.hostinfo['rrdupdates'].GetVMData(uuid, param, row))
                    if epoch > max_time:
                        max_time = epoch
                        data = dv
                result[param] = data
        return result

    def _LogVerbose(self, msg):
        ''' Be verbose, if self.verbose is True'''
        if not self.__verbose:
            return
        self.log.info('xenserver-collectd [verbose]: %s' % msg)



if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option('--console', dest="console", action="store_true", help="print the data to console")
    parser.add_option('--collectd-exec', dest="collectd_exec", action="store_true", help="use collectd-exec plugin")
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--passwd", dest="passwd", help="Passward for host server")
    parser.add_option("--server", dest="server", help="Carbon server ip")
    parser.add_option("--port", dest="port", help="Port on carbon server")
    parser.add_option("--step", dest="step", help="Time interval to send data")
    parser.add_option("--verbose", dest="verbose", action="store_true", help="Record log to console and /var/log/graphitePlugin.log")
    (options, args) = parser.parse_args()

    host_name = options.host
    # For python 2.4, can not use  user = options.user if options.user else "root"
    if options.user:
        user = options.user
    else:
        user ="root"

    if options.passwd:
        passwd = str(options.passwd).replace('\\', '')
    else:
        passwd = ""

    if options.step:
        try:
            step = int(options.step)
        except ValueError:
            step = 10
    else:
        step = 10

    if options.verbose:
        verboselog = logging.getLogger("xenserverPlugin")
        verboselog.setLevel(logging.DEBUG)
        file_handler = handlers.RotatingFileHandler('/var/log/graphitePlugin.log', 'a', 10 * 1024 * 1024, 5)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(asctime)s|%(levelname)-7s|%(name)s|%(filename)-20s%(lineno)4d : %(message)s"))
        verboselog.addHandler(file_handler)
    else:
        verboselog = None

    if options.console:
        xen_plugin = xenserverPlugin(host=host_name, user=user, passwd=passwd, verbose=verboselog)
        t1 = time.time()
        xen_plugin.console()
        t2 = time.time()
        data= xen_plugin.generate_graphite_data()
        for item in data:
            print item
        t3=time.time()
        print t2-t1, t3-t2
    elif options.collectd_exec:
        while True:
            xen_plugin = xenserverPlugin(host=host_name, user=user, passwd=passwd, verbose=verboselog)
            xen_plugin.report()
            sys.stdout.flush()
            xen_plugin.Shutdown()
            time.sleep(step)
    else:
        if not options.server or not options.port:
            print "Please input a server an a port for socket to send data to carbon"
            sys.exit(1)
        try:
            server, port = options.server, int(options.port)
        except ValueError:
            print "Port need to be an integer"
            port = 2003
        while True:
            # The inital should put in the while so that each loop will generate a new time
            xen_plugin = xenserverPlugin(host=host_name, user=user, passwd=passwd, verbose=verboselog)
            xen_plugin.send_to_carbon(server, port)
            sys.stdout.flush()
            xen_plugin.Shutdown()
            time.sleep(step)
