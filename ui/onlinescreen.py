from json.decoder import JSONDecodeError
import threading
from functools import partial
from ui.concertoscreen import ConcertoScreen
from ui.modals import *
import ui.lang
import config
import requests
import pyperclip
from kivy.clock import Clock

class OnlineScreen(ConcertoScreen):
    
    def __init__(self, CApp):
        super().__init__(CApp)
        self.direct_pop = None  # Direct match popup for user settings
        self.opponent = None
        self.spectate = False

    def direct(self,spectate=False):
        self.direct_pop = DirectModal()
        self.direct_pop.screen = self
        if spectate:
            self.direct_pop.connect_txt.text = ui.lang.localize("TERM_WATCH")
            self.spectate = True
        self.direct_pop.open()

    def lobby(self):
        check = self.online_login()
        if "UPDATE" in check:
            self.update()
            return None
        elif check != []:
            self.error_message(check)
        else:
            self.app.LobbyList.refresh()

    def online_login(self): #version and name validation before going to screen, returns a list of problems if any
        err = []
        if config.revival_config['Network']['Name'].strip() == '':
            err.append(self.localize('ERR_LOBBY_NONAME'))
            return err
        elif len(config.revival_config['Network']['Name']) > 16:
            name = config.revival_config['Network']['Name'][0:15].strip()
        else:
            name = config.revival_config['Network']['Name'].strip()
        params = {
            'action' : 'login',
            'version' : config.CURRENT_VERSION,
            'name' : name,
            'lang' : self.app.lang,
            'game' : 'efz'
        }
        try:
            req = requests.get(url=config.VERSIONURL,params=params,timeout=5)
            req.raise_for_status()
        except requests.exceptions.RequestException:
            err.append(self.localize('ERR_LOGIN_CONN'))
            return err

        resp = None
        try:
            resp = req.json()
        except JSONDecodeError:
            err.append(self.localize('ERR_BAD_RESPONSE'))
            return err

        if resp != None and resp['status'] != 'OK':
            err.append(resp['msg'])
        elif resp == None:
            return err
        else:
            self.app.player_name = name #assign name to be used everywhere
        return err

    def host(self):
        popup = GameModal(self.localize('ONLINE_MENU_HOSTING'),self.localize('TERM_QUIT'))
        popup.bind_btn(partial(self.dismiss, p=popup))
        popup.open()
        self.active_pop = popup
        self.app.mode = 'Direct Match'
        caster = threading.Thread(
            target=self.app.game.host, args=[self], daemon=True)
        caster.start()

    def set_ip(self,ip=None):
        if self.active_pop != None:
            self.active_pop.modal_txt.text += 'IP: %s:%s' % (ip,config.revival_config['Network']['Port'])
            if config.app_config['Concerto']['copy_ip_clipboard'] == "1":
                pyperclip.copy('%s:%s' % (ip,config.revival_config['Network']['Port']))
                self.active_pop.modal_txt.text += '\n(IP:Port copied to clipboard)'
            return True
        else:
            return False

    def join(self, ip=None, spectate=False):
        if not self.validate_ip(ip):
            ip = self.direct_pop.join_ip.text
            if not self.validate_ip(ip):
                self.error_message(self.localize('ERR_INVALID_IP'))
                return None
        if spectate:
            caster = threading.Thread(target=self.app.game.watch, args=[ip, self], daemon=True)
            caster.start()
            popup = GameModal(msg=self.localize('ONLINE_WATCHING_IP') % ip,btntext=self.localize('TERM_QUIT'))
            popup.bind_btn(partial(self.dismiss,p=popup))        
            popup.open()
            self.active_pop = popup
            self.app.offline_mode = 'Spectating' #needs to be an offline mode for lobby multitasking
        else:
            caster = threading.Thread(target=self.app.game.join, args=[ip, self], daemon=True)
            caster.start()
            popup = GameModal(self.localize("ONLINE_MENU_CONNECTING") % ip,self.localize('TERM_QUIT'))
            popup.bind_btn(partial(self.dismiss,p=popup))
            popup.open()
            self.active_pop = popup
            self.app.mode = 'Direct Match'

    def confirm(self, obj, p, d, *args):
        try:
            if self.app.game.playing is False:
                self.app.game.confirm_frames(int(d.text))
                self.active_pop.modal_txt.text += "\n" + self.localize("ONLINE_MENU_CONN_INFO")
                p.dismiss()
        except ValueError:
            pass

    def set_frames(self, delay, avg_ping, min_ping, max_ping,target=None): #target for Lobby call, dummied out here
        Clock.schedule_once(partial(self.set_frames_func,delay,avg_ping,min_ping,max_ping))

    def set_frames_func(self, delay, avg_ping, min_ping, max_ping, *args):
        popup = FrameModal()
        popup.frame_txt.text = self.localize('GAME_MODAL_INFO') % (
            avg_ping, max_ping, min_ping, delay)
        popup.d_input.text = str(delay)
        popup.start_btn.bind(on_release=partial(
            self.confirm, p=popup, d=popup.d_input))
        popup.close_btn.bind(on_release=partial(
            self.dismiss, p=popup))
        popup.open()

    # TODO prevent players from dismissing caster until EFZ is open to avoid locking issues
    def dismiss(self, obj, p=None, *args):
        self.app.game.kill_revival()
        self.opponent = None
        self.spectate = False
        if p:
            p.dismiss()
        self.dismiss_active_pop()
