import machine
import time
from machine import Timer, Pin, PWM
from micropython import const
import gc
import wlan_wrapper
import uart_wrapper
from _thread import allocate_lock, start_new_thread
import json

DEVICE_FREQ = const(240 * 1000000)
BOOT_TIME = const(3)
HEARTBEAT_PERIOD = const(5)  # s
DEFAULT_MOTION_DURATION_MS = const(500)  # ms
DEFAULT_ROTATE_DURATION_MS = const(200)  # ms
MOTOR_DUTY_FREQ = const(20)  # Hz

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


def get_pin_number(pin_instance):
    return int(str(pin_instance)[4:-1])


# microphone pins
mic1 = Pin(13, Pin.IN)
mic2 = Pin(34, Pin.IN)
mic3 = Pin(39, Pin.IN)
mic4 = Pin(36, Pin.IN)

mics = [mic1, mic2, mic3, mic4]
mic_timers = {}


def init_mic_timers():
    for idx, mic in enumerate(mics):
        mic_timer = Timer(-idx)
        mic_timer.init(period=1000, mode=Timer.ONE_SHOT,
                       callback=lambda t: re_enable_mic_isr(t, mic))
        mic_timers[get_pin_number(mic)] = mic_timer


def re_enable_mic_isr(tim_instance, pin_instance):
    pin_instance.irq(mic_isr, Pin.IRQ_FALLING)
    print('Reenable {}'.format(pin_instance))


def mic_isr(pin_instance):
    pin_instance.irq(None)
    mic_timer = mic_timers[get_pin_number(pin_instance)]
    mic_timer.init(period=1000, mode=Timer.ONE_SHOT,
                   callback=lambda t: re_enable_mic_isr(t, pin_instance))
    print('Disable {}'.format(pin_instance))


def set_mic_isrs():
    mic1.irq(mic_isr, Pin.IRQ_FALLING)
    mic2.irq(mic_isr, Pin.IRQ_FALLING)
    mic3.irq(mic_isr, Pin.IRQ_FALLING)
    mic4.irq(mic_isr, Pin.IRQ_FALLING)


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


def robot_backward(duration_ms=DEFAULT_MOTION_DURATION_MS):
    global power_level
    in1.duty(power_level)
    in2.duty(0)
    in3.duty(power_level)
    in4.duty(0)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_forward(duration_ms=DEFAULT_MOTION_DURATION_MS):
    global power_level
    in1.duty(0)
    in2.duty(power_level)
    in3.duty(0)
    in4.duty(power_level)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_rotate_right(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    global power_level
    in1.duty(0)
    in2.duty(power_level)
    in3.duty(power_level)
    in4.duty(0)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_rotate_left(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    global power_level
    in1.duty(power_level)
    in2.duty(0)
    in3.duty(0)
    in4.duty(power_level)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_turn_right(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    global power_level
    in1.duty(0)
    in2.duty(power_level)
    in3.duty(0)
    in4.duty(0)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_turn_left(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    global power_level
    in1.duty(0)
    in2.duty(0)
    in3.duty(0)
    in4.duty(power_level)
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    robot_stop()


def robot_wait(duration_ms=DEFAULT_MOTION_DURATION_MS):
    time.sleep_ms(duration_ms)


def robot_wait_1s():
    time.sleep_ms(1000)


def robot_wait_5s():
    time.sleep_ms(5000)


def get_pins_status():
    global pins
    pin_str = '('
    for pin in pins:
        pin_str = pin_str + '{}, '.format(pin.duty())
    pin_str += ')'
    return pin_str


def robot_set_motor_powers(motor1: int, motor2: int):
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
              robot_get_power,
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


def websocket_on_accept(microWebSrv2, webSocket):
    print('Example WebSocket accepted:')
    print('   - User   : %s:%s' % webSocket.Request.UserAddress)
    print('   - Path   : %s' % webSocket.Request.Path)
    print('   - Origin : %s' % webSocket.Request.Origin)
    if webSocket.Request.Path.lower() == '/controller_ws':
        controller_websocket_join(webSocket)
    elif webSocket.Request.Path.lower() == '/motors_ws':
        motors_websocket_join(webSocket)
    else:
        print('Uknown ws path: "%s"' % webSocket.Request.Path.lower())
        webSocket.OnTextMessage = websocket_on_recv_text
        webSocket.OnBinaryMessage = websocket_on_recv_binary
        webSocket.OnClosed = websocket_on_close
        webSocket.Close()

# ============================================================================
# ============================================================================
# ============================================================================


global controller_ws
controller_ws = None
global motors_ws
motors_ws = None

global _wsLock
_wsLock = allocate_lock()


def websocket_on_recv_text(webSocket, msg):
    pass

# ------------------------------------------------------------------------


def websocket_on_recv_binary(webSocket, msg):
    pass

# ------------------------------------------------------------------------


def websocket_on_close(webSocket):
    global controller_ws, motors_ws
    print('WebSocket %s:%s closed' % webSocket.Request.UserAddress)
    if webSocket == controller_ws:
        controller_ws = None
    if webSocket == motors_ws:
        motors_ws = None

# ------------------------------------------------------------------------


def controller_websocket_join(webSocket):
    global controller_ws
    webSocket.OnTextMessage = controller_websocket_on_recv_text
    webSocket.OnClosed = websocket_on_close
    addr = webSocket.Request.UserAddress
    print('# Websocket join attempt from <%s:%s>' % addr)
    accepted = True
    with _wsLock:
        if controller_ws is None:
            controller_ws = webSocket
            controller_ws.SendTextMessage('# HELLO <%s:%s>' % addr)
        else:
            webSocket.SendTextMessage('# REJECTED <%s:%s>' % addr)
            controller_ws.SendTextMessage('# REJECTED <%s:%s>' % addr)
            webSocket.Close()
            accepted = False
    if accepted:
        print('# ACCEPTED <%s:%s>' % addr)
    else:
        print('# REJECTED <%s:%s>' % addr)


def motors_websocket_join(webSocket):
    global motors_ws
    webSocket.OnTextMessage = motors_websocket_on_recv_text
    webSocket.OnClosed = websocket_on_close
    addr = webSocket.Request.UserAddress
    print('# Websocket join attempt from <%s:%s>' % addr)
    accepted = True
    with _wsLock:
        if motors_ws is None:
            motors_ws = webSocket
            motors_ws.SendTextMessage('# HELLO <%s:%s>' % addr)
        else:
            webSocket.SendTextMessage('# REJECTED <%s:%s>' % addr)
            motors_ws.SendTextMessage('# REJECTED <%s:%s>' % addr)
            webSocket.Close()
            accepted = False
    if accepted:
        print('# ACCEPTED <%s:%s>' % addr)
    else:
        print('# REJECTED <%s:%s>' % addr)
# ------------------------------------------------------------------------


def controller_websocket_on_recv_text(webSocket, msg):
    json_data = json.loads(msg)
    cmd = None
    param = None
    if 'cmd' not in json_data:
        return
    if json_data['cmd'] not in valid_cmd_dict:
        return
    cmd = valid_cmd_dict[json_data['cmd']]
    param = None
    if 'param' in json_data:
        param = json_data['param']
        if param is not None:
            try:
                param = int(param)
            except OSError:
                pass
    cmd_queue.append((cmd, param, webSocket))
    print('%s(%s)' % (cmd.__name__, str(param), ))


def motors_websocket_on_recv_text(webSocket, msg):
    global in1, in2, in3, in4
    json_data = json.loads(msg)
    if 'm1' not in json_data:
        return
    if 'm2' not in json_data:
        return
    motor1 = 0
    motor2 = 0
    try:
        motor1 = int(json_data['m1'])
        motor2 = int(json_data['m2'])
    except OSError:
        webSocket.Close()
        pass
    robot_set_motor_powers(motor1, motor2)
    # print('%s,%s' % (str(motor1), str(motor2)))


# ============================================================================
# ============================================================================
# ============================================================================


# Loads the WebSockets module globally and configure it,
wsMod = MicroWebSrv2.LoadModule('WebSockets')
wsMod.OnWebSocketAccepted = websocket_on_accept
mws2 = MicroWebSrv2()
mws2.SetEmbeddedConfig()
# All pages not found will be redirected to the home '/',
mws2.NotFoundURL = 'https://alpsayin.com'
mws2.StartManaged()


def prepare_status_string():
    global status_dict, in1, in2, in3, in4
    status_dict['mem_free'] = gc.mem_free()
    status_dict['pin_str'] = get_pins_status()
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
    print('''
        robot_stop
        robot_backward
        robot_forward
        robot_rotate_left
        robot_rotate_right
        robot_turn_left
        robot_turn_right
        robot_wait
        robot_wait_1s
        robot_wait_5s
        execute_cmds
        robot_get_power
        robot_set_power
        print_status
        print_help
        get_pins_status
        get_motors_status

        robot_stop as stop
        robot_stop as rs
        robot_backward as b
        robot_forward as f
        robot_rotate_left as rl
        robot_rotate_right as rr
        robot_turn_left as tl
        robot_turn_right as tr
        robot_wait as rw
        robot_wait_1s as rw1
        robot_wait_5s as rw5
        execute_cmds as ec
        robot_get_power as getpow, robot_set_power as setpow
        get_pins_status as getpins
        get_motors_status as getmotors
        print_help as robot_help
    ''')
    print('')
    print('# You can issue multiple commands like below:')
    print('f(), rl(), rl(), rl(), b(), b()')
    print('# Or you can use the ec shorthand:')
    print('ec(f, rw1, rl, rw, rl, rw, rl, rw5, b, b)')
    print('')


def WASD_robot_handler_task(read_period_ms=100):
    global cmd_queue
    while True:
        time.sleep_ms(read_period_ms)
        if uart_wrapper.is_bluetooth_connected():
            while uart_wrapper.raw_uart.any():
                single_char = uart_wrapper.raw_uart.read(1)
                if single_char == b'w':
                    robot_set_motor_powers(power_level, power_level)
                if single_char == b's':
                    robot_set_motor_powers(-power_level, -power_level)
                if single_char == b'a':
                    robot_set_motor_powers(int(power_level/4), power_level)
                if single_char == b'd':
                    robot_set_motor_powers(power_level, int(power_level/4))
                if single_char == b'h':
                    robot_set_motor_powers(0, 0)


def main_init():
    global status_dict

    machine.freq(DEVICE_FREQ)

    init_gpio()

    uart_wrapper.init()

    print_help()

    init_wlan_result = wlan_wrapper.init_wifi(
        WLAN_SSID,
        WLAN_KEY,
        DHCP_HOSTNAME,
        timeout=10)

    if(init_wlan_result):
        status_dict.update(hostname=wlan_wrapper.wlan.config('dhcp_hostname'))
        print('Wifi initialised')

    init_heartbeat_timer()

    init_mic_timers()
    set_mic_isrs()

    print('\nPress CTRL-C to drop to REPL to control the robot with existing functions\n')  # noqa E501


def heartbeat_task():
    # print_status()
    # TODO: flip a led here
    pass


def main():
    global heartbeat_timer_flag, publish_timer_flag, status_dict, cmd_queue
    main_init()
    start_new_thread(WASD_robot_handler_task, (100,))
    try:
        while True:
            machine.idle()  # wait until cpu wake
            # Periodic Heartbeat Task
            if heartbeat_timer_flag:
                heartbeat_timer_flag = False
                heartbeat_task()

            while cmd_queue:
                cmd, param, websocket = cmd_queue.pop()
                if param:
                    result = cmd(param)
                else:
                    result = cmd()
                if websocket:
                    with _wsLock:
                        websocket.SendTextMessage(
                            '{"result":"%s"}' % str(result))

    except KeyboardInterrupt:
        print('Caught CTRL-C')
        pass
