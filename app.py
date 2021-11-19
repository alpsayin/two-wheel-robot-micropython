import machine
import time
from machine import Timer, Pin
from micropython import const
import gc
import repl_drop
import wlan_wrapper

BOOT_TIME = const(3)
HEARTBEAT_PERIOD = const(2000)  # ms
DEFAULT_MOTION_DURATION_MS = const(500)  # ms
DEFAULT_ROTATE_DURATION_MS = const(100)  # ms

# wifi
# make sure you have a credentials.py file which defines the below variables
from credentials import WLAN_SSID, WLAN_KEY  # noqa E402
DHCP_HOSTNAME = 'alpo'

# motor control pins
in1 = Pin(25, Pin.OUT)
in2 = Pin(26, Pin.OUT)
in3 = Pin(27, Pin.OUT)
in4 = Pin(14, Pin.OUT)
pins = [in1, in2, in3, in4]

# status
heartbeat_timer_flag = True
heartbeat = Timer(-1)
status_dict = dict(
    hostname='null',
    seconds=0,
    freq=115200,
    mem_free=gc.mem_free()
)

# publish timer
publish_timer_flag = False
publish_period = 5  # seconds
publish_timer = Timer(-2)

# capture buffer
capture_buffer = bytearray()


def stop():
    in1.off()
    in2.off()
    in3.off()
    in4.off()


def robot_forward(duration_ms=DEFAULT_MOTION_DURATION_MS):
    in1.on()
    in2.off()
    in3.on()
    in4.off()
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def robot_backward(duration_ms=DEFAULT_MOTION_DURATION_MS):
    in1.off()
    in2.on()
    in3.off()
    in4.on()
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def robot_rotate_right(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    in1.off()
    in2.on()
    in3.on()
    in4.off()
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def robot_rotate_left(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    in1.on()
    in2.off()
    in3.off()
    in4.on()
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def robot_turn_right(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    in1.off()
    in2.off()
    in3.on()
    in4.off()
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def robot_turn_left(duration_ms=DEFAULT_ROTATE_DURATION_MS):
    in1.on()
    in2.off()
    in3.off()
    in4.off()
    if duration_ms != -1:
        time.sleep_ms(duration_ms)
    stop()


def robot_wait(duration_ms=DEFAULT_MOTION_DURATION_MS):
    time.sleep_ms(duration_ms)


def robot_wait_1s():
    time.sleep_ms(1000)


def robot_wait_5s():
    time.sleep_ms(5000)


def execute_cmds(*args):
    valid_cmds = [robot_forward,
                  robot_backward,
                  robot_rotate_left,
                  robot_rotate_right,
                  robot_turn_left,
                  robot_turn_right,
                  robot_wait,
                  robot_wait_1s,
                  robot_wait_5s
                  ]
    # print(args)

    for arg in args:
        # print(arg)
        if arg in valid_cmds:
            print('Executing {}'.format(arg.__name__))
            arg()


def get_pin_status():
    global pins
    pin_str = ''
    for pin in pins:
        pin_str = pin_str + '{:x}'.format(pin.value())
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
    in1.off()
    in2.off()
    in3.off()
    in4.off()


def print_status():
    global status_dict
    print(prepare_status_string())
    status_dict['seconds'] += 1


def heartbeat_callback(timer_obj):
    global heartbeat_timer_flag
    heartbeat_timer_flag = True


def init_heartbeat_timer():
    heartbeat.init(
        period=round(HEARTBEAT_PERIOD),
        mode=Timer.PERIODIC,
        callback=heartbeat_callback
    )


def main_init():
    global status_dict
    init_gpio()

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
    print('# boot.py script defines easy-to-type shorthands for robot control')
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


def heartbeat_task():
    print_status()


def main():
    global heartbeat_timer_flag, publish_timer_flag, status_dict
    repl_drop.wait(BOOT_TIME)
    print('app.py')
    main_init()
    while True:
        # Periodic Heartbeat Task
        if heartbeat_timer_flag:
            heartbeat_timer_flag = False
            heartbeat_task()

        time.sleep(0.005)
