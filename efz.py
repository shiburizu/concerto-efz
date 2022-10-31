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
        self.rs = -1 # Revival's suggested rollback frames. Sent to UI.
        self.ds = -1 # delay suggestion
        self.aproc = None # active caster Thread object to check for isalive()
        self.offline = False #True when an offline mode has been started
        self.broadcasting = False #True when Broadcasting offline has been started
        self.startup = False #True when waiting for efz.exe to start in offline
        self.pid = None #PID of efz.exe

    def host(self,sc):
        self.kill_revival()
        logger.write('\n== Host ==\n')
        try:
            self.aproc = PtyProcess.spawn(app_config['settings']['revival_exe'].strip())
        except FileNotFoundError:
            sc.error_message('%s not found.' % app_config['settings']['revival_exe'].strip())
        while self.aproc.isalive(): # find IP and port combo for host
        #TODO use cumulative text for this stage of the process
            txt = self.aproc.read()
            if "Press 2 to cancel." in txt:
                #replace with ping back to the lobby server
                self.adr = urllib.request.urlopen('https://ident.me').read().decode('utf8')
                #NOTE: Heroku does not serve IPV6 requests so anyone using that will need to be re-routed to an external resolve.
                #Should be fine otherwise.
                while True:
                    flag = sc.set_ip(self.adr)
                    if flag:
                        break
                break
            elif "1: Host" in txt:
                self.aproc.write('1')
        print("IP: %s" % self.adr)
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
                sc.set_frames('EfzPlayer',int(str(cur_delay[0][-2:])),ping)
                break

    def host_old(self, sc, port='0', mode="Versus",t=None): #sc is a Screen for UI triggers
        self.kill_caster()
        self.app.offline_mode = None
        if app_config['settings']['write_scores'] == '1':
            write_name_to_file(1, 'NETPLAY P1')
            write_name_to_file(2, 'NETPLAY P2')
            reset_score_file(1)
            reset_score_file(2)
        try:
            if mode == "Training":
                self.aproc = PtyProcess.spawn('%s -n -t %s' % (app_config['settings']['caster_exe'].strip(),port))
            else:
                self.aproc = PtyProcess.spawn('%s -n %s' % (app_config['settings']['caster_exe'].strip(),port)) 
        except FileNotFoundError:
            sc.error_message('%s not found.' % app_config['settings']['caster_exe'].strip())
            return None
        # Stats
        threading.Thread(target=self.update_stats,daemon=True).start()
        logger.write('\n== Host ==\n')
        while self.aproc.isalive(): # find IP and port combo for host
            txt = self.aproc.read()
            ip = re.findall(
                r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{,5}', txt)
            if ip != []:
                self.adr = str(ip[0])
                sc.set_ip(self.adr) #tell UI we have the IP address
                break
            elif self.check_msg(txt) != []:
                sc.error_message(self.check_msg(txt))
                return None
        logger.write('IP: %s\n' % self.adr)
        cur_con = "" #current Caster read
        last_con = "" #last Caster read
        con = "" #cumulative string of all cur_con reads
        while self.aproc.isalive():
            cur_con = ansi_escape.sub('', str(self.aproc.read()))
            con += last_con + cur_con #con is what we send to validate_read
            logger.write('\n=================================\n')
            logger.write(str(con.split()))
            if self.playing == False and self.rs == -1 and self.ds == -1: #break self.playing is True
                n = self.validate_read(con)
                if n != False:
                    logger.write('\n=================================\n')
                    logger.write(str(con.split()))
                    if int(n[-2]) - int(n[-1]) < 0: # last item should be rollback frames, 2nd to last is network delay
                        self.ds = 0
                    else:
                        self.ds = int(n[-2]) - int(n[-1])
                    self.rs = int(n[-1])
                    r = []
                    name = False  # try to read names from caster output
                    for x in reversed(con.split()):
                        if name == False and (x == "connected" or x == "conected"):
                            name = True
                        elif name == True and x == '*':
                            break
                        elif name == True and x.replace('*', '') != '':
                            r.insert(0, x)
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
                        self.aproc = None
                        break
                    elif last_con != cur_con:
                        last_con = cur_con
                        continue
            else:
                break

    def join(self, ip, sc, t=None, *args): #t is required by the Lobby screen to send an "accept" request later
        self.kill_caster()
        self.app.offline_mode = None
        if app_config['settings']['write_scores'] == '1':
            write_name_to_file(1, 'NETPLAY P1')
            write_name_to_file(2, 'NETPLAY P2')
            reset_score_file(1)
            reset_score_file(2)
        try:
            self.aproc = PtyProcess.spawn('%s -n %s' % (app_config['settings']['caster_exe'].strip(),ip)) 
        except FileNotFoundError:
            sc.error_message('%s not found.' % app_config['settings']['caster_exe'].strip())
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

    def confirm_frames(self,rf,df):
        print("test")
        if self.aproc:
            print("check")
            self.aproc.write(str(rf))
            self.aproc.write('\x0D')
            self.playing = True

    def watch(self, ip, sc, *args):
        self.kill_caster()
        try:
            self.aproc = PtyProcess.spawn('%s -n -s %s' % (app_config['settings']['caster_exe'].strip(),ip))
        except FileNotFoundError:
            sc.error_message('%s not found.' % app_config['settings']['caster_exe'].strip())
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
                if app_config['settings']['write_scores'] == '1':
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

    def local(self,sc):
        self.kill_revival()
        self.startup = True
        logger.write('\n== Host ==\n')
        try:
            self.aproc = PtyProcess.spawn(app_config['settings']['revival_exe'].strip())
        except FileNotFoundError:
            sc.error_message('%s not found.' % app_config['settings']['revival_exe'].strip())
        while self.aproc.isalive(): # find IP and port combo for host
            txt = self.aproc.read()
            print(txt)
            if "1: Host" in txt:
                self.aproc.write('5')
                self.flag_offline(sc)
                break

    def local_old(self,sc):
        self.kill_caster()
        self.startup = True
        if app_config['settings']['write_scores'] == '1':
            write_name_to_file(1, 'LOCAL P1')
            write_name_to_file(2, 'LOCAL P2')
            reset_score_file(1)
            reset_score_file(2)
        try:
            proc = PtyProcess.spawn(app_config['settings']['caster_exe'].strip())
        except FileNotFoundError:
            sc.error_message('%s not found.' % app_config['settings']['caster_exe'].strip())
            return None
        self.aproc = proc
        while self.aproc.isalive():
            con = self.aproc.read()
            if self.find_button(con.split(),'Offline') or self.find_button(con.split(),'Ofline'):
                self.aproc.write('2')
                self.flag_offline(sc)
                break
            else:
                if self.check_msg(con) != []:
                    sc.error_message(self.check_msg(con))
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
                    self.startup = False
                    self.offline = True
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

    def check_msg(self,s):
        e = []
        for i in error_strings:
            if i in s:
                if i == 'Latest version is' or i == 'Update?': #update prompt
                    e.append("A new version of CCCaster is available. Please update by opening CCCaster.exe manually or downloading manually from concerto.shib.live.")
                else:
                    e.append(i)
                logger.write('\n%s\n' % e)
        if e != []:
            self.kill_caster()
        return e
