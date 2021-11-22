import time
import websocket
from pynput import keyboard
import simplejson as json

DEFAULT_POWER = 750

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
            motor2 /= 2
        if right:
            motor1 /= 2
    elif down:
        motor1 = -DEFAULT_POWER
        motor2 = -DEFAULT_POWER
        if left:
            motor2 /= 2
        if right:
            motor1 /= 2
    else:
        if left:
            motor1 = DEFAULT_POWER / 2
            motor2 = -DEFAULT_POWER / 2
        if right:
            motor1 = -DEFAULT_POWER / 2
            motor2 = DEFAULT_POWER / 2
    ret_dict = {'motor1': motor1, 'motor2': motor2}
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


def main():
    global motors_ws
    hostname = input('enter esp32 hostname:')
    motors_ws = websocket.WebSocket()
    motors_ws.connect(f'ws://{hostname}/motors_ws', timeout=2)
    print(f'Websockets connected: {motors_ws.getstatus()}')

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
            data_json_str = json.dumps(motors_powers)
            print(f'{data_json_str}')
            motors_ws.send(data_json_str)
        except KeyboardInterrupt:
            print('Caught CTRL-C')
            motors_ws.close()
            break


if __name__ == '__main__':
    main()
