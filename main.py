from collections import defaultdict
from dataclasses import dataclass
import math
from random import choice, random, randint
from time import time
import types
from typing import Tuple

import ppb
from ppb import keycodes as k
from ppb.events import KeyPressed, KeyReleased, PlaySound
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
from text import Text
from menu import MenuSystem
import spells

V = ppb.Vector


# Constants

COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_DARKRED = (255, 0, 0)
COLOR_YELLOW = (255, 255, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_VIOLET = (255, 128, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_NEARBLACK = (64, 64, 64)
COLORS = (
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    COLOR_BLUE,
    COLOR_WHITE,
)

SEED_CORRUPTED = -1
SEED_GREEN = 1
SEED_RED = 2
SEED_YELLOW = 3
SEED_BLUE = 4
SEED_VIOLET = 5
SEED_COLORS = {
    SEED_GREEN: COLOR_GREEN,
    SEED_RED: COLOR_RED,
    SEED_YELLOW: COLOR_YELLOW,
    SEED_BLUE: COLOR_BLUE,
    SEED_VIOLET: COLOR_VIOLET,
}

# Images loaded for each color
SEED_IMAGES = {
    SEED_GREEN: ppb.Image("resources/seed3.png"),
    SEED_RED: ppb.Image("resources/seed1.png"),
    SEED_YELLOW: ppb.Image("resources/seed2.png"),
    SEED_BLUE: ppb.Image("resources/seed5.png"),
    SEED_VIOLET: ppb.Image("resources/seed4.png"),
}

SOUND_SWAP = ppb.Sound("resources/sound/swap.wav")
SOUND_CHIME = ppb.Sound("resources/sound/chime1.wav")
SOUND_HURT1 = ppb.Sound("resources/sound/hurt1.wav")
SOUND_HURT2 = ppb.Sound("resources/sound/hurt2.wav")
SOUND_HURT3 = ppb.Sound("resources/sound/hurt3.wav")
SOUND_HURT_SET = (SOUND_HURT1, SOUND_HURT2, SOUND_HURT3)

ENEMIES = [
    {
        "image": ppb.Image("resources/monster_ant.png"),
        "hp": 3,
        "strength": 1,
    },
    {
        "image": ppb.Image("resources/monster_spider.png"),
        "hp": 4,
        "strength": 1,
    },
    {
        "image": ppb.Image("resources/monster_snake.png"),
        "hp": 6,
        "strength": 2,
    },
    {
        "image": ppb.Image("resources/monster_snapblossum.png"),
        "hp": 8,
        "strength": 3,
    },
    {
        "image": ppb.Image("resources/monster_5.png"),
        "hp": 10,
        "strength": 2,
    },
    {
        "image": ppb.Image("resources/monster_6.png"),
        "hp": 10,
        "strength": 3,
    },
    {
        "image": ppb.Image("resources/monster_7.png"),
        "hp": 12,
        "strength": 2,
    },
    {
        "image": ppb.Image("resources/monster_8.png"),
        "hp": 15,
        "strength": 4,
    },
    {
        "image": ppb.Image("resources/monster_9.png"),
        "hp": 20,
        "strength": 5,
        "deathtime": 5.0,
    },
]

POS_PLAYER = V(-7, -1)
POS_ENEMY = V(7, -1)


def dist(v1, v2):
    a = abs(v1.x - v2.x) ** 2
    b = abs(v1.y - v2.y) ** 2
    return math.sqrt(a + b)

def first(iterator):
    return next(iter(iterator))


@dataclass
class Sparkler:
    position: ppb.Vector
    sparkle_timer = None

    def spark(self, color):
        x = -2.0 + random() * 4.0
        y = -2.0 + random() * 4.0
        pos = self.position + V(x, y)
        ParticleSystem.spawn(self.position, color, pos)

    def sparkle(self, seconds, color):
        if self.sparkle_timer:
            self.stop_sparkle()
        self.sparkle_timer = repeat(0.01, lambda: self.spark(color))
        delay(seconds, self.stop_sparkle)
    
    def stop_sparkle(self):
        if self.sparkle_timer:
            cancel(self.sparkle_timer)
            self.sparkle_timer = None

    def burst(self, duration, color, source=None, target=None):
        if target is None:
            tleft, ttop = -2, 2
            tright, tbottom = 2, -2
        elif isinstance(target, ppb.Vector):
            tleft, ttop = target
            tright, tbottom = target
        else:
            tleft, ttop = target[0]
            tright, tbottom = target[1]

        if source is None:
            sleft, stop = 0, 0
            sright, sbottom = 0, 0
        elif isinstance(source, ppb.Vector):
            sleft, stop = source
            sright, sbottom = source
        else:
            sleft, stop = source[0]
            sright, sbottom = source[1]

        step = duration / 100
        for i in range(int(100 * duration)):
            tx = tleft + random() * (tright - tleft)
            ty = tbottom + random() * (ttop - tbottom)
            sx = sleft + random() * (sright - sleft)
            sy = sbottom + random() * (stop - sbottom)
            spos = self.position + V(sx, sy)
            tpos = self.position + V(tx, ty)
            delay(i * step, lambda spos=spos, tpos=tpos: ParticleSystem.spawn(spos, color, tpos))


class Seed(ppb.BaseSprite):
    position = V(0, 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = int(self.position.x)
        self.y = int(self.position.y)
        self.is_corrupt = False
        self.is_free = False
        self.color = COLOR_WHITE
        self.sparkle_timer = None
    
    def on_hover_seed(self, ev, signal):
        if not ev.grid.frozen and self.x == ev.x and self.y == ev.y:
            if not self.is_corrupt:
                self.size = 1.1
            else:
                self.size = 0.9
        else:
            if not self.is_corrupt:
                self.size = 1.0
            else:
                self.size = 0.8
    
    def on_seed_corruption(self, ev, signal):
        if self.x == ev.x and self.y == ev.y:
            if not self.is_corrupt:
                self.is_corrupt = True
                tween(self, 'color', COLOR_NEARBLACK, 1.0, easing='out_quad')
                tween(self, 'size', 0.8, 1.0, easing='out_quad')
                self.sparkle(1.0, rate=0.1)
                delay(1.0, lambda: signal(SeedCorruptionComplete()))
    
    @property
    def seed_type(self):
        if self.is_corrupt:
            return -1
        else:
            return self.seed_color
    
    def free(self):
        """Remove the seed from the grid."""
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

        self.color = COLOR_WHITE
        self.is_corrupt = False
        self.seed_color = choice(list(SEED_COLORS.keys()))
        self.image = SEED_IMAGES[self.seed_color]
        self.size = 0.0
        self.position = V(self.x, self.y + 4)

        GRID[x, y] = self

        t.tween(self, 'size', 1.0, 0.25, delay=0.5)
        t.tween(self, 'position', V(self.x, self.y), 1 + random()*0.25, easing='out_bounce')

    def spark(self):
        if self.is_corrupt:
            color = COLOR_BLACK
            ParticleSystem.spawn(self.position, color, tsize=1.0)
        else:
            color = SEED_COLORS[self.seed_color]
            ParticleSystem.spawn(self.position, color)

    def sparkle(self, seconds, rate=0.01):
        self.stop_sparkle()
        self.sparkle_timer = repeat(rate, self.spark)
        delay(seconds, self.stop_sparkle)
    
    def stop_sparkle(self):
        if self.sparkle_timer:
            cancel(self.sparkle_timer)
            self.sparkle_timer = None


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
    kwargs['seed_color'] = SEED_VIOLET
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


# TODO: Simplify this
_chime_playing = False
def chime(t, signal):
    global _chime_playing
    if not _chime_playing:
        signal(PlaySound(SOUND_CHIME))
        SOUND_CHIME.volume = 6.0
        tween(SOUND_CHIME, 'volume', 0.0, t, easing='out_quad')
        _chime_playing = True
        def done():
            global _chime_playing
            _chime_playing = False
        delay(t, done)


class TickSystem(System):
    callbacks = []
    game_started = False
    
    @classmethod
    def call_later(self, seconds, func):
        self.callbacks.append((time() + seconds, func))
    
    @classmethod
    def on_start_game(cls, ev, signal):
        cls.callbacks = []
        cls.game_started = True
    
    @classmethod
    def on_player_death(cls, ev, signal):
        cls.game_started = False

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
    
    @classmethod
    def on_key_released(cls, ev, signal):
        if ev.key == k.Escape:
            signal(ToggleMenu())


@dataclass
class GridCellMissing(Exception):
    x: int
    y: int

@dataclass
class GridCellOutOfBounds(Exception):
    x: int
    y: int


@dataclass
class Grid:
    scene: ppb.BaseScene = None
    size: float = 0
    frozen: bool = True
    seed_held: bool = False

    def __hash__(self):
        return hash(id(self))
    
    def get(self, x, y, *args):
        if x < -2 or x > 2 or y < -2 or y > 2:
            if args:
                return args[0]
            else:
                raise GridCellOutOfBounds(x, y)
        try:
            return GRID[(x, y)]
        except KeyError:
            if args:
                return args[0]
            raise GridCellMissing(x, y)
    
    def send_seed_corrupt(self, signal):
        if not self.frozen:
            signal(SeedCorruption(randint(-2, 2), randint(-2, 2)))
    
    def on_start_game(self, ev, signal):
        self.frozen = False
        t = Tweener()
        ev.scene.add(t)
        for x in range(-2, 3):
            for y in range(-2, 3):
                seed = GRID[x, y]
                seed.drop(t, x, y)
        t.when_done(lambda: self.find_matches(signal))

    def on_scene_started(self, ev, signal):
        self.scene = ev.scene
        repeat(3, lambda: self.send_seed_corrupt(signal))
    
    def on_movement_start(self, ev, signal):
        self.frozen = True
        self.waiting_for_movement = True

    def on_movement_done(self, ev, signal):
        if self.waiting_for_movement:
            self.waiting_for_movement = False
            self.frozen = False
            if not self.seed_held:
                self.find_matches(signal)
    
    def on_seed_held(self, ev, signal):
        self.seed_held = True

    def on_seed_released(self, ev, signal):
        self.seed_held = False
        if not self.frozen:
            self.find_matches(signal)

    def on_seed_corruption_complete(self, ev, signal):
        if not self.frozen and not self.seed_held:
            self.find_matches(signal)
    
    def on_monster_death(self, ev, signal):
        self.frozen = True
    
    def on_monster_spawn(self, evn, signal):
        self.frozen = False

    def on_open_menu(self, ev, signal):
        self.frozen = True
    
    def on_close_menu(self, evn, signal):
        self.frozen = False

    last_click = (0, 0)
    last_seed = None

    def on_button_pressed(self, ev, signal):
        if self.frozen:
            return

        x = round(ev.position.x)
        y = round(ev.position.y)

        self.last_click = (x, y)
        self.last_seed = self.get(x, y, None)

        signal(SeedHeld())
    
    def on_mouse_motion(self, ev, signal):
        if self.last_seed:
            self.last_seed.position = ev.position
        else:
            x = round(ev.position.x)
            y = round(ev.position.y)
            signal(HoverSeed(self, x, y))


    def on_button_released(self, ev, signal):
        if self.frozen or not self.last_click:
            return

        signal(SeedReleased())

        x = round(ev.position.x)
        y = round(ev.position.y)
        lx, ly = self.last_click

        if x == lx and y != ly:
            if ly - 2 == y:
                y += 1
            elif ly + 2 == y:
                y -= 1
        elif y == ly and x != lx:
            if lx - 2 == x:
                x += 1
            elif lx + 2 == x:
                x -= 1

        missed = False
        if (x, y) not in GRID:
            missed = True
        if (lx, ly) not in GRID:
            missed = True

        tweener = Tweener()
        nx = abs(lx-x) == 1
        ny = abs(ly-y) == 1
        if not missed and (nx or ny) and not (nx and ny):
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

            signal(PlaySound(SOUND_SWAP))
            signal(MovementStart())
        elif self.last_seed:
            tweener.tween(self.last_seed, 'position', V(lx, ly), 0.25, easing='out_quad')

        if tweener.is_tweening:
            @tweener.when_done
            def on_tweening_done():
                signal(MovementDone())
            ev.scene.add(tweener)
        
        self.last_click = None
        self.last_seed = None
    
    def find_one_match(self, x, y):
        seeds = set()
        points = 0

        # Row and column matching starts with the same seed1
        seed1 = self.get(x, y)

        # Match UP along a column
        seed2 = self.get(x, y + 1, None)
        seed3 = self.get(x, y + 2, None)
        seed4 = self.get(x, y + 3, None)
        seed5 = self.get(x, y + 4, None)

        # Find a simple 3-match
        if all((seed1, seed2, seed3)) and seed1.seed_type == seed2.seed_type == seed3.seed_type:
            for seed in (seed1, seed2, seed3):
                seeds.add(seed)
            points += 250
            # Extend to a 4-match...
            if seed4 and seed3.seed_type == seed4.seed_type:
                seeds.add(seed4)
                points += 250 # 500 total for match
                # Extend to a 5-match...
                if seed5 and seed4.seed_type == seed5.seed_type:
                    seeds.add(seed5)
                    points += 500 # 1000 total for match

        # Match RIGHT along a row
        seed2 = self.get(x + 1, y, None)
        seed3 = self.get(x + 2, y, None)
        seed4 = self.get(x + 3, y, None)
        seed5 = self.get(x + 4, y, None)

        # Find a simple 3-match
        if all((seed1, seed2, seed3)) and seed1.seed_type == seed2.seed_type == seed3.seed_type:
            for seed in (seed1, seed2, seed3):
                seeds.add(seed)
            points += 250
            # Extend to a 4-match...
            if seed4 and seed3.seed_type == seed4.seed_type:
                seeds.add(seed4)
                points += 250
                # Extend to a 5-match...
                if seed5 and seed4.seed_type == seed5.seed_type:
                    seeds.add(seed5)
                    points += 500
        
        return seeds, points

    def find_matches(self, signal):
        if self.frozen:
            return

        tweener = Tweener()
        seeds = set()
        colors = defaultdict(int)
        points = 0

        # [-2, -1, =0, +1, +2]
        # Only need to loop to 0's because we look at at least the next two to make 3-matches
        for x in range(-2, 3):
            for y in range(-2, 3):

                try:
                    match_seeds, match_points = self.find_one_match(x, y)
                except GridCellOutOfBounds:
                    continue
                except GridCellMissing:
                    # A cell was missing, so something is in motion, stop looking for matches...
                    return
                else:
                    if match_seeds:
                        points += match_points
                        seeds.update(match_seeds)

        # END grid loop   
        signal(ScorePoints(points))

        if seeds:
            # Add up the matched seeds for each color and animate them accordingly
            d = 0.5
            # Calculate damage and spell effects
            dmg = 0
            shield = 0
            heal = 0
            corruption = 0
            for seed in seeds:
                attack = False
                colors[seed.seed_type] += 1
                if seed.seed_type == SEED_GREEN:
                    dest = POS_PLAYER
                    heal += 1
                elif seed.seed_type == SEED_YELLOW:
                    dest = POS_PLAYER
                    shield += 1
                elif seed.seed_type == SEED_CORRUPTED:
                    dest = POS_ENEMY
                    corruption += 1
                else:
                    dest = POS_ENEMY
                    dmg += 1
                    attack = True
                    
                t = 0.1 * dist(seed.position, dest)

                seed.free()
                seed.layer = 10

                delay((1.0 - d), lambda seed=seed: seed.sparkle(t))
                tweener.tween(seed, 'size', 1.1, 0.1, easing='out_quad', delay=1.0 - d - 0.1)
                tweener.tween(seed, 'position', dest, t, easing='out_quad', delay=1.0 - d)
                tweener.tween(seed, 'size', 0.0, t, easing='in_quad', delay=1.0 - d)

                if attack:
                    delay(t + (1.0 - d), lambda: signal(DamageDealt('monster', 1)))

                d *= 0.5

            signal(MovementStart(colors))

            def _():
                chime(t + 1.0 - d, signal)
            delay(d, _)

            def _():
                enemy = first(self.scene.get(tag='enemy'))

                if corruption:
                    enemy.sparkler.burst(1, COLOR_BLACK,
                        source=(V(-2, -2), V(2, 2)),
                        target=V(0, 0),
                    )
                    delay(1, lambda: signal(EnemyAttack(enemy, corruption)))

                if dmg:
                    # signal(DamageDealt('monster', dmg))
                    i = choice([c for c in colors if c >= 0])
                    enemy.sparkler.burst(0.25, SEED_COLORS[i])

                if heal:
                    player = first(self.scene.get(tag='player'))
                    player.sparkler.burst(2.0, COLOR_GREEN,
                        source=V(0, -1.25),
                        target=(V(-1, 1.5), V(1, 1)),
                    )
                    spells.heal(2.0, player, 4)
                
                if shield:
                    player = first(self.scene.get(tag='player'))
                    player.sparkler.burst(3.0, COLOR_YELLOW,
                        source=V(2, 0),
                        target=(V(2, 2.5), V(2, -2.5)),
                    )
                    spells.shield(3.0, player, 6)

            delay(1.0-d+t, _)

            @tweener.when_done
            def on_tweening_done():
                for seed in seeds:
                    seed.layer = 1

                tweener = Tweener()
                self.scene.add(tweener)

                # Drop new seeds at the top of each column with gaps
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

                    # Add new seeds at the top
                    for i in range(gap):
                        if seeds:
                            seed = seeds.pop()
                            seed.drop(tweener, x, 2 - i)

                tweener.when_done(lambda: signal(MovementDone()))

            tweener.on_tweening_done = on_tweening_done 
            self.scene.add(tweener)


class Player(ppb.sprites.Sprite):
    image = ppb.Image("resources/ANGELA.png")
    size = 4.0

    @property
    def hp(self):
        return self._hp
    
    @hp.setter
    def hp(self, value):
        value = min(10, value)
        self._hp = value
        self.hp_text.text = str(value)
        self.hp_bar.set_value(value)
    
    @property
    def shield(self):
        return self._shield
    
    @shield.setter
    def shield(self, value):
        value = min(10, value)
        self._shield = value
        self.shield_bar.set_value(value)
    
    def on_start_game(self, ev, signal):
        self.hp = 10

    def on_scene_started(self, ev, signal):
        self.hp_text = Text('', self.position + V(0, -3))
        self.hp_text.scene = ev.scene
        self.hp_text.setup()
        ev.scene.add(self.hp_text)

        self.hp_bar = Bar(
            color=COLOR_DARKRED,
            scene=ev.scene,
            position=V(self.position + V(0, -3.5)),
        )
        ev.scene.add(self.hp_bar)

        self.shield_bar = Bar(
            color=COLOR_YELLOW,
            scene=ev.scene,
            position=V(self.position + V(0, -4.0)),
            value=0,
        )
        ev.scene.add(self.shield_bar)

        self.hp = 10
        self.shield = 0

        self.sparkler = Sparkler(self.position)
    
    def on_player_death(self, ev, signal):
        pass

    def on_damage_dealt(self, ev, signal):
        if ev.target == 'player':
            self.shield -= ev.dmg
            if self.shield < 0:
                self.hp += self.shield
                self.shield = 0
                if self.hp < 0:
                    self.hp = 0

                if self.hp <= 0:
                    signal(PlayerDeath(self))
                else:
                    tween(self, 'position', self.position - V(1, 0), 0.1, easing='in_quad')
                    tween(self, 'position', self.position, 0.2, delay=0.1, easing='out_quad')
                    signal(PlaySound(choice(SOUND_HURT_SET)))


class Monster(ppb.sprites.Sprite):
    image = ENEMIES[0]['image']
    size = 4.0
    shake = False
    next_attack = float('inf')
    opacity = 255

    @property
    def hp(self):
        return self._hp
    
    @hp.setter
    def hp(self, value):
        value = max(0, value)
        self._hp = value
        self.hp_text.text = str(value)
        self.hp_bar.set_value(value)
    
    def plan_attack(self):
        pass
        # self.next_attack = time() + randint(3, 6)
    
    def on_enemy_attack(self, ev, signal):
        if self.hp:
            self.attack(self.strength + ev.dmg, signal)
    
    def attack(self, dmg, signal):
        tween(self, 'position', self.position - V(1, 0), 0.1, easing='in_quad')
        tween(self, 'position', self.position, 0.1, delay=0.1, easing='out_quad')
        delay(0.1, lambda: signal(DamageDealt('player', dmg)))
        self.plan_attack()
    
    def on_start_game(self, ev, signal):
        self.hp = ENEMIES[0]["hp"]
        self.hp_bar.set_max(self.hp)
        self.strength = ENEMIES[0]["strength"]
        self.plan_attack()

    def on_idle(self, ev, signal):
        if self.shake:
            px, py = POS_ENEMY
            y = math.sin(time() * 50) / 25
            self.position = V(px, py + y)
        elif self.next_attack <= time():
            self.attack(signal)
    
    def on_movement_start(self, ev, signal):
        def deal_damage():
            # self.shake = True
            def stop():
                self.shake = False
                self.position = POS_ENEMY

            TickSystem.call_later(0.5, stop)
        TickSystem.call_later(1, deal_damage)

    def on_scene_started(self, ev, signal):
        self.hp_text = Text('', self.position + V(0, -3))
        self.hp_text.scene = ev.scene
        self.hp_text.setup()

        ev.scene.add(self.hp_text)

        self.hp_bar = Bar(
            color=COLOR_DARKRED,
            scene=ev.scene,
            position=V(self.position + V(0, -3.5)),
        )
        ev.scene.add(self.hp_bar)

        self.sparkler = Sparkler(self.position)

    def on_damage_dealt(self, ev, signal):
        if ev.target == 'monster' and self.hp:
            tween(self, 'position', self.position + V(0.25, 0), 0.1, easing='in_quad')
            tween(self, 'position', self.position, 0.1, delay=0.1, easing='out_quad')
            self.hp -= ev.dmg

            if self.hp <= 0:
                signal(MonsterDeath(self))
            else:
                self.plan_attack()


class MonsterManager(System):

    def on_scene_started(self, ev, signal):
        self.monster_index = 0
        self.danger = 1.0

    def on_monster_death(self, ev, signal):
        t = ENEMIES[self.monster_index].get('deathtime', 2.0)
        tween(ev.monster, 'size', ev.monster.size * 0.75, t, easing='in_quad')
        tween(ev.monster, 'opacity', 0, t, easing='out_bounce')

        delay(t, lambda: signal(MonsterSpawn(ev.monster)))
    
    def on_monster_spawn(self, ev, signal):
        self.monster_index += 1
        if self.monster_index >= len(ENEMIES):
            self.monster_index = 0
            self.danger += 0.1

        ev.monster.image = ENEMIES[self.monster_index]['image']
        ev.monster.hp = int(ENEMIES[self.monster_index]['hp'] * self.danger)
        ev.monster.hp_bar.max = ev.monster.hp
        ev.monster.strength = int(ENEMIES[self.monster_index]['strength'] * self.danger)

        ev.monster.position = POS_ENEMY + V(4, 0)
        ev.monster.opacity = 255
        ev.monster.size = 4.0

        tween(ev.monster, 'position', POS_ENEMY, 1.0)


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
    opacity_mode = 'add'
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
            s.size = 0
            ev.scene.add(s)
            cls.sparkles.append(s)

    @classmethod
    def spawn(cls, pos, color, heading=None, tsize=2.5):
        s = cls.sparkles[cls.index]
        cls.index = (cls.index + 1) % cls.size
        if color == COLOR_BLACK:
            s.opacity_mode = 'blend'
            s.opacity = 255
        else:
            s.opacity_mode = 'add'
            s.opacity = 128
        s.color = color
        s.position = pos
        s.rotation = randint(0, 260)
        s.size = 1.5
        s.layer = 100
        cls.t.tween(s, 'opacity', 0, 0.5, easing='linear')
        cls.t.tween(s, 'size', tsize, 0.5, easing='linear')
        delay(0.5, lambda: setattr(s, 'size', 0))
        if heading:
            cls.t.tween(s, 'position', heading, 0.5, easing='linear')


@dataclass
class ScorePoints:
    points: int


class ScoreBoard(System):
    
    @classmethod
    def on_scene_started(cls, ev, signal):
        cls.score = 0
        cls.text = Text(str(cls.score), V(0, 4))
        ev.scene.add(cls.text)
    
    @classmethod
    def on_score_points(cls, ev, signal):
        cls.score += ev.points
        cls.text.text = str(cls.score)


@dataclass
class Bar:
    color: Tuple[int]
    position: ppb.Vector
    value: int = 10
    max: int = 10
    size: int = 0
    bg: ppb.Sprite = None
    segments: Tuple[ppb.Sprite] = ()

    BAR_BG = ppb.Image("resources/BAR_BG.png")
    BAR_SEGMENT = ppb.Image("resources/BAR_SEGMENT.png")

    def __hash__(self):
        return hash(id(self))

    def __init__(self, scene, **kwargs):
        super().__init__()
        self.__dict__.update(kwargs)
        self.bg = ppb.Sprite(
            position=self.position,
            image=self.BAR_BG,
            size=1/4,
            layer=50,
        )
        scene.add(self.bg)

        segments = []
        for i in range(16):
            segment = ppb.Sprite(
                position=self.position + V(i/4 - 2, 0),
                image=self.BAR_SEGMENT,
                color=self.color,
                size=1/4,
                layer=51,
            )
            segments.append(segment)
            scene.add(segment)
        self.segments = tuple(segments)

        self.set_value(10)
    
    def set_max(self, new_max):
        self.max = new_max
        self.set_value(self.value)
    
    def set_value(self, value):
        self.value = value
        if value == 0:
            p = 0
        else:
            p = int(value / self.max * 16)
        for i, segment in enumerate(self.segments):
            if i >= p:
                segment.size = 0
            else:
                segment.size = 1/4


def setup(scene):
    for x in range(-2, 3):
        for y in range(-2, 3):
            seed_class = choice(SEEDS)
            seed = seed_class(position=V(x, y))
            scene.add(seed)
            GRID[x, y] = seed
    
    player = Player(position=POS_PLAYER)
    scene.add(player, tags=['player', 'character'])

    snake = Monster(position=POS_ENEMY)
    scene.add(snake, tags=['enemy', 'character'])

    scene.add(Grid(), tags=['grid', 'manager'])

    scene.add(ppb.Sprite(
        image=ppb.Image("resources/BACKGROUND.png"),
        size=12,
        layer=-1,
    ), tags=['bg'])


ppb.run(
    setup=setup,
    basic_systems=(CustomRenderer, Updater, EventPoller, SoundController, AssetLoadingSystem),
    systems=[
        TickSystem,
        MenuSystem,
        MonsterManager,
        TweenSystem,
        Timers,
        ParticleSystem,
        ScoreBoard,
    ],
    resolution=(1280, 720),
    window_title='✨Seed Magic✨',
    target_frame_rate=60,
)
