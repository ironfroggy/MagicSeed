from dataclasses import dataclass
from time import monotonic
from types import FunctionType
from typing import Optional

import ppb
from ppb.systemslib import System


@dataclass
class Timer:
    end_time: float
    callback: FunctionType
    repeating: float = 0
    clear: bool = False

    def __hash__(self):
        return hash(id(self))


class Timers(System):
    timers = set()

    @classmethod
    def delay(cls, seconds, func):
        t = Timer(monotonic() + seconds, func)
        cls.timers.add(t)
        return t
    
    @classmethod
    def repeat(cls, seconds, func):
        t = Timer(monotonic() + seconds, func, repeating=seconds)
        cls.timers.add(t)
        return t
    
    @classmethod
    def cancel(cls, timer):
        timer.clear = True

    @classmethod
    def on_idle(cls, idle, signal):
        clear = []
        for t in list(cls.timers):
            if t.clear:
                clear.append(t)
            else:
                now = monotonic()
                if now >= t.end_time:
                    t.callback()
                    if t.repeating > 0:
                        t.end_time += t.repeating
                    else:
                        clear.append(t)
        for t in clear:
            cls.timers.remove(t)


delay = Timers.delay
repeat = Timers.repeat
cancel = Timers.cancel
