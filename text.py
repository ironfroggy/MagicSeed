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
    def __init__(self, text, position, layer=100, align='center'):
        self.position = position
        self.layer = layer
        self.align = align
        self.signal = None
        self.letters = []
        self._text = text
        self._size = 2
    
    def __image__(self):
        return None

    def on_scene_started(self, ev, signal):
        self.scene = ev.scene
        self.text = self._text
    
    def setup(self):
        self.text = self._text
    
    @property
    def text(self):
        return self._text
    
    @property
    def size(self):
        return self._size
    
    @size.setter
    def size(self, value):
        self._size = value
        for l in self.letters:
            l.size = value

    @text.setter
    def text(self, value):
        self._text = value
        for l in self.letters:
            self.scene.remove(l)
        self.letters.clear()
        
        p = self.position

        if self.align == 'center':
            align = -0.25 * len(self.text)
        elif self.align == 'left':
            raise NotImplementedError()
        elif self.align == 'right':
            align = 0
        else:
            raise ValueError()

        for i, c in enumerate(self.text):
            l = Letter(c)
            l.layer = self.layer
            l.position = ppb.Vector(p.x + i/2 + align, p.y)
            self.scene.add(l)
            self.letters.append(l)
