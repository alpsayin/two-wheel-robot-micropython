import time
import websocket
from pynput import keyboard
import simplejson as json
from argparse import ArgumentParser, ArgumentTypeError

DEFAULT_POWER = 1000
LOW_POWER = 500
HOSTNAME = None

motors_ws = None

up = False
down = False
left = False
right = False


def compute_motor_speeds():
    global up, down, left, right
    motor1 = 0
    motor2 = 0
    if up and down:
        motor1 = 0
        motor2 = 0
    elif up:
        motor1 = DEFAULT_POWER
        motor2 = DEFAULT_POWER
        if left:
            motor2 = LOW_POWER
        if right:
            motor1 = LOW_POWER
    elif down:
        motor1 = -DEFAULT_POWER
        motor2 = -DEFAULT_POWER
        if left:
            motor2 = -LOW_POWER
        if right:
            motor1 = -LOW_POWER
    else:
        if left:
            motor1 = LOW_POWER
            motor2 = -LOW_POWER
        if right:
            motor1 = -LOW_POWER
            motor2 = LOW_POWER
    ret_dict = {'m1': motor1, 'm2': motor2}
    return ret_dict


def on_press(key):
    global keys_lock, up, down, left, right
    try:
        if key == keyboard.Key.up:
            up = True
            print('\r UP', end='')
        if key == keyboard.Key.down:
            down = True
            print('\r DOWN', end='')
        if key == keyboard.Key.left:
            left = True
            print('\r LEFT', end='')
        if key == keyboard.Key.right:
            right = True
            print('\r RIGHT', end='')
    except AttributeError:
        print('special key {0} pressed'.format(
            key))


def on_release(key):
    global up, down, left, right
    print('')
    if key == keyboard.Key.up:
        up = False
        print('\r^UP', end='')
    if key == keyboard.Key.down:
        down = False
        print('\r^DOWN', end='')
    if key == keyboard.Key.left:
        left = False
        print('\r^LEFT', end='')
    if key == keyboard.Key.right:
        right = False
        print('\r^RIGHT', end='')
    if key == keyboard.Key.esc:
        # Stop listener
        return False


def deci_percent_input(arg_decipercent: str) -> int:
    try:
        result = int(arg_decipercent)
    except Exception as ex:
        raise ArgumentTypeError(f"Input is not a valid integer string -> {ex}")
    if result < 0 or result > 1023:
        raise ArgumentTypeError(
            f"Input is not in valid range [0, 1023] -> {result}")
    return result


def process_args():
    global LOW_POWER, DEFAULT_POWER, HOSTNAME
    parser = ArgumentParser(
        description='Simple esp32 robot controller with arrow keys')
    parser.add_argument(
        '--target', '-t', help='Target esp32 hostname or IP address')
    parser.add_argument(
        '--low-power', '-lp',
        type=deci_percent_input,
        default=LOW_POWER,
        help='Deci percentage of motor power to use to send low power')
    parser.add_argument(
        '--default-power', '-dp',
        type=deci_percent_input,
        default=DEFAULT_POWER,
        help='Deci percentage of motor power to use to send default power')
    vargs = vars(parser.parse_args())
    print(vargs)
    HOSTNAME = vargs['target']
    if not HOSTNAME:
        HOSTNAME = input('enter esp32 hostname:')
    LOW_POWER = vargs['low_power']
    DEFAULT_POWER = vargs['default_power']


def main():
    global motors_ws, HOSTNAME
    process_args()
    motors_ws = websocket.WebSocket()
    motors_ws.connect(f'ws://{HOSTNAME}/motors_ws',
                      timeout=2)
    print(f'Websockets connected: {motors_ws.getstatus()}')
    print(f'Welcome message = {motors_ws.recv()}')

    # ...or, in a non-blocking fashion:
    listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release)
    listener.start()
    print(f'Keyboard listener started: {listener}')

    motors_powers = compute_motor_speeds()

    while True:
        try:
            time.sleep(0.1)
            motors_powers = compute_motor_speeds()
            data_json_str = json.dumps(motors_powers, separators=(',', ':'))
            print(f'{data_json_str}')
            motors_ws.send(data_json_str)
        except KeyboardInterrupt:
            print('Caught CTRL-C')
            motors_ws.close()
            break


if __name__ == '__main__':
    main()
