#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import telnetlib
import re


class CommandError(Exception):
    def __init__(self, value):
        self.value = value


def sendcmd(tn, cmd, waitstr='return', waittime=1):
    tn.write(cmd + '\n')
    res = tn.read_until(waitstr, waittime)
    if res.find('mpls l2vc 10.2.0.21 776') != -1:
        print "SIGNAL PERM"
    elif res.find('mpls l2vc 10.2.0.21 886') != -1:
        print "SIGNAL SAMARA"
    else:
        print "ERROR"


def dologin(login, password):
    tn = telnetlib.Telnet()
    tn.open('10.2.0.12', 23, 10)
    res = tn.read_until('Username:', 3)
    if res.find('Username:') == -1:
        raise CommandError('No login prompt.')
    tn.write(login + '\n')
    res = tn.read_until('Password:', 3)
    if res.find('Password:') == -1:
        raise CommandError('No password prompt or empty login.')
    tn.write(password + '\n')
    res = tn.read_until('<S9703>', 3)
    if res.find('<S9703>') == -1:
        raise CommandError('No command prompt or wrong login/password.')
    return tn


tn = None
try:

    res = sendcmd(tn, 'display current-configuration interface Vlanif776')


except CommandError as e:
    print 'ERROR: ', e.value
