import paramiko
import getpass
import sys
import time
import telnetlib
from pysnmp.entity.rfc3413.oneliner import cmdgen
import socket
from logger import logger, logwrap, entering, exiting

USER_BIRD = 'test'
PASSWORD_BIRD = 'test'


def result_cmd(result):
    if result.find(result) != -1:
        logger.info(f'Command result: {result}')
        return (result)


@logwrap(entering, exiting)
def bird_commands(ip, operator, action):
    try:
        print(f'Connection BIRD {ip}')
        logger.info(f'Connection BIRD {ip}')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=ip,
            username=USER_BIRD,
            password=PASSWORD_BIRD,
            look_for_keys=False,
            allow_agent=False)

        with client.invoke_shell() as ssh:
            def bird_status():
                ssh.send(f'show protocols all {operator}\n')
                time.sleep(1)
                result = ssh.recv(5000).decode('ascii')
                if result.find('BGP state:          Established') != -1:
                    logger.info(f'BGP session UP')
                    return("Session UP")
                else:
                    logger.info(f'BGP session DOWN')
                    return("Session DOWN")

            def get_ssh_cmd():
                ssh.send(f'{action} {operator}\n')
                time.sleep(1)
                result = ssh.recv(5000).decode('ascii')
                if result.find(f'{operator}: {action}d') != -1:
                    logger.info(
                        f'Session with operator {operator} of {action}d')
                    return (f'{operator}: {action}d')
                if result.find(f'{operator}: already {action}d') != -1:
                    logger.info(
                        f'Session with operator {operator} already {action}d')
                    return (f'{operator}: already {action}d')
                else:
                    logger.error(f'Command error ssh BIRD')
                    return('Error')

            ssh.send('sudo birdc\n')
            ssh.send(f'{PASSWORD_BIRD}\n')
            ssh.recv(20)
            time.sleep(1)
            if action == 'status':
                return bird_status()
            elif action in ['enable', 'disable']:
                get_ssh_cmd()
            else:
                logger.error(f'Action type error')
                return("Error")
    except socket.timeout:
        logger.error(f'SSH channel timeout exceeded.')
        return("Error")
    except Exception as e:
        logger.error(e)
        return("Error")


def check_send_cmd(tn, cmd):
    tn.write(cmd)
    res = tn.read_until(b'#', 5)
    if res.find(b'%') != -1:
        logger.error(f'Command telnet error:{res}')
        return("Error")


@logwrap(entering, exiting)
def router_commands(ip, operator, action):
    print(f'Connection router {ip}')
    logger.info(f'Connection router {ip}')
    tn = do_login(ip)
    commands = [
        b'conf t\n',
        b'router bgp 65000\n'
    ]
    if tn:
        if action == 'enable':
            command = f'no neighbor {operator} shutdown\n'
            commands.append(command.encode(encoding='UTF-8'))
        elif action == 'disable':
            command = f'neighbor {operator} shutdown\n'
            commands.append(command.encode(encoding='UTF-8'))
        else:
            logger.error(f'Action type error')
            return('Error')
        for cmd in commands:
            if check_send_cmd(tn, cmd):
                return ('Error')
        logger.info(
            f'Session with operator {operator} of {action}d')
        return (f'{operator}: {action}d')
    else:
        return ('Error')


def do_login(ip):
    try:
        tn = telnetlib.Telnet(ip)
        res = tn.read_until(b'Password:', 5)
        if res.find(b'Password:') == -1:
            logger.error(f'No password prompt or empty login.')
            return 'Error'
        tn.write(b'cisco\n')
        res = tn.read_until(b'#', 3)
        if res.find(b'#') == -1:
            logger.error(f'No command prompt or wrong login/password.')
            return 'Error'
        logger.info(f'Telnet connected')
        return tn
    except Exception as e:
        logger.error(e)
        return 'Error'


@logwrap(entering, exiting)
def router_bgp_status(ip, operator):
    print(f'Connection router {ip}')
    logger.info(f'Connection router {ip}')
    cmdGen = cmdgen.CommandGenerator()
    errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
        cmdgen.CommunityData('public'),
        cmdgen.UdpTransportTarget((ip, 161)),
        '1.3.6.1.2.1.15.3.1.2.' + operator,
    )

    if errorIndication:
        logger.error(errorIndication)
        return('Error')
    else:
        if errorStatus:
            logger.error('%s at %s' % (
                errorStatus.prettyPrint(),
                errorIndex and varBinds[int(errorIndex)-1] or '?'
            )
            )
            return('Error')
        else:
            for val in varBinds:
                res = val.prettyPrint()
            if res == 6:
                logger.info(f'BGP session {operator} UP')
                return("Session UP")
            else:
                logger.info(f'BGP session {operator} DOWN')
                return("Session DOWN")
