import sys
import telnetlib
import re
import paramiko
from device_connect import bird_commands, router_bgp_status, router_commands
from devices import *
from logger import logger, logwrap, entering, exiting


@logwrap(entering, exiting)
def check_amount_active_session(operator):
    counter = 0
    if bird_commands(BIRD, operator, action='status') == 'Session UP':
        counter += 1
    if router_bgp_status(R1, globals()['R1' + operator]) == 'Session UP':
        counter += 1
    if router_bgp_status(R2, globals()['R2' + operator]) == 'Session UP':
        counter += 1
    logger.info(f'Active BGP session number: {counter}')
    return counter


@logwrap(entering, exiting)
def set_command(device, operator, action):
    if action == 'disable':
        if check_amount_active_session(operator) < 2:
            logger.info(f'Active BGP session {operator} < 2')
            return (f'Active BGP session {operator} < 2')
    if device == ('BIRD'):
        return bird_commands(BIRD, operator, action)
    elif device in ['R1', 'R2']:
        if action == 'status':
            return router_bgp_status(globals()[device], globals()[
                device + operator])
        else:
            return router_commands(globals()[device], globals()[
                device + operator], action)


result = set_command('R2', 'BEELINE', 'disable')
print(result)
