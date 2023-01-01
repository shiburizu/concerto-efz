from ui.concertoscreen import ConcertoScreen
import re, math
from config import PATH
from datetime import timedelta
from kivy.properties import ObjectProperty
from ui.buttons import SessionBtn
from ui.modals import SessionModal
import pyperclip
from functools import partial

session_row = r'(\d{4}\/\d{2}\/\d{2}) (\d{2}:\d{2}:\d{2})\s+(.+) VS (.+)'
match_row = r'(\d{4}\/\d{2}\/\d{2}) (\d{2}:\d{2}:\d{2})\s+(\w+) VS (\w+)\s+Rounds: (\d) (\d)\s+Duration:\s+(\d{1,}:\d{1,})\s+Score:\s+(\d{1,}) (\d{1,})'


def truncate(number, digits) -> float:
    nbDecimals = len(str(number).split('.')[1]) 
    if nbDecimals <= digits:
        return number
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper

class LogScreen(ConcertoScreen):
    nameLabel = ObjectProperty(None)
    rateLabel = ObjectProperty(None)
    timeLabel = ObjectProperty(None)
    resultList = ObjectProperty(None)
    logList = ObjectProperty(None)
    
    def __init__(self,CApp):
        super().__init__(CApp)
        self.sessions = {}
        self.matches = {}
        self.players = {}

    def buildLog(self,file='BattleLog.txt'):
        self.sessions = {}
        self.matches = {}
        self.players = {}
        #builds the internal data based on the battlelog.
        with open(PATH + file,'r',encoding='utf-8') as f:
            last_session = None
            for i in f.readlines():
                if len(i) > 10: #basic way to skip empty lines
                    result = re.search(match_row, i)
                    if result == None:
                        result = re.search(session_row,i)
                        if result != None:
                            s = Session(result.group(1),result.group(2),
                            result.group(3).strip(),result.group(4).strip())
                            self.sessions[result.group(1) + ' ' + result.group(2)] = s
                            last_session = s
                            if s.p1 in self.players:
                                self.players[s.p1].append(s)
                            else:
                                self.players[s.p1] = [s]
                            if s.p2 in self.players:
                                self.players[s.p2].append(s)
                            else:
                                self.players[s.p2] = [s]
                    else:
                        result = re.search(match_row,i)
                        if result != None:
                            m = Match(result.group(1),result.group(2),
                            result.group(3),result.group(4),result.group(5),
                            result.group(6),result.group(7),result.group(8),
                            result.group(9),session=last_session)
                            last_session.add_match(m)
                            self.matches[result.group(1) + ' ' + result.group(2)] = m
    
    def buildMatchup(self,p1,p2=None,c1='All',c2='All'):
        self.buildLog()
        report = {
            'result' : 'fail'
        }
        if p1 in self.players:
            if p2 in self.players or p2 == None:
                p1data = self.players[p1]
                p1time = timedelta()
                p1win = 0
                p1loss = 0
                p1games = 0
                p1scores = {}
                p1sessions = []
                for i in p1data:
                    for g in i.matches:
                        if g.p1 == p1 and (c1 == 'All' or g.c1 == c1) and (p2 == None or g.p2 == p2):
                            p1time += g.d
                            if g.r1 > g.r2:
                                p1win += 1
                            elif g.r1 < g.r2:
                                p1loss += 1
                            p1games += 1
                            if "%s-%s" % (g.r1,g.r2) not in p1scores:
                                p1scores["%s-%s" % (g.r1,g.r2)] = 1
                            else:
                                p1scores["%s-%s" % (g.r1,g.r2)] += 1

                            if i not in p1sessions:
                                p1sessions.append(i)
                        elif g.p2 == p1 and (c1 == 'All' or g.c2 == c1) and (p2 == None or g.p1 == p2):
                            p1time += g.d
                            if g.r2 > g.r1:
                                p1win += 1
                            elif g.r2 < g.r1:
                                p1loss += 1
                            p1games += 1
                            if "%s-%s" % (g.r2,g.r1) not in p1scores:
                                p1scores["%s-%s" % (g.r2,g.r1)] = 1
                            else:
                                p1scores["%s-%s" % (g.r2,g.r1)] += 1

                            if i not in p1sessions:
                                p1sessions.append(i)
                if p1sessions != []:
                    report = {
                        'result': 'success',
                        'player': p1,
                        'char' : c1,
                        'oppchar' : c2,
                        'hours' : str(p1time),
                        'avg' : str(timedelta(seconds=int(p1time.total_seconds()/p1games))),
                        'total_matches' : p1games,
                        'wins' : p1win,
                        'losses' : p1loss,
                        'winrate' : truncate(p1win / p1games * 100,2),
                        'scores' : p1scores,
                        'sessions' : p1sessions
                    }
                    if p2 == None:
                        report['opponent'] = 'All'
                    else:
                        report['opponent'] = p2
                else:
                    report['result'] = "No data found for your criteria."
            else:
                report['result'] = "Opponent not found."
        else:
            report['result'] = "Player not found."
        return report

    def buildUI(self,report):
        data = []
        if report['result'] == 'success':
            self.nameLabel.text = '%s (%s) vs %s (%s)' % (report['player'],report['char'],report['opponent'],report['oppchar'])
            self.rateLabel.text = '%s%% Winrate, %sW/%sL (%s Total)' % (report['winrate'],report['wins'],report['losses'],report['total_matches'])
            self.timeLabel.text = '%s Hours Played, Avg. Match Time %s' % (report['hours'],report['avg'])
            self.resultList.clear_widgets()
            for i in reversed(report['scores'].items()):
                r = SessionBtn()
                r.text = "[%s]: %s times, %s%% of games" % (i[0],i[1],truncate(i[1]/ report['total_matches'] * 100,2))
                r.halign = 'center'
                self.resultList.add_widget(r)
            for i in reversed(report['sessions']):
                session = { 'text' : "%s %s: %s (%s) VS %s (%s) - %s" % (i.date,i.time,i.p1,i.final[0],i.p2,i.final[1],i.duration) }
                g = "[b]" + session['text'] + "[/b]" + "\n"
                for n in i.matches:
                    if n.r1 > n.r2:
                        g += "%s %s: [color=47ff66][b]%s[/color] (%s)[/b] VS [color=e03838][b]%s[/color] (%s)[/b] - %s\n" % (n.date,n.time,n.c1,n.r1,n.c2,n.r2,n.d)
                    elif n.r2 > n.r1:
                        g += "%s %s: [color=e03838][b]%s[/color] (%s)[/b] VS [color=47ff66][b]%s[/color] (%s)[/b] - %s\n" % (n.date,n.time,n.c1,n.r1,n.c2,n.r2,n.d)
                session['on_release'] = partial(self.openSession,g.strip())
                data.append(session)
            self.logList.data = data
        else:
            pass #return fail reason

    def copySummary(self):
        res = self.nameLabel.text + "\n" + self.rateLabel.text + "\n" + self.timeLabel.text
        for i in self.resultList.children:
            res += "\n"+ i.text
        pyperclip.copy(res)
    
    def copyFromPartial(self,text,obj=None):
        text = text.replace("[b]","")
        text = text.replace("[/b]","")
        text = text.replace("[color=47ff66]","")
        text = text.replace("[color=e03838]","")
        text = text.replace("[/color]","")
        pyperclip.copy(text)

    def openSession(self,text,obj=None):
        if text != "":
            s = SessionModal()
            s.modal_txt.text = text
            s.btn_1.text = "Close"
            s.btn_2.text = "Copy"
            s.btn_1.bind(on_release=s.dismiss)
            s.btn_2.bind(on_release=partial(self.copyFromPartial,text))
            s.open()
        
class Match():

    def __init__(self,date,time,c1,c2,r1,r2,d,s1,s2,session=None):
        self.date = date
        self.time = time
        self.c1 = c1
        self.c2 = c2
        self.r1 = r1
        self.r2 = r2
        self.d = timedelta(minutes=int(d.split(':')[0]),seconds=int(d.split(':')[1]))
        self.s1 = s1
        self.s2 = s2
        self.session = session
        if session != None:
            self.p1 = session.p1
            self.p2 = session.p2

class Session():

    def __init__(self,date,time,p1,p2,matches=[]):
        self.date = date
        self.time = time
        self.p1 = p1
        self.p2 = p2
        self.chars = ([],[])
        self.final = [0,0]
        self.matches = []
        if matches != []:
            for i in matches:
                self.add_match(i)
        self.duration = timedelta()

    def add_match(self,match):
        #add chars, add up duration, update final
        self.matches.append(match)
        if match.c1 not in self.chars[0]:
            self.chars[0].append(match.c1)
        if match.c2 not in self.chars[1]:
            self.chars[1].append(match.c2)
        self.final[0] = int(match.s1)
        self.final[1] = int(match.s2)
        self.duration += match.d

    def get_summary(self):
        print("SUMMARY FOR: %s vs %s" % (self.p1,self.p2))
        print("START TIME: %s %s" % (self.date,self.time))
        print("TOTAL DURATION: %s" % self.duration)
        print("FINAL SCORE: %s to %s" % (self.final[0], self.final[1]))
        print("P1 CHARS: %s" % ",".join(self.chars[0]))
        print("P2 CHARS: %s" % ",".join(self.chars[1]))
        print("TOTAL MATCHES: %s" % len(self.matches))
        #return start time, total duration, final score and characters used per player

# Match Format
# time: Timestamp
# p1 : Shimatora
# p2 : dobster
# c1 : Akiko
# c2 : Nagamori
# r1 : 2
# r2 : 1
# d: 2:39
# s1: 1
# s2: 0
# session: reference to Session object

# Session format
# time: Session timestamp
# p1: Shimatora
# p2: dobster
# chars: List of all characters used in Session (Char, PlayerName)
# matches: list of all Match objects
# final: final set score (taken from last match)

# sessions: {timestamp: Session object}
# matches: {timestamp: Match object}
# players: {player name : Session object}