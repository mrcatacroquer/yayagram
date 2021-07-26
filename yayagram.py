# coding=utf-8

from __future__ import unicode_literals
from __future__ import print_function
import base64, sys
from configparser import ConfigParser
from pytg.utils import coroutine
from pytg import Telegram
from thermalprinter import *
from datetime import datetime
from multiprocessing import Process
import textwrap
import threading
import time
import RPi.GPIO as GPIO
import shlex
import uuid
import subprocess
import signal
import os
import os.path
import re

STOP_TG = False
STATUS = True

CONFIG_FILE = 'yayagram.conf'
CONFIG = ConfigParser()

def main():
    print("Loading config")
    load_config()
    print ("Doing pins setup")
    setup_pins()
    print ("Creating Telegram object")
    tg = Telegram(
        telegram=CONFIG['global']['TG_CLI_PATH'],
        pubkey_file=CONFIG['global']['TG_PUB_PATH'])
    print("Creating the receiver and the sender")
    receiver = tg.receiver
    sender = tg.sender
    print("Creating the printer")
    printer = ThermalPrinter(port=
        CONFIG['printer']['ADDR'],
        baudrate=CONFIG['printer']['BAUDRATE']
        )

    # start the Receiver, so we can get messages!
    print("Starting the Telegram message receiver")
    receiver.start()  # note that the Sender has no need for a start function.

    try:
        print("Running testconnection")
        test_connection_thread = Process(
            target=test_connection, args=(sender, printer,), name="TestConnectionThread")
        test_connection_thread.start()
        test_connection_thread.join(timeout=10)

        if test_connection_thread.exitcode is None:
            print(f'Oops, {test_connection_thread} timeouts!')
            STATUS = False
            kill_telegram_cli()
            sys.exit(1)

    except Exception as e:
        print_exception(e)
        STATUS = False
        sys.exit(1)

    print("Creating Sender thread")
    sender_thread = threading.Thread(target=sender_worker, args=(sender,))
    sender_thread.setName("TheSenderThread")
    sender_thread.daemon = True
    sender_thread.start()
    print("Creating Status thread")
    status_thread = threading.Thread(target=status_worker)
    status_thread.setName("TheStatusThread")
    status_thread.daemon = True
    status_thread.start()
    print("Creating the callback")
    receiver.message(receiver_function(sender, printer))

    # continues here, after exiting the while loop in receiver_function()
    print("Waiting for sender thread")
    sender_thread.join()
    print("Waiting for status thread")
    status_thread.join()
    GPIO.output(int(CONFIG['global']['STATUS_LED_PIN']),GPIO.LOW)
    sender.status_offline()
    print("Trying to safe quit")

    try:
        sender.safe_quit()
    except Exception as e:
        print_exception(e)
        print ("Safe quit failed")

    time.sleep(1)
    print("Going to quit sender")

    try:
        sender.quit()
    except Exception as e:
        print_exception(e)
        print("Receiver stop failed")

    kill_telegram_cli()
    time.sleep(1)
    print("Bye")

    sys.exit(0)
    # the sender will disconnect after each send, so there is no need to stop it.
    # if you want to shutdown the telegram cli:
    # sender.safe_quit() # this shuts down the telegram cli.
    # sender.quit() # this shuts down the telegram cli, without waiting for downloads to complete.

def test_connection(sender, printer):
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    print("Going to send test_connection TG message")
    message = "Yayagram up: " + dt_string
    res = sender.send_msg(CONFIG['admin']['ADMIN_ID'], message)
    print("Test connection response: {response}".format(response=res))
    printer.out("--------------------------------",size='S')
    printer.out(message,size="S",codepage=CodePage.ISO_8859_1)
    printer.out("--------------------------------",size='S')
    printer.feed(2)

def setup_pins():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for x in range(int(CONFIG['destinations']['DST_MAX'])):
        GPIO.setup(
            int(CONFIG['destinations']['DST' + str(x) + '_PIN']),
            GPIO.IN,
            pull_up_down = GPIO.PUD_DOWN)

    GPIO.setup(int(CONFIG['destinations']['ALL_PIN']), GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
    GPIO.setup(int(CONFIG['recording']['RECORD_BUTTON_PIN']), GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
    GPIO.setup(int(CONFIG['global']['STATUS_LED_PIN']), GPIO.OUT)
    GPIO.setup(int(CONFIG['recording']['RECORDING_LED_PIN']), GPIO.OUT)
    GPIO.output(int(CONFIG['global']['STATUS_LED_PIN']),GPIO.HIGH)
    GPIO.output(int(CONFIG['recording']['RECORDING_LED_PIN']),GPIO.LOW)

def status_worker():
    global STOP_TG
    while not STOP_TG:
        GPIO.output(int(CONFIG['global']['STATUS_LED_PIN']),GPIO.HIGH)
        time.sleep(1)
        if (STATUS):
            GPIO.output(int(CONFIG['global']['STATUS_LED_PIN']),GPIO.LOW)
        time.sleep(1)

def sender_worker(sender):
    while not STOP_TG:
        if (GPIO.input(int(CONFIG['recording']['RECORD_BUTTON_PIN'])) == 0):
            time.sleep(0.30)
            continue

        try:
            destination = get_yayagram_destination()
            filename=do_recording()
            send_recording(sender, destination, filename)
            os.remove(filename)
        except Exception as e:
            print_exception(e)
            GPIO.output(int(CONFIG['recording']['RECORDING_LED_PIN']),GPIO.LOW)

def send_recording(sender, destination, filetosend):
    if (os.path.isfile(filetosend) == False):
        sender.send_msg(destination, CONFIG['recording']['RECORDING_SEND_ERROR_MSG'])
        return

    print ("dst" + str(destination))
    print ("all" + str(CONFIG['destinations']['ALL_PIN']))

    if (destination == int(CONFIG['destinations']['ALL_PIN'])):
        send_broadcast(sender, filetosend)
        return

    sender.send_msg(destination, CONFIG['global']['NEW_MSG_FOR_YOU'])
    sender.send_audio(destination, filetosend)

def send_broadcast(sender, filetosend):
    print("Send broadcast")
    for x in range(int(CONFIG['destinations']['DST_MAX'])):
        print (str(x))
        if not CONFIG.has_option('destinations', 'DST' + str(x) + '_TGID'):
            continue

        destination_user_id = CONFIG['destinations']['DST' + str(x) + '_TGID']
        message = CONFIG['global']['BROADCAST_MESSAGE']

        sender.send_msg(destination_user_id, message)
        sender.send_audio(destination_user_id, filetosend)

def do_recording():
    GPIO.output(int(CONFIG['recording']['RECORDING_LED_PIN']),GPIO.HIGH)
    fileName = CONFIG['recording']['RECORDINGS_PATH'] + str(uuid.uuid4()) + ".wav"
    command = CONFIG['recording']['ARECORD_PATH'] + " -D plughw:" + CONFIG['recording']['PLUG_HW'] + " --format=S16_LE --rate=16000 --file-type=wav " + fileName
    popen_cmd = shlex.split(command)
    pro = subprocess.Popen(popen_cmd, stdout=subprocess.PIPE, shell=False, preexec_fn=os.setsid)

    while (GPIO.input(int(CONFIG['recording']['RECORD_BUTTON_PIN']))):
        time.sleep(0.30)

    os.killpg(os.getpgid(pro.pid), signal.SIGTERM)

    GPIO.output(int(CONFIG['recording']['RECORDING_LED_PIN']),GPIO.LOW)

    time.sleep(0.30)

    return fileName

def get_yayagram_destination():
    for x in range(int(CONFIG['destinations']['DST_MAX'])):
        if not CONFIG.has_option('destinations', 'DST' + str(x) + '_TGID'):
            continue
        if not (GPIO.input(int(CONFIG['destinations']['DST' + str(x) + '_PIN']))):
            continue

        print("The " + CONFIG['destinations']['DST' + str(x) + '_NAME'] +" switch is ON")
        return CONFIG['destinations']['DST' + str(x) + '_TGID']

    if (GPIO.input(int(CONFIG['destinations']['ALL_PIN']))):
        print("The ALL_PIN input is ON")
        return int(CONFIG['destinations']['ALL_PIN'])

# this is the function which will process our incoming messages
@coroutine
def receiver_function(sender, printer):
    global STOP_TG
    quit = False
    try:
        while not quit:  # loop for messages
            print("Message received")

            msg = (yield)  # it waits until the generator has a has message here.
            #sender.status_online()  # so we will stay online.
            # (if we are offline it might not receive the messages instantly,
            #  but eventually we will get them)
            #print(msg)
            messageText = ""
            try:
                if msg.event != "message":
                    continue  # is not a message.
                if msg.own:  # the bot has send this message.
                    continue
                if msg.text is None:  # we have media instead.
                    continue  # and again, because we want to process only text message.
                messageText = msg.text
            except:
              messageText = "El Yayagram solo admite texto, " + str(msg.peer.first_name) + "."
              sender.send_msg(msg.peer.cmd, messageText)
              continue

            clean_messageText=demojify(messageText)
            
            print ("Valid message received from " + str(msg.peer.first_name) + ": " + messageText)
            try:
                if (messageText.startswith(CONFIG['admin']['COMMAND_PREFIX'])):
                    process_command(sender, messageText, msg)
                    continue

                if messageText.lower() == "kill":
                    if not is_user_admin(sender, msg):
                        continue

                    sender.send_msg(msg.sender.cmd, u"Bye!")
                    quit = True
                    STOP_TG = True
                    continue

                
                
                printer.out("--------------------------------",size='S')
                printer.out("De "+str(msg.peer.first_name) +" :",size='L',codepage=CodePage.ISO_8859_1)

                lines = clean_messageText.split("\n")
                lists = (textwrap.TextWrapper(width=32,break_long_words=False).wrap(line) for line in lines)
                messageToPrint  = "\n".join("\n".join(list) for list in lists)
                
                printer.out(messageToPrint,size="M",codepage=CodePage.ISO_8859_1)
                printer.out("--------------------------------",size='S')
                
                printer.feed(2)

                sender.send_msg(msg.peer.cmd, CONFIG['global']['THANK_YOU_FOR_MSG'])
            except Exception as e:
                print_exception(e)

    except GeneratorExit:
        print ("Generator exited")
        STOP_TG = True
        pass
    except KeyboardInterrupt:
        print ("KeyboardIterrupt(Ctrl+C) received")
        STOP_TG = True
        pass
    else:
        print ("Admin requested to quit")
        STOP_TG = True
        pass

def demojify(text):
    regrex_pattern = re.compile(pattern = "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags = re.UNICODE)
    return regrex_pattern.sub(r'',text)

def process_command(sender, command, msg):
    command = command.strip(CONFIG['admin']['COMMAND_PREFIX']).lower()

    if (command == "ping"):
        sender.send_msg(msg.peer.cmd, u"pong")
        return

    if (command.startswith("printboard")):
        printboard(sender, msg)
        return

    if (command.startswith("lockedits")):
        lock_edits(sender, msg)
        return

    if (command.startswith("unlockedits")):
        unlock_edits(sender, msg)
        return

    if eval(CONFIG['admin']['ADMIN_LOCK']):
        sender.send_msg(msg.peer.cmd, CONFIG['global']['YAYAGRAM_LOCKED'])
        return

    if (command.startswith("addmeasroot")):
        add_user_as_root(sender, msg)
        return

    if (command.startswith("addme")):
        add_user_to_board(sender, command, msg)
        return

    if (command.startswith("removeme")):
        remove_user_from_board(sender, msg)
        return

    sender.send_msg(msg.peer.cmd, u"Unknown command.")

def printboard(sender, msg):
    sender.send_msg(msg.peer.cmd, "Users at the Yayagram board:")
    for x in range(int(CONFIG['destinations']['DST_MAX'])):
        if not CONFIG.has_option('destinations', 'DST' + str(x) + '_TGID'):
            continue

        message = '''# {name}\nBoard position: {position}.\nTelegram ID: {tgid}.\nRaspPi PIN: {pin}.'''.format(
            name=CONFIG['destinations']['DST' + str(x) + '_NAME'],
            position=CONFIG['destinations']['DST' + str(x) + '_BOARD_POSITION'],
            tgid=CONFIG['destinations']['DST' + str(x) + '_TGID'],
            pin=CONFIG['destinations']['DST' + str(x) + '_PIN'])

        sender.send_msg(msg.peer.cmd, message)

def add_user_as_root(sender, msg):
    if CONFIG.has_option('admin', 'ADMIN_ID'):
        sender.send_msg(msg.peer.cmd, 'Sorry, this Yayagram already has an owner')
        return

    CONFIG.set('admin', 'ADMIN_ID', str(msg.peer.cmd))
    save_config()
    sender.send_msg(msg.peer.cmd, "Added! You are now the Yayagram owner")

def add_user_to_board(sender, command, msg):
    command = command.strip("addme")
    pos = -1
    if bool(command.strip()):
        pos = int(command)
        sender.send_msg(msg.peer.cmd, "Adding user to requested position (" + str(pos) + ")...")
    else:
        sender.send_msg(msg.peer.cmd, "Adding user to first available position...")
        for x in range(int(CONFIG['destinations']['DST_MAX'])):
            if CONFIG.has_option('destinations', 'DST' + str(x) + '_TGID'):
                continue
            pos=x
            sender.send_msg(msg.peer.cmd, "Spot found at " + str(pos) + ", adding now...")
            break

    if pos == -1:
        sender.send_msg(msg.peer.cmd, "Cannot find spot for user.")
        return

    try:
        CONFIG.set('destinations', 'DST' + str(pos) + '_TGID', str(msg.peer.cmd))
        CONFIG.set('destinations', 'DST' + str(pos) + '_NAME', str(msg.peer.first_name))
        CONFIG.set('destinations', 'DST' + str(pos) + '_BOARD_POSITION', str(pos))

        save_config()

        sender.send_msg(msg.peer.cmd, "Added! Your board position is: " + str(pos))
    except Exception as e:
        print_exception(e)

def remove_user_from_board(sender, msg):
    for x in range(int(CONFIG['destinations']['DST_MAX'])):
        if not CONFIG.has_option('destinations', 'DST' + str(x) + '_TGID'):
            continue

        if not CONFIG['destinations']['DST' + str(x) + '_TGID'] == msg.peer.cmd:
            continue

        try:
            sender.send_msg(msg.peer.cmd, "Removing your user from the Yayagram board...")
            CONFIG.remove_option('destinations', 'DST' + str(x) + '_TGID')
            CONFIG.remove_option('destinations', 'DST' + str(x) + '_NAME')
            CONFIG.remove_option('destinations', 'DST' + str(x) + '_BOARD_POSITION')
            sender.send_msg(msg.peer.cmd, "Almost done. Saving removal...")
            save_config()
            sender.send_msg(msg.peer.cmd, "Removed!")
        except Exception as e:
            print_exception(e)

def lock_edits(sender, msg):
    sender.send_msg(msg.peer.cmd, "Locking the Yayagram board")
    if not is_user_admin(sender,msg):
        return

    CONFIG.set('admin', 'ADMIN_LOCK', 'True')
    save_config()
    sender.send_msg(msg.peer.cmd, "Done.")

def unlock_edits(sender, msg):
    sender.send_msg(msg.peer.cmd, "Unlocking the Yayagram board")
    if not is_user_admin(sender,msg):
        return

    CONFIG.set('admin', 'ADMIN_LOCK', 'False')
    save_config()
    sender.send_msg(msg.peer.cmd, "Done.")

def is_user_admin(sender, msg):
    if msg.sender.id != CONFIG['admin']['ADMIN_ID']:
        reply = u"You are not my Admin.\nMy Admin has id {admin_id} but you have {user_id}".format(
            admin_id=CONFIG['admin']['ADMIN_ID'], user_id=msg.sender.id)
        sender.send_msg(msg.sender.cmd, reply)
        return False

    return True


def load_config():
    CONFIG.read(CONFIG_FILE)

    if not CONFIG.has_section('destinations'):
            CONFIG.add_section('destinations')
    if not CONFIG.has_section('admin'):
            CONFIG.add_section('admin')
    if not CONFIG.has_section('recording'):
            CONFIG.add_section('recording')
    if not CONFIG.has_section('printer'):
            CONFIG.add_section('printer')
    if not CONFIG.has_section('global'):
            CONFIG.add_section('global')

    #Printer default parameters
    if not CONFIG.has_option('printer', 'BAUDRATE'):
        CONFIG.set('printer', 'BAUDRATE', '9600')
    if not CONFIG.has_option('printer', 'ADDR'):
        CONFIG.set('printer', 'ADDR', '/dev/serial0')
    #Record default parameters
    if not CONFIG.has_option('recording', 'RECORDINGS_PATH'):
        CONFIG.set('recording', 'RECORDINGS_PATH', '/home/pi/.telegram-cli/uploads/')
    if not CONFIG.has_option('recording', 'RECORD_BUTTON_PIN'):
        CONFIG.set('recording', 'RECORD_BUTTON_PIN', '10')
    if not CONFIG.has_option('recording', 'RECORDING_LED_PIN'):
        CONFIG.set('recording', 'RECORDING_LED_PIN', '26')
    if not CONFIG.has_option('recording', 'ARECORD_PATH'):
        CONFIG.set('recording', 'ARECORD_PATH', '/usr/bin/arecord')
    if not CONFIG.has_option('recording', 'PLUG_HW'):
        CONFIG.set('recording', 'PLUG_HW', '1,0')
    if not CONFIG.has_option('recording', 'RECORDING_SEND_ERROR_MSG'):
        CONFIG.set('recording', 'RECORDING_SEND_ERROR_MSG', 'An error occured while sending the voice message.')
    #Destinations default CONFIG
    if not CONFIG.has_option('destinations', 'DST_MAX'):
        CONFIG.set('destinations', 'DST_MAX', '2')

    if not CONFIG.has_option('destinations', 'DST0_PIN'):
        CONFIG.set('destinations', 'DST0_PIN', '6')

    if not CONFIG.has_option('destinations', 'DST1_PIN'):
        CONFIG.set('destinations', 'DST1_PIN', '5')

    if not CONFIG.has_option('destinations', 'ALL_PIN'):
        CONFIG.set('destinations', 'ALL_PIN', '13')
    #Admin default CONFIG
    if not CONFIG.has_option('admin', 'COMMAND_PREFIX'):
        CONFIG.set('admin', 'COMMAND_PREFIX', '<!>')
    if not CONFIG.has_option('admin', 'ADMIN_LOCK'):
        CONFIG.set('admin', 'ADMIN_LOCK', 'False')
    #Global default CONFIG
    if not CONFIG.has_option('global', 'BROADCAST_MESSAGE'):
        CONFIG.set('global', 'BROADCAST_MESSAGE', 'Yayagram tiene un mensaje para todos las nietas y nietos!!')
    if not CONFIG.has_option('global', 'STATUS_LED_PIN'):
        CONFIG.set('global', 'STATUS_LED_PIN', '21')
    if not CONFIG.has_option('global', 'NEW_MSG_FOR_YOU'):
        CONFIG.set('global', 'NEW_MSG_FOR_YOU', 'Yayagram tiene un mensaje para ti!!')
    if not CONFIG.has_option('global', 'THANK_YOU_FOR_MSG'):
        CONFIG.set('global', 'THANK_YOU_FOR_MSG', 'Thank you, your message has been printed :)')
    if not CONFIG.has_option('global', 'YAYAGRAM_LOCKED'):
        CONFIG.set('global', 'YAYAGRAM_LOCKED', 'This Yayagram configuration is locked.')
    if not CONFIG.has_option('global', 'TG_CLI_PATH'):
        CONFIG.set('global', 'TG_CLI_PATH', '/home/pi/tg/bin/telegram-cli')
    if not CONFIG.has_option('global', 'TG_PUB_PATH'):
        CONFIG.set('global', 'TG_PUB_PATH', '/home/pi/tg/tg-server.pub')

    save_config()

def save_config():
    with open(CONFIG_FILE, 'w') as configfile:
        CONFIG.write(configfile)

def kill_telegram_cli():
    for line in os.popen("ps ax | grep telegram-cli | grep -v grep"):
        fields = line.split()
        pid = fields[0]
        os.kill(int(pid), signal.SIGKILL)

def print_exception(e):
    if hasattr(e, 'message'):
        print("Exception sending message" + e.message)
    else:
        print("Exception sending message" + str(e))

# # program starts here ##
if __name__ == '__main__':
    main()
