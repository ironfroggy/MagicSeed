from dataclasses import dataclass
from tweening import Tweener


@dataclass
class StartGame:
    pass

@dataclass
class OpenMenu:
    pass

@dataclass
class MovementStart:
    scene: object
    colors: dict

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
class PlayerDeath:
    player: object
