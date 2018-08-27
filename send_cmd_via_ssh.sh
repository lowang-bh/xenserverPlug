#!/usr/bin/env bash
#########################################################################
# File Name: send_cmd_vid_ssh.sh
# Author: longhui
# Created Time: 2018-08-27 12:37:12
#########################################################################

if [[ $# -ne 3 ]];then
    echo "Usage: <$0 iplist_file passwd command>"
    exit 1
else
    myfile=$1
    passwd=$2
    command=$3
fi

read_file()
{
    cat $myfile| while read host_ip
    do
        echo "process host $host_ip"
        ssh_cmd
    done
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
expect "]#" { send "$command \n"}
expect "]#" { send "exit\n"}
expect eof
EOF
}

read_file
