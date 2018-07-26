#!/usr/bin/env bash
#########################################################################
# File Name: sync_file_via_ssh.sh
# Author: longhui
# Created Time: 2018-05-04 10:22:24
#########################################################################
if [[ $# -ne 2 ]];then
    echo "Usage: <$0 iplist_file passwd>"
    exit 1
else
    myfile=$1
    passwd=$2
fi

read_file()
{
    cat $myfile| while read host_ip
    do
        echo "process host $host_ip"
        scp_file
        ssh_cmd
    done
}

scp_file()
{

/usr/bin/expect << EOF
set timeout 3
spawn scp graphite_plugin.py root@$host_ip:/root/
expect {
            "(yes/no)?"
            {
                send "yes\n"
                expect "*assword:" { send "$passwd\n"}
            }
            "*assword:"
            {
                send "$passwd\n"
            }
            "100%"
        }
expect eof
EOF
}

ssh_cmd()
{
/usr/bin/expect << EOF
set timeout 3

spawn ssh root@$host_ip

expect {
            "(yes/no)?"
            {
                send "yes\n"
                expect "*assword:" { send "$passwd\n"}
            }
            "*assword:"
            {
                send "$passwd\n"
            }
        }
expect "]#" { send "nohup python /root/graphite_plugin.py --server=192.168.1.1--port=2003 --step=10  &\n"}
expect "]#" { send "exit\n"}
expect eof
EOF
}

read_file
