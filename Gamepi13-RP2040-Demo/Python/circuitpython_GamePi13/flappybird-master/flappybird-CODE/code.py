import board
import displayio
import busio
from adafruit_st7789 import ST7789
import adafruit_imageload
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import digitalio
from time import sleep
from random import randrange

displayio.release_displays()
spi = busio.SPI(board.GP10,board.GP11)

while not spi.try_lock():
    print(".")
    pass

spi.configure(baudrate=24000000) # Configure SPI for 24MHz
spi.unlock()
tft_cs = board.GP8
tft_dc = board.GP25

display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.GP27)
display = ST7789(display_bus, width=240, height=240, rowstart=80,colstart=0,rotation=180)

button_up = digitalio.DigitalInOut(board.GP15)
button_up.direction = digitalio.Direction.INPUT
button_up.pull = digitalio.Pull.UP

button_center = digitalio.DigitalInOut(board.GP21)
button_center.direction = digitalio.Direction.INPUT
button_center.pull = digitalio.Pull.UP

button_down = digitalio.DigitalInOut(board.GP6)
button_down.direction = digitalio.Direction.INPUT
button_down.pull = digitalio.Pull.UP

font = bitmap_font.load_font("fonts/Junction-regular-24.bdf")


text_score = label.Label(font, text=str(0), color=0xd83c02)
text_score.anchor_point = (0, 0)
text_score.anchored_position = (10, 10)

group = displayio.Group()
display.show(group)

pipe_sheet, palette = adafruit_imageload.load("images/pipe.bmp",bitmap=displayio.Bitmap,palette=displayio.Palette)
palette.make_transparent(0)
pipe = displayio.TileGrid(pipe_sheet, pixel_shader=palette,width = 1,height = 1,tile_width = 30,tile_height = 135)
pipe[0] = 0
pipe.y = 80
pipe.x = 80

#gameover
gameover_image, palette = adafruit_imageload.load(
    "images/gameover.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)
palette.make_transparent(0)
gameover = displayio.TileGrid(gameover_image, pixel_shader=palette)
gameover.x = 4
gameover.y = 32

store={
    'time':0,
    'score':0,
    'gameover':False
}



class Sprite:
    def __init__(self,w,h,x,y,speed,img,transparent=False):
        sprite_sheet, palette = adafruit_imageload.load(img,bitmap=displayio.Bitmap,palette=displayio.Palette)
        if transparent:
            palette.make_transparent(0)
        sheet = displayio.TileGrid(sprite_sheet, pixel_shader=palette,width = 1,height = 1,tile_width = w,tile_height = h)
        sheet[0] = 0
        sheet.x = x
        sheet.y = y
        self.sheet=sheet
        self.w=w
        self.h=h
        self.x=x
        self.y=y
        self.speed=speed
        group.append(self.sheet)

class Bird(Sprite):
    def __init__(self):
        Sprite.__init__(self,46,32,20,20,3,'images/bird.bmp',True)
        self.current=0
        self.jump=False
        self.toy=135-self.h
    def fly(self,time):
        if time % 100 ==0:
            self.current+=1
            if self.current == 2:
                self.current = 0
        self.sheet[0]=self.current

    def update(self,time):
        self.fly(time)

        if button_up.value == 0:
            if self.jump==False:
                self.toy=self.y-self.h
                self.jump=True

        if time % 30 ==0:
            if self.jump==True:
                self.y-=self.speed
                if self.y<=0:
                    self.y=0
                    self.jump=False
                if self.y<=self.toy:
                    self.toy=135-self.h
                    self.jump=False
            if self.jump==False:
                self.y+=self.speed
                if self.y>135-self.h:
                    self.y=135-self.h

        self.sheet.y=self.y

class Background(Sprite):
    def __init__(self,x):
        Sprite.__init__(self,240,135,x,0,1,'images/bg.bmp')
    def update(self,time):
        if time % 150==0:
            self.x-=self.speed
            self.sheet.x=self.x
            if self.x<=-240:
                self.x=240

bg1 = Background(0)
bg2 = Background(240)
bird = Bird()


class Pipe(Sprite):
    def __init__(self,x,y,img,t):
        Sprite.__init__(self,30,135,x,y,1,img)
        self.t=t
    def update(self,time):
        if time % 15==0:
            self.x-=self.speed
            if self.x<-30:
                self.x=240
                store['score']+=1
                text_score.text = str(store['score'])
                if self.t == 'a':
                    self.y=randrange(50,120,20)
                else:
                    self.y=randrange(-120,-50,20)
                self.sheet.y=self.y
            self.sheet.x=self.x

            if bird.x>self.x and bird.x<(self.x+self.w):
                if bird.y>self.y and bird.y<(self.y+self.h):
                    group.append(gameover)
                    store['gameover']=True
            if (bird.x+bird.w)>self.x and (bird.x+bird.w)<(self.x+self.w):
                if (bird.y+bird.h)>self.y and (bird.y+bird.h)<(self.y+self.h):
                    group.append(gameover)
                    store['gameover']=True


pipe1 = Pipe(240,50,'images/pipe.bmp','a')
pipe2 = Pipe(380,-50,'images/pipe2.bmp','b')

group.append(text_score)

while True:
    if store['gameover']==False:
        store['time'] +=1
        bird.update(store['time'])
        bg1.update(store['time'])
        bg2.update(store['time'])
        pipe1.update(store['time'])
        pipe2.update(store['time'])
    else:
        if button_down.value == 0:
            group.remove(gameover)
            pipe1.x=240
            pipe2.x=380
            store['score']=0
            store['gameover']=False
            text_score.text = str(store['score'])


import board
import displayio
import busio
from adafruit_st7789 import ST7789
import adafruit_imageload
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import digitalio
from time import sleep
from random import randrange

# Release any existing displays
displayio.release_displays()

# Initialize SPI bus
spi = busio.SPI(board.GP10, board.GP11)
while not spi.try_lock():
    pass
spi.configure(baudrate=24000000)  # Configure SPI for 24MHz
spi.unlock()

# Define display pins
tft_cs = board.GP8  # Chip select
tft_dc = board.GP25  # Data/Command
tft_reset = board.GP27  # Reset pin

# Setup display bus and ST7789 display
display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=tft_reset)
display = ST7789(display_bus, width=240, height=240, rowstart=80, colstart=0, rotation=180)

# Initialize button pins
def setup_button(pin):
    button = digitalio.DigitalInOut(pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    return button

button_up = setup_button(board.GP15)
button_center = setup_button(board.GP21)
button_down = setup_button(board.GP6)

# Load font for text display
font = bitmap_font.load_font("fonts/Junction-regular-24.bdf")

# Score label setup
text_score = label.Label(font, text="0", color=0xd83c02)
text_score.anchor_point = (0, 0)
text_score.anchored_position = (10, 10)

# Display group to hold all graphical elements
group = displayio.Group()
display.show(group)

# Load pipe image
pipe_sheet, palette = adafruit_imageload.load("images/pipe.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
palette.make_transparent(0)
pipe = displayio.TileGrid(pipe_sheet, pixel_shader=palette, width=1, height=1, tile_width=30, tile_height=135)
pipe.x = 80
pipe.y = 80

# Load gameover image
gameover_image, gameover_palette = adafruit_imageload.load(
    "images/gameover.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)
gameover_palette.make_transparent(0)
gameover = displayio.TileGrid(gameover_image, pixel_shader=gameover_palette, x=4, y=32)

# Game state storage
store = {
    'time': 0,
    'score': 0,
    'gameover': False
}

# Sprite base class
class Sprite:
    def __init__(self, w, h, x, y, speed, img, transparent=False):
        sprite_sheet, palette = adafruit_imageload.load(img, bitmap=displayio.Bitmap, palette=displayio.Palette)
        if transparent:
            palette.make_transparent(0)
        self.sheet = displayio.TileGrid(sprite_sheet, pixel_shader=palette, width=1, height=1, tile_width=w, tile_height=h)
        self.sheet[0] = 0
        self.sheet.x = x
        self.sheet.y = y
        self.x = x
        self.y = y
        self.speed = speed
        self.w = w
        self.h = h
        group.append(self.sheet)

# Bird class
class Bird(Sprite):
    def __init__(self):
        super().__init__(46, 32, 20, 20, 3, 'images/bird.bmp', True)
        self.current_frame = 0
        self.jump = False
        self.target_y = 135 - self.h

    def fly(self, time):
        if time % 100 == 0:
            self.current_frame = (self.current_frame + 1) % 2
        self.sheet[0] = self.current_frame

    def update(self, time):
        self.fly(time)
        if not button_up.value and not self.jump:
            self.target_y = self.y - self.h
            self.jump = True

        if time % 30 == 0:
            if self.jump:
                self.y = max(0, self.y - self.speed)
                if self.y <= self.target_y:
                    self.target_y = 135 - self.h
                    self.jump = False
            else:
                self.y = min(135 - self.h, self.y + self.speed)

        self.sheet.y = self.y

# Background class
class Background(Sprite):
    def __init__(self, x):
        super().__init__(240, 135, x, 0, 1, 'images/bg.bmp')

    def update(self, time):
        if time % 150 == 0:
            self.x -= self.speed
            if self.x <= -240:
                self.x = 240
            self.sheet.x = self.x

# Pipe class
class Pipe(Sprite):
    def __init__(self, x, y, img, pipe_type):
        super().__init__(30, 135, x, y, 1, img)
        self.pipe_type = pipe_type

    def update(self, time):
        if time % 15 == 0:
            self.x -= self.speed
            if self.x < -30:
                self.x = 240
                store['score'] += 1
                text_score.text = str(store['score'])
                self.y = randrange(50, 120, 20) if self.pipe_type == 'a' else randrange(-120, -50, 20)
                self.sheet.y = self.y

            self.sheet.x = self.x

            if bird.x < self.x + self.w and bird.x + bird.w > self.x:
                if bird.y < self.y + self.h and bird.y + bird.h > self.y:
                    group.append(gameover)
                    store['gameover'] = True

# Initialize game objects
bg1 = Background(0)
bg2 = Background(240)
bird = Bird()
pipe1 = Pipe(240, 50, 'images/pipe.bmp', 'a')
pipe2 = Pipe(380, -50, 'images/pipe2.bmp', 'b')

# Add score label to the group
group.append(text_score)

# Main game loop
while True:
    if not store['gameover']:
        store['time'] += 1
        bird.update(store['time'])
        bg1.update(store['time'])
        bg2.update(store['time'])
        pipe1.update(store['time'])
        pipe2.update(store['time'])
    else:
        if not button_down.value:  # Restart game on button press
            group.remove(gameover)
            pipe1.x = 240
            pipe2.x = 380
            store['score'] = 0
            store['gameover'] = False
            text_score.text = str(store['score'])
