import ppb


FONTSHEET = ppb.Image("resources/sonic_asalga.png")
LEGEND = """ !"#$%&'
<>*+,-./
01234567
89:;<=>?
@ABCDEFG
HIJKLMNO
PQRSTUVW
XYZ[\]^_
`abcdefg
hijklmno
pqrstuvw
xyz{|}~
"""

class Letter(ppb.Sprite):
    image = FONTSHEET
    rect = (0, 0, 16, 16)
    size = 2

    def __init__(self, char):
        super().__init__()
        self.char = char
        for y, row in enumerate(LEGEND.split('\n')):
            for x, col in enumerate(row):
                if char in col:
                    self.rect = (x*16, y*16, 16, 16)

class Text:
    def __init__(self, text, position):
        self.size = 0
        self.position = position
        self._text = text
        self.signal = None
        self.letters = []
    
    @property
    def text(self):
        return self._text
    
    @text.setter
    def text(self, value):
        self._text = value
        for l in self.letters:
            self.scene.remove(l)
        self.letters.clear()
        
        p = self.position
        align = 0.5 * len(self.text)
        for i, c in enumerate(self.text):
            l = Letter(c)
            l.position = ppb.Vector(p.x + i/2 - align, p.y)
            self.scene.add(l)
            self.letters.append(l)
    
    def on_scene_started(self, ev, signal):
        self.scene = ev.scene
        self.text = self._text