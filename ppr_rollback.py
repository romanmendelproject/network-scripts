#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import telnetlib
import re
import socket
import time
from pysnmp.entity.rfc3413.oneliner import cmdgen


def loginhuawei():
    tn = telnetlib.Telnet()
    tn.open(ipsw, 23, 10)
    tn.read_until('Username:', 3)
    tn.write('<LOGIN>\n')
    tn.read_until('Password:', 3)
    tn.write('<TACACS_PASSWORD>\n')
    tn.read_until('>', 3)
    return tn


def logincisco():
    tn = telnetlib.Telnet()
    tn.open(ipsw, 23, 10)
    tn.read_until('login:', 3)
    tn.write('<LOGIN>\r')
    res = tn.read_until(':', 3)
    tn.write('<TACACS_PASSWORD>\r')
    tn.read_until('#', 3)
    return tn


def switch1(ipsw, oid):
    cmdGen = cmdgen.CommandGenerator()
    errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
        cmdgen.CommunityData('<SNMP_PASSWORD>'),
        cmdgen.UdpTransportTarget((ipsw, 161)),
        oid,
    )

    if errorIndication:
        print(errorIndication)
    else:
        if errorStatus:
            print('%s at %s' % (
                errorStatus.prettyPrint(),
                errorIndex and varBinds[int(errorIndex)-1] or '?'
            )
            )
        else:
            for name, val in varBinds:
                res = val.prettyPrint()
    return res


tn = None
ipsw_file = []
swt = open(u"all_sw.txt", u"r")
port = open(u"port_sw.txt", u"r")
vlan = open(u"vlan.txt", u"r")
for stroka in swt.readlines():
    ipsw_file.append(stroka.split())

i = 0
while True:
    a = False
    try:
        np = port.readline()
        VLAN = vlan.readline()
        ipt = str(ipsw_file[i])
        ipsw = ipt[2:-2]
        print ipsw
        kol = len(ipsw)-1
    except IndexError:
        break
    try:
        if ipsw[kol] == "\n":
            ipsw = ipsw[:-1]
    except IndexError:
        break

    print u"---------------------------"
    print ipsw
    print u"---------------------------"

    try:
        res = switch1(ipsw, '.1.3.6.1.2.1.1.4.0')
        print res
        if res == "R&D Beijing, Huawei Technologies co.,Ltd.":
            print 'huawei'
            if i == 0 or str(ipt) != str(ipsw_file[i-1]):
                tn = loginhuawei()
                print 'HUAWEI'
            tn.write('sys\n')
            tn.read_until(']', 3)
            tn.write('vlan %s\n' % VLAN)
            tn.read_until('-vlan', 3)
            tn.write('interface Ethernet0/0/%s\n' % np)
            tn.read_until('-Ethernet0/0/', 3)
            tn.write('shutdown\n')
            time.sleep(0.5)
            tn.write('undo shutdown\n')
            tn.write('disp this\n')
            res = tn.read_until('dhcp', 3)
            for line in res.split('\n'):
                c1 = re.search('port hybrid untagged vlan', line)
                if c1 is not None:
                    c2 = (re.search("\d+", line)).group()
                    tn.write('undo port hybrid vlan %s\n' % c2)
                    tn.write('undo port hybrid pvid vlan\n')
                    tn.read_until(']', 3)
                    tn.write('port hybrid pvid vlan %s\n' % VLAN)
                    tn.read_until(']', 3)
                    tn.write('port hybrid untagged vlan %s\n' % VLAN)
                    tn.read_until(']', 3)
                c3 = re.search('port default vlan', line)
                if c3 is not None:
                    c4 = (re.search("\d+", line)).group()
                    tn.write('port default vlan %s\n' % c4)
            tn.write('disp this\n')
            res = tn.read_until('dhcp', 3)
            print res
            if str(ipt) != str(ipsw_file[i+1]):
                tn.write('q\n')
                tn.write('q\n')
                tn.write('save\n')
                tn.write('y\n')
                res = tn.read_until('successful', 1)
                print res
            i += 1

            continue

        if res == 'support@nag.ru':
            print 'cisco type'
            if i == 0 or str(ipt) != str(ipsw_file[i-1]):
                tn = logincisco()
                print 'CISCO'
            tn.write('show version\r')
            res1 = tn.read_until('Device', 3)
            c3 = re.search('SNR-S2960-48G', res1)
            if c3 is not None:
                print c3.group()
                tn.write('conf t\r')
                tn.read_until('config', 3)
                tn.write('vlan %s\n' % VLAN)
                tn.read_until('-vlan', 3)
                tn.write('show running-config interface ethernet 0/0/%s\r' % np)
                res = tn.read_until('dhcp', 5)
                tn.write('Interface Ethernet0/0/%s\r' % np)
                tn.read_until('config-if-ethernet', 3)
                for line in res.split('\n'):
                    c1 = re.search('switchport access vlan', line)
                    if c1 is not None:
                        tn.write('switchport access vlan %s\r' % VLAN)
                        tn.write(
                            'loopback-detection specified-vlan %s\r' % VLAN)
                        continue
                    c3 = re.search('switchport hybrid native vlan', line)
                    if c3 is not None:
                        tn.write(
                            'switchport hybrid allowed vlan %s untag\r' % VLAN)
                        tn.write('switchport hybrid native vlan %s\r' % VLAN)
                        tn.write(
                            'loopback-detection specified-vlan %s\r' % VLAN)
                        continue
                tn.write('shutdown\r')
                time.sleep(0.5)
                tn.write('no shutdown\r')
                tn.write('show running-config interface ethernet 0/0/%s\r' % np)
                res = tn.read_until('dhcp', 5)
                print res
                f3 = open(u"log.txt", 'a')
                f3.write("-- %s -- \n %s\n\n" % (ipsw, res))
                if str(ipt) != str(ipsw_file[i+1]):
                    tn.write('exit\n')
                    tn.write('exit\n')
                    tn.write('write\n')
                    tn.write('y\n')
                    res = tn.read_until('successful', 3)
                    print res
                i += 1

                continue
            else:
                print res1
                tn.write('conf t\r')
                tn.read_until('config', 3)
                tn.write('show running-config interface ethernet 1/%s\r' % np)
                res = tn.read_until('dhcp', 5)
                tn.write('Interface Ethernet1/%s\r' % np)
                tn.read_until('config-if-ethernet', 3)
                for line in res.split('\n'):
                    c1 = re.search('switchport access vlan', line)
                    if c1 is not None:
                        tn.write('switchport access vlan %s\r' % VLAN)
                        tn.write(
                            'loopback-detection specified-vlan %s\r' % VLAN)
                        continue
                    c3 = re.search('switchport hybrid native vlan', line)
                    if c3 is not None:
                        tn.write(
                            'switchport hybrid allowed vlan %s untag\r' % VLAN)
                        tn.write('switchport hybrid native vlan %s\r' % VLAN)
                        tn.write(
                            'loopback-detection specified-vlan %s\r' % VLAN)
                        continue
                tn.write('switchport hybrid allowed vlan %s untag\r' % VLAN)
                tn.write('switchport hybrid native vlan %s\r' % VLAN)
                tn.write('loopback-detection specified-vlan %s\r' % VLAN)
                tn.write('shutdown\r')
                time.sleep(0.5)
                tn.write('no shutdown\r')
                tn.write('show running-config interface ethernet 1/%s\r' % np)
                res = tn.read_until('dhcp', 5)
                print res
                f3 = open(u"log.txt", 'a')
                f3.write("-- %s -- \n %s\n\n" % (ipsw, res))
                if str(ipt) != str(ipsw_file[i+1]):
                    tn.write('exit\n')
                    tn.write('exit\n')
                    tn.write('write\n')
                    tn.write('y\n')
                    res = tn.read_until('successful', 3)
                    print res
                i += 1

                continue

        else:
            print "error"
            f4 = open(u"log_error.txt", 'a')
            f4.write("%s -- неверный тип устройства \n" % ipsw)
            i += 1
            continue

    except socket.error:
        f4 = open(u"log_error.txt", 'a')
        f4.write("%s -- недоступен\n" % ipsw)
        i += 1
        continue
    except UnboundLocalError:
        f4 = open(u"log_error.txt", 'a')
        f4.write("%s -- недоступен\n" % ipsw)
        i += 1
        continue

    if not np:
        break
