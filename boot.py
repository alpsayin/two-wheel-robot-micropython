from machine import reset  # noqa F401
import webrepl

print('boot.py')
webrepl.start()

from app import robot_stop
from app import robot_backward
from app import robot_forward
from app import robot_rotate_left
from app import robot_rotate_right
from app import robot_turn_left
from app import robot_turn_right
from app import robot_wait
from app import robot_wait_1s
from app import robot_wait_5s
from app import execute_cmds
from app import robot_get_power
from app import robot_set_power
from app import print_status
from app import print_help
from app import print_help
from app import robot_stop

from app import robot_backward as b
from app import robot_forward as f
from app import robot_rotate_left as rl
from app import robot_rotate_right as rr
from app import robot_turn_left as tl
from app import robot_turn_right as tr
from app import robot_wait as rw
from app import robot_wait_1s as rw1
from app import robot_wait_5s as rw5
from app import execute_cmds as ec
from app import robot_get_power as gp, robot_set_power as sp
from app import print_help as robot_help