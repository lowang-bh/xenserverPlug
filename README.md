collectd-xenserver
==================

A Collectd plugin to monitor Citrix XenServer

# Introduction

This is a module for collectd. It try to fetch the last metrics from a Citrix Xenserver
host and the VMs running on it. This is done by fetching and parsing a xml on the server:

http://$username:$password@$host/rrd_updates?start=<secondssinceepoch>&host=true

For more informations about this API, see the Citrix documentation here:

http://docs.vmd.citrix.com/XenServer/6.1.0/1.0/en_gb/sdk.html#persistent_perf_stats


# Dependencies

* Collectd 4.9 or later (for the Python plugin)
* Python 2.4 or later
* XenAPI python module: http://pypi.python.org/pypi/XenAPI
* collectd python module: http://pypi.python.org/pypi/collectd


# Configuration

The plugin has some mandatory configuration options. This is done by passing parameters via the <Module> config section in your Collectd config. The following parameters are recognized:

* Host - hostname or IP address of the XenServer
* User - the username for authentication
* Password - the password for authentication

```
  <LoadPlugin python>
    Globals true
  </LoadPlugin>

  <Plugin python>
        ModulePath "/path/to/modules/"
        LogTraces true
        Interactive false
        Import "collectd-xenserver"
        <Module "collectd-xenserver">
              <Host "10.0.0.100">
                    User "root"
                    Password "mysecretpassword"
              </Host>
              <Host "10.0.0.101">
                    User "root"
                    Password "mysecretpassword"
              </Host>
        </Module>
  </Plugin>
```
# issue
Q1. ImportError: No module named collectd-xenserver
Apr 18 07:55:35 test2 collectd[10826]: python plugin: Error importing module "collectd-xenserver".
Apr 18 07:55:35 test2 collectd[10826]: Unhandled python exception in importing module: ImportError: No module named collectd-xenserver

it was SELinux problem that collectd can't read python files. *setenforce 0* to disable it; and set *SELINUX=disabled* in /etc/selinux/config

XenApi/rrd_updates
------------------
http://wiki.xensource.com/xenwiki/XAPI_RRDs
http://community.citrix.com/display/xs/Using+XenServer+RRDs
