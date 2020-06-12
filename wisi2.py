import requests
import re
import os
import subprocess
import paramiko
import socket
import time
from requests.auth import HTTPBasicAuth
import email.mime.text
from smtplib import SMTP

NOTIFICATION = {'email': ['<EMAILS>']}


def notify(Tema, Telo):
    import email.mime.text
    from smtplib import SMTP

    msg = email.mime.text.MIMEText(Tema, 'plain', 'utf-8')
    msg['Subject'] = <SUBJECT>
    msg['From'] = <FROM >'
    msg['To'] = ', '.join(NOTIFICATION['email'])

    smtp = SMTP()
    smtp.connect('<SERVER>', 25)
    smtp.login('<LOGIN>', '<PASSWORD>')
    smtp.sendmail('', NOTIFICATION['email'], msg.as_string())
    smtp.quit()


def main(ippbi, multiplex):
    resp = requests.get('http://%s/cgi-bin/status.cgi' %
                        ippbi, auth=HTTPBasicAuth('root', 'root'))
    status = str(resp.content).find('Video: OK')
    if status != -1:
        print('OK')
    else:
        print("Пропали ПИДы")
        repeat = 0
        slave(ippbi, multiplex)


def slave(ippbi, multiplex):
    pop = True
    while True:
        time.sleep(20)
        resp = requests.get('http://%s/cgi-bin/status.cgi' %
                            ippbi, auth=HTTPBasicAuth('root', 'root'))
        status = str(resp.content).find('Video: OK')
        if status != -1:
            print('OK')
            if pop == False:
                notify(u'Вещание восстановлено', u'ЗАВЕРШЕНО АВАРИЯ РТРС!')
            break
        else:
            print('Нет вещания')
            if pop == True:
                notify(u'Фиксируется отсутствие вещания в потоке от РТРС',
                       u'АВАРИЯ РТРС!')
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect("192.168.0.1", username="<LOGIN>",
                            password="<PASSWORD>")
                stdin, stdout, stderr = ssh.exec_command(
                    "/usr/local/bin/zvonok2.py")
                os.system(
                    'snmpset -v2c -c <SNMP_PASSWORD> 10.0.0.3 1.3.6.1.2.1.17.7.1.4.3.1.2.4001 x 0000006000000000')
                time.sleep(20)
                os.system(
                    'snmpset -v2c -c <SNMP_PASSWORD> 10.0.0.3 1.3.6.1.2.1.17.7.1.4.3.1.2.4001 x 000000E000000000')
                pop = False


while True:
    time.sleep(20)
    main('10.0.0.1', 'ПЕРВОМ')
    main('10.0.0.2', 'ВТОРОМ')

