from machine import reset  # noqa F401
# import webrepl

print('boot.py')
# webrepl.start()

from robot import stop
from robot import backward
from robot import forward
from robot import rotate_left
from robot import rotate_right
from robot import turn_left
from robot import turn_right
from robot import wait
from robot import wait_1s
from robot import wait_5s
from robot import execute_cmds
from robot import get_power
from robot import set_power
from app import print_status
from app import print_help
from robot import get_pins_status
from robot import get_motors_status

from robot import stop as rs
from robot import backward as b
from robot import forward as f
from robot import rotate_left as rl
from robot import rotate_right as rr
from robot import turn_left as tl
from robot import turn_right as tr
from robot import wait as rw
from robot import wait_1s as rw1
from robot import wait_5s as rw5
from robot import execute_cmds as ec
from robot import get_power as getpow, set_power as setpow
from robot import get_pins_status as getpins
from robot import get_motors_status as getmotors
from app import print_help as robot_help