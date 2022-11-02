from winpty import PtyProcess  # pywinpty
from datetime import datetime
import re
import time
import subprocess
import threading
import pyperclip
from config import *
import urllib.request

#error messages
error_strings = [
]

ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')

spec_names = re.compile(r'^Spectating versus mode \(\d* delay, \d* rollback\) (.*) \(.*\) vs (.*) \(.*\) \(Tap the spacebar to toggle fast-forward\)$')
player_name_host_mm = re.compile(r'')
player_name_join_mm = re.compile(r'\w* connected')

delay = re.compile(r'Recommended input delay: \d{1,2}')
avg_ping = re.compile(r'Average Ping: \d{1,4}')
max_ping = re.compile(r'Max Ping: \d{1,4}')
min_ping = re.compile(r'Min Ping: \d{1,4}')

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
        self.aproc = None # active caster Thread object to check for isalive()
        self.offline = False #True when an offline mode has been started
        self.startup = False #True when waiting for efz.exe to start in offline

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
                #replace with ping back to the lobby server
                self.adr = urllib.request.urlopen('https://ident.me').read().decode('utf8')
                #NOTE: Heroku does not serve IPV6 requests so anyone using that will need to be re-routed to an external resolve.
                #Should be fine otherwise.
                while True:
                    if flag:
                        break
                    flag = sc.set_ip(self.adr)
                break
            elif "1: Host" in sum_txt:
                self.aproc.write('1')
            elif self.check_msg(sum_txt) != []:
                sc.error_message(self.check_msg(sum_txt))
                return None
        cur_delay = None
        cur_max_ping = None
        cur_min_ping = None
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

            if cur_delay != [] and cur_avg_ping != [] and cur_max_ping != [] and cur_min_ping != []:
                if ":" in cur_avg_ping[0][-3:]:
                    ping = int(cur_avg_ping[0][-2:])
                else:
                    ping = int(cur_avg_ping[0][-3:])
                sc.set_frames(int(str(cur_delay[0][-2:])),ping,int(str(cur_min_ping[0][-3:])),int(str(cur_max_ping[0][-3:])),target=t)
                break #do we need to break? can we keep the process alive and listen for errors?
            else:
                if self.check_msg(sum_txt) != []:
                    sc.error_message(self.check_msg(sum_txt))
                    self.aproc = None
                    break

    def join(self, ip, sc, t=None, *args): #t is required by the Lobby screen to send an "accept" request later
        self.kill_caster()
        self.app.offline_mode = None
        if app_config['Concerto']['write_scores'] == '1':
            write_name_to_file(1, 'NETPLAY P1')
            write_name_to_file(2, 'NETPLAY P2')
            reset_score_file(1)
            reset_score_file(2)
        try:
            self.aproc = PtyProcess.spawn('%s -n %s' % (app_config['Concerto']['caster_exe'].strip(),ip)) 
        except FileNotFoundError:
            sc.error_message('%s not found.' % app_config['Concerto']['caster_exe'].strip())
            return None
        # Stats
        threading.Thread(target=self.update_stats,daemon=True).start()
        cur_con = ""
        last_con = ""
        con = ""
        logger.write('\n== Join %s ==\n' % ip)
        while self.aproc.isalive():
            cur_con = ansi_escape.sub('', str(self.aproc.read()))
            con += last_con + cur_con
            logger.write('\n=================================\n')
            logger.write(str(con.split()))
            if self.playing == False and self.rs == -1 and self.ds == -1:
                n = self.validate_read(con)
                if n != False:
                    logger.write('\n=================================\n')
                    logger.write(str(con.split()))
                    if int(n[-2]) - int(n[-1]) < 0:
                        self.ds = 0
                    else:
                        self.ds = int(n[-2]) - int(n[-1])
                    self.rs = int(n[-1])
                    r = []
                    name = False 
                    for x in con.split():
                        if x == "to" and name == False:
                            name= True
                        elif x == '*' and name == True:
                            break
                        elif name == True and x.replace('*', '') != '':
                            r.append(x)
                    #Regex for Ping
                    p = re.findall('Ping: \d+\.\d+ ms', con)
                    ping = p[-1].replace('Ping:','')
                    ping = ping.replace('ms','')
                    ping = ping.strip()
                    #Network Delay
                    delay = n[-2]
                    #Mode and rounds
                    m = ""
                    rd = 2
                    if "Versus" in con:
                        m = "Versus"
                        rd = n[-3]
                    elif "Training" in con:
                        m = "Training"
                        rd = 0
                    #Name
                    opponent_name = ' '.join(r)
                    sc.set_frames(opponent_name,delay,ping,mode=m,rounds=rd,target=t) #trigger frame delay settings in UI
                    break
                else:
                    if self.check_msg(con) != []:
                        sc.error_message(self.check_msg(con))
                        break
                    elif 'Spectating versus mode' in con:
                        sc.error_message('Host is already in a game!')
                        break
                    elif last_con != cur_con:
                        last_con = cur_con
                        continue
            else:
                break

    def confirm_frames(self,df):
        if self.aproc:
            self.aproc.write(str(df))
            self.aproc.write('\x0D')
            threading.Thread(target=self.flag_playing,daemon=True).start()
            
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

    def watch(self, ip, sc, *args):
        self.kill_caster()
        try:
            self.aproc = PtyProcess.spawn('%s -n -s %s' % (app_config['Concerto']['caster_exe'].strip(),ip))
        except FileNotFoundError:
            sc.error_message('%s not found.' % app_config['Concerto']['caster_exe'].strip())
            return None
        cur_con = ""
        last_con = ""
        con = ""
        logger.write('\n== Watch %s ==\n' % ip)
        self.broadcasting = True
        threading.Thread(target=self.update_stats,daemon=True).start()
        while self.aproc.isalive():
            cur_con = ansi_escape.sub('', str(self.aproc.read()))
            con += last_con + cur_con
            logger.write('\n=================================\n')
            logger.write(str(con.split()))
            if "fast-forward)" in con:
                logger.write('\n=================================\n')
                logger.write(str(con.split()))
                self.aproc.write('1')  # start spectating, find names after
                r = []
                startWrite = False
                for x in reversed(con.split()):
                    if startWrite is False and "fast-forward" not in x:
                        pass
                    elif "fast-forward)" in x:
                        startWrite = True
                        r.insert(0, x)
                    elif x == '*' and len(r) > 0:
                        if r[0] == "Spectating":
                            break
                    elif x != '*' and x.replace('*', '') != '':
                        r.insert(0, x)
                if app_config['Concerto']['write_scores'] == '1':
                    regex_result = re.match(pattern=spec_names, string=' '.join(r))
                    write_name_to_file(1, regex_result.group(1))
                    write_name_to_file(2, regex_result.group(2))
                    reset_score_file(1)
                    reset_score_file(2)
                sc.active_pop.modal_txt.text = ' '.join(r)
                # replace connecting text with match name in caster
                break
            else:
                if self.check_msg(con) != []:
                    sc.error_message(self.check_msg(con))
                    break
                elif last_con != cur_con:
                    last_con = cur_con
                    continue

    def local(self,sc,tournament=False):
        self.kill_revival()
        self.startup = True
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
            if "1: Host" in sum_txt:
                time.sleep(0.1)
                if tournament is True:
                    self.aproc.write('6')
                else:
                    self.aproc.write('5')
                self.flag_offline(sc)
                break
            else:
                if self.check_msg(sum_txt) != []:
                    sc.error_message(self.check_msg(sum_txt))
                    self.aproc = None
                    break

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
        self.rs = -1
        self.ds = -1
        if self.aproc != None:
            subprocess.run('taskkill /f /im efz.exe', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run('taskkill /f /im EfzRevival.exe', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self.aproc = None
        self.startup = False
        self.offline = False
        self.broadcasting = False
        self.playing = False

    def input(self,sc):
        try:
            subprocess.run(['config_EN.exe'])
        except FileNotFoundError:
            sc.error_message('config_EN not found.')
        
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
            self.kill_caster()
        return e
