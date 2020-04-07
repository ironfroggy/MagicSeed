from dataclasses import dataclass
import math
from random import choice, random
from time import time
import types

import ppb
from ppb import keycodes
from ppb.events import KeyPressed, KeyReleased
from ppb.systemslib import System


# Constants

COLOR_GREEN = 1
COLOR_RED = 2
COLOR_YELLOW = 3
COLOR_BLUE = 4
COLOR_WHITE = 5
COLORS = (
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    COLOR_BLUE,
    COLOR_WHITE,
)

# Images loaded for each color
SEED_IMAGES = {
    COLOR_GREEN: ppb.Image("resources/seed3.png"),
    COLOR_RED: ppb.Image("resources/seed1.png"),
    COLOR_YELLOW: ppb.Image("resources/seed2.png"),
    COLOR_BLUE: ppb.Image("resources/seed5.png"),
    COLOR_WHITE: ppb.Image("resources/seed4.png"),
}

class Seed(ppb.BaseSprite):
    position = ppb.Vector(0, 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = int(self.position.x)
        self.y = int(self.position.y)
        self.is_free = False
    
    def free(self):
        try:
            del GRID[self.x, self.y]
        except KeyError:
            pass
        self.x = None
        self.y = None
        self.is_free = True

    def drop(self, scene, x, y):
        self.x = x
        self.y = y

        color = choice(COLORS)
        self.color = color
        self.image = SEED_IMAGES[color]
        self.size = 0
        self.position = ppb.Vector(self.x, self.y + 4)

        GRID[x, y] = self

        t = Tweener()
        scene.add(t)
        t.tween(self, 'size', 1.0, 0.25, delay=0.5)
        t.tween(self, 'position', ppb.Vector(self.x, self.y), 0.5, delay=0.25, easing=in_quad)


def GreenSeed(*args, **kwargs):
    kwargs['color'] = COLOR_GREEN
    kwargs['image'] = SEED_IMAGES[kwargs['color']]
    return Seed(*args, **kwargs)

def RedSeed(*args, **kwargs):
    kwargs['color'] = COLOR_RED
    kwargs['image'] = SEED_IMAGES[kwargs['color']]
    return Seed(*args, **kwargs)

def YellowSeed(*args, **kwargs):
    kwargs['color'] = COLOR_YELLOW
    kwargs['image'] = SEED_IMAGES[kwargs['color']]
    return Seed(*args, **kwargs)

def BlueSeed(*args, **kwargs):
    kwargs['color'] = COLOR_BLUE
    kwargs['image'] = SEED_IMAGES[kwargs['color']]
    return Seed(*args, **kwargs)

def WhiteSeed(*args, **kwargs):
    kwargs['color'] = COLOR_WHITE
    kwargs['image'] = SEED_IMAGES[kwargs['color']]
    return Seed(*args, **kwargs)


SEEDS = (
    GreenSeed,
    RedSeed,
    YellowSeed,
    BlueSeed,
    WhiteSeed,
)

GRID = {}


# Easing functions

def linear(t):
    return t

def in_quad(t):
    return t*t

def out_quad(t):
    return t * (2 - t)


# Tweening

def flerp(f1, f2, t):
    return f1 + t * (f2 - f1)


def vlerp(v1, v2, t):
    return ppb.Vector(
        v1.x + t * (v2.x - v1.x),
        v1.y + t * (v2.y - v1.y),
    )


@dataclass
class Tween:
    start_time: float
    end_time: float
    obj: object
    attr: str
    start_value: object
    end_value: object
    easing: types.FunctionType = linear


class Tweener:
    """A controller of object transitions over time.
    
    A Tweener has to be added to a scene in order to work! After creating it,
    make multiple calls to tween() to set transitions of object members over
    time. Callbacks may be added to the Tweener with when_done() and all
    callbacks will be invoked when the final transition ends.

    Example:

        t = Tweener()
        t.tween(bomb, 'position', v_target, 1.0)
        t.when_done(play_sound("BOOM"))
    """

    size = 0

    def __init__(self):
        self.tweens = []
        self.callbacks = []
        self.used = False
        self.done = False

    def __hash__(self):
        return hash(id(self))

    @property
    def is_tweening(self):
        return bool(self.tweens)

    def tween(self, entity, attr, end_value, duration, **kwargs):
        assert not self.done
        self.used = True
        start_time = time() + kwargs.pop('delay', 0)
        self.tweens.append(Tween(
            start_time=start_time,
            end_time=start_time + duration,
            obj=entity,
            attr=attr,
            start_value=getattr(entity, attr),
            end_value=end_value,
            **kwargs,
        ))
    
    def when_done(self, func):
        self.callbacks.append(func)

    def on_idle(self, update, signal):
        t = time()
        clear = []

        for i, tween in enumerate(self.tweens):
            tr = (t - tween.start_time) / (tween.end_time - tween.start_time)
            tr = min(1.0, max(0.0, tr))
            tr = tween.easing(tr)
            if isinstance(tween.end_value, ppb.Vector):
                value = vlerp(tween.start_value, tween.end_value, tr)
            else:
                value = flerp(tween.start_value, tween.end_value, tr)
            setattr(tween.obj, tween.attr, value)
            if tr >= 1.0:
                clear.append(i)

        for i in reversed(clear):
            del self.tweens[i]
        
        if self.used and not self.tweens and not self.done:
            self.done = True
            for func in self.callbacks:
                func()


# Event classes

@dataclass
class MovementStart:
    scene: object

@dataclass
class MovementDone:
    scene: object

@dataclass
class TweeningDone:
    tweener: Tweener

@dataclass
class CellEmptied:
    seed: Seed
    x: int
    y: int


class TickSystem(System):
    callbacks = []
    
    @classmethod
    def call_later(self, seconds, func):
        self.callbacks.append((time() + seconds, func))

    @classmethod
    def on_idle(self, update, signal):
        t = time()
        clear = []
        for i, (c, func) in enumerate(self.callbacks):
            if c <= t:
                func()
                clear.append(i)
        for i in reversed(clear):
            del self.callbacks[i]
    
    last_click = None

    @classmethod
    def on_button_pressed(self, press_event, signal):
        x = round(press_event.position.x)
        y = round(press_event.position.y)
        tweener = Tweener()

        if self.last_click:
            lx, ly = self.last_click
            missed = False
            if (x, y) not in GRID:
                missed = True
            if (lx, ly) not in GRID:
                missed = True

            if not missed and abs(lx-x) <= 1 and abs(ly-y) <= 1:
                seed1 = GRID[x, y]
                seed2 = GRID[lx, ly]
                GRID[x, y] = seed2
                GRID[lx, ly] = seed1
                seed2.x = x
                seed2.y = y
                seed1.x = lx
                seed1.y = ly
                tweener.tween(seed1, 'position', ppb.Vector(lx, ly), 0.25)
                tweener.tween(seed2, 'position', ppb.Vector(x, y), 0.25)
        
        if tweener.is_tweening:
            @tweener.when_done
            def on_tweening_done():
                signal(MovementDone(press_event.scene))
            press_event.scene.add(tweener)

        if self.last_click == None:
            self.last_click = (x, y)
        else:
            self.last_click = None


class Timer:
    size = 0

    def __init__(self, callback):
        self.callback = callback
        self.start_time = time()
        self.duraction = None
        self.end_time = None
        self.repeating = False

    def delay(self, seconds):
        self.duration = seconds
        self.end_time = time() + seconds
    
    def repeat(self, seconds):
        self.repeating = True
        self.delay(seconds)

    def on_idle(self, idle, signal):
        if self.end_time:
            t = time()
            if t >= self.end_time:
                self.callback()
                if self.repeating:
                    self.end_time += self.duration
                else:
                    self.end_time = None        


@dataclass
class Grid:
    scene: ppb.BaseScene = None
    size: float = 0

    def __hash__(self):
        return hash(id(self))

    def on_scene_started(self, ev, signal):
        # TODO: Find out if there is a better way to do this
        self.scene = ev.scene
        self.find_matches(signal)

    def on_movement_done(self, ev, signal):
        self.find_matches(signal)

    def on_cell_emptied(self, ev, signal):
        color = choice(COLORS)
        seed = ev.seed
        seed.color = color
        seed.image = SEED_IMAGES[color]
        seed.size = 0.0
        seed.position = ppb.Vector(ev.x, ev.y)

        t = Tweener()
        self.scene.add(t)
        t.tween(seed, 'size', 1.0, 0.25)


    def find_matches(self, signal):
        tweener = Tweener()
        seeds = set()

        for x in range(-2, 3):
            for y in range(-2, 3):
                seed1 = GRID.get((x, y))

                # Match UP along a column
                seed2 = GRID.get((x, y + 1))
                seed3 = GRID.get((x, y + 2))
                seed4 = GRID.get((x, y + 3))
                seed5 = GRID.get((x, y + 4))
                # Find a simple 3-match
                if all((seed1, seed2, seed3)) and seed1.color == seed2.color == seed3.color:
                    for seed in (seed1, seed2, seed3):
                        # seed.free()
                        seeds.add(seed)
                    # Extend to a 4-match...
                    if seed4 and seed3.color == seed4.color:
                        # seed4.free()
                        seeds.add(seed4)
                        # Extend to a 5-match...
                        if seed5 and seed4.color == seed5.color:
                            # seed5.free()
                            seeds.add(seed5)
                
                # Match RIGHT along a row
                seed2 = GRID.get((x + 1, y))
                seed3 = GRID.get((x + 2, y))
                seed4 = GRID.get((x + 3, y))
                seed5 = GRID.get((x + 4, y))
                # Find a simple 3-match
                if all((seed1, seed2, seed3)) and seed1.color == seed2.color == seed3.color:
                    for seed in (seed1, seed2, seed3):
                        # seed.free()
                        seeds.add(seed)
                    # Extend to a 4-match...
                    if seed4 and seed3.color == seed4.color:
                        # seed4.free()
                        seeds.add(seed4)
                        # Extend to a 5-match...
                        if seed5 and seed4.color == seed5.color:
                            # seed5.free()
                            seeds.add(seed5)

        if seeds:
            delay = 0.5
            for seed in seeds:
                seed.free()
                tweener.tween(seed, 'position', ppb.Vector(5, 0), 0.25 + random()*0.5, easing=out_quad, delay=1.0 - delay)
                tweener.tween(seed, 'size', 0, 0.25 + random()*0.5, easing=in_quad, delay=1.0 - delay)
                delay *= 0.5

            signal(MovementStart(self.scene))
            @tweener.when_done
            def on_tweening_done():
                tweener = Tweener()
                self.scene.add(tweener)
                # for seed in seeds:
                #     seed.free()
                    # signal(CellEmptied(seed, seed.x, seed.y))

                for x in range(-2, 3):

                    # Collect all the seeds in a column and drop them
                    column = []
                    for y in range(-2, 3):
                        seed = GRID.get(x, y)
                        if seed:
                            column.append(seed)
                    if len(column) < 5:
                        gap = 0
                        for y in range(-2, 3):
                            if (x, y) not in GRID:
                                gap += 1
                                # print("gap", x, y)
                            else:
                                if gap > 0:
                                    seed = GRID[x, y]
                                    del GRID[x, y]
                                    seed.y -= gap
                                    # gap = 0
                                    # xassert (seed.x, seed.y) in GRID, (seed.x, seed.y)
                                    GRID[seed.x, seed.y] = seed
                                    tweener.tween(seed, 'position', seed.position + ppb.Vector(0, 0.25), 0.25)
                                    tweener.tween(seed, 'position', ppb.Vector(seed.x, seed.y), 0.25, delay=0.5)

                    for i in range(gap):
                        if seeds:
                            seed = seeds.pop()
                            seed.drop(self.scene, x, 2 - i)

                TickSystem.call_later(1, lambda: signal(MovementDone(self.scene)))

            tweener.on_tweening_done = on_tweening_done 
            self.scene.add(tweener)


class Player(ppb.sprites.Sprite):
    image = ppb.Image("resources/ANGELA.png")
    size = 4


class Monster(ppb.sprites.Sprite):
    image = ppb.Image("resources/MONSTER_SNAKE.png")
    size = 4
    shake = False

    def on_idle(self, ev, signal):
        if self.shake:
            y = math.sin(time() * 50) / 25
            self.position = ppb.Vector(5, y)
    
    def on_movement_start(self, ev, signal):
        self.shake = True
        def stop():
            self.shake = False
            self.position = ppb.Vector(5, 0)
        TickSystem.call_later(0.5, stop)


def setup(scene):
    for x in range(-2, 3):
        for y in range(-2, 3):
            seed_class = choice(SEEDS)
            seed = seed_class(position=ppb.Vector(x, y))
            scene.add(seed)
            GRID[x, y] = seed
    
    player = Player(position=ppb.Vector(-5, 0))
    scene.add(player)

    snake = Monster(position=ppb.Vector(5, 0))
    scene.add(snake)

    scene.add(Grid())




ppb.run(setup=setup, systems=[
    TickSystem,
])
