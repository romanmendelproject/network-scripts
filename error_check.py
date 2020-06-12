#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902
import telnetlib
import time
import sys
import re


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


def switch(ipsw):
    cmdGen = cmdgen.CommandGenerator()
    for port in range(3):
        res = 0
        errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
            cmdgen.CommunityData('<PASSWORD>'),
            cmdgen.UdpTransportTarget((ipsw, 161)),
            '1.3.6.1.2.1.10.7.2.1.3.%d' % (port + 25),
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

        if int(res) > 100:
            tn = telnetlib.Telnet(ipsw)
            tn.read_until("ame:")
            tn.write("<LOGIN>\n")
            tn.read_until("ord:")
            tn.write("<RADIUS_PASSWORD>\n")
            tn.write("show lldp remote_ports %s\n" % (port+25))
            res1 = tn.read_until("System Description", 5)
            for line in res1.split('\n'):
                if line.find('GigabitEthernet') > -1:
                    mmgsport = re.search('\d+/\d+/\d+', line)
                    mgsport = mmgsport.group()
                    break
                else:
                    mgsport = "None MGS"

            tn.close()

            f = open(u'errors.txt', 'a')
            f.write("ip:       %s\n" "Address:  %s\n" "port:     %s\n" "errors:   %s\n" "MGS port: %s\n\n\n\n" % (
                ipsw, (switch1(ipsw, '1.3.6.1.2.1.1.6.0')), port+25, res, mgsport))
            f1 = open(u'errorsip.txt', 'a')
            f1.write("%s\n" % ipsw)
    return res


swt = open(u"all_sw.txt", u"r")
while True:
    ipsw = swt.readline()
    kol = len(ipsw)-1
    try:
        if ipsw[kol] == "\n":
            ipsw = ipsw[:-1]
    except IndexError:
        break
    print u"---------------------------"
    print ipsw
    print u"---------------------------"
    res = switch1(ipsw, '.1.3.6.1.2.1.1.1.0')
    if res == "D-Link DES-1228/ME Metro Ethernet Switch" or res == "DES-1210-28/ME          6.07.B004":
        switch(ipsw)
    else:
        print(u"Unknown device")
