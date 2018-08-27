#!/usr/bin/env bash
#########################################################################
# File Name: check_graphite_plugin.sh
# Author: longhui
# Created Time: 2018-08-27 12:31:57
#########################################################################

processNums=$(ps aux| grep graphite_plugin.py |grep -v grep|wc -l)

if [[ $processNums -lt 1 ]];then
    echo "`date`: start /root/graphite_plugin.py"
    nohup python /root/graphite_plugin.py --server=192.168.1.1 --port=2003 --step=10  &
fi
