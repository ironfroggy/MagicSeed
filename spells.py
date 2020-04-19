from math import floor
from time import perf_counter

from timer import delay


def heal(duration, target, hp):
    """Heal the target an amount of HP over a number of seconds."""

    start = perf_counter()
    end = start + duration
    d = floor(hp / duration)

    def tick():
        nonlocal hp
        hp -= d
        if target.hp >= d:
            target.hp += d

        if perf_counter() > end:
            if hp > 0:
                target.hp += hp
        else:
            delay(1.0, tick)

    delay(1.0, tick)


def shield(duration, target, hp):
    """Reduce incoming damage by a certain amount over a number of seconds."""

    start = perf_counter()
    end = start + duration
    d = floor(hp / duration)

    def tick():
        nonlocal hp
        hp -= d
        if target.hp >= d:
            target.shield += d

        if perf_counter() > end:
            if hp > 0:
                target.shield += hp
        else:
            delay(1.0, tick)

    delay(1.0, tick)
