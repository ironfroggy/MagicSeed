from ppb.systems import Renderer

from sdl2 import (
    SDL_BLENDMODE_ADD,
    SDL_BLENDMODE_BLEND,
    SDL_SetTextureAlphaMod,
    SDL_SetTextureBlendMode,
    SDL_SetTextureColorMod,
    SDL_QueryTexture,
    SDL_Rect,
)
import ppb.flags as flags
from ppb.systems._sdl_utils import sdl_call

import ctypes
import io
import logging
import random
from time import monotonic

import sdl2
import sdl2.ext


class CustomRenderer(Renderer):
    last_opacity = 255
    last_opacity_mode = 'blend'
    last_color = (255, 255, 255)

    def prepare_resource(self, game_object):
        texture = super().prepare_resource(game_object)
        if texture:
            opacity = getattr(game_object, 'opacity', 255)
            opacity_mode = getattr(game_object, 'opacity_mode', 'blend')
            color = getattr(game_object, 'color', (255, 255, 255))

            if opacity != self.last_opacity:
                sdl_call(
                    SDL_SetTextureAlphaMod, texture.inner, opacity,
                    _check_error=lambda rv: rv < 0
                )
                self.last_opacity = opacity
            
            if opacity_mode != self.last_opacity_mode:
                if opacity_mode == 'add':
                    sdl_call(
                        SDL_SetTextureBlendMode, texture.inner, SDL_BLENDMODE_ADD,
                        _check_error=lambda rv: rv < 0
                    )
                elif opacity_mode == 'blend':
                    sdl_call(
                        SDL_SetTextureBlendMode, texture.inner, SDL_BLENDMODE_BLEND,
                        _check_error=lambda rv: rv < 0
                    )
                else:
                    raise ValueError(f"Support modes for translucent sprites are 'add' or 'blend', not '{opacity_mode}'.")
            
            if color != self.last_color:
                sdl_call(
                    SDL_SetTextureColorMod, texture.inner, color[0], color[1], color[2],
                    _check_error=lambda rv: rv < 0
                )
                self.last_color = color

            return texture
    
    def compute_rectangles(self, texture, game_object, camera):
        rect = getattr(game_object, 'rect', None)

        flags = sdl2.stdinc.Uint32()
        access = ctypes.c_int()
        img_w = ctypes.c_int()
        img_h = ctypes.c_int()
        sdl_call(
            SDL_QueryTexture, texture, ctypes.byref(flags), ctypes.byref(access),
            ctypes.byref(img_w), ctypes.byref(img_h),
            _check_error=lambda rv: rv < 0
        )

        if rect:
            src_rect = SDL_Rect(*rect)
            win_w = rect[2] * game_object.size
            win_h = rect[3] * game_object.size
        else:
            src_rect = SDL_Rect(x=0, y=0, w=img_w, h=img_h)
            win_w, win_h = self.target_resolution(img_w.value, img_h.value, game_object.size)

        center = camera.translate_to_viewport(game_object.position)
        dest_rect = SDL_Rect(
            x=int(center.x - win_w / 2),
            y=int(center.y - win_h / 2),
            w=int(win_w),
            h=int(win_h),
        )

        return src_rect, dest_rect, ctypes.c_double(-game_object.rotation)