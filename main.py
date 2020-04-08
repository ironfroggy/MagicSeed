from dataclasses import dataclass
import math
from random import choice, random
from time import time
import types

import ppb
from ppb import keycodes
from ppb.events import KeyPressed, KeyReleased
from ppb.systemslib import System

import easing
from tweening import Tweener


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


def dist(v1, v2):
    a = abs(v1.x - v2.x) ** 2
    b = abs(v1.y - v2.y) ** 2
    return math.sqrt(a + b)


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

    def drop(self, t, x, y):
        self.x = x
        self.y = y

        color = choice(COLORS)
        self.color = color
        self.image = SEED_IMAGES[color]
        self.size = 0
        self.position = ppb.Vector(self.x, self.y + 4)

        GRID[x, y] = self

        t.tween(self, 'size', 1.0, 0.25, delay=0.5)
        t.tween(self, 'position', ppb.Vector(self.x, self.y), 1 + random()*0.25, easing='out_bounce')


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
                        seeds.add(seed)
                    # Extend to a 4-match...
                    if seed4 and seed3.color == seed4.color:
                        seeds.add(seed4)
                        # Extend to a 5-match...
                        if seed5 and seed4.color == seed5.color:
                            seeds.add(seed5)
                
                # Match RIGHT along a row
                seed2 = GRID.get((x + 1, y))
                seed3 = GRID.get((x + 2, y))
                seed4 = GRID.get((x + 3, y))
                seed5 = GRID.get((x + 4, y))
                # Find a simple 3-match
                if all((seed1, seed2, seed3)) and seed1.color == seed2.color == seed3.color:
                    for seed in (seed1, seed2, seed3):
                        seeds.add(seed)
                    # Extend to a 4-match...
                    if seed4 and seed3.color == seed4.color:
                        seeds.add(seed4)
                        # Extend to a 5-match...
                        if seed5 and seed4.color == seed5.color:
                            seeds.add(seed5)

        if seeds:
            delay = 0.5
            dest = ppb.Vector(5, 0)
            for seed in seeds:
                seed.free()
                t = 0.1 * dist(seed.position, dest)
                seed.layer = 10
                tweener.tween(seed, 'position', dest, t, easing='out_quad', delay=1.0 - delay)
                tweener.tween(seed, 'size', 0, t, easing='in_quad', delay=1.0 - delay)
                delay *= 0.5

            signal(MovementStart(self.scene))
            @tweener.when_done
            def on_tweening_done():
                for seed in seeds:
                    seed.layer = 1

                tweener = Tweener()
                self.scene.add(tweener)

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
                                    GRID[seed.x, seed.y] = seed
                                    tweener.tween(seed, 'position', ppb.Vector(seed.x, seed.y), 1 + random()*0.25, delay=0.5, easing='out_bounce')

                    for i in range(gap):
                        if seeds:
                            seed = seeds.pop()
                            seed.drop(tweener, x, 2 - i)

                tweener.when_done(lambda: signal(MovementDone(self.scene)))

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
], resolution=(1080, 800))
