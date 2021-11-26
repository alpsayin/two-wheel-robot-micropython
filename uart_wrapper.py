import machine
from machine import UART, Pin
from micropython import const

TX_PIN = const(32)
RX_PIN = const(33)
STATE_PIN = const(35)
BAUD_R5 = const(115200)
BAUD_R8 = const(921600)
DEFAULT_BAUDRATE = const(115200)
TXBUF_LEN = const(256)
RXBUF_LEN = const(256)
# timeout specifies the time to wait for the first character (ms)
READ_TIMEOUT = 0
# timeout_char specifies the time to wait between characters (ms)
WRITE_WAIT = 0

raw_uart = None
baudrate = DEFAULT_BAUDRATE
bt_state_pin = Pin(35, Pin.IN)


def update_baudrate(new_baudrate):
    global raw_uart, baudrate
    raw_uart.deinit()
    baudrate = int(round(new_baudrate))
    init()


def is_bluetooth_connected():
    global bt_state_pin
    return bt_state_pin.value() == 1


def init():
    global raw_uart, baudrate
    raw_uart = UART(1, tx=TX_PIN, rx=RX_PIN)
    raw_uart.init(
        baudrate=baudrate,
        bits=8,
        parity=None,
        stop=1,
        tx=TX_PIN,
        rx=RX_PIN,
        txbuf=TXBUF_LEN,
        rxbuf=RXBUF_LEN,
        timeout=READ_TIMEOUT,
        timeout_char=WRITE_WAIT
    )
    raw_uart.write('AT')
    return raw_uart
