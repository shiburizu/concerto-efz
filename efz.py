from winpty import PtyProcess  # pywinpty
from datetime import datetime
import re
import time
import subprocess
import threading
import pyperclip
from config import *
from urllib.request import urlopen

#error messages
error_strings = [
    "Connection timed out",
    "Host timed out",
    "Invalid address",
    "Only one net instance allowed",
    "Could not open EFZ.exe, check that it is in the same directory and you have the rights to run it.",
    "Cannot read from the memory. Check user access rights.",
    "Efz.exe is not EFZ Memorial 4.02",
    "The loader could not allocate memory in EFZ.",
    "Could not create a remote thread",
    "EFZ could not load EfzRevival.dll. Make sure that it is in the same directory as the EFZ executable.",
    "The loader could not load EfzRevival.dll. Make sure that they are in the same directory.",
    "Could not create a remote thread for the dll",
    "New version available, please update",
    "Remote is using a deprecated version",
    "Already playing, spectators have been disabled by the host",
    "Spectators have been disabled by the host",
    "Invalid delay"
]

ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')

spec_names = re.compile(r'^Spectating versus mode \(\d* delay, \d* rollback\) (.*) \(.*\) vs (.*) \(.*\) \(Tap the spacebar to toggle fast-forward\)$')
player_name_host_mm = re.compile(r'')
player_name_join_mm = re.compile(r'\w* connected')

delay = re.compile(r'Recommended input delay: (\d{1,2})')
avg_ping = re.compile(r'Average Ping: (\d{1,4})')
max_ping = re.compile(r'Max Ping: (\d{1,4})')
min_ping = re.compile(r'Min Ping: (\d{1,4})')
min_delay = re.compile(r'(\d+) and \d+, none for recommended')

class loghelper():
    dateTimeObj = datetime.now()
    timestampStr = 'Concerto_' + \
        dateTimeObj.strftime("%d-%b-%Y-%H-%M-%S") + '.txt'

    def write(self, s):
        if not os.path.isdir(PATH + 'concerto-logs'):
            os.mkdir(PATH + 'concerto-logs')
        with open(PATH + 'concerto-logs\\' + self.timestampStr, 'a') as log:
            log.write(s)

logger = loghelper()

class Revival():

    def __init__(self, CApp):
        self.app = CApp
        self.adr = None #our IP when hosting, needed to trigger UI actions
        self.playing = False #True when netplay begins via input to Revival
        self.aproc = None # active caster Thread object to check for isalive()}
        self.secondary = None # Thread object only used to provide Local Play while in a locking action like Host
        self.offline = False #True when an offline mode has been started
        self.startup = False #True when waiting for efz.exe to start in offline
        self.min_delay = 0 #minimum delay frames when EFZ connection is started

    def host(self,sc,t=None,ipv6=False):
        flag = False #set to True when hosting is ready
        self.kill_revival()
        logger.write('\n== Host ==\n')
        try:
            self.aproc = PtyProcess.spawn(app_config['Concerto']['revival_exe'].strip())
        except FileNotFoundError:
            sc.error_message('%s not found.' % app_config['Concerto']['revival_exe'].strip())
        sum_txt = ""
        prev_txt = ""
        while self.aproc.isalive():
            txt = ansi_escape.sub('', str(self.aproc.read()))
            if prev_txt != '':
                if prev_txt in txt:
                    txt = txt.replace(prev_txt,'')
            sum_txt += txt
            prev_txt = txt
            logger.write(str(sum_txt.split()))
            logger.write("\n\n")
            print(str(sum_txt.split()))
            if "Press 2 to cancel." in sum_txt:
                if ipv6 is False:
                    try:
                        with urlopen('http://4.ident.me') as resp:
                            self.adr = resp.read().decode('ascii')
                    except:
                        sc.error_message('Cannot start IPv4 Session. Please ensure you have an IPv4 IP address assigned.')
                        self.kill_revival()
                        return None
                else:
                    try:
                        with urlopen('http://6.ident.me') as resp:
                            self.adr = resp.read().decode('ascii')
                    except:
                        sc.error_message('Cannot start IPv6 Session. Please ensure you have an IPv6 IP address assigned.')
                        self.kill_revival()
                        return None
                while True:
                    if flag:
                        break
                    flag = sc.set_ip(self.adr)
                break
            elif "1:" in sum_txt:
                time.sleep(0.1)
                self.aproc.write('1')
            elif self.check_msg(sum_txt) != []:
                sc.error_message(self.check_msg(sum_txt))
                return None
        sum_txt = ""
        prev_txt = ""
        while self.aproc.isalive():
            txt = ansi_escape.sub('', str(self.aproc.read()))
            if prev_txt != '':
                if prev_txt in txt:
                    txt = txt.replace(prev_txt,'')
            sum_txt += txt
            prev_txt = txt
            logger.write(str(sum_txt.split()))
            logger.write("\n\n")
            print(str(sum_txt.split()))

            cur_delay = re.findall(delay,sum_txt)
            cur_avg_ping = re.findall(avg_ping,sum_txt)
            cur_max_ping = re.findall(max_ping,sum_txt)
            cur_min_ping = re.findall(min_ping,sum_txt)
            cur_min_delay = re.findall(min_delay,sum_txt)

            if cur_delay != [] and cur_min_delay != [] and cur_avg_ping != [] and cur_max_ping != [] and cur_min_ping != []:
                #if ":" in cur_avg_ping[0][-3:]:
                #    ping = int(str(cur_avg_ping[0][-2:]).replace(":",""))
                #else:
                #    ping = int(str(cur_avg_ping[0][-3:]).replace(":",""))
                self.min_delay = int(cur_min_delay[-1])
                sc.set_frames(int(cur_delay[-1]),int(cur_avg_ping[-1]),
                    int(cur_min_ping[-1]),int(cur_max_ping[-1]),
                    int(cur_min_delay[-1]),target=t)
                break #do we need to break? can we keep the process alive and listen for errors?
            else:
                if self.check_msg(sum_txt) != []:
                    sc.error_message(self.check_msg(sum_txt))
                    self.aproc = None
                    break

    def join(self,ip,sc,t=None):
        self.kill_revival()
        logger.write('\n== Join ==\n')
        try:
            self.aproc = PtyProcess.spawn(app_config['Concerto']['revival_exe'].strip())
        except FileNotFoundError:
            sc.error_message('%s not found.' % app_config['Concerto']['revival_exe'].strip())
        sum_txt = ""
        prev_txt = ""
        join_flag = False
        while self.aproc.isalive():
            txt = ansi_escape.sub('', str(self.aproc.read()))
            if prev_txt != '':
                if prev_txt in txt:
                    txt = txt.replace(prev_txt,'')
            sum_txt += txt
            prev_txt = txt
            logger.write(str(sum_txt.split()))
            logger.write("\n\n")
            print(str(sum_txt.split()))
            if "Input host ip:port" in sum_txt:
                time.sleep(0.1)
                self.aproc.write(ip)
                time.sleep(0.1)
                self.aproc.write('\x0D')
                break
            elif "1:" in sum_txt and join_flag == False:
                time.sleep(0.1)
                self.aproc.write('2')
                join_flag = True
                time.sleep(0.1)
            elif self.check_msg(sum_txt) != []:
                sc.error_message(self.check_msg(sum_txt))
                return None
        sum_txt = ""
        prev_txt = ""
        while self.aproc.isalive():
            txt = ansi_escape.sub('', str(self.aproc.read()))
            if prev_txt != '':
                if prev_txt in txt:
                    txt = txt.replace(prev_txt,'')
            sum_txt += txt
            prev_txt = txt
            logger.write(str(sum_txt.split()))
            logger.write("\n\n")
            print(str(sum_txt.split()))

            cur_delay = re.findall(delay,sum_txt)
            cur_avg_ping = re.findall(avg_ping,sum_txt)
            cur_max_ping = re.findall(max_ping,sum_txt)
            cur_min_ping = re.findall(min_ping,sum_txt)
            cur_min_delay = re.findall(min_delay,sum_txt)

            if cur_delay != [] and cur_min_delay != [] and cur_avg_ping != [] and cur_max_ping != [] and cur_min_ping != []:
                #if ":" in cur_avg_ping[0][-3:]:
                #    ping = int(str(cur_avg_ping[0][-2:]).replace(":",""))
                #else:
                #    ping = int(str(cur_avg_ping[0][-3:]).replace(":",""))
                self.min_delay = int(cur_min_delay[-1])
                sc.set_frames(int(cur_delay[-1]),int(cur_avg_ping[-1]),
                    int(cur_min_ping[-1]),int(cur_max_ping[-1]),
                    int(cur_min_delay[-1]),target=t)
                break
            else:
                if self.check_msg(sum_txt) != []:
                    sc.error_message(self.check_msg(sum_txt))
                    self.aproc = None
                    break

    def watch(self,ip,sc,*args):
        self.kill_revival()
        self.startup = True
        logger.write('\n== Watch ==\n')
        try:
            self.aproc = PtyProcess.spawn(app_config['Concerto']['revival_exe'].strip())
        except FileNotFoundError:
            sc.error_message('%s not found.' % app_config['Concerto']['revival_exe'].strip())
        sum_txt = ""
        prev_txt = ""
        watch_flag = False #True when IP has been pasted
        while self.aproc.isalive():
            txt = ansi_escape.sub('', str(self.aproc.read()))
            if prev_txt != '':
                if prev_txt in txt:
                    txt = txt.replace(prev_txt,'')
            sum_txt += txt
            prev_txt = txt
            logger.write(str(sum_txt.split()))
            logger.write("\n\n")
            print(str(sum_txt.split()))
            if 'Successfully loaded' in sum_txt:
                threading.Thread(target=self.flag_watching,daemon=True).start()
                break #maybe dont break to listen for errors
            elif "4:" in sum_txt and watch_flag == False:
                time.sleep(0.1)
                old = pyperclip.paste()
                pyperclip.copy(ip)
                self.aproc.write('4')
                time.sleep(0.1)
                pyperclip.copy(old)
                watch_flag = True
            else:
                if self.check_msg(sum_txt) != []:
                    sc.error_message(self.check_msg(sum_txt))
                    self.aproc = None
                    break

    def local(self,sc=None,tournament=False,secondary=False):
        if not secondary:
            self.kill_revival()
        self.startup = True
        logger.write('\n== Local Play ==\n')
        try:
            if secondary:
                proc = PtyProcess.spawn(app_config['Concerto']['revival_exe'].strip())
                self.secondary = True
            else:
                proc = PtyProcess.spawn(app_config['Concerto']['revival_exe'].strip())
                self.aproc = proc
        except FileNotFoundError:
            if secondary == False:
                sc.error_message('%s not found.' % app_config['Concerto']['revival_exe'].strip())
        sum_txt = ""
        prev_txt = ""
        while proc.isalive():
            txt = ansi_escape.sub('', str(proc.read()))
            if prev_txt != '':
                if prev_txt in txt:
                    txt = txt.replace(prev_txt,'')
            sum_txt += txt
            prev_txt = txt
            if "1:" in sum_txt:
                time.sleep(0.1)
                if tournament is True:
                    proc.write('6')
                else:
                    proc.write('5')
                if not secondary:
                    self.flag_offline(sc)
                break
            else:
                if self.check_msg(sum_txt) != [] and secondary == False:
                    sc.error_message(self.check_msg(sum_txt))
                    proc = None
                    break

    def confirm_frames(self,df):
        if self.secondary:
            subprocess.run('taskkill /f /im efz.exe', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.secondary = False
        if self.aproc:
            self.aproc.write(str(df))
            self.aproc.write('\x0D')
            threading.Thread(target=self.flag_playing,daemon=True).start()

    def flag_watching(self):
        while True:
            cmd = f"""tasklist /FI "IMAGENAME eq efz.exe" /FO CSV /NH"""
            task_data = subprocess.check_output(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL).decode("UTF8","ignore")
            try:
                task_data.replace("\"", "").split(",")[1]
                self.startup = False
                time.sleep(0.1)
                break
            except IndexError:
                pass
            
    def flag_playing(self):
        while True:
            cmd = f"""tasklist /FI "IMAGENAME eq efz.exe" /FO CSV /NH"""
            task_data = subprocess.check_output(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL).decode("UTF8","ignore")
            try:
                task_data.replace("\"", "").split(",")[1]
                self.playing = True
                time.sleep(0.1)
                break
            except IndexError:
                pass

    def flag_offline(self,sc):
        while True:
            cmd = f"""tasklist /FI "IMAGENAME eq EfzRevival.exe" /FO CSV /NH"""
            task_data = subprocess.check_output(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL).decode("UTF8","ignore")
            try:
                task_data.replace("\"", "").split(",")[1]
            except IndexError:
                pass
            else:
                if self.offline is False:
                    self.offline = True
                    self.startup = False
                    break
            if self.aproc != None:
                if self.aproc.isalive() is False:
                    break
            else:
                break
        sc.dismiss_active_pop()

    def kill_revival(self):
        self.adr = None
        if self.aproc != None:
            subprocess.run('taskkill /f /im efz.exe', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run('taskkill /f /im EfzRevival.exe', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self.aproc = None
        self.startup = False
        self.offline = False
        self.playing = False
        self.secondary = False

    def input(self,sc):
        if os.path.isfile('config_EN.exe'):
            subprocess.run(['config_EN.exe'])
        else:
            try:
                subprocess.run(['config.exe'])
            except FileNotFoundError:
                sc.error_message('config.exe or config_EN.exe not found.')
        
    def dinput(self,sc):
        try:
            subprocess.run('start cmd /K DInput_Config_Beta.exe', shell=True)
        except FileNotFoundError:
            sc.error_message('DInput_Config_Beta.exe not found.')

    def paledit(self,sc):
        try:
            subprocess.run(['pal_edit.exe'])
        except FileNotFoundError:
            sc.error_message('pal_edit.exe not found.')
        
    def check_msg(self,s):
        e = []
        for i in error_strings:
            if i in s:
                e.append(i)
                logger.write('\n%s\n' % e)
        if e != []:
            self.kill_revival()
        return e
