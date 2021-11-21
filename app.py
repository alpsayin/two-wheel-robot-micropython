import machine
import time
from machine import Timer, Pin, PWM
from micropython import const
import gc
import wlan_wrapper
from _thread import allocate_lock, start_new_thread
import json


BOOT_TIME = const(3)
HEARTBEAT_PERIOD = const(5)  # s
DEFAULT_MOTION_DURATION_MS = const(500)  # ms
DEFAULT_ROTATE_DURATION_MS = const(200)  # ms

import repl_drop
repl_drop.wait(BOOT_TIME)
print('app.py')

from MicroWebSrv2 import *

# wifi
# make sure you have a credentials.py file which defines the below variables
from credentials import WLAN_SSID, WLAN_KEY  # noqa E402
DHCP_HOSTNAME = 'alpo'


# motor control pins
pin1 = Pin(25, Pin.OUT)
in1 = PWM(pin1, freq=10, duty=0)
pin2 = Pin(26, Pin.OUT)
in2 = PWM(pin2, freq=10, duty=0)
pin3 = Pin(27, Pin.OUT)
in3 = PWM(pin3, freq=10, duty=0)
pin4 = Pin(14, Pin.OUT)
in4 = PWM(pin4, freq=10, duty=0)
pins = [in1, in2, in3, in4]
power_level = 1000  # max is 1023 but we can happily treat this as decipercent

# status
heartbeat_timer_flag = True
heartbeat = Timer(-1)
status_dict = dict(
    hostname='null',
    seconds=0,
    freq=115200,
    mem_free=gc.mem_free()
)


def robot_get_power():
    global power_level
    return power_level


def robot_set_power(new_power_level):
    global power_level
    power_level = new_power_level


def robot_stop():
    in1.duty(0)
    in2.duty(0)
    in3.duty(0)
    in4.duty(0)


def robot_forward(duration_ms=DEFAULT_MOTION_DURATION_MS):
    in1.duty(power_level)
    in2.duty(0)
    in3.duty(power_level)
    in4.duty(0)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_backward(duration_ms=DEFAULT_MOTION_DURATION_MS):
    in1.duty(0)
    in2.duty(power_level)
    in3.duty(0)
    in4.duty(power_level)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_rotate_right(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    in1.duty(0)
    in2.duty(power_level)
    in3.duty(power_level)
    in4.duty(0)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_rotate_left(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    in1.duty(power_level)
    in2.duty(0)
    in3.duty(0)
    in4.duty(power_level)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_turn_right(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    in1.duty(0)
    in2.duty(0)
    in3.duty(power_level)
    in4.duty(0)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_turn_left(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    in1.duty(power_level)
    in2.duty(0)
    in3.duty(0)
    in4.duty(0)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_wait(duration_ms=DEFAULT_MOTION_DURATION_MS):
    time.sleep_ms(duration_ms)


def robot_wait_1s():
    time.sleep_ms(1000)


def robot_wait_5s():
    time.sleep_ms(5000)


valid_cmds = [robot_stop,
              robot_forward,
              robot_backward,
              robot_rotate_left,
              robot_rotate_right,
              robot_turn_left,
              robot_turn_right,
              robot_wait,
              robot_wait_1s,
              robot_wait_5s,
              robot_set_power,
              robot_get_power
              ]

valid_cmd_dict = {cmd.__name__: cmd for cmd in valid_cmds}
# print(valid_cmd_dict)


def execute_cmds(*args):
    for arg in args:
        # print(arg)
        if arg in valid_cmds:
            print('Executing {}'.format(arg.__name__))
            arg()


def render_control_form(request, previous_form=None):
    if previous_form is None:
        robot_function_val = ''
        param_val = ''
    else:
        robot_function_val = previous_form['robot_function']
        param_val = previous_form['param']
    content = """\
    <!DOCTYPE html>
    <html>
        <head>
            <title>micropython robot control</title>
        </head>
        <body>
            <h2>micropython robot control</h2>
            User address: %s<br />
            <form action="/robot_control" method="post">
                Function:   <input type="text" name="robot_function" value="%s"><br />
                Parameter:  <input type="text" name="param" value="%s"><br />
                <input type="submit" value="OK">
            </form>
        </body>
    </html>
    """ % (request.UserAddress[0], robot_function_val, param_val)
    return content


@WebRoute(GET, '/robot_control')
def RequestTestRedirect(microWebSrv2, request):
    content = render_control_form(request)
    request.Response.ReturnOk(content)


@WebRoute(POST, '/robot_control', name='robot_control')
def RequestTestPost(microWebSrv2, request):
    data = request.GetPostedURLEncodedForm()
    print(data)
    result = None
    try:
        robot_function_name = str(data['robot_function'])
        print(robot_function_name)
        if robot_function_name in valid_cmd_dict:
            robot_function = valid_cmd_dict[robot_function_name]
            print(robot_function)
    except:
        request.Response.ReturnBadRequest()
        return
    robot_function_param = None
    try:
        robot_function_param = int(data['param'])
        print(robot_function_param)
    except:
        pass
    if robot_function_param:
        result = robot_function(robot_function_param)
    else:
        result = robot_function()

    # content = """\
    # {\"success\" : \"true\", \"result\" : \"%s\"}
    # """ % (result)
    content = render_control_form(request, previous_form=data)
    request.Response.ReturnOk(content)


mws2 = MicroWebSrv2()
mws2.SetEmbeddedConfig()
mws2.StartManaged()


def get_pin_status():
    global pins
    pin_str = ''
    for pin in pins:
        pin_str = pin_str + '+{:.2f}'.format(pin.duty() / 1023.0)
    return pin_str


def prepare_status_string():
    global status_dict, in1, in2, in3, in4
    status_dict['mem_free'] = gc.mem_free()
    status_dict['pin_str'] = get_pin_status()
    s = 'Uptime: {seconds: 5d}s\tpins:{pin_str}\tmem_free:{mem_free}'.format(
        **status_dict)
    return s


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


def print_status():
    global status_dict
    print(prepare_status_string())
    status_dict['seconds'] += HEARTBEAT_PERIOD


def heartbeat_callback(timer_obj):
    global heartbeat_timer_flag
    heartbeat_timer_flag = True


def init_heartbeat_timer():
    heartbeat.init(
        period=HEARTBEAT_PERIOD * 1000,
        mode=Timer.PERIODIC,
        callback=heartbeat_callback
    )


def print_help():
    print('# boot.py script defines easy-to-type shorthands for robot control')
    print('')
    print('robot_backward as b')
    print('robot_forward as f')
    print('robot_rotate_left as rl')
    print('robot_rotate_right as rr')
    print('robot_turn_left as tl')
    print('robot_turn_right as tr')
    print('robot_wait as rw')
    print('robot_wait_1s as rw1')
    print('robot_wait_5s as rw5')
    print('execute_cmds as ec')
    print('print_status')
    print('print_help')
    print('print_help as robot_help')
    print('')
    print('# You can issue multiple commands like below:')
    print('f(), rl(), rl(), rl(), b(), b()')
    print('# Or you can use the ec shorthand:')
    print('ec(f, rw1, rl, rw, rl, rw, rl, rw5, b, b)')
    print('')
    print('# You can even use the ec shorthand with threading:')
    print('from _thread import start_new_thread as snt')
    print('snt(ec, (f, rl, rl, rl, rw1, b, b,))')
    print('')


def main_init():
    global status_dict
    init_gpio()

    print_help()

    init_wlan_result = wlan_wrapper.init_wifi(
        WLAN_SSID,
        WLAN_KEY,
        DHCP_HOSTNAME,
        timeout=None)

    if(init_wlan_result):
        status_dict.update(hostname=wlan_wrapper.wlan.config('dhcp_hostname'))
        print('Wifi initialised')

    init_heartbeat_timer()

    print('\nPress CTRL-C to drop to REPL to control the robot with existing functions\n')  # noqa E501


def heartbeat_task():
    # print_status()
    pass


def main():
    global heartbeat_timer_flag, publish_timer_flag, status_dict
    main_init()
    try:
        while True:
            # Periodic Heartbeat Task
            if heartbeat_timer_flag:
                heartbeat_timer_flag = False
                heartbeat_task()

            time.sleep(0.005)
    except KeyboardInterrupt:
        print('Caught CTRL-C')
        pass
