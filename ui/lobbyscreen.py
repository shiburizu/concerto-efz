import time
import requests
import threading
import pyperclip
from functools import partial
from config import *
from kivy.properties import ObjectProperty
from ui.concertoscreen import ConcertoScreen
from ui.modals import *
from ui.buttons import DummyBtn, PlayerRow
import logging
from kivy.clock import Clock
from config import revival_config

# detect ipv4 or ipv6 type from IP and add a suffix to the label

class LobbyScreen(ConcertoScreen):
    player_list = ObjectProperty(None)  # layout for idle players
    challenge_list = ObjectProperty(None)  # layout for challenges
    match_list = ObjectProperty(None)  # ongoing match list
    lobby_code = ObjectProperty(None)  # top right lobby label

    def __init__(self, CApp):
        super().__init__(CApp)
        self.secret = None  # secret required for server messages
        self.lobby_thread_flag = 0 #whether or not the thread is running
        self.watch_player = None  # id of player to watch for spectating
        self.player_id = None  # our own ID as provided by the JSON
        self.code = None  # lobby code
        self.lobby_updater = None  # thread to manage lobby updates
        self.widget_index = {} #ids of players, widget of lobby
        self.challenge_name = None #name of player being challenged
        self.opponent = None # name of player currently being played against
        self.challenge_id = None #id of player being challenged
        self.type = None
        self.get_attempts = 0 #if 2, exit
        self.alias = None #lobby alias if any
        self.spectate = False # flag True if watching a match

        self.global_lobby = False # True if started from the global lobby button

    def create(self, j, first=False, type='Private'):  # json response object
        #this does not use self.type because it should only run once per lobby.
        #the reason for this is that a player may start a Direct Online match separately and we do not want to erase that status.
        #self.type is used for update_stats in the Caster function to signal info to the presence.
        print(j)
        newSound = False
        if first is True:
            self.player_id = j['msg']
            self.code = j['id']
            if j['alias']:
                self.alias = j['alias']
                if self.global_lobby is False:
                    self.lobby_code.text = "[%s %s]" % (self.localize("TERM_LOBBYCODE"),self.alias)
            else:
                if self.global_lobby is False:
                    self.lobby_code.text = "[%s %s %s]" % (self.localize("TERM_%s" % type.upper()), self.localize("TERM_LOBBYCODE"), self.code)
            if self.global_lobby is False:
                self.lobby_code.bind(on_release=self.invite_link)
            else:
                self.lobby_code.text = ""
                self.lobby_code.unbind(on_release=self.invite_link)
            self.widget_index = {}
            self.player_list.clear_widgets()
            self.match_list.clear_widgets()
            self.challenge_list.clear_widgets()
            self.type = type
        challenging_ids = []
        
        # TODO: come up with a solution for players with identical names (this does not affect the server )
        if j['challenges'] != []:
            if 'c' not in self.widget_index:
                h = DummyBtn()
                h.text = self.localize("LOBBY_MENU_CHALLENGES")
                self.challenge_list.add_widget(h)
                self.widget_index.update({'c':h})
            for i in j['challenges']:  # name, id, ip of challenger
                challenging_ids.append(i[1])
                if i[1] in self.widget_index:
                    if self.widget_index.get(i[1]).parent == self.challenge_list:
                        pass
                    else: #remove idle player
                        self.widget_index.get(i[1]).parent.remove_widget(self.widget_index.get(i[1]))
                        p = PlayerRow()
                        p.ids['PlayerBtn'].text = i[0]
                        if "[" in i[2]: #IPv6 Challenger
                            p.ids['PlayerBtn'].text += " (IPv6)"
                        p.ids['PlayerBtn'].bind(on_release=partial(
                            self.accept_challenge, name=i[0], id=i[1], ip=i[2]))
                        p.ids['WatchBtn'].text = ""
                        self.challenge_list.add_widget(p)
                        self.widget_index.update({i[1]:p})
                        if newSound is False:
                            self.app.sound.play_alert()
                            newSound = True
                else:
                    p = PlayerRow()
                    p.ids['PlayerBtn'].text = i[0]
                    p.ids['PlayerBtn'].bind(on_release=partial(
                        self.accept_challenge, name=i[0], id=i[1], ip=i[2]))
                    p.ids['WatchBtn'].text = ""
                    self.challenge_list.add_widget(p)
                    self.widget_index.update({i[1]:p})
                    if newSound is False:
                        self.app.sound.play_alert()
                        newSound = True
        else:
            n = []
            for k,v in self.widget_index.items():
                if v in self.challenge_list.children:
                    v.parent.remove_widget(v)
                    n.append(k)
            for i in n:
                self.widget_index.pop(i)

        if j['idle'] != []:
            if 'i' not in self.widget_index:
                h = DummyBtn()
                h.text = self.localize("LOBBY_MENU_IDLE")
                self.player_list.add_widget(h)
                self.widget_index.update({'i':h})
            for i in j['idle']:
                if i[1] not in challenging_ids:
                    if i[1] in self.widget_index:
                        pass
                    else:
                        p = PlayerRow()
                        p.ids['PlayerBtn'].text = i[0]
                        if i[1] != self.player_id:
                            p.ids['PlayerBtn'].bind(on_release=partial(
                                self.send_challenge, name=i[0], id=i[1]))
                            if i[1] == self.watch_player:
                                p.ids['WatchBtn'].text = self.localize("TERM_FOLLOWING").upper()
                            else:
                                p.ids['WatchBtn'].text = self.localize("TERM_FOLLOW").upper()
                            p.ids['WatchBtn'].bind(on_release=partial(self.follow_player, i=i[1]))
                        else:
                            p.ids['PlayerBtn'].text += " (%s)" % self.localize("TERM_SELF")
                            p.ids['WatchBtn'].disabled = True
                            p.ids['WatchBtn'].text = ""
                        self.player_list.add_widget(p)
                        self.widget_index.update({i[1]:p})
        else:
            n = []
            for k,v in self.widget_index.items():
                if v in self.player_list.children:
                    v.parent.remove_widget(v)
                    n.append(k)
            for i in n:
                self.widget_index.pop(i)

        if j['playing'] != []:
            if 'w' not in self.widget_index:
                h = DummyBtn()
                h.text = self.localize("LOBBY_MENU_PLAYING")
                self.match_list.add_widget(h)
                self.widget_index.update({'w':h})
            for i in j['playing']:
                if (i[2],i[3]) in self.widget_index or (i[3],i[2]) in self.widget_index:
                    pass
                else:
                    p = PlayerRow()
                    p.ids['PlayerBtn'].text = "%s vs %s" % (i[0], i[1])
                    if i[2] != self.player_id and i[3] != self.player_id:
                        if "[" in i[4]: #ipv6 spectator
                            p.ids['PlayerBtn'].bind(on_release=partial(self.watch_match,
                                name="%s vs %s (IPv6)" % (i[0], i[1]), ip=i[4]))
                        else:
                            p.ids['PlayerBtn'].bind(on_release=partial(self.watch_match,
                                name="%s vs %s" % (i[0], i[1]), ip=i[4]))
                    p.ids['WatchBtn'].text = ""
                    self.match_list.add_widget(p)
                    self.widget_index.update({(i[2],i[3]):p})
                if self.watch_player != None:
                    if i[2] == self.watch_player or i[3] == self.watch_player:
                        self.watch_match(name="%s vs %s" % (i[0], i[1]), ip=i[4])
        else:
            n = []
            for k,v in self.widget_index.items():
                if v in self.match_list.children:
                    v.parent.remove_widget(v)
                    n.append(k)
            for i in n:
                self.widget_index.pop(i)
        #if any widgets in the list don't correspond to json items, remove them
        n = []
        for k in self.widget_index.keys():
            ok = False
            if k != 'w' and k != 'c' and k != 'i':
                for i in j['challenges']:
                    if k == i[1]:
                        ok = True
                for i in j['idle']:
                    if k == i[1]:
                        ok = True
                for i in j['playing']:
                    if k == (i[2],i[3]) or k == (i[3],i[2]):
                        ok = True
                if ok is False:
                    n.append(k)
        for i in n:
            self.widget_index.get(i).parent.remove_widget(self.widget_index.get(i))
            self.widget_index.pop(i)
        if first is True:
            self.app.lobby_button()
            self.lobby_thread_flag = 0
            self.lobby_updater = threading.Thread(
                target=self.auto_refresh, daemon=True)  # netplay watchdog
            self.lobby_updater.start()
        else:
            code = self.code
            if self.alias != None:
                code = self.alias
            if len(self.challenge_list.children) > 0:
                self.app.update_lobby_button('%s %s (%s)' % (self.localize("TERM_LOBBY").upper(),code,len(self.challenge_list.children) - 1))
            else:
                self.app.update_lobby_button('%s %s' % (self.localize("TERM_LOBBY").upper(),code))

    def follow_player(self,obj,i):
        w = self.widget_index.get(i).ids['WatchBtn']
        if w.text == self.localize("TERM_FOLLOW").upper():
            self.watch_player = i
            for k,v in self.widget_index.items(): # clear first
                try:
                    if v.parent == self.player_list and k != self.player_id:
                        v.ids['WatchBtn'].text = self.localize("TERM_FOLLOW").upper()
                except KeyError:
                    pass
            w.text = self.localize("TERM_FOLLOWING").upper()
        else:
            self.watch_player = None
            w.text = self.localize("TERM_FOLLOW").upper()

    def auto_refresh(self):
        net = requests.Session()
        while True:
            if self.lobby_thread_flag != 0:
                break
            p = {
                'action': 'status',
                'id': self.code,
                'p': self.player_id,
                'secret': self.secret
            }
            try:
                req = net.get(url=LOBBYURL, params=p, timeout=5)
                req.raise_for_status()
            except (requests.exceptions.ConnectionError,requests.exceptions.Timeout) as e:
                logging.warning('LOBBY REFRESH: %s' % e.__class__)
                if self.get_attempts < 2:
                    self.get_attempts += 1
                    logging.warning('GET_ATTEMPTS: %s' % self.get_attempts)
                else:
                    logging.warning('GET_ATTEMPTS: %s' % self.get_attempts)
                    Clock.schedule_once(partial(self.exit,'Error: %s' % e.__class__))
                    break
            else:
                r = req.json()
                if r['msg'] == 'OK':
                    Clock.schedule_once(partial(self.create,r))
                    time.sleep(1)
                else:
                    Clock.schedule_once(partial(self.exit,r['msg']))
                    break
                
    def exit(self,msg=None,*args): #TODO create way to exit to main screen in case of network error
        self.lobby_thread_flag = 1
        try:
            p = {
                'action': 'leave',
                'id': self.code,
                'p': self.player_id,
                'secret': self.secret
            }
            requests.get(url=LOBBYURL, params=p)
        except:
            pass
        self.secret = None
        self.watch_player = None
        self.player_id = None
        self.code = None
        self.alias = None
        self.challenge_id = None
        self.challenge_name = None
        self.type = None
        self.lobby_updater = None
        self.get_attempts = 0
        self.app.remove_lobby_button()
        if self.global_lobby is True:
            self.app.sm.current = 'Online'
            self.global_lobby = False
        else:
            self.app.LobbyList.refresh()
        if msg:
            GameModal(msg,self.localize("TERM_DISMISS")).open()

    def send_challenge(self, obj, name, id, *args):
        self.opponent = name
        self.watch_player = None
        for k,v in self.widget_index.items():
            try:
                if k != self.player_id and v.parent == self.player_list:
                    v.ids['WatchBtn'].text = self.localize("TERM_FOLLOW").upper()
            except KeyError:
                pass
        self.challenge_name = name
        self.challenge_id = id
        popup = GameModal(self.localize("LOBBY_MENU_CHALLENGING",self.challenge_name),self.localize("TERM_QUIT"))
        popup.bind_btn(partial(self.dismiss, p=popup))
        popup.open()
        self.active_pop = popup
        caster = threading.Thread(
            target=self.app.game.host, args=[self,id], daemon=True)
        caster.start()

    def set_ip(self,ip=None):
        if ":" in ip: #IPv6 if :
            ip = "[" + ip + "]" + ":" + revival_config['Network']['Port']
        else:
            ip = ip + ":" + revival_config['Network']['Port']
        p = {
            't': self.challenge_id,
            'p': self.player_id,
            'action': 'challenge',
            'id': self.code,
            'ip': ip,
            'secret': self.secret
        }
        c = requests.get(url=LOBBYURL, params=p).json()
        return True
        
    def accept_challenge(self, obj, name, id, ip, *args):
        #TODO automatically switch to IPv6 if challenge is accepted
        self.opponent = name
        self.watch_player = None
        for k,v in self.widget_index.items():
            try:
                if k != self.player_id and v.parent == self.player_list:
                    v.ids['WatchBtn'].text = self.localize("TERM_FOLLOW").upper()
            except KeyError:
                pass
        caster = threading.Thread(target=self.app.game.join, args=[
                                  ip, self, id], daemon=True)
        caster.start()
        threading.Thread(target=self.send_pre_accept,args=[self.player_id,id]).start()
        popup = GameModal(self.localize("LOBBY_MENU_CONNECTING",name),self.localize("TERM_QUIT"))
        popup.bind_btn(partial(self.dismiss, p=popup))
        popup.open()
        self.active_pop = popup

    def send_pre_accept(self,id,target):
        p = {
            't': target,
            'p': id,
            'action': 'pre_accept',
            'id': self.code,
            'secret': self.secret
        }
        c = requests.get(url=LOBBYURL, params=p).json()

    def confirm(self, obj, p, d, n, t=None, *args):
        try:
            self.app.game.confirm_frames(int(d.text))
            #self.opponent = n # do we need this?
            self.active_pop.modal_txt.text += "\n" + self.localize("ONLINE_MENU_CONN_INFO")
            p.dismiss()
            if t != None: #if accepting, run EFZ check
                threading.Thread(target=self.wait_for_EFZ, args=[t]).start()
        except ValueError:
            pass
        
    def wait_for_EFZ(self, t):
        while True:
            if self.app.game.playing is True and self.active_pop != None:
                resp = {
                    't': t,
                    'p': self.player_id,
                    'action': 'accept',
                    'id': self.code,
                    'secret': self.secret
                }
                print(resp)
                c = requests.get(url=LOBBYURL, params=resp).json()
                print(c)
                break
            elif self.app.game.aproc == None:
                break

    def watch_match(self, obj=None, name="", ip="", *args):
        #TODO auto switch to IPv6 if IP is confirmed
        self.watch_player = None
        self.spectate = True
        for k,v in self.widget_index.items():
            try:
                if k != self.player_id and v.parent == self.player_list:
                    v.ids['WatchBtn'].text = self.localize("TERM_FOLLOW").upper()
            except KeyError:
                pass
        caster = threading.Thread(
            target=self.app.game.watch, args=[ip,self], daemon=True)
        caster.start()
        popup = GameModal(self.localize("LOBBY_MENU_WATCHING",name),self.localize("TERM_QUIT"))
        popup.bind_btn(partial(self.dismiss, p=popup))
        popup.open()
        self.active_pop = popup

    def set_frames(self, delay, avg_ping, min_ping, max_ping, min_delay, target): #target for Lobby call, dummied out here
        Clock.schedule_once(partial(self.set_frames_func, delay, avg_ping, min_ping, max_ping, min_delay, target))

    def set_frames_func(self, delay, avg_ping, min_ping, max_ping, min_delay, target, *args):
        popup = FrameModal()
        popup.frame_txt.text = self.localize('GAME_MODAL_INFO_NAME') % (
            self.opponent, avg_ping, max_ping, min_ping, delay, min_delay)
        popup.d_input.text = str(delay)
        popup.start_btn.bind(on_release=partial(
            self.confirm, p=popup, d=popup.d_input, n=self.opponent, t=target))
        popup.close_btn.bind(on_release=partial(
            self.dismiss, p=popup))
        popup.open()

    def dismiss(self, obj, p, *args):
        self.app.game.kill_revival()
        self.spectate = False
        self.challenge_name = None
        self.opponent = None
        self.challenge_id = None
        r = {
            'action': 'end',
            'p': self.player_id,
            'id': self.code,
            'secret': self.secret
        }
        requests.get(url=LOBBYURL, params=r)
        p.dismiss()
        self.dismiss_active_pop()

    def invite_link(self,*args):
        if self.alias:
            pyperclip.copy('concertoefz://%s' % self.alias)
        else:
            pyperclip.copy('concertoefz://%s' % self.code)
        threading.Thread(target=self.invite_ui).start()

    def invite_ui(self):
        if self.lobby_code.text != self.localize("LOBBY_MENU_LINK"):
            t = self.lobby_code.text
            self.lobby_code.text = self.localize("LOBBY_MENU_LINK")
            time.sleep(1)
            self.lobby_code.text = t