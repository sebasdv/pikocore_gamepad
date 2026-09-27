# GamePi13

From Waveshare Wiki

Jump to: [navigation](https://www.waveshare.com/wiki/GamePi13#mw-navigation), [search](https://www.waveshare.com/wiki/GamePi13#p-search)

## Contents

- [1Introduction](https://www.waveshare.com/wiki/GamePi13#Introduction)
  - [1.1Specifications](https://www.waveshare.com/wiki/GamePi13#Specifications)
  - [1.2Functional Pins](https://www.waveshare.com/wiki/GamePi13#Functional_Pins)
- [2Raspberrypi Tutorial](https://www.waveshare.com/wiki/GamePi13#Raspberrypi_Tutorial)
  - [2.1Pre-installed Image](https://www.waveshare.com/wiki/GamePi13#Pre-installed_Image)
  - [2.2Official Systems](https://www.waveshare.com/wiki/GamePi13#Official_Systems)
    - [2.2.1Bookworm system display configuration](https://www.waveshare.com/wiki/GamePi13#Bookworm_system_display_configuration)
      - [2.2.1.1Suitable for Rpi4 & Rpi5](https://www.waveshare.com/wiki/GamePi13#Suitable_for_Rpi4_.26_Rpi5)
      - [2.2.1.2Suitable for all Raspberry Pi models](https://www.waveshare.com/wiki/GamePi13#Suitable_for_all_Raspberry_Pi_models)
    - [2.2.2Bullseye/Buster system display configuration](https://www.waveshare.com/wiki/GamePi13#Bullseye.2FBuster_system_display_configuration)
    - [2.2.3Audio configuration](https://www.waveshare.com/wiki/GamePi13#Audio_configuration)
    - [2.2.4Button configuration](https://www.waveshare.com/wiki/GamePi13#Button_configuration)
  - [2.3Retropie System](https://www.waveshare.com/wiki/GamePi13#Retropie_System)
    - [2.3.1Method one: Use the pre-installed driver image (recommended)](https://www.waveshare.com/wiki/GamePi13#Method_one:_Use_the_pre-installed_driver_image_.28recommended.29)
    - [2.3.2Method two: Install the driver](https://www.waveshare.com/wiki/GamePi13#Method_two:_Install_the_driver)
      - [2.3.2.1Download the system](https://www.waveshare.com/wiki/GamePi13#Download_the_system)
      - [2.3.2.2Configure WIFI](https://www.waveshare.com/wiki/GamePi13#Configure_WIFI)
      - [2.3.2.3Run the fbcp porting program](https://www.waveshare.com/wiki/GamePi13#Run_the_fbcp_porting_program)
      - [2.3.2.4Set the user interface size](https://www.waveshare.com/wiki/GamePi13#Set_the_user_interface_size)
      - [2.3.2.5Set up automatic startup at boot](https://www.waveshare.com/wiki/GamePi13#Set_up_automatic_startup_at_boot)
      - [2.3.2.6Configure the joystick](https://www.waveshare.com/wiki/GamePi13#Configure_the_joystick)
      - [2.3.2.7Audio Configuration Tutorial](https://www.waveshare.com/wiki/GamePi13#Audio_Configuration_Tutorial)
      - [2.3.2.8Add games](https://www.waveshare.com/wiki/GamePi13#Add_games)
  - [2.4Parameter introduction](https://www.waveshare.com/wiki/GamePi13#Parameter_introduction)
- [3RP2040-PiZero Tutorial](https://www.waveshare.com/wiki/GamePi13#RP2040-PiZero_Tutorial)
  - [3.1Running Demo](https://www.waveshare.com/wiki/GamePi13#Running_Demo)
    - [3.1.1Install Thonny IDE](https://www.waveshare.com/wiki/GamePi13#Install_Thonny_IDE)
    - [3.1.2MicroPython](https://www.waveshare.com/wiki/GamePi13#MicroPython)
    - [3.1.3CircuitPython](https://www.waveshare.com/wiki/GamePi13#CircuitPython)
    - [3.1.4C/C++ Series](https://www.waveshare.com/wiki/GamePi13#C.2FC.2B.2B_Series)
      - [3.1.4.1Environment Setup](https://www.waveshare.com/wiki/GamePi13#Environment_Setup)
        - [3.1.4.1.1Install VSCode](https://www.waveshare.com/wiki/GamePi13#Install_VSCode)
        - [3.1.4.1.2Install the extension](https://www.waveshare.com/wiki/GamePi13#Install_the_extension)
        - [3.1.4.1.3Configure the extension](https://www.waveshare.com/wiki/GamePi13#Configure_the_extension)
        - [3.1.4.1.4Create a new project](https://www.waveshare.com/wiki/GamePi13#Create_a_new_project)
        - [3.1.4.1.5Import a project](https://www.waveshare.com/wiki/GamePi13#Import_a_project)
        - [3.1.4.1.6Update the extension](https://www.waveshare.com/wiki/GamePi13#Update_the_extension)
    - [3.1.5Open Source Demos](https://www.waveshare.com/wiki/GamePi13#Open_Source_Demos)
- [4Resources](https://www.waveshare.com/wiki/GamePi13#Resources)
  - [4.1Demo](https://www.waveshare.com/wiki/GamePi13#Demo)
  - [4.2Datasheets](https://www.waveshare.com/wiki/GamePi13#Datasheets)
  - [4.3Schematic](https://www.waveshare.com/wiki/GamePi13#Schematic)
  - [4.4Software](https://www.waveshare.com/wiki/GamePi13#Software)
- [5Support](https://www.waveshare.com/wiki/GamePi13#Support)

# Introduction

- Offers Raspberry Pi series and RP2040-PiZero series tutorials.
- 1.3inch IPS screen with 240×240 resolution, good image quality, bright colors and wide viewing angle.
- It supports RetroPie game system and Recalbox game system, with thousands of classic games. As long as the TF card capacity is big enough, you can add your favorite games at will.
- On-board PWM audio output speaker and earphone Jack, convenient for listening to the familiar BGM.

## Specifications

- Working voltage: 3.3V
- Communication interface: SPI
- Screen type: IPS
- Control chip: ST7789
- Resolution: 240(H)RGB x 240(V)
- Display size: 23.4 (H) x 23.4 (V) (mm)
- Pixel size: 0.0975 (H) x 0.0975 (V) (mm)
- Product size:65 x 31(mm)

## Functional Pins

| Functional pins | Board physical pin serial number | BCM coding | Description |
| --- | --- | --- | --- |
| 5V | 2/4 | / | 5V power supply positive |
| 3.3V | 1 | / | 3.3V power supply positive |
| GND | 6/9/30/34 | / | Power supply ground |
| R | 8 | 14 | Key TR |
| L | 16 | 23 | Key TL |
| X | 10 | 15 | Key X |
| Y | 32 | 12 | Key Y |
| B | 38 | 20 | Key B |
| A | 40 | 21 | Key A |
| Up | 29 | 5 | Key Up |
| Left | 36 | 16 | Key Left |
| Down | 31 | 6 | Key Down |
| Right | 33 | 13 | Key Right |
| Select | 35 | 19 | Key Select |
| Start | 37 | 26 | Key Start |
| DC | 22 | 25 | LCD display data/command selection pin |
| SCLK | 23 | 11 | LCD SPI Clock |
| CS | 24 | 8 | LCD enable select pin; enabled low, disabled high |
| MOSI | 19 | 10 | LCD SPI data input |
| RST | 13 | 27 | LCD reset, enabled low |
| AUDIO | 12 | 18 | Audio output |

# Raspberrypi Tutorial

## Pre-installed Image

- For beginners, we provide a pre-installed image to help you get started with the module more quickly. After flashing the pre-installed image, simply insert the TF card into your Raspberry Pi, power it up, and you're ready to go.
- Official Systems:
  - [GamePi13 Bullseye System Pre-installed - 3D Display](https://drive.google.com/file/d/1hq4kbtsDO77lZ_fOIU1HZiE-oWx6DTSH/view?usp=sharing)
  - [GamePi13 Bullseye System Pre-installed - Direct Display](https://drive.google.com/file/d/1rdb6KmYe3eppZTnV_mRylpSL7-z5F6ej/view?usp=sharing)
  - [GamePi13 Bookworm System Pre-installed - Direct Display](https://drive.google.com/file/d/1BC2OrTgD17x4gUleSbgdc1lIkRF8ni_q/view?usp=sharing)
- Retropie Systems:
  - [GamePi13 Pre-installed with Raspberry Pi Zero - Direct Display](https://drive.google.com/file/d/1rZDuuf1X3zLapeHrXp98rM2r0e8g3ysV/view?usp=sharing)
  - [GamePi13 Pre-installed with Raspberry Pi Zero - 3D Display](https://drive.google.com/file/d/1Rsn-iNlg2s7Xf4jM5qu7io-GhEXx4fzN/view?usp=sharing)
  - [GamePi13 Pre-installed with Raspberry Pi Zero 2W - Direct Display](https://drive.google.com/file/d/1mgKGYllVUsKrX-igS3IZ5RP0HAxGTojd/view?usp=sharing)
  - [GamePi13 Pre-installed with Raspberry Pi Zero 2W - 3D Display](https://drive.google.com/file/d/1O403emEUOk_g6i8spEHZuFEE4X-wOnMf/view?usp=sharing)

Here are the specific configuration steps.

## Official Systems

### Bookworm system display configuration

#### Suitable for Rpi4 & Rpi5

**Configure SPI Display:**

After downloading the system, insert the TF card into your PC，download and copy [waveshare13.dtbo](https://files.waveshare.com/wiki/GamePi13/Doc/Waveshare13.dtbo) to the /boot/overlays/ directory

**Edit the config.txt configuration file:**

- Disable KMS and dual-screen display, as shown in the figure below


[![FBCP CLOSE.jpg](https://www.waveshare.com/w/upload/3/38/FBCP_CLOSE.jpg)](https://www.waveshare.com/wiki/File:FBCP_CLOSE.jpg)

- Add the following configurations at the end of the file

```
dtparam=spi=on
dtoverlay=waveshare13
dtoverlay=audremap18
hdmi_force_hotplug=1
max_usb_current=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 480 480 60 6 0 0 0
hdmi_drive=2
display_hdmi_rotate=0
```

If you need to use it with a prism, you can change the "display\_hdmi\_rotate=0" at the end to "display\_hdmi\_rotate=0x10002", for details see [Parameter introduction](https://www.waveshare.com/wiki/GamePi13#Parameter_introduction)

**Set up CLI for automatic login:**

```
sudo raspi-config nonint do_boot_behaviour B2
```

Note1：Ensure that the Raspberry Pi username is "pi"; otherwise, automatic login will not function properly

**Switch to X11:**

```
sudo raspi-config nonint do_wayland W1
sudo reboot
```

Note2：After setting all the above configurations, the system will take a bit longer to restart each time, and you will also need to wait a moment before you can access it via SSH

**Download, compile, and install fbcp:**

```
sudo apt install libraspberrypi-dev -y
sudo apt-get install unzip -y
sudo apt-get install cmake -y
sudo wget https://files.waveshare.com/wiki/GamePi13/Doc/Rpi-fbcp.zip
sudo unzip ./Rpi-fbcp.zip
cd rpi-fbcp/
sudo rm -rf build
sudo mkdir -m 777 ./build
cd build
sudo cmake ..
sudo make
sudo install fbcp /usr/local/bin/fbcp
```

**Set up automatic startup at boot:**

- Open the .bash\_profile file; if there is no .bash\_profile file, create one yourself

```
sudo nano ~/.bash_profile
```

- Add the following code to the bottom of the .bash\_profile file

```
if [ "$(cat /proc/device-tree/model | cut -d ' ' -f 3)" = "5" ]; then
    # rpi 5B configuration
    export FRAMEBUFFER=/dev/fb1
    startx  2> /tmp/xorg_errors
else
    # Non-pi5 configuration
    export FRAMEBUFFER=/dev/fb0
    fbcp &
    startx  2> /tmp/xorg_errors
Fi
```

The above configuration will take effect after a reboot

```
sudo reboot
```

#### Suitable for all Raspberry Pi models

Operation must be based on the Bookworm-Lite version, [64-bit Lite](https://files.waveshare.com/wiki/GamePi13/Doc/2024-03-15-raspios-bookworm-arm64-lite.img.xz), [32-bit Lite](https://files.waveshare.com/wiki/GamePi13/Doc/2024-03-15-raspios-bookworm-armhf-lite.img.xz)

**Configure SPI Display:**

After downloading the system, insert the TF card into your PC，download and copy [waveshare13.dtbo](https://files.waveshare.com/wiki/GamePi13/Doc/Waveshare13.dtbo) to the /boot/overlays/ directory

**Edit the config.txt configuration file:**

- Disable the corresponding command for the figure below


[![FBCP CLOSE.jpg](https://www.waveshare.com/w/upload/3/38/FBCP_CLOSE.jpg)](https://www.waveshare.com/wiki/File:FBCP_CLOSE.jpg)

- Add the following configurations at the end of the file

```
dtparam=spi=on
dtoverlay=waveshare13
dtoverlay=audremap18
hdmi_force_hotplug=1
max_usb_current=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 480 480 60 6 0 0 0
hdmi_drive=2
display_hdmi_rotate=0
arm_freq=1200
core_freq=500
over_voltage=2
gpu_freq=700
force_turbo=1
```

If you need to use it with a prism, you can change the "display\_hdmi\_rotate=0" at the end to "display\_hdmi\_rotate=0x10002", for details see [Parameter introduction](https://www.waveshare.com/wiki/GamePi13#Parameter_introduction)

**Download necessary software:**

- Update the system

```
sudo apt update && sudo apt upgrade && sudo apt full-upgrade -y
```

- Install xorg services

```
sudo apt-get install --no-install-recommends xserver-xorg -y
sudo apt-get install --no-install-recommends xinit -y
```

- Install desktop manager

```
sudo apt install lightdm -y
```

- Install Raspberry Pi official GUI

```
sudo apt install raspberrypi-ui-mods -y
```

- Install browser (optional)

```
sudo apt install chromium-browser -y
```

- Install music player (optional)

```
sudo apt install vlc -y
```

- Install git (optional)

```
sudo apt install git -y
```

**Download, compile and install fbcp:**

Open the Raspberry Pi terminal and execute:

```
sudo apt install libraspberrypi-dev -y
sudo apt-get install unzip -y
sudo apt-get install cmake -y
sudo wget https://files.waveshare.com/wiki/GamePi13/Doc/Rpi-fbcp.zip
sudo unzip ./Rpi-fbcp.zip
cd rpi-fbcp/
sudo rm -rf build
sudo mkdir -m 777 ./build
cd build
sudo cmake ..
sudo make
sudo install fbcp /usr/local/bin/fbcp
```

**Set up automatic startup at boot:**

- Open the .bash\_profile file; if there is no .bash\_profile file, create one yourself

```
sudo nano ~/.bash_profile
```

Add the following code to the bottom of the .bash\_profile file

```
if [ "$(cat /proc/device-tree/model | cut -d ' ' -f 3)" = "5" ]; then
    # rpi 5B configuration
    export FRAMEBUFFER=/dev/fb1
    startx  2> /tmp/xorg_errors
else
    # Non-pi5 configuration
    export FRAMEBUFFER=/dev/fb0
    fbcp &
    startx  2> /tmp/xorg_errors
fi
```

The above configuration will take effect after a reboot

```
sudo reboot
```

**Set up CLI for automatic login:**

```
sudo raspi-config nonint do_boot_behaviour B2
sudo raspi-config nonint do_wayland W1
sudo reboot
```

After the restart, the main screen will display normally.

Note1: Ensure that the Raspberry Pi username is "pi"; Otherwise, automatic login will not function properly

Note2：After setting all the above configurations, the system will take a bit longer to restart each time, and you will also need to wait a moment before you can access it via SSH

### Bullseye/Buster system display configuration

**Configure SPI Display:**

Download and copy [waveshare13.dtbo](https://files.waveshare.com/wiki/GamePi13/Doc/Waveshare13.dtbo) to the /boot/overlays/ directory

```
sudo cp waveshare13.dtbo /boot/overlays/
```

**Edit the config.txt file:**

Comment out the corresponding lines as shown in the figure below

[![FBCP CLOSE.jpg](https://www.waveshare.com/w/upload/3/38/FBCP_CLOSE.jpg)](https://www.waveshare.com/wiki/File:FBCP_CLOSE.jpg)

Add the following code at the end of config.txt

```
dtparam=spi=on
dtoverlay=waveshare13
dtoverlay=audremap18
hdmi_force_hotplug=1
max_usb_current=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 480 480 60 6 0 0 0
hdmi_drive=2
display_hdmi_rotate=0
#arm_freq=1200
#core_freq=500
#over_voltage=2
#gpu_freq=700
#force_turbo=1
```

If you need to use it with a prism, you can change the "display\_hdmi\_rotate=0" at the end to "display\_hdmi\_rotate=0x10002", for details see [Parameter introduction](https://www.waveshare.com/wiki/GamePi13#Parameter_introduction)

**Download and run the driver:**

Open the Raspberry Pi terminal and execute:

```
sudo apt-get install unzip -y
sudo apt-get install cmake -y
sudo wget https://files.waveshare.com/wiki/GamePi13/Doc/Rpi-fbcp.zip
sudo unzip ./Rpi-fbcp.zip
cd rpi-fbcp/
sudo mkdir -m 777 ./build
cd build
sudo cmake ..
sudo make -j8
sudo install fbcp /usr/local/bin/fbcp
sudo ./fbcp
```

**Set up automatic startup at boot:**

```
sudo cp ~/rpi-fbcp/build/fbcp /usr/local/bin/fbcp
sudo nano /etc/rc.local
```

Add fbcp& before exit 0. Be sure to add & to run it in the background; otherwise, the system may not start up properly.

[![1in3 lcd fb5.png](https://www.waveshare.com/w/upload/d/dd/1in3_lcd_fb5.png)](https://www.waveshare.com/wiki/File:1in3_lcd_fb5.png)

After that, you need to restart the system

```
sudo reboot
```

Then, the display should work normally

### Audio configuration

1.Download and copy [audremap18.dtbo](https://files.waveshare.com/wiki/GamePi13/Doc/Audremap18.dtbo) to the /boot/overlays/ directory

```
sudo cp audremap18.dtbo /boot/overlays/
```

2.Edit the config.txt configuration file

- Add the following configuration at the end of the file

```
dtoverlay=audremap18
```

3.Switch audio output

```
sudo raspi-config
```

Select System Options --> Audio --> Headphones -->Ok

[![GameP13-t35.jpg](https://www.waveshare.com/w/upload/f/f0/GameP13-t35.jpg)](https://www.waveshare.com/wiki/File:GameP13-t35.jpg)

4.Restart to apply changes

```
sudo reboot
```

5.Audio output test

- Method one: Test in the command line CLI；

```
vlc xxx.mp3
```

If vlc is not installed, then

```
sudo apt-get install vlc
```

- Method two: Test in the graphical user interface GUI;

Double-click the xxx.mp3 file to open with vlc by default. If vlc is not installed, you will need to install it

```
sudo apt-get install vlc
```

### Button configuration

Run the button press test Demo

```
 sudo wget https://files.waveshare.com/wiki/GamePi13/Doc/Button_press_detector.zip
 sudo unzip ./Button_press_detector.zip
 sudo python3 ~/Desktop/button_press_detector.py
```

## Retropie System

Note: This system is not supported on Pi5.

### Method one: Use the pre-installed driver image (recommended)

For use with Raspberry Pi Zero/Zero 2W, it is recommended to directly use the [#Pre-installed image](https://www.waveshare.com/wiki/GamePi13#Pre-installed_image)

### Method two: Install the driver

#### Download the system

1\. Connect the TF card to the PC, download, and use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash the corresponding system image.

[![Raspberry-Pi-Monitor-details-1.png](https://www.waveshare.com/w/upload/thumb/9/98/Raspberry-Pi-Monitor-details-1.png/800px-Raspberry-Pi-Monitor-details-1.png)](https://www.waveshare.com/wiki/File:Raspberry-Pi-Monitor-details-1.png)

2\. After the image is written, open the config.txt file in the root directory of the TF card, add the following code at the end of config.txt, save it, and safely eject the TF card.

```
hdmi_force_hotplug=1
```

3\. After the writing is complete, connect the HDMI monitor to the Raspberry Pi, power up the Raspberry Pi, and enter the system. Then press F4 on the keyboard to enter the terminal. (Alternatively, you can log in to the terminal control interface over the network)

#### Configure WIFI

Enter the terminal and type **raspi-config** to open the system configuration interface, select System Options -> Wireless LAN

[![Wifi gamepi13 1.png](https://www.waveshare.com/w/upload/7/78/Wifi_gamepi13_1.png)](https://www.waveshare.com/wiki/File:Wifi_gamepi13_1.png)

[![Wifi gamepi13 2.png](https://www.waveshare.com/w/upload/5/52/Wifi_gamepi13_2.png)](https://www.waveshare.com/wiki/File:Wifi_gamepi13_2.png)

Select the country, here I chose CN China.

[![Wifi gamepi13 3.png](https://www.waveshare.com/w/upload/3/36/Wifi_gamepi13_3.png)](https://www.waveshare.com/wiki/File:Wifi_gamepi13_3.png)

[![Wifi gamepi13 4.png](https://www.waveshare.com/w/upload/0/01/Wifi_gamepi13_4.png)](https://www.waveshare.com/wiki/File:Wifi_gamepi13_4.png)

Enter the Wi-Fi network name.

[![Wifi gamepi13 5.png](https://www.waveshare.com/w/upload/7/77/Wifi_gamepi13_5.png)](https://www.waveshare.com/wiki/File:Wifi_gamepi13_5.png)

Enter the Wi-Fi password and reboot to save the changes.

[![Wifi gamepi13 6.png](https://www.waveshare.com/w/upload/7/7c/Wifi_gamepi13_6.png)](https://www.waveshare.com/wiki/File:Wifi_gamepi13_6.png)

[![Wifi gamepi13 7.png](https://www.waveshare.com/w/upload/f/f6/Wifi_gamepi13_7.png)](https://www.waveshare.com/wiki/File:Wifi_gamepi13_7.png)

#### Run the fbcp porting program

```
cd ~
wget https://files.waveshare.com/wiki/GamePi13/Doc/Gamepi13_fbcp.zip
unzip Gamepi13_fbcp.zip
cd Gamepi13_fbcp/build
sudo chmod +x *
sudo ./fbcp-ili9341
```

Wait for a few seconds, and the 1.3 inch screen should display normally

#### Set the user interface size

Change the LCD display resolution

```
sudo nano /boot/config.txt
```

Add the following code

```
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=1
hdmi_mode=87
hdmi_cvt 480 480 60 6 0 0 0
#display_rotate=0
avoid_warnings=1
```

Reboot to save the changes

```
sudo reboot
```

If you need to use it with a prism, you can change "display\_rotate=0" to "display\_rotate=0x10002", for details see [#Parameter introduction](https://www.waveshare.com/wiki/GamePi13#Parameter_introduction)

#### Set up automatic startup at boot

```
sudo nano /etc/rc.local
```

Add the following line before exit 0. Be sure to add "&" to run it in the background; otherwise, the system may not start up properly.

```
sudo /home/pi/fbcp-ili9341/build/fbcp-ili9341 &
```

#### Configure the joystick

- Open the Raspberry Pi terminal and enter the following command to access the configuration interface

```
cd RetroPie-Setup/
sudo ./retropie_setup.sh
```

[![Retropie gamepi13 1.png](https://www.waveshare.com/w/upload/a/a7/Retropie_gamepi13_1.png)](https://www.waveshare.com/wiki/File:Retropie_gamepi13_1.png)

[![Retropie gamepi13 2.png](https://www.waveshare.com/w/upload/thumb/b/b2/Retropie_gamepi13_2.png/600px-Retropie_gamepi13_2.png)](https://www.waveshare.com/wiki/File:Retropie_gamepi13_2.png)

[![Retropie gamepi13 3.png](https://www.waveshare.com/w/upload/thumb/c/c7/Retropie_gamepi13_3.png/600px-Retropie_gamepi13_3.png)](https://www.waveshare.com/wiki/File:Retropie_gamepi13_3.png)

[![Retropie gamepi13 4.png](https://www.waveshare.com/w/upload/thumb/6/6e/Retropie_gamepi13_4.png/600px-Retropie_gamepi13_4.png)](https://www.waveshare.com/wiki/File:Retropie_gamepi13_4.png)

[![Retropie gamepi13 5.png](https://www.waveshare.com/w/upload/thumb/4/41/Retropie_gamepi13_5.png/600px-Retropie_gamepi13_5.png)](https://www.waveshare.com/wiki/File:Retropie_gamepi13_5.png)

- After installing the driver, edit the mk\_arcade\_joystick\_rpi.conf file

```
sudo nano /etc/modprobe.d/mk_arcade_joystick_rpi.conf
```

Comment out the existing lines and add the following joystick configuration to this file

```
options mk_arcade_joystick_rpi map=5 gpio=5,6,16,13,26,19,21,20,15,12,14,23
```

[![Retropie gamepi13 7.jpg](https://www.waveshare.com/w/upload/thumb/d/d5/Retropie_gamepi13_7.jpg/600px-Retropie_gamepi13_7.jpg)](https://www.waveshare.com/wiki/File:Retropie_gamepi13_7.jpg)

After restarting to remap your buttons, the Gamepad will work

#### Audio Configuration Tutorial

- Download audremap18.dtbo to your pi

```
wget https://files.waveshare.com/wiki/GamePi13/Doc/Audremap18.dtbo
sudo cp Audremap18.dtbo /boot/overlays/
```

- Edit config.txt

```
sudo nano /boot/config.txt
```

Add the following code at the end to enable gpio18 as a PWM audio pin

```
dtoverlay=audremap18，pins_18_19
```

- After restarting, you need to add local audio

Enter **sudo raspi-config** and select System Options -> Audio -> Headphones

- Go to the Retropie menu


[![Retropie gamepi13 8.png](https://www.waveshare.com/w/upload/thumb/e/ee/Retropie_gamepi13_8.png/600px-Retropie_gamepi13_8.png)](https://www.waveshare.com/wiki/File:Retropie_gamepi13_8.png)

Select->Audio->Headphones,and reboot to save the audio function, which will then work properly.

#### Add games

- Since most games have large file sizes, we first need to expand the file system before adding games.

In the Retropie menu interface select RASPI-CONFIG

[![Retropie gamepi13 8.png](https://www.waveshare.com/w/upload/thumb/e/ee/Retropie_gamepi13_8.png/600px-Retropie_gamepi13_8.png)](https://www.waveshare.com/wiki/File:Retropie_gamepi13_8.png)

[![Game-HAT-Manual04.jpg](https://www.waveshare.com/w/upload/thumb/2/2b/Game-HAT-Manual04.jpg/600px-Game-HAT-Manual04.jpg)](https://www.waveshare.com/wiki/File:Game-HAT-Manual04.jpg)

Select 7 Advanced Options -> A1 Expand Filesystem, press Enter -> Finish. (This process requires a USB keyboard to operate)

[![Game-HAT-Manual05.jpg](https://www.waveshare.com/w/upload/thumb/4/4c/Game-HAT-Manual05.jpg/600px-Game-HAT-Manual05.jpg)](https://www.waveshare.com/wiki/File:Game-HAT-Manual05.jpg)

Select Ok to restart the system. After the restart, the file system expansion will be complete.

- Prepare the corresponding game ROMs.

I recommend a very cool website: [http://coolrom.com/](http://coolrom.com/)

You can download various game ROMs on your PC. For example, if you want to play Sony Playstation games, you can choose to download them from this site.

[![Game-HAT-Manual06.png](https://www.waveshare.com/w/upload/3/32/Game-HAT-Manual06.png)](https://www.waveshare.com/wiki/File:Game-HAT-Manual06.png)

For example: [http://coolrom.com/roms/psx/39719/Tekken\_3.php](http://coolrom.com/roms/psx/39719/Tekken_3.php)

Click here to download.

[![Game-HAT-Manual07.png](https://www.waveshare.com/w/upload/a/ab/Game-HAT-Manual07.png)](https://www.waveshare.com/wiki/File:Game-HAT-Manual07.png)

Unzip the downloaded files to obtain the following ROMs

[![Game-HAT-Manual08.png](https://www.waveshare.com/w/upload/thumb/9/90/Game-HAT-Manual08.png/600px-Game-HAT-Manual08.png)](https://www.waveshare.com/wiki/File:Game-HAT-Manual08.png)

- Update ROMs

Connect an Ethernet cable to the Raspberry Pi (the Raspberry Pi needs to be on the same local network as your PC). Find SHOW IP under the RetroPie menu and press "A" to view the current Raspberry Pi's IP address. See the figure below:

[![Game-HAT-Manual09.jpg](https://www.waveshare.com/w/upload/thumb/9/95/Game-HAT-Manual09.jpg/600px-Game-HAT-Manual09.jpg)](https://www.waveshare.com/wiki/File:Game-HAT-Manual09.jpg)

On your PC, open the corresponding IP address in a web browser. See the figure below:

[![Game-HAT-Manual10.png](https://www.waveshare.com/w/upload/thumb/2/24/Game-HAT-Manual10.png/600px-Game-HAT-Manual10.png)](https://www.waveshare.com/wiki/File:Game-HAT-Manual10.png)

Simply copy the ROMs to the relevant directory. See the figure below:

[![Game-HAT-Manual11.png](https://www.waveshare.com/w/upload/thumb/0/06/Game-HAT-Manual11.png/600px-Game-HAT-Manual11.png)](https://www.waveshare.com/wiki/File:Game-HAT-Manual11.png)

After that, in the emulator selection interface, press "Start"->QUIT->RESTART EMULATIONSTATION，and press "A" to confirm. After restarting the emulator, you will see the newly added games.

So, embark on your retro gaming journey!

## Parameter introduction

By setting the display\_hdmi\_rotate parameter in the config.txt file, you can adjust the orientation of the HDMI display, including rotation and flipping.

Here is a detailed explanation of the parameters:

| display\_hdmi\_rotate | result |
| --- | --- |
| 0 | no rotation (default direction) |
| 1 | rotate 90 degrees clockwise |
| 2 | rotate 180 degrees clockwise |
| 3 | rotate 270 degrees clockwise |
| 0x10000 | horizontal flip |
| 0x20000 | vertical flip |

- You can also combine settings to achieve more complex effects. For example:

180-degree rotation + horizontal and vertical flip= 0x20000 + 0x10000 + 2 = 0x30002

- If you set display\_hdmi\_rotate=1(90 degrees) or display\_hdmi\_rotate=3 (270 degrees), the system will use additional GPU memory to complete the image rotation.

For devices with GPU memory set to 16MB, these options may not work properly. You can modify the gpu\_mem parameter in the config.txt file to increase the GPU memory allocation.

```
gpu_mem=64
```

# RP2040-PiZero Tutorial

## Running Demo

### Install Thonny IDE

To facilitate the development of RP2040-PiZero boards using MicroPython on your computer, it is recommended to download Thonny IDE.

- Download [Thonny IDE](https://files.waveshare.com/wiki/GamePi13/Doc/Thonny-3.3.3.zip) and install it according to the steps provided. The installation packages are for Windows versions; for other versions, please refer to [thonny.org](https://thonny.org/).
- After installation, you need to configure the language and board environment for the first time. Since we are using RP2040-PiZero, pay attention to selecting the Raspberry Pi option for the board environment


[![Pico-R3-Tonny1.png](https://www.waveshare.com/w/upload/thumb/e/e4/Pico-R3-Tonny1.png/600px-Pico-R3-Tonny1.png)](https://www.waveshare.com/wiki/File:Pico-R3-Tonny1.png)

### MicroPython

1.Download and unzip the [MicroPython firmware](https://files.waveshare.com/wiki/GamePi13/RPI_PICO-20250415-v1.25.0.uf2) in .uf2 format.

2.Hold the BOOT button, connect the device to your computer, then release the BOOT button. A removable disk will appear on your computer. Copy the firmware onto it.

3.Download and unzip the [sample program](https://files.waveshare.com/wiki/GamePi13/Micropython_GamePi13.zip), then upload the code to the Raspberry Pi Pico. Here are the steps.(using the Tetris game as an example)

- In the view, check the files and select the corresponding file path in the left toolbar


[![Thonny gamepi13 1.png](https://www.waveshare.com/w/upload/6/63/Thonny_gamepi13_1.png)](https://www.waveshare.com/wiki/File:Thonny_gamepi13_1.png)

[![Thonny gamepi13 2.png](https://www.waveshare.com/w/upload/thumb/7/71/Thonny_gamepi13_2.png/600px-Thonny_gamepi13_2.png)](https://www.waveshare.com/wiki/File:Thonny_gamepi13_2.png)

- Select all files and right-click to upload


[![Thonny gamepi13 3.png](https://www.waveshare.com/w/upload/6/64/Thonny_gamepi13_3.png)](https://www.waveshare.com/wiki/File:Thonny_gamepi13_3.png)

4.After the upload is successful, unplug the USB, insert the GamePi13 into the RP2040-PiZero, and power it on again to automatically run the game program.

### CircuitPython

1.Download and unzip the [CircuitPython firmware](https://files.waveshare.com/wiki/GamePi13/Flappybird.zip) in .uf2 format.

2.Hold the BOOT button, connect the device to your computer, then release the BOOT button. A removable disk will appear on your computer. Copy the firmware onto it, and wait for a few seconds for another disk to appear.

3.Delete all files in the newly generated removable disk, download and unzip the [sample program](https://files.waveshare.com/wiki/GamePi13/Circuitpython_GamePi13.zip) , and copy all files from the "flappybird-CODE" folder of the sample program into the disk, as shown in the figure below.

[![Thonny gamepi13 4.png](https://www.waveshare.com/w/upload/thumb/8/80/Thonny_gamepi13_4.png/600px-Thonny_gamepi13_4.png)](https://www.waveshare.com/wiki/File:Thonny_gamepi13_4.png)

4.After the copy is successful, unplug the USB, insert the GamePi13 into the RP2040-PiZero, and power it on again to automatically run the game program.

### C/C++ Series

#### Environment Setup

For C/C++, it is recommended to use the Pico VS Code extension, which is a Microsoft Visual Studio Code extension designed to make it easier for you to create, develop, and debug projects for the Raspberry Pi Pico series of development boards. Whether you are a beginner or an experienced professional, this tool can help you develop Pico with confidence and ease. Below, we will introduce how to install this extension and use it.

- Official tutorial： [https://www.raspberrypi.com/news/pico-vscode-extension/](https://www.raspberrypi.com/news/pico-vscode-extension/)
- This tutorial is suitable for Raspberry Pi Pico, Pico2, and the RP2040, RP2350 series development boards developed by our company
- The development environment is by default based on Windows, for other environments please refer to the official tutorial for installation

##### Install VSCode

1.First, click to download the [pico-vscode package](https://files.waveshare.com/wiki/GamePi13/Doc/pico-vscode.zip), unzip it, open the package, and double-click to install VSCode

[![Pico-vscode-1.jpg](https://www.waveshare.com/w/upload/thumb/9/92/Pico-vscode-1.jpg/600px-Pico-vscode-1.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-1.jpg)

Note: If you have already installed VSCode, make sure the version is 1.87.0 or higher

[![Pico-vscode-2.jpg](https://www.waveshare.com/w/upload/thumb/a/a6/Pico-vscode-2.jpg/600px-Pico-vscode-2.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-2.jpg)

[![Pico-vscode-3.jpg](https://www.waveshare.com/w/upload/thumb/5/5d/Pico-vscode-3.jpg/300px-Pico-vscode-3.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-3.jpg)

##### Install the extension

1.Click on Extensions, and choose to install from VSIX

[![Pico-vscode-4.jpg](https://www.waveshare.com/w/upload/a/a4/Pico-vscode-4.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-4.jpg)

2.Select the software package with the vsix suffix and click to install

[![Pico-vscode-5.jpg](https://www.waveshare.com/w/upload/0/09/Pico-vscode-5.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-5.jpg)

3.Then VSCode will automatically install the raspberry-pi-pico and its dependent extensions. You can click to refresh to view the installation progress

[![Pico-vscode-6.jpg](https://www.waveshare.com/w/upload/5/5f/Pico-vscode-6.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-6.jpg)

4.Once the installation is complete, as indicated in the bottom right corner, close VSCode

[![Pico-vscode-7.jpg](https://www.waveshare.com/w/upload/thumb/8/81/Pico-vscode-7.jpg/600px-Pico-vscode-7.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-7.jpg)

##### Configure the extension

1.Open the directory C:\\Users\\Username, and copy the entire .pico-sdk to this directory

[![Pico-vscode-8.jpg](https://www.waveshare.com/w/upload/thumb/6/60/Pico-vscode-8.jpg/600px-Pico-vscode-8.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-8.jpg)

2.Copying is complete

[![Pico-vscode-9.jpg](https://www.waveshare.com/w/upload/thumb/3/33/Pico-vscode-9.jpg/600px-Pico-vscode-9.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-9.jpg)

3.Open VSCode and configure the paths for the Raspberry Pi Pico extension

[![Pico-vscode-10.jpg](https://www.waveshare.com/w/upload/thumb/f/f0/Pico-vscode-10.jpg/600px-Pico-vscode-10.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-10.jpg)

Configurations are as follows:

```
Cmake Path：
${HOME}/.pico-sdk/cmake/v3.28.6/bin/cmake.exe

Git Path:
${HOME}/.pico-sdk/git/cmd/git.exe

Ninja Path:
${HOME}/.pico-sdk/ninja/v1.12.1/ninja.exe

Python3 Path:
${HOME}/.pico-sdk/python/3.12.1/python.exe
```

##### Create a new project

1.After configuration, test by creating a new project. Enter the project name and select the path, then click Create to create the project

Test the official examples by clicking on the Example next to the project name to select

[![Pico-vscode-11.jpg](https://www.waveshare.com/w/upload/thumb/f/f6/Pico-vscode-11.jpg/600px-Pico-vscode-11.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-11.jpg)

2.Once the project is created successfully, you can proceed to the next steps

[![Pico-vscode-12.jpg](https://www.waveshare.com/w/upload/thumb/6/69/Pico-vscode-12.jpg/600px-Pico-vscode-12.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-12.jpg)

3.Select SDK Version

[![Pico-vscode-13.jpg](https://www.waveshare.com/w/upload/thumb/1/1e/Pico-vscode-13.jpg/600px-Pico-vscode-13.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-13.jpg)

4.Choose Yes to proceed with advanced configuration

[![Pico-vscode-14.JPG](https://www.waveshare.com/w/upload/6/6d/Pico-vscode-14.JPG)](https://www.waveshare.com/wiki/File:Pico-vscode-14.JPG)

5.Select the cross-compilation toolchain. 13.2.Rel1 is suitable for ARM cores, and RISCV.13.3 is suitable for RISCV cores. You can choose either according to your needs

[![Pico-vscode-15.JPG](https://www.waveshare.com/w/upload/3/35/Pico-vscode-15.JPG)](https://www.waveshare.com/wiki/File:Pico-vscode-15.JPG)

6.Choose the CMake version as Default (the path configured earlier)

[![Pico-vscode-16.JPG](https://www.waveshare.com/w/upload/1/1f/Pico-vscode-16.JPG)](https://www.waveshare.com/wiki/File:Pico-vscode-16.JPG)

7.Choose the Ninja version as Default

[![Pico-vscode-17.JPG](https://www.waveshare.com/w/upload/e/e6/Pico-vscode-17.JPG)](https://www.waveshare.com/wiki/File:Pico-vscode-17.JPG)

8.Select the development board

[![Pico-vscode-18.jpg](https://www.waveshare.com/w/upload/thumb/e/e4/Pico-vscode-18.jpg/600px-Pico-vscode-18.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-18.jpg)

9.Click compile to compile the project

[![Pico-vscode-19.jpg](https://www.waveshare.com/w/upload/thumb/5/5a/Pico-vscode-19.jpg/600px-Pico-vscode-19.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-19.jpg)

10.Once the compilation is successful, you will get a .uf2 file

[![Pico-vscode-20.jpg](https://www.waveshare.com/w/upload/thumb/b/bd/Pico-vscode-20.jpg/600px-Pico-vscode-20.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-20.jpg)

##### Import a project

1.Open a [C example program](https://files.waveshare.com/wiki/GamePi13/Doc/Gamepi_RP2040_C.zip) and import the project. Note: The Cmake file for the imported project must not contain Chinese characters (including comments), as this may cause the import to fail

2.Once you have successfully compiled a .uf2 file, you can proceed to update the firmware

[![Pico-vscode-20.JPG](https://www.waveshare.com/w/upload/f/f7/Pico-vscode-20.JPG)](https://www.waveshare.com/wiki/File:Pico-vscode-20.JPG)

3.After connecting the device to your computer while holding down the BOOT button, release the BOOT button. A removable disk will appear on your computer. Copy the .uf2 file into it.

##### Update the extension

1.The extension version in the offline package is 0.15.2. After installation, you can also choose to update to the latest version

[![Pico-vscode-22.jpg](https://www.waveshare.com/w/upload/thumb/5/5b/Pico-vscode-22.jpg/600px-Pico-vscode-22.jpg)](https://www.waveshare.com/wiki/File:Pico-vscode-22.jpg)

### Open Source Demos

[MircoPython Video Demo (github)](https://github.com/waveshareteam/Pico_MircoPython_Examples)

[MicroPython Firmware/Blink Demo（C）](https://files.waveshare.com/wiki/GamePi13/Doc/Raspberry_Pi_Pico_Demo.zip)

[Raspberry Pi Official C/C++ Demos(github)](https://github.com/raspberrypi/pico-examples/)

[Raspberry Pi Official MicroPython Demos(github)](https://github.com/raspberrypi/pico-micropython-examples)

# Resources

## Demo

[GamePi13 RP2040 Demo](https://files.waveshare.com/wiki/GamePi13/Doc/Gamepi13-RP2040-Demo.zip)

## Datasheets

- [1.3 inch LCD Datasheet](https://files.waveshare.com/wiki/common/1.3inch_LCD_Module.pdf)
- [ST7789VW Datasheet](https://files.waveshare.com/wiki/common/ST7789VW.pdf)

## Schematic

- [GamePi13 Schematic Diagram](https://files.waveshare.com/wiki/RPi-1.3inch-MINI-LCD.pdf)

## Software

- [Zimo221 Chinese character conversion software](https://files.waveshare.com/wiki/common/Zimo221.7z)
- [Image2Lcd image bitmap conversion software](https://files.waveshare.com/wiki/common/Image2Lcd2.9.zip)
- [Image bitmap conversion tutorial](https://www.waveshare.com/wiki/Image_extraction)
- [Font library conversion tutorial](https://www.waveshare.com/wiki/E-Paper_Font_Tutorial)
- [Flash\_download\_tool](https://dl.espressif.com/public/flash_download_tool.zip)

# Support

Technical Support

If you need technical support or have any feedback/review, please click the **Submit Now** button to submit a ticket, Our support team will check and reply to you within 1 to 2 working days. Please be patient as we make every effort to help you to resolve the issue.


Working Time: 9 AM - 6 PM GMT+8 (Monday to Friday)

[Submit Now](https://service.waveshare.com/)

Retrieved from " [https://www.waveshare.com/w/index.php?title=GamePi13&oldid=105165](https://www.waveshare.com/w/index.php?title=GamePi13&oldid=105165)"