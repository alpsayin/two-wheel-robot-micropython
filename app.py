import machine
import time
from machine import Timer, Pin, PWM
from micropython import const, alloc_emergency_exception_buf
import gc
import wlan_wrapper
import uart_wrapper
from _thread import start_new_thread

alloc_emergency_exception_buf(100)

import esp
esp.osdebug(0)          # redirect vendor O/S debugging messages to UART(0)

import robot
robot.init_gpio()

import mic_experiments

DEVICE_FREQ = const(240 * 1000000)
BOOT_TIME = const(3)
HEARTBEAT_PERIOD = const(5)  # s

import repl_drop
repl_drop.wait(BOOT_TIME)
print('app.py')

import robot_websocket_server

# wifi
# make sure you have a credentials.py file which defines the below variables
from credentials import WLAN_SSID, WLAN_KEY  # noqa E402
DHCP_HOSTNAME = 'alpo'

# status
heartbeat_timer_flag = True
heartbeat = Timer(3)
status_dict = dict(
    hostname='null',
    seconds=0,
    freq=115200,
    mem_free=gc.mem_free()
)


def prepare_status_string():
    global status_dict
    status_dict['mem_free'] = gc.mem_free()
    status_dict['pin_str'] = robot.get_pins_status()
    s = 'Uptime: {seconds: 5d}s\tpins:{pin_str}\tmem_free:{mem_free}'.format(
        **status_dict)
    return s


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
        robot.stop
        robot.backward
        robot.forward
        robot.rotate_left
        robot.rotate_right
        robot.turn_left
        robot.turn_right
        robot.wait
        robot.wait_1s
        robot.wait_5s
        execute_cmds
        robot.get_power
        robot.set_power
        print_status
        print_help
        get_pins_status
        get_motors_status

        robot.stop as stop
        robot.stop as rs
        robot.backward as b
        robot.forward as f
        robot.rotate_left as rl
        robot.rotate_right as rr
        robot.turn_left as tl
        robot.turn_right as tr
        robot.wait as rw
        robot.wait_1s as rw1
        robot.wait_5s as rw5
        execute_cmds as ec
        robot.get_power as getpow, robot.set_power as setpow
        get_pins_status as getpins
        get_motors_status as getmotors
        print_help as robot.help
    ''')
    print('')
    print('# You can issue multiple commands like below:')
    print('f(), rl(), rl(), rl(), b(), b()')
    print('# Or you can use the ec shorthand:')
    print('ec(f, rw1, rl, rw, rl, rw, rl, rw5, b, b)')
    print('')


def WASD_robot_handler_task(read_period_ms=100):
    while True:
        time.sleep_ms(read_period_ms)
        if uart_wrapper.is_bluetooth_connected():
            while uart_wrapper.raw_uart.any():
                single_char = uart_wrapper.raw_uart.read(1)
                if single_char == b'w':
                    robot.set_motor_powers(robot.power_level,
                                           robot.power_level)
                if single_char == b's':
                    robot.set_motor_powers(-robot.power_level,
                                           -robot.power_level)
                if single_char == b'a':
                    robot.set_motor_powers(int(robot.power_level / 4),
                                           robot.power_level)
                if single_char == b'd':
                    robot.set_motor_powers(robot.power_level,
                                           int(robot.power_level / 4))
                if single_char == b'h':
                    robot.set_motor_powers(0, 0)


def main_init():
    global status_dict

    machine.freq(DEVICE_FREQ)

    robot.init_gpio()

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

    mic_experiments.init_mic_experiments()

    print('\nPress CTRL-C to drop to REPL to control the robot with existing functions\n')  # noqa E501


def heartbeat_task():
    # print_status()
    # TODO: flip a led here
    pass


def main():
    global heartbeat_timer_flag, publish_timer_flag, status_dict
    main_init()
    start_new_thread(WASD_robot_handler_task, (100,))
    try:
        while True:
            machine.idle()  # wait until cpu wake
            # Periodic Heartbeat Task
            if heartbeat_timer_flag:
                heartbeat_timer_flag = False
                heartbeat_task()

            while robot.cmd_queue:
                cmd, param, websocket = robot.cmd_queue.pop()
                if param:
                    result = cmd(param)
                else:
                    result = cmd()
                if websocket:
                    with robot_websocket_server._wsLock:
                        websocket.SendTextMessage(
                            '{"result":"%s"}' % str(result))

    except KeyboardInterrupt:
        print('Caught CTRL-C')
        pass
