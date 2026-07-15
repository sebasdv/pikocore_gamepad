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
tft_cs = board.GP9
tft_dc = board.GP8

display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.GP12)
display = ST7789(display_bus, width=240, height=135, rowstart=40,colstart=53,rotation=90)

button_up = digitalio.DigitalInOut(board.GP2)
button_up.direction = digitalio.Direction.INPUT
button_up.pull = digitalio.Pull.UP

button_center = digitalio.DigitalInOut(board.GP3)
button_center.direction = digitalio.Direction.INPUT
button_center.pull = digitalio.Pull.UP

button_down = digitalio.DigitalInOut(board.GP18)
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

        