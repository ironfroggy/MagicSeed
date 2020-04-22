from dataclasses import dataclass
from tweening import Tweener


@dataclass
class StartGame:
    pass

@dataclass
class OpenMenu:
    pass

@dataclass
class CloseMenu:
    pass

@dataclass
class ToggleMenu:
    pass

@dataclass
class HoverSeed:
    grid: object
    x: int
    y: int

@dataclass
class MovementStart:
    colors: dict = None

@dataclass
class MovementDone:
    pass

@dataclass
class TweeningDone:
    tweener: Tweener

@dataclass
class SeedCorruption:
    x: int
    y: int

@dataclass
class SeedCorruptionComplete:
    pass

@dataclass
class EnemyAttack:
    enemy: object
    dmg: int

@dataclass
class DamageDealt:
    target: str
    dmg: int

@dataclass
class MonsterDeath:
    monster: object

@dataclass
class MonsterSpawn:
    monster: object

@dataclass
class PlayerDeath:
    player: object
