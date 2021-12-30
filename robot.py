
from machine import Timer, Pin, PWM
from micropython import const
import time
import json
import uart_wrapper

DEFAULT_MOTION_DURATION_MS = const(500)  # ms
DEFAULT_ROTATE_DURATION_MS = const(200)  # ms
MOTOR_DUTY_FREQ = const(20)  # Hz

# motor control pins
pin1 = Pin(25, Pin.OUT)
in1 = PWM(pin1, freq=MOTOR_DUTY_FREQ, duty=0)
pin2 = Pin(26, Pin.OUT)
in2 = PWM(pin2, freq=MOTOR_DUTY_FREQ, duty=0)
pin3 = Pin(27, Pin.OUT)
in3 = PWM(pin3, freq=MOTOR_DUTY_FREQ, duty=0)
pin4 = Pin(14, Pin.OUT)
in4 = PWM(pin4, freq=MOTOR_DUTY_FREQ, duty=0)
pins = [in1, in2, in3, in4]
power_level = 1000  # max is 1023 but we can happily treat this as decipercent
cmd_queue = []


def get_power():
    global power_level
    return power_level


def set_power(new_power_level):
    global power_level
    power_level = new_power_level


def stop():
    in1.duty(0)
    in2.duty(0)
    in3.duty(0)
    in4.duty(0)


def backward(duration_ms=DEFAULT_MOTION_DURATION_MS):
    global power_level
    in1.duty(power_level)
    in2.duty(0)
    in3.duty(power_level)
    in4.duty(0)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def forward(duration_ms=DEFAULT_MOTION_DURATION_MS):
    global power_level
    in1.duty(0)
    in2.duty(power_level)
    in3.duty(0)
    in4.duty(power_level)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def rotate_right(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    global power_level
    in1.duty(0)
    in2.duty(power_level)
    in3.duty(power_level)
    in4.duty(0)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def rotate_left(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    global power_level
    in1.duty(power_level)
    in2.duty(0)
    in3.duty(0)
    in4.duty(power_level)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def turn_right(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    global power_level
    in1.duty(0)
    in2.duty(power_level)
    in3.duty(0)
    in4.duty(0)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def turn_left(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    global power_level
    in1.duty(0)
    in2.duty(0)
    in3.duty(0)
    in4.duty(power_level)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def wait(duration_ms=DEFAULT_MOTION_DURATION_MS):
    time.sleep_ms(duration_ms)


def wait_1s():
    time.sleep_ms(1000)


def wait_5s():
    time.sleep_ms(5000)


def get_pins_status():
    global pins
    pin_str = '('
    for pin in pins:
        pin_str = pin_str + '{}, '.format(pin.duty())
    pin_str += ')'
    return pin_str


def set_motor_powers(motor1: int, motor2: int):
    global in1, in2, in3, in4
    if motor1 == 0:
        in1.duty(0)
        in2.duty(0)
    elif motor1 > 0:
        in1.duty(0)
        in2.duty(motor1)
    elif motor1 < 0:
        in1.duty(-motor1)
        in2.duty(0)
    if motor2 == 0:
        in3.duty(0)
        in4.duty(0)
    elif motor2 > 0:
        in3.duty(0)
        in4.duty(motor2)
    elif motor2 < 0:
        in3.duty(-motor2)
        in4.duty(0)
    if uart_wrapper.is_bluetooth_connected():
        uart_wrapper.raw_uart.write(get_pins_status() + '\n')


def get_motors_status():
    motor1 = 0
    motor2 = 0
    if in1.duty() == 0:
        motor1 = -in2.duty()
    else:
        motor1 = in1.duty()
    if in3.duty() == 0:
        motor2 = -in3.duty()
    else:
        motor2 = in3.duty()
    return json.dumps({'m1': motor1, 'm2': motor2})


valid_cmds = [stop,
              forward,
              backward,
              rotate_left,
              rotate_right,
              turn_left,
              turn_right,
              wait,
              wait_1s,
              wait_5s,
              set_power,
              get_power,
              get_pins_status,
              get_motors_status,
              ]

valid_cmd_dict = {cmd.__name__: cmd for cmd in valid_cmds}
# print(valid_cmd_dict)


def execute_cmds(*cmds):
    for cmd in cmds:
        # print(cmd)
        if cmd in valid_cmds:
            print('Executing {}'.format(cmd.__name__))
            cmd()


def init_gpio():
    global in1, in2, in3, in4
    pin1.value(0)
    pin2.value(0)
    pin3.value(0)
    pin4.value(0)
    in1.duty(0)
    in2.duty(0)
    in3.duty(0)
    in4.duty(0)
