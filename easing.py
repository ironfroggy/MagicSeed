# Easing functions

def linear(t):
    return t

def in_quad(t):
    return t*t

def out_quad(t):
    return t * (2 - t)

def out_bounce(t, b=0, c=1, d=1):
  t = t / d
  if t < 1 / 2.75:
    return c * (7.5625 * t * t) + b
  elif t < 2 / 2.75:
    t = t - (1.5 / 2.75)
    return c * (7.5625 * t * t + 0.75) + b
  elif t < 2.5 / 2.75:
    t = t - (2.25 / 2.75)
    return c * (7.5625 * t * t + 0.9375) + b
  else:
    t = t - (2.625 / 2.75)
    return c * (7.5625 * t * t + 0.984375) + b
