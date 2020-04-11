from ppb.systems import Renderer

from sdl2 import (
    SDL_BLENDMODE_ADD,
    SDL_BLENDMODE_BLEND,
    SDL_SetTextureAlphaMod,
    SDL_SetTextureBlendMode,
    SDL_SetTextureColorMod,
)
import ppb.flags as flags
from ppb.systems._sdl_utils import sdl_call


class CustomRenderer(Renderer):
    last_opacity = 255
    last_color = (255, 255, 255)

    def prepare_resource(self, game_object):
        texture = super().prepare_resource(game_object)
        if texture:
            opacity = getattr(game_object, 'opacity', 255)
            color = getattr(game_object, 'color', (255, 255, 255))

            if opacity != self.last_opacity:
                sdl_call(
                    SDL_SetTextureAlphaMod, texture.inner, opacity,
                    _check_error=lambda rv: rv < 0
                )
                if opacity < 255:
                    sdl_call(
                        SDL_SetTextureBlendMode, texture.inner, SDL_BLENDMODE_ADD,
                        _check_error=lambda rv: rv < 0
                    )
                else:
                    sdl_call(
                        SDL_SetTextureBlendMode, texture.inner, SDL_BLENDMODE_BLEND,
                        _check_error=lambda rv: rv < 0
                    )
                self.last_opacity = opacity
            
            if color != self.last_color:
                sdl_call(
                    SDL_SetTextureColorMod, texture.inner, color[0], color[1], color[2],
                    _check_error=lambda rv: rv < 0
                )
                self.last_color = color

            return texture