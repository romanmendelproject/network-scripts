import serial
import time

number = "+79608888888"
message = "Test"


def str_send(ser, textline):
    print("<<" + textline)
    ser.write(textline)

    out = ''
    N = 10
    while N > 0:
        time.sleep(1)
        while ser.inWaiting() > 0:
            out += ser.read(1)

        if ('OK' in out) or ('ERROR' in out) or ('>' in out):
            print(">>" + out)
            N = 1

        N -= 1


ser = serial.Serial("/dev/ttyUSB1", 115200, timeout=1)
try:
    ser.open()
except:
    ser.close()
    ser.open()

str_send(ser, 'AT+CMGF=1\r')
str_send(ser, 'AT+CMGS="%s"\r' % number)
str_send(ser, '%s %s' % (message, chr(26)))


ser.close()
