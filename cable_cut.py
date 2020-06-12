#!/usr/bin/python
# -*- coding: utf-8 -*-
from datetime import datetime
import multiprocessing
import netsnmp
import yaml
import time
import os
import paramiko
import re
import socket
# --- Global variable --- #
NUMBER_OF_PROCESSES = 2570

DATAFILE = '/usr/local/bin/scripts/back/data.yml'
HOSTSFILE = '/usr/local/bin/scripts/back/vse1228.yml.old'
FILEPATH = '/usr/local/bin/scripts/back/'

LEN_DELTA = 5
MIN_PORTS = 4

CABLEDIAG_OID = '.1.3.6.1.4.1.171.12.58.1.1.1'
IF_TABLE_OID = '1.3.6.1.2.1.2.2.1'
COMMUNITY = 'password'


def notify(ip_addr, cable_deltas):
    import email.mime.text
    from smtplib import SMTP
    import socket

    # make message
    nameoid = netsnmp.Varbind(".1.3.6.1.2.1.1.6.0")
    namesw = netsnmp.snmpget(
        nameoid, Version=2, DestHost=ip_addr, Community=COMMUNITY)
    msg_items = [u'Подозрения на вырез кабеля: %s по адресу %s\n\n' %
                 (ip_addr, namesw), ]
    for port, delta in cable_deltas.items():
        dloid = netsnmp.Varbind(".1.3.6.1.4.1.171.12.58.1.1.1.8.%s" % port)
        tekdlina = netsnmp.snmpget(
            dloid, Version=2, DestHost=ip_addr, Community=COMMUNITY)
        msg_items.append(u'порт %d: ' % port +
                         u'вырезанная длина %d текущая длина %s\n\n' % (delta, tekdlina[0]))

     # send email
    msg = email.mime.text.MIMEText(u''.join(msg_items), 'plain', 'utf-8')
    msg['Subject'] = u'Подозрения на вырез кабеля'
    msg['From'] = 'monitoring'
    msg['To'] = ', '.join(NOTIFICATION['email'])

    smtp = SMTP()
    smtp.connect('mail.ru', 25)
    smtp.login('monitoring', 'password')
    smtp.sendmail('monitoring@ru', NOTIFICATION['email'], msg.as_string())
    smtp.quit()


def worker(cablediag_queue, result_queue):
    for host in iter(cablediag_queue.get, 'STOP'):
        # print 'Start check ', host['ip_addr']
        if_oper_status = netsnmp.snmpgetbulk(0, 24,
                                             netsnmp.Varbind(IF_TABLE_OID, 8),
                                             Version=2,
                                             Community=COMMUNITY,
                                             DestHost=host['ip_addr'])
        if len(if_oper_status) != 24:
            result_queue.put(host)
            continue

        # run cablediag on 'down' ports
        for port in range(24):
            if if_oper_status[port] == '2' or int(host['pair1len'][port]) == 0:
                netsnmp.snmpset(
                    netsnmp.Varbind(CABLEDIAG_OID, '12.%d' %
                                    (port + 1), 1, 'INTEGER'),
                    Version=2,
                    Community=COMMUNITY,
                    DestHost=host['ip_addr'])

# 1 - Port UP
# 2 - Port DOWN

        pair1status = netsnmp.snmpgetbulk(0, 24,
                                          netsnmp.Varbind(CABLEDIAG_OID, 4),
                                          Version=2,
                                          Community=COMMUNITY,
                                          DestHost=host['ip_addr'])

# 0 - Pair OPEN
# 1 - Pair OK

        pair1len = netsnmp.snmpgetbulk(0, 24,
                                       netsnmp.Varbind(CABLEDIAG_OID, 8),
                                       Version=2,
                                       Community=COMMUNITY,
                                       DestHost=host['ip_addr'])

        if len(pair1status) != 24 or len(pair1len) != 24:
            result_queue.put(host)
            continue

        # check if cable length is changed
        cable_deltas = {}
        for port in range(24):
            if (if_oper_status[port] == '2' and pair1status[port] in ['1', '2', '3']):
                cable_delta = int(host['pair1len'][port]) - int(pair1len[port])
                if cable_delta > LEN_DELTA and int(pair1len[port]) > 0:
                    cable_deltas[port + 1] = cable_delta

        if len(cable_deltas) >= MIN_PORTS:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect("192.168.0.1", username="asterisk",
                        password="password")
            stdin, stdout, stderr = ssh.exec_command(
                "/usr/local/bin/call.py %s" % host['ip_addr'])
            notify(host['ip_addr'], cable_deltas)'

        # put new data
        host['pair1status'] = pair1status
        host['pair1len'] = pair1len
        result_queue.put(host)


def main():
    start = datetime.now()
    etlog = open(FILEPATH+('cablecut.log'), 'w+')
    etlog.write(str(start)+' started at ')
    try:
        HOSTS = yaml.load(file(HOSTSFILE))
    except:
        print 'hosts.yml not found!'
    print len(HOSTS)
    try:
        data = yaml.load(file(DATAFILE))
    except:
        data = []
        for ip_addr in HOSTS:
            host = {'ip_addr': ip_addr,
                    'pair1status': tuple('0' for port in range(24)),
                    'pair1len': tuple('0' for port in range(24)), }
            data.append(host)

    cablediag_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    for record in data:
        cablediag_queue.put(record)

    # start processes
    for i in range(NUMBER_OF_PROCESSES):
        multiprocessing.Process(target=worker, args=(
            cablediag_queue, result_queue)).start()

    # get and save results
    new_data = []
    for i in range(len(data)):
        new_data.append(result_queue.get())
    yaml.dump(new_data, file(DATAFILE, 'w'))

    # stop processes
    for i in range(NUMBER_OF_PROCESSES):
        cablediag_queue.put('STOP')
    end = datetime.now()
    etlog.write(str(end) + ' ended at with '+str(len(HOSTS))+' devices')
    etlog.close()


if __name__ == '__main__':
    main()
