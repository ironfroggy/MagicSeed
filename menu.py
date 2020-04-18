import ppb
from ppb.events import Quit
from ppb.assets import Square
from ppb.systemslib import System

from events import *
from text import Text
from tweening import tween

V = ppb.Vector

MENU_LAYER = 1000

class MenuSystem(System):
    menu_active = True

    def on_start_game(self, ev, signal):
        tween(self.bg, 'size', 0.0, 1, easing='in_quad')
        tween(self.opt_start, 'size', 0.0, 1, easing='in_quad')
        tween(self.opt_quit, 'size', 0.0, 1, easing='in_quad')
        tween(self.title, 'size', 0.0, 1, easing='in_quad')

        self.menu_active = False
    
    def on_player_death(self, ev, signal):
        tween(self.bg, 'size', 8.0, 1, easing='out_bounce')
        tween(self.opt_start, 'size', 2.0, 1, easing='out_bounce')
        tween(self.opt_quit, 'size', 2.0, 1, easing='out_bounce')
        tween(self.title, 'size', 2.0, 1, easing='out_bounce')

        self.menu_active = True

    def on_scene_started(self, ev, signal):

        G = 32
        self.bg = ppb.Sprite(
            image=Square(G, G, G),
            size=8,
            layer=MENU_LAYER,
            opacity=225,
        )
        ev.scene.add(self.bg)

        self.title = Text('Seed Magic', V(0, 2), layer=MENU_LAYER + 1)
        ev.scene.add(self.title)

        self.opt_start = Text('start', V(0, -1), layer=MENU_LAYER + 1)
        ev.scene.add(self.opt_start)

        self.opt_quit = Text('quit', V(0, -2), layer=MENU_LAYER + 1)
        ev.scene.add(self.opt_quit)

        self.options = (
            (self.opt_start, lambda: signal(StartGame())),
            (self.opt_quit, lambda: signal(Quit())),
        )

    def on_button_released(self, ev, signal):
        if self.menu_active:
            x = ev.position.x
            y = ev.position.y

            for opt, callback in self.options:
                dx = abs(x - opt.position.x)
                dy = abs(y - opt.position.y)

                if dy < 0.25 and dx < 1.5:
                    callback()
