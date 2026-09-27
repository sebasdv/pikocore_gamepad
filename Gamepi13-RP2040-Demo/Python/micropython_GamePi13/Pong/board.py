### board.py --- eetree micropython training board configuration.
## author: picospuch

class game_kit:
    # joystick FJO8K-N VR1
    key_up = 15
    key_down = 6

    # buzzer Buzzer LS1
    buzzer = 18

    # accelerometer MMA7660FC U2
    accelerometer_scl = 11
    accelerometer_sda = 10
    accelerometer_int = 9

    # keys (SW3 SW4 SW5 SW6)
    key_b = 20
    key_a = 21
    key_start = 26
    key_select = 19

    # infra-red-rtx (IRM-H638T VSMB10940) U4
    ir_rx = 25
    ir_tx = 24

    # liquid-crystal-display ST7789_1.54_240x240 DS1
    lcd_sck = 10
    lcd_sda = 11
    lcd_rst = 27
    lcd_dc = 25
    lcd_cs =8
    # status-led STA D1
    led_sta=28
    
class pin_cfg:
  
    buzzer = 18
    mic = 27
    


