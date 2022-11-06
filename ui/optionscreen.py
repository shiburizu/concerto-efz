from ui.concertoscreen import ConcertoScreen
from config import *
from ui.modals import GameModal
from ui.buttons import DummyBtn
import ui.lang
import ui.options
import threading

class OptionScreen(ConcertoScreen):

    def __init__(self, CApp):
        super().__init__(CApp)
        self.optrows = {}
        self.loaded = False

    def create_options(self,conf):
        for s in conf.sections():
            hd = DummyBtn()
            hd.text = s
            self.ids['opt_grid'].add_widget(hd)
            for (k, v) in conf.items(s):
                row = ui.options.OptionRow()
                if v.strip() == "True" or v.strip() == "False":
                    row.create_opt(k.strip(),v.strip(),inptype="bool",hint="hint")
                elif v.strip() == "0" or v.strip() == "1":
                    row.create_opt(k.strip(),v.strip(),inptype="boolint",hint="hint")
                elif v.strip() == "IPv4" or v.strip() == "IPv6":
                    row.create_opt(k.strip(),v.strip(),inptype="spinner",vals=["IPv4","IPv6"],hint="hint")
                elif k == "Port" or k == "MaxRollback" or "Window" in k or "BackBuffer" in k:
                    row.create_opt(k.strip(),v.strip(),inptype="int",hint="hint")
                else:
                    row.create_opt(k.strip(),v.strip(),hint="hint")
                self.ids['opt_grid'].add_widget(row)
                self.optrows[k] = row

    def load(self):
        
        if self.loaded is False: #Build widgets if they don't exist

            self.create_options(app_config)
            self.create_options(revival_config)

            self.loaded = True

        self.app.sm.current = 'Options'

    def save(self):
        #TODO Validate settings before save
        error_check = []
        #Write EfzRevival.ini settings
        with open(PATH + 'EfzRevival.ini','r',encoding='UTF-16') as f:
            config_file = f.readlines()
            n = 0
            for i in config_file:
                if i[0] != ';' and i[0] != '[' and len(i.strip()) != 0:
                    opt_k = i.split("=",1)[0].strip()
                    opt_v = i.split("=",1)[1].strip()
                    if opt_k in self.optrows:
                        opt = self.optrows[opt_k]                            
                        if opt.inptype == 'bool':
                            if opt.inp.active == True:
                                config_file[n] = "%s=True\n" % (opt_k)
                            else:
                                config_file[n] = "%s=False\n" % (opt_k)
                        elif opt.inptype == 'boolint':
                            if opt.inp.active == True:
                                config_file[n] = "%s=1\n" % (opt_k)
                            else:
                                config_file[n] = "%s=0\n" % (opt_k)
                        else:
                            config_file[n] = "%s=%s\n" % (opt_k, self.optrows[opt_k].inp.text)
                n += 1
            out = open(PATH + 'EfzRevival.ini','w',encoding="UTF-16")
            out.writelines(config_file)
            out.close()
            f.close()  
        with open(PATH + 'EfzRevival.ini','r',encoding='UTF-16') as f:
            config_string = f.read()
        revival_config.read_string(config_string) 
        #Write Concerto.ini settings
        with open(PATH + 'concerto.ini','r') as f:
            config_file = f.readlines()
            n = 0
            for i in config_file:
                if i[0] != ';' and i[0] != '[' and len(i.strip()) != 0:
                    opt_k = i.split("=",1)[0].strip()
                    opt_v = i.split("=",1)[1].strip()
                    if opt_k in self.optrows:
                        opt = self.optrows[opt_k]                            
                        if opt.inptype == 'bool':
                            if opt.inp.active == True:
                                config_file[n] = "%s=True\n" % (opt_k)
                            else:
                                config_file[n] = "%s=False\n" % (opt_k)
                        elif opt.inptype == 'boolint':
                            if opt.inp.active == True:
                                config_file[n] = "%s=1\n" % (opt_k)
                            else:
                                config_file[n] = "%s=0\n" % (opt_k)
                        else:
                            config_file[n] = "%s=%s\n" % (opt_k, self.optrows[opt_k].inp.text)
                n += 1
            out = open(PATH + 'concerto.ini','w')
            out.writelines(config_file)
            out.close()
            f.close()  
        with open(PATH + 'concerto.ini','r') as f:
            config_string = f.read()
        app_config.read_string(config_string) 
        #apply sound settings
        if "mute_alerts" in self.optrows:
            if self.optrows['mute_alerts'].inp.active is True:
                self.app.sound.mute_alerts = True
        if "mute_bgm" in self.optrows:
            if self.optrows['mute_bgm'].inp.active is True:
                if self.app.sound.muted is False:
                    if self.app.sound.bgm.state == 'play':
                        self.app.sound.cut_bgm() 
                    self.app.sound.muted = True 
            else:
                if self.app.sound.muted is True:
                    self.app.sound.muted = False
                    if self.app.sound.bgm.state == 'stop':
                        self.app.sound.cut_bgm() 
                    

    def input(self):
        threading.Thread(target=self.app.game.input,args=[self],daemon=True).start()

    def dinput(self):
        threading.Thread(target=self.app.game.dinput,args=[self],daemon=True).start()

    def paledit(self):
        threading.Thread(target=self.app.game.paledit,args=[self],daemon=True).start()