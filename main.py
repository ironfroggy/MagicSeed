from collections import defaultdict
from dataclasses import dataclass
import math
from random import choice, random, randint
from time import time
import types

import ppb
from ppb import keycodes
from ppb.events import KeyPressed, KeyReleased
from ppb.systemslib import System
from ppb.assetlib import AssetLoadingSystem
from ppb.systems import EventPoller
from ppb.systems import SoundController
from ppb.systems import Updater

import easing
from events import *
from timer import Timers, delay, repeat, cancel
from tweening import Tweener, TweenSystem, tween
from renderer import CustomRenderer


# Constants

COLOR_GREEN = (128, 255, 128)
COLOR_RED = (255, 128, 128)
COLOR_YELLOW = (255, 255, 128)
COLOR_BLUE = (128, 128, 255)
COLOR_WHITE = (255, 128, 255)
COLORS = (
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    COLOR_BLUE,
    COLOR_WHITE,
)

SEED_GREEN = 1
SEED_RED = 2
SEED_YELLOW = 3
SEED_BLUE = 4
SEED_WHITE = 5
SEED_COLORS = {
    SEED_GREEN: COLOR_GREEN,
    SEED_RED: COLOR_RED,
    SEED_YELLOW: COLOR_YELLOW,
    SEED_BLUE: COLOR_BLUE,
    SEED_WHITE: COLOR_WHITE,
}

# Images loaded for each color
SEED_IMAGES = {
    SEED_GREEN: ppb.Image("resources/seed3.png"),
    SEED_RED: ppb.Image("resources/seed1.png"),
    SEED_YELLOW: ppb.Image("resources/seed2.png"),
    SEED_BLUE: ppb.Image("resources/seed5.png"),
    SEED_WHITE: ppb.Image("resources/seed4.png"),
}

V = ppb.Vector


def dist(v1, v2):
    a = abs(v1.x - v2.x) ** 2
    b = abs(v1.y - v2.y) ** 2
    return math.sqrt(a + b)


class Seed(ppb.BaseSprite):
    position = V(0, 0)

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

        color = choice(list(SEED_COLORS.keys()))
        self.seed_color = color
        self.image = SEED_IMAGES[color]
        self.size = 0.0
        self.position = V(self.x, self.y + 4)

        GRID[x, y] = self

        t.tween(self, 'size', 1.0, 0.25, delay=0.5)
        t.tween(self, 'position', V(self.x, self.y), 1 + random()*0.25, easing='out_bounce')

    def spark(self):
        color = SEED_COLORS[self.seed_color]
        ParticleSystem.spawn(self.position, color)

    def sparkle(self, seconds):
        self.sparkle_timer = repeat(0.05, self.spark)
        delay(seconds, self.stop_sparkle)
    
    def stop_sparkle(self):
        cancel(self.sparkle_timer)
    
    def burst(self, color, center):
        color = SEED_COLORS[color]
        for _ in range(10):
            x = -1.0 + random() * 2.0
            y = -1.0 + random() * 2.0
            pos = center + V(x, y)
            ParticleSystem.spawn(pos, color, pos)


def GreenSeed(*args, **kwargs):
    kwargs['seed_color'] = SEED_GREEN
    kwargs['image'] = SEED_IMAGES[kwargs['seed_color']]
    return Seed(*args, **kwargs)

def RedSeed(*args, **kwargs):
    kwargs['seed_color'] = SEED_RED
    kwargs['image'] = SEED_IMAGES[kwargs['seed_color']]
    return Seed(*args, **kwargs)

def YellowSeed(*args, **kwargs):
    kwargs['seed_color'] = SEED_YELLOW
    kwargs['image'] = SEED_IMAGES[kwargs['seed_color']]
    return Seed(*args, **kwargs)

def BlueSeed(*args, **kwargs):
    kwargs['seed_color'] = SEED_BLUE
    kwargs['image'] = SEED_IMAGES[kwargs['seed_color']]
    return Seed(*args, **kwargs)

def WhiteSeed(*args, **kwargs):
    kwargs['seed_color'] = SEED_WHITE
    kwargs['image'] = SEED_IMAGES[kwargs['seed_color']]
    return Seed(*args, **kwargs)


SEEDS = (
    GreenSeed,
    RedSeed,
    YellowSeed,
    BlueSeed,
    WhiteSeed,
)

GRID = {}


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
                tweener.tween(seed1, 'position', V(lx, ly), 0.25)
                tweener.tween(seed2, 'position', V(x, y), 0.25)
        
        if tweener.is_tweening:
            @tweener.when_done
            def on_tweening_done():
                signal(MovementDone(press_event.scene))
            press_event.scene.add(tweener)

        if self.last_click == None:
            self.last_click = (x, y)
        else:
            self.last_click = None     


@dataclass
class Grid:
    scene: ppb.BaseScene = None
    size: float = 0

    def __hash__(self):
        return hash(id(self))

    def on_scene_started(self, ev, signal):
        print(1)
        # TODO: Find out if there is a better way to do this
        self.scene = ev.scene
        self.find_matches(signal)

    def on_movement_done(self, ev, signal):
        self.find_matches(signal)

    def find_matches(self, signal):
        tweener = Tweener()
        seeds = set()
        colors = defaultdict(int)

        for x in range(-2, 3):
            for y in range(-2, 3):
                seed1 = GRID.get((x, y))

                # Match UP along a column
                seed2 = GRID.get((x, y + 1))
                seed3 = GRID.get((x, y + 2))
                seed4 = GRID.get((x, y + 3))
                seed5 = GRID.get((x, y + 4))
                # Find a simple 3-match
                if all((seed1, seed2, seed3)) and seed1.seed_color == seed2.seed_color == seed3.seed_color:
                    for seed in (seed1, seed2, seed3):
                        seeds.add(seed)
                    # Extend to a 4-match...
                    if seed4 and seed3.seed_color == seed4.seed_color:
                        seeds.add(seed4)
                        # Extend to a 5-match...
                        if seed5 and seed4.seed_color == seed5.seed_color:
                            seeds.add(seed5)

                    colors[seed1.seed_color] += 1
                
                # Match RIGHT along a row
                seed2 = GRID.get((x + 1, y))
                seed3 = GRID.get((x + 2, y))
                seed4 = GRID.get((x + 3, y))
                seed5 = GRID.get((x + 4, y))
                # Find a simple 3-match
                if all((seed1, seed2, seed3)) and seed1.seed_color == seed2.seed_color == seed3.seed_color:
                    for seed in (seed1, seed2, seed3):
                        seeds.add(seed)
                    # Extend to a 4-match...
                    if seed4 and seed3.seed_color == seed4.seed_color:
                        seeds.add(seed4)
                        # Extend to a 5-match...
                        if seed5 and seed4.seed_color == seed5.seed_color:
                            seeds.add(seed5)
                    
                    colors[seed1.seed_color] += 1

        if seeds:
            d = 0.5
            dest = V(5, 0)
            for seed in seeds:
                seed.free()
                t = 0.1 * dist(seed.position, dest)
                seed.layer = 10
                delay((1.0 - d), lambda seed=seed: seed.sparkle(t))
                tweener.tween(seed, 'position', dest, t, easing='out_quad', delay=1.0 - d)
                tweener.tween(seed, 'size', 0.0, t, easing='in_quad', delay=1.0 - d)
                delay(1.0-d+t, lambda seed=seed, color=seed.seed_color: seed.burst(color, dest))

                d *= 0.9

            signal(MovementStart(self.scene, colors))

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
    size = 4.0


class Monster(ppb.sprites.Sprite):
    image = ppb.Image("resources/MONSTER_SNAKE.png")
    size = 4.0
    shake = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hp = 10

    def on_idle(self, ev, signal):
        if self.shake:
            y = math.sin(time() * 50) / 25
            self.position = V(5, y)
    
    def on_movement_start(self, ev, signal):
        def deal_damage():
            dmg = sum(ev.colors.values())
            self.hp -= dmg
            if self.hp <= 0:
                signal(MonsterDeath(self))
            else:
                self.shake = True
                def stop():
                    self.shake = False
                    self.position = V(5, 0)

                TickSystem.call_later(0.5, stop)
        TickSystem.call_later(1, deal_damage)


class MonsterManager(System):
    # def on_scene_started(self, ev, signal):
    #     self.scene = ev.scene

    def on_monster_death(self, ev, signal):
        # t = Tweener()
        # self.scene.add(t)
        tween(ev.monster, 'position', V(5, -8), 1.0, easing='in_quad')
        tween(ev.monster, 'position', V(5, 0), 1.0, delay=1, easing='out_quad')
        ev.monster.hp = 10


def proxy_method(attr, name):
    def _(self, *args, **kwargs):
        obj = getattr(self, attr)
        return getattr(obj, name)(*args, **kwargs)
    _.__name__ = name
    return _


class EffectedImage:
    def __init__(self, image, opacity=255):
        self.image = image
        self.opacity = opacity

    load = proxy_method('image', 'load')


class Particle(ppb.sprites.Sprite):
    base_image = ppb.Image("resources/sparkle1.png")
    opacity = 128
    color = COLOR_WHITE
    size = 2
    rotation = 0

    def __init__(self, *args, **kwargs):
        self.color = kwargs.pop('color', COLOR_WHITE)
        super().__init__(*args, **kwargs)
        self.image = EffectedImage(self.base_image, opacity=128)


class ParticleSystem(System):
    sparkles = []
    index = 0
    size = 100

    @classmethod
    def on_scene_started(cls, ev, signal):
        t = Tweener()
        cls.t = t
        ev.scene.add(t)

        for _ in range(cls.size):
            position = V(random()*12 - 6, random()*12 - 6)
            s = Particle(position=position)
            s.opacity = 0
            ev.scene.add(s)
            cls.sparkles.append(s)

    @classmethod
    def spawn(cls, pos, color, heading=None):
        s = cls.sparkles[cls.index]
        cls.index = (cls.index + 1) % cls.size
        s.color = color
        s.position = pos
        s.opacity = 128
        s.rotation = randint(0, 260)
        s.size = 1.5
        s.layer = 100
        cls.t.tween(s, 'opacity', 0, 0.5, easing='linear')
        cls.t.tween(s, 'size', 2.5, 0.5, easing='linear')
        if heading:
            cls.t.tween(s, 'position', heading, 0.5, easing='linear')


def setup(scene):
    for x in range(-2, 3):
        for y in range(-2, 3):
            seed_class = choice(SEEDS)
            seed = seed_class(position=V(x, y))
            scene.add(seed)
            GRID[x, y] = seed
    
    player = Player(position=V(-5, 0))
    scene.add(player)

    snake = Monster(position=V(5, 0))
    scene.add(snake)

    scene.add(Grid())


ppb.run(
    setup=setup,
    basic_systems=(CustomRenderer, Updater, EventPoller, SoundController, AssetLoadingSystem),
    systems=[
        TickSystem,
        MonsterManager,
        TweenSystem,
        Timers,
        ParticleSystem,
    ],
    resolution=(1080, 800),
)
