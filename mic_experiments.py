
from time import time
from machine import Timer, Pin, PWM
from micropython import const, schedule
from util import get_pin_number
import _thread
from collections import deque

# microphone pins
mic_left = Pin(13, Pin.IN)  # left
mic_right = Pin(34, Pin.IN)  # right
mic_back = Pin(39, Pin.IN)  # back
mic_front = Pin(36, Pin.IN)  # front

mics = [mic_left, mic_right, mic_back, mic_front]
mic_positions = {get_pin_number(mic_left): 'left',
                 get_pin_number(mic_right): 'right',
                 get_pin_number(mic_back): 'back',
                 get_pin_number(mic_front): 'front'}
mic_array = None


def mic_reen_print(*args, **kwargs):
    print('Re-enabled {}'.format(args[0]))


def mic_dis_print(*args, **kwargs):
    print('Disabled {}'.format(args[0]))


def first_mic_print(*args, **kwargs):
    print('FIRST {}!'.format(mic_positions[args[0]]))


class MicrophoneArray(object):
    def __init__(self, mics):
        self.mics = [mic for mic in mics]
        self.timer = Timer(2)
        self.timer_isr_ref = self.timer_isr
        self.pin_isr_ref = self.pin_isr
        for mic in self.mics:
            mic.irq(self.pin_isr)
        self.ignore_mic = False

    def disable_irqs(self):
        self.ignore_mic = True
        for mic in self.mics:
            mic.irq(None)
        self.timer.init(period=2000,
                        mode=Timer.ONE_SHOT,
                        callback=self.timer_isr_ref)
        # print('Disabled')

    def timer_isr(self, timer_instance):
        self.ignore_mic = False
        for mic in self.mics:
            mic.irq(self.pin_isr_ref)
        print('Re-enabled')

    def pin_isr(self, pin_instance):
        if self.ignore_mic:
            return
        self.disable_irqs()
        first_mic_print(get_pin_number(pin_instance))


def init_mic_experiments():
    global mics, mic_array
    mic_array = MicrophoneArray(mics)
