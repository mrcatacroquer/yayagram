# The Yayagram

# Intro

Hello! I'm Manu ([@mrcatacroquer](https://twitter.com/mrcatacroquer)), the guy who created the first Yayagram, A
machine that helps our beloved elders to keep communicating with their
grandchildren.

In this guide I'll explain you how to build your own Yayagram.

https://twitter.com/mrcatacroquer/status/1386318806411325440?s=20

# Disclaimer

I'm not an expert, I'm not a guru, I'm just an average guy.
So, if you see something that can be improved, fork it and change it, you are
also very welcome to comment anything or ask me anything. I'll be happy to keep
learning and help.

# Ingredients

To build the original Yayagram you will need  the following items but you can
change it to match your necessities. At the bottom of this guide I'll enumerate
a few variations.

| Item      | Description | Average price |
| ----------- | ----------- | ----------- |
|[Raspberry pi 4](https://www.raspberrypi.org/products/raspberry-pi-4-model-b/) | The brain of the project|40€
|[Jack connectors and sockets](https://en.wikipedia.org/wiki/Phone_connector_(audio))|To access the source and destination people| 20€ |
|Microphone cable | To connect people | 3€
|32Gb Micro SD Card | To store the Raspberry Pi OS | 8€
|Arcade button | To start recording the message|1€
|USB Microphone | To record the message|10€
|Thermal printer. | To print the messages|30€
|Powerful power supply 5V | Juice for the Pi |10€
|Powerful power supply 9V | Juice for the thermal printer|10€
|Cables. | For the electronic connections|3€
|A box. | To frame the project |10€
|HDMI Cable | To connect the Pi to a screen|10€

I assume that you already have basic items like a soldering iron, a screen,
a keyboard and a mouse. So the total cost is around 155€.

I recommend you to buy all the items at your local electronic shop. It might
be slighter more expensive but it's important to support the local business.

Some parts like the thermal printer might be hard to find, so for those search
the internet to find the cheapest option.

# Raspberry Pi setup

First you will need to install the most up to date Raspberry Pi OS in your
Raspberry Pi SD card. There's a tool called "Raspberry Pi Imager" that does it
in no time and it's very straightforward to use.

Open the Raspberry Pi Imager tool, you need to choose the OS you want to
install, and the SD card you want to use for the Raspberry Pi.

I chose the default "Raspberry PI OS" which is based on Debian, and optimized
for the Raspberry Pi hardware.

Once the flashing process finish you can remove the SD card from the reader and
insert it inside the Raspberry Pi.

### Boot your Raspberry Pi and first steps.

The first time you boot your Raspberry Pi it might take more time to start, it's
normal, it has to automatically configure a lot of things, but you will also need
to accomplish some manual steps.

The start-up wizard will ask you to select:
- Your time zone.
- Language.
- Wifi network to connect to.

After you made your selection it will ask you to do a software upgrade, I
recommend you to do it. It might take a while depending on your Raspberry Pi
version and Internet speed.

Once the software updates are installed the Raspberry Pi asks you to reboot.

### Enable SSH in the raspberry pi

This is optional but very useful, it will allow you to access the Raspberry Pi
using a SSH client, like [Putty](https://www.putty.org). It will save you from
connecting the Pi to a keyboard, mouse and screen every time you want to check
something.

Open a terminal window in your Raspberry Pi, [here you can find how](https://magpi.raspberrypi.org/articles/terminal-help). And now type the following
commands:
```
sudo systemctl enable ssh
sudo systemctl start ssh
```

This is going to be useful when we turn the rasp into a headless machine.

To check the Rasp Pi IP you can run a ping command from another computer
connected to the same network, use the default Pi name: "*raspberrypi*"

```
C:\Users\manu>ping -4 raspberrypi

Pinging raspberrypi.local [192.168.2.159] with 32 bytes of data:
Reply from 192.168.2.159: bytes=32 time=88ms TTL=64
Reply from 192.168.2.159: bytes=32 time=5ms TTL=64
Reply from 192.168.2.159: bytes=32 time=5ms TTL=64
Reply from 192.168.2.159: bytes=32 time=5ms TTL=64
```
So now, using Putty, we can access it to install what is left to do.
```
login as: pi
pi@192.168.2.159's password:
Linux raspberrypi 5.10.17-v7+ #1403 SMP Mon Feb 22 11:29:51 GMT 2021 armv7l

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Last login: Sat May  1 11:36:33 2021
pi@raspberrypi:~ $
```

# Software
Let's talk about the software needed for this project.

### Telegram
This project use Telegram to send and receive messages using the Raspberry Pi.
We need to components, one is a command line interface to do all the Telegram
actions, the other a wrapper in Python that uses the first application and
symplifies its usage.

#### TG CLI

[This](https://github.com/kenorb-contrib/tg) is the command line for Telegram
as the core of the sudo telegram communications.

Execute the commands below to download and compile the project:

- git clone --recursive https://github.com/kenorb-contrib/tg.git && cd tg
- sudo apt-get install libreadline-dev libconfig-dev libssl-dev lua5.2 liblua5.2-dev libevent-dev libjansson-dev libpython-dev libpython3-dev libgcrypt-dev zlib1g-dev lua-lgi make
- ./configure
- make

The *make* command might take a few minutes to complete. If everything ends fine
you should see this once the *make* finishes.

```shell
a - objs/auto/auto-fetch-ds.o
a - objs/auto/auto-free-ds.o
a - objs/auto/auto-store-ds.o
a - objs/auto/auto-print-ds.o
gcc objs/main.o objs/loop.o objs/interface.o objs/lua-tg.o objs/json-tg.o objs/python-tg.o objs/python-types.o libs/libtgl.a -L/usr/local/lib -L/usr/lib -L/usr/lib  -rdynamic -ggdb -levent -ljansson -lconfig -lz -levent   -lreadline -llua5.2  -lm -ldl -lssl -lcrypto -lpthread -lutil -ldl -o bin/telegram-cli
pi@raspberrypi:~/tg $
```
#### Python wrapper to use the telegram library

Now its time for the [Python wrapper](https://github.com/luckydonald/pytg), this
library provides everything you need to interact with the telegram commands
through the CLI TG application.

Run the following command to install it:
- pip3 install pytg

The output should look like this:
```shell
pi@raspberrypi:~/tg $ pip3 install pytg
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Collecting pytg
  Downloading https://www.piwheels.org/simple/pytg/pytg-0.4.10-py3-none-any.whl
Collecting luckydonald-utils>=0.17 (from pytg)
  Downloading https://files.pythonhosted.org/packages/36/31/e1f75be41cca1f9582551786deaa55c38d4cd07ab86264c6613038ef871d/luckydonald_utils-0.83-py3-none-any.whl (82kB)
    100% |████████████████████████████████| 92kB 1.2MB/s
Collecting DictObject (from pytg)
  Downloading https://www.piwheels.org/simple/dictobject/DictObject-1.1.1-py3-none-any.whl
Requirement already satisfied: pip in /usr/lib/python3/dist-packages (from luckydonald-utils>=0.17->pytg) (18.1)
Requirement already satisfied: setuptools in /usr/lib/python3/dist-packages (from luckydonald-utils>=0.17->pytg) (40.8.0)
Installing collected packages: DictObject, luckydonald-utils, pytg
Successfully installed DictObject-1.1.1 luckydonald-utils-0.83 pytg-0.4.10
```

### The thermal printer

* [Tutorial](https://www.hackster.io/glowascii/using-a-thermal-printer-with-raspberry-pi-d74619)
* https://learn.adafruit.com/networked-thermal-printer-using-cups-and-raspberry-pi/connect-and-configure-printer


# Telegram Setup

Now its time to bind the TG CLI tool to a real Telegram account. To do it
please follow these instructions.

You need to change your directory to the */home/pi/tg/bin* directory:
```shell
cd /home/pi/tg/bin/
```
Run the *telegram-cli* application. This is your very first time running it so
it will ask you for the phone number you want to use to connect to Telegram.
You need to provide the country code as well.

```
pi@raspberrypi:~/tg/bin $ ./telegram-cli
Telegram-cli version 1.4.1, Copyright (C) 2013-2015 Vitaly Valtman
Telegram-cli comes with ABSOLUTELY NO WARRANTY; for details type `show_license'.
This is free software, and you are welcome to redistribute it
under certain conditions; type `show_license' for details.
Telegram-cli uses libtgl version 2.1.0
Telegram-cli includes software developed by the OpenSSL Project
for use in the OpenSSL Toolkit. (http://www.openssl.org/)
I: config dir=[/home/pi/.telegram-cli]
[/home/pi/.telegram-cli] created
[/home/pi/.telegram-cli/downloads] created
phone number:
```

The phone receives a validation code through Telegram as soon as you type enter.

Provide the code to the tool and the TG CLI app will store it for the future.

```
phone number: +34651XXXXXX
code ('CALL' for phone code): 17626
User Manu XXXXXXX updated flags -- [2021/05/01 17:19:23]
User Manu XXXXXXX offline (was online [2021/05/01 17:19:47])
```
If you want to change the phone number to use another one you just need to
remove the following directory and all its content: */home/pi/.telegram-cli*

### Test it

Create a *tg-test.py* file with the following content. Well, not exactly it,
replace *@theTelegramContact* with the real Telegram user name you want to use
as the destination of the "Hello from Python API!" message.

```python
import logging

from pytg import Telegram
tg = Telegram(
	telegram="/home/pi/tg/bin/telegram-cli",
	pubkey_file="/home/pi/tg/tg-server.pub")

sender = tg.sender

res = sender.msg("@theTelegramContact", "Hello from Python API!")
```

You should see something like this:


# Hardware

At the hardware side we are going to work with cables, connectors, a button and
a microphone.

### GPIO

GPIO pins are going to be used to read the input signals.
User the *pinout* command to check the GPIO ports you
can use.

Don't connect the power directly to the pin as it would be
dangerous! Use something like this in the middle:

Make sure there is enough resistance in the
circuit. Also, never connect the 5V power directly to
the GPIO as it only accepts 3.3V. [Source](https://raspberrypi.stackexchange.com/questions/14680/raspberry-pi-gpio-input-pins-give-random-values)

https://github.com/mrcatacroquer/Yayagram/blob/42eb97c3873d2ab9ef27cd3d421dd03ed9d28dc2/images/IMG_8635.JPEG

![image](https://github.com/mrcatacroquer/Yayagram/blob/42eb97c3873d2ab9ef27cd3d421dd03ed9d28dc2/images/IMG_8635.JPEG)
### Microphone

Setup USB Mic: https://pimylifeup.com/raspberrypi-microphone/

### Printer

# Creating the Systemd service

In order to execute the yayagram.py script on the Raspberry Pi and restart it
in case of unexpected crashes we are going to create a Systemd service.

[Here](https://www.shubhamdipt.com/blog/how-to-create-a-systemd-service-in-linux/)
you can read more about how to do it with extra details, but I'm going to give
you the minimal information to get it running.

Create a file at "/etc/systemd/system" called *yayagram.service*, and add the
following content:

```
[Unit]
Description=The Yayagram
After=multi-user.target network.target syslog.target

[Service]
Restart=on-failure
RestartSec=4
Type=idle
WorkingDirectory=/home/pi/Desktop
User=pi
ExecStart=/usr/bin/python3 /home/pi/Desktop/yayagram.py

[Install]
WantedBy=multi-user.target
```
Reload the services list:
```
sudo systemctl daemon-reload
```
Start the ysyagram service:
```
sudo systemctl start yayagram.service
```
And, enable it so it starts the next time you reboot your Raspberry Pi:
```
sudo systemctl enable example.service
```

### LEDS

Starter tutorial about how to use LEDS: https://thepihut.com/blogs/raspberry-pi-tutorials/27968772-turning-on-an-led-with-your-raspberry-pis-gpio-pins
