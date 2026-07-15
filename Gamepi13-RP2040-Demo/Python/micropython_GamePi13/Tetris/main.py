import machine
import st7789 as st7789
import time
from machine import Pin, ADC
import random
from fonts import vga2_8x8 as font1
from fonts import vga1_16x32 as font2
from buzzer_music import music
from time import sleep
st7789_cs= 8
st7789_res = 27
st7789_dc = 25
disp_width = 240
disp_height = 240
spi_sck=machine.Pin(10)
spi_tx=machine.Pin(11)
spi0=machine.SPI(1,baudrate=900000000, phase=0, polarity=0, sck=spi_sck, mosi=spi_tx)
display = st7789.ST7789(spi0, disp_width, disp_width,
    reset=machine.Pin(st7789_res, machine.Pin.OUT),
    dc=machine.Pin(st7789_dc, machine.Pin.OUT),
    cs=machine.Pin(st7789_cs, machine.Pin.OUT),                  
    xstart=0, ystart=0, rotation=0)

display.fill(st7789.BLACK)
buttonB = Pin(20,Pin.IN, Pin.PULL_UP)
buttonA = Pin(21,Pin.IN, Pin.PULL_UP)
buttonright= Pin(13,Pin.IN, Pin.PULL_UP)
buttonleft= Pin(16,Pin.IN, Pin.PULL_UP)
buttondown= Pin(14,Pin.IN, Pin.PULL_UP)
g=[]
for i in range(16):
    g.append([0]*12)

song = '0 A#4 1 1;2 F5 1 1;4 D#5 1 1;8 D5 1 1;11 D5 1 1;6 A#4 1 1;14 D#5 1 1;18 A#4 1 1;20 D#5 1 1;22 A#4 1 1;24 D5 1 1;27 D5 1 1;30 D#5 1 1;32 A#4 1 1;34 F5 1 1;36 D#5 1 1;38 A#4 1 1;40 D5 1 1;43 D5 1 1;46 D#5 1 1;50 A#4 1 1;52 D#5 1 1;54 G5 1 1;56 F5 1 1;59 D#5 1 1;62 F5 1 1;64 A#4 1 1;66 F5 1 1;68 D#5 1 1;70 A#4 1 1;72 D5 1 1;75 D5 1 1;78 D#5 1 1;82 A#4 1 1;84 D#5 1 1;86 A#4 1 1;88 D5 1 1;91 D5 1 1;94 D#5 1 1;96 A#4 1 1;100 D#5 1 1;102 A#4 1 1;104 D5 1 1;107 D5 1 1;110 D#5 1 1;114 A#4 1 1;116 D#5 1 1;118 G5 1 1;120 F5 1 1;123 D#5 1 1;126 F5 1 1;98 F5 1 1'

boxO = [[1,1],[1,1]]
boxz_1 = [[1,1,0],[0,1,1],[0,0,0]]
boxz_2 = [[0,1,1],[1,1,0],[0,0,0]]
box7_1 = [[1,1,0],[0,1,0],[0,1,0]]
box7_2 = [[0,1,1],[0,1,0],[0,1,0]]
boxT = [[0,1,0],[1,1,1],[0,0,0]]
boxI = [[0,0,0,0,0],[0,0,0,0,0],[1,1,1,1,0],[0,0,0,0,0],[0,0,0,0,0]]
boxes = [boxO,boxz_1,boxz_2,box7_1,box7_2,boxT,boxI]
color = [0xFFE0,0x867f,0x7ef,0xfb08]
score = 0
box_column = 4
box_row = 0
global cell
global reachtop
reachtop = False
cell = 15
box_column = 4
box_row = 0
def newbox():
    box_id=random.randint(0,6)
    box_org = boxes[box_id]
    b = []
    for i in range(len(box_org)):
        b.append(box_org[i][:])
    return b
box=newbox()
def clockwise():
    N = len(box)
    a=[]
    for i in range(N):
        a.append(box[i][:])
    for i in range(N):
        for j in range(N):
            box[N-j-1][i]=a[i][j]

def counter_clockwise():
    N = len(box)
    a=[]
    for i in range(N):
        a.append(box[i][:])
    for i in range(N):
        for j in range(N):
            box[j][N-i-1] = a[i][j]

def leave():
    j=box_row
    for r in box:
        i=box_column
        for d in r:
            if d==1:
                g[j][i]=0
            i+=1
        j+=1
def enter():
    global box_row
    global box_column
    j=box_row
    for r in box:
        i=box_column
        for d in r:
            if d==1:
                g[j][i]=1
            i+=1
        j+=1
def checkvalid():
    global box_row
    global box_column
    j=box_row
    for r in box:
        i=box_column
        for d in r:
            if d==1:
                if i<0 or i>= 12:
                    return False
                if j<0 or j>= 16:
                    return False
                if g[j][i]==1:
                    return False
            i+=1
        j+=1
    return True
def turn():
    leave()
    clockwise()
    if checkvalid()==False:
        counter_clockwise()
    enter()

def down():
    global box_row
    leave()
    box_row+=1
    if checkvalid() == False:
        box_row-=1
    enter()

def left():
    global box_column
    leave()
    box_column-=1
    if checkvalid()==False:
        box_column+=1
    enter()

def right():
    global box_column
    leave()
    box_column+=1
    if checkvalid()==False:
        box_column-=1
    enter()

def clear():
    global score,reachtop
    i = 0
    c = 0
    while i<16:
        if 0 in g[i]:
            i+=1
        else:
            c+=1
            del g[i]
            g.insert(0,[0]*12)
    if c>0:
        score+=10*(2**(c-1))
        if score >1000:
            score=999
    if 1 in g[0]:
        reachtop = True
def autodrop():
    global box_row,box_column,box,box_id
    leave()
    box_row+=1
    if checkvalid() == False:
        box_row-=1
        enter()
        clear()
        box=newbox()
        box_column = 4
        box_row = 0
    enter()
def falldown():
    global color
    display.fill(0x0000)
    y=0
    for r in g:
        x=0
        for d in r:
            if d==1:
                display.rect(x,y,15,15,0x10)
                display.fill_rect(x+1,y+1,13,13, color[0])
            x+=cell
        y+=cell
def timeaxis (mySong, time):
    l = 0
    time0 = time/40
    while l<time0:
        l+=1
        mySong.tick()
        sleep(0.04)
def game():
    global reachtop,song
    mySong = music(song, pins=[Pin(18)])
    while True:
        timeaxis(mySong, 400)
        
        f=4
        if buttonB.value()==0:
            turn()
        elif buttondown.value()==0: 
            down()
        elif buttonleft.value()==0: 
            left()
        elif buttonright.value()==0:  
            right()
        else:
            print("stop" )
        falldown()
        display.fill_rect(181,0,4,240,color[1])
        display.text(font1,"Tetris",185,25)
        display.text(font1,"Score",185,50)
        display.text(font2,str(score),185,80)
        autodrop()
        if reachtop==True:
            mySong.stop()
            display.fill(0x0000)
            display.text(font2,"   GAME   ",45,60)
            display.text(font2,"   OVER   ",45,130)
            time.sleep(1)
            Tetris()
def Tetris():
    display.fill(0x0000)
    display.text(font2,"Press A", 30, 40, color=0x7e0)
    display.text(font2,"To Start", 30, 80, color=0x7e0)
    buttonValueB = buttonB.value()
    while True:
        buttonValueA = buttonA.value()
        if buttonValueA==0:
            print("OK" )
            g=[]
            for i in range(16):
                g.append([0]*12)
            enter()
            game()
Tetris()

