from dataclasses import dataclass
from random import choice, random
from time import time

import ppb
from ppb import keycodes
from ppb.events import KeyPressed, KeyReleased
from ppb.systemslib import System


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
SEED_IMAGES = {
    COLOR_GREEN: ppb.Image("resources/seed3.png"),
    COLOR_RED: ppb.Image("resources/seed1.png"),
    COLOR_YELLOW: ppb.Image("resources/seed2.png"),
    COLOR_BLUE: ppb.Image("resources/seed5.png"),
    COLOR_WHITE: ppb.Image("resources/seed4.png"),
}
SEEDS = (
    GreenSeed,
    RedSeed,
    YellowSeed,
    BlueSeed,
    WhiteSeed,
)

GRID = {}


def flerp(f1, f2, t):
    return f1 + t * (f2 - f1)


def vlerp(v1, v2, t):
    return ppb.Vector(
        v1.x + t * (v2.x - v1.x),
        v1.y + t * (v2.y - v1.y),
    )


class Tweener:
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

    def tween(self, entity, attr, end_value, duration):
        assert not self.done
        self.used = True
        start_time = time()
        self.tweens.append(Tween(
            start_time=start_time,
            end_time=start_time + duration,
            obj=entity,
            attr=attr,
            start_value=getattr(entity, attr),
            end_value=end_value,
        ))
    
    def when_done(self, func):
        self.callbacks.append(func)

    def on_idle(self, update, signal):
        t = time()
        clear = []

        for i, tween in enumerate(self.tweens):
            tr = (t - tween.start_time) / (tween.end_time - tween.start_time)
            if isinstance(tween.end_value, ppb.Vector):
                value = vlerp(tween.start_value, tween.end_value, min(1.0, tr))
            else:
                value = flerp(tween.start_value, tween.end_value, min(1.0, tr))
            setattr(tween.obj, tween.attr, value)
            if tr >= 1.0:
                clear.append(i)

        for i in reversed(clear):
            del self.tweens[i]
        
        if self.used and not self.tweens and not self.done:
            self.done = True
            for func in self.callbacks:
                func()


@dataclass
class Tween:
    start_time: float
    end_time: float
    obj: object
    attr: str
    start_value: object
    end_value: object


@dataclass
class MovementDone:
    scene: object


@dataclass
class TweeningDone:
    tweener: Tweener


class TickSystem(System):
    callbacks = []
    tweens = []
    
    @classmethod
    def call_later(self, seconds, func):
        self.callbacks.append((time() + seconds, func))

    @classmethod
    def transition(self, entity, attr, end_value, duration):
        start_time = time()
        self.tweens.append(Tween(
            start_time=start_time,
            end_time=start_time + duration,
            obj=entity,
            attr=attr,
            start_value=getattr(entity, attr),
            end_value=end_value,
        ))

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
        
        clear = []
        for i, tween in enumerate(self.tweens):
            tr = (t - tween.start_time) / (tween.end_time - tween.start_time)
            if isinstance(tween.end_value, ppb.Vector):
                value = vlerp(tween.start_value, tween.end_value, min(1.0, tr))
            else:
                value = flerp(tween.start_value, tween.end_value, min(1.0, tr))
            setattr(tween.obj, tween.attr, value)
            if tr >= 1.0:
                clear.append(i)
        for i in reversed(clear):
            del self.tweens[i]
    
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


class Seed(ppb.BaseSprite):
    position = ppb.Vector(0, 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = int(self.position.x)
        self.y = int(self.position.y)
        self.empty = False


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


@dataclass
class CellEmptied:
    seed: Seed
    x: int
    y: int

@dataclass
class Grid:
    scene: ppb.BaseScene = None
    size: float = 0
    dirty: bool = True

    def __hash__(self):
        return hash(id(self))

    def on_scene_started(self, ev, signal):
        # TODO: Find out if there is a better way to do this
        self.scene = ev.scene
        self.find_matches(signal)

    def on_movement_done(self, ev, signal):
        self.dirty = True
        self.find_matches(signal)

    def on_cell_emptied(self, ev, signal):
        color = choice(COLORS)
        seed = ev.seed
        seed.color = color
        seed.image = SEED_IMAGES[color]
        seed.size = 0.0
        seed.position = ppb.Vector(ev.x, ev.y)
        TickSystem.transition(seed, 'size', 1.0, 0.25)


    def find_matches(self, signal):
        tweener = Tweener()
        seeds = set()
        for x in range(-2, 3):
            for y in range(-2, 3):
                seed1 = GRID.get((x, y))

                seed2 = GRID.get((x, y + 1))
                seed3 = GRID.get((x, y + 2))
                if all((seed1, seed2, seed3)) and seed1.color == seed2.color == seed3.color:
                    for seed in (seed1, seed2, seed3):
                        seeds.add(seed)
                        tweener.tween(seed, 'position', ppb.Vector(5, 0), 0.25 + random()*0.5)
                        tweener.tween(seed, 'size', 0, 0.25 + random()*0.5)

                    self.dirty = True
                
                seed2 = GRID.get((x + 1, y))
                seed3 = GRID.get((x + 2, y))
                if all((seed1, seed2, seed3)) and seed1.color == seed2.color == seed3.color:
                    for seed in (seed1, seed2, seed3):
                        seeds.add(seed)
                        tweener.tween(seed, 'position', ppb.Vector(5, 0), 0.25 + random()*0.5)
                        tweener.tween(seed, 'size', 0, 0.25 + random()*0.5)

                    self.dirty = True
        
        if tweener.is_tweening:
            @tweener.when_done
            def on_tweening_done():
                for seed in seeds:
                    signal(CellEmptied(seed, seed.x, seed.y))
                TickSystem.call_later(1, lambda: signal(MovementDone(self.scene)))

            tweener.on_tweening_done = on_tweening_done 
            self.scene.add(tweener)


class Player(ppb.sprites.Sprite):
    image = ppb.Image("resources/ANGELA.png")
    size = 4


def setup(scene):
    for x in range(-2, 3):
        for y in range(-2, 3):
            seed_class = choice(SEEDS)
            seed = seed_class(position=ppb.Vector(x, y))
            scene.add(seed)
            GRID[x, y] = seed
    
    player = Player(position=ppb.Vector(-5, 0))
    scene.add(player)

    scene.add(ppb.sprites.Sprite(
        position=ppb.Vector(5, 0),
        image=ppb.Image("resources/MONSTER_SNAKE.png"),
        size=4,
    ))

    scene.add(Grid())




ppb.run(setup=setup, systems=[
    TickSystem,
])
