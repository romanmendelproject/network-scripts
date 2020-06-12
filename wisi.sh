#!/bin/bash
logfile=/home/gs/new/wisilog.txt

function notify {
FROM=<FROM>
MAILTO=<MAILTO>
SMTPSERVER=<SMTPSERVER>
SMTPLOGIN=<SMTPLOGIN>
SMTPPASS=<SMTPPASS>
/usr/bin/sendEmail -f $FROM -t $MAILTO -o message-charset=utf-8  -u $2 -m $1 -s $SMTPSERVER -o tls=no -xu $SMTPLOGIN -xp $SMTPPASS &> /dev/null
}

function main {
sleep 20
curl -s -u root:root http://$1/cgi-bin/status.cgi -m 5 >  /dev/null
echo $?
if [[ $? = "0" ]]
then
    status=$(curl -s -u root:root http://$1/cgi-bin/status.cgi -m 5 | grep "Video: OK" -c)
    echo $status
    if [[ $status = "1" ]]
        then
        echo "OK"
    else
        date >> $logfile
        echo "Пропали ПИДы" >> $logfile
        slave $1
    fi
else
    date >> $logfile
    echo "Устройство $1 недоступно"
    notify "Устройство $1 недоступно" "АВАРИЯ РТРС!"
    while true
    do
        status=$(curl -s -u root:root http://$1/cgi-bin/status.cgi -m 5)
        if [[ $? = "0" ]]
        then
            date >> $logfile
            echo "Устройство $1 доступно" >> $logfile
            notify "Устройство $1 доступно" "ЗАВЕРШЕНО АВАРИЯ РТРС!"
            break
        fi
    done
fi
}

function slave {
pop=true
while true
do
sleep 20
status=$(curl -s -u root:root http://$1/cgi-bin/status.cgi -m 5 | grep "Video: OK" -c)
echo $status
if [[ $status = "1" ]]
then
    echo "OK"
    if [[ $pop = false ]]
    then
        date >> $logfile
        echo "Вещание восстановлено" >> $logfile
        notify "Вещание восстановлено" "ЗАВЕРШЕНО АВАРИЯ РТРС ТЕСТ!"
        break
    fi
else
    echo "Нет вещания"
    if [[ $pop = true ]]
    then
        notify "Фиксируется отсутствие вещания в потоке от РТРС" "АВАРИЯ РТРС ТЕСТ!"
        ssh asterisk@192.168.0.1 /usr/local/bin/zvonok2.py
        snmpset -v2c -c <SNMP_PASSWORD> 10.0.0.1 1.3.6.1.2.1.17.7.1.4.3.1.2.4001 x 0000006000000000
        sleep 20
        snmpset -v2c -c <SNMP_PASSWORD> 10.0.0.1 1.3.6.1.2.1.17.7.1.4.3.1.2.4001 x 0000006000000000
        pop=false
    fi
fi
done
}

while true
do
main "10.0.0.1"
done
