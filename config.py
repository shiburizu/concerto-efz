import os
import sys
import logging
if getattr(sys,'frozen', False): #frozen exe
    PATH = os.path.dirname(sys.argv[0]) + '\\'
    logging.basicConfig(filename= os.path.dirname(sys.argv[0]) + '\concerto.log', level=logging.DEBUG)
else: #not frozen
    PATH = os.path.dirname(os.path.abspath(__file__)) + '\\'
    logging.basicConfig(filename= os.path.dirname(os.path.abspath(__file__)) + '\concerto.log', level=logging.DEBUG)
import configparser
from kivy.config import Config
from kivy.resources import resource_add_path
if hasattr(sys, '_MEIPASS'):
    resource_add_path(os.path.join(sys._MEIPASS))
os.environ["KIVY_AUDIO"] = "sdl2"
# Kivy app configs
Config.set('graphics', 'width', '600')
Config.set('graphics', 'height', '400')
Config.set('graphics', 'resizable', False)
Config.set('graphics', 'multisamples', 0)
Config.set('graphics', 'fullscreen', 0)
Config.set('kivy', 'desktop', 1)
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Config.set('kivy', 'window_icon', 'concertoicon.ico')
Config.set(
    "kivy",
    "default_font",
    [
        "Roboto",
        'data/fonts/Roboto-Regular.ttf', 
        'data/fonts/Roboto-Italic.ttf',
        'data/fonts/Roboto-Bold.ttf', 
        'data/fonts/Roboto-BoldItalic.ttf'
    ],
)
Config.write()

#Concerto ini default settings
opt = [
        'copy_ip_clipboard',
        'mute_alerts',
        'mute_bgm',
        'revival_exe',

]
if os.path.exists(PATH + 'concerto.ini'):
    with open(PATH + 'concerto.ini') as f:
        for i in f.readlines():
            for x in opt:
                if x in i:
                    opt.remove(x)
    if len(opt) != 0:
        with open(PATH + 'concerto.ini','a') as f:
            for i in opt:
                if i == 'revival_exe':
                    f.write('\nrevival_exe=EfzRevival.exe\n')
                else:
                    f.write('\n%s=0\n' % i)
            f.close()
else:
    with open(PATH + 'concerto.ini', 'w') as f:
        f.write('[Concerto]')
        for i in opt:
            if i == 'revival_exe':
                f.write('\nrevival_exe=EfzRevival.exe\n')
            else:
                f.write('\n%s=0\n' % i)
        f.close()
with open(PATH + 'concerto.ini','r') as f:
    config_string = f.read()
app_config = configparser.ConfigParser()
app_config.optionxform = str
app_config.read_string(config_string)

revival_config = configparser.ConfigParser(comment_prefixes=';', allow_no_value=True)
revival_config.optionxform = str
revival_config.read('EfzRevival.ini',encoding='UTF-16')

LOBBYURL = "https://concerto-efz-testing.herokuapp.com/l"
VERSIONURL = "https://concerto-mbaacc.shib.live/v"
CURRENT_VERSION = '1.04'
DEBUG_VERSION = 'EFZ-4' # set to '' if not in use. This string is printed to logging to track specific test builds.
def find_img(file):
    if os.path.exists(file):
        return PATH + file
    else:
        return 'res/%s' % file

def img_credit(file,txt):
    if os.path.exists(file):
        return ''
    else:
        return txt