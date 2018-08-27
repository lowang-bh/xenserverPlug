#!/usr/bin/env bash
#########################################################################
# File Name: upload_file_via_ssh.sh
# Author: longhui
# Created Time: 2018-05-04 10:22:24
#########################################################################
if [[ $# -ne 3 ]];then
    echo "Usage: <$0 iplist_file passwd filename>"
    exit 1
else
    myfile=$1
    passwd=$2
    filename=$3
fi

read_file()
{
    cat $myfile| while read host_ip
    do
        echo "process host $host_ip"
        scp_file
    done
}

scp_file()
{
/usr/bin/expect << EOF
set timeout 3
spawn scp $filename root@$host_ip:/root/
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

read_file
