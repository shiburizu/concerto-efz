from ui.concertoscreen import ConcertoScreen
import re
from config import PATH

session_row = r'(\d{4}/\d{2}/\d{2}) (\d{2}:\d{2}:\d{2})\s+(\w+) VS (\w+)'
match_row = r'(\d{4}/\d{2}/\d{2}) (\d{2}:\d{2}:\d{2})\s+(\w+) VS (\w+)\s+Rounds: (\d \d)\s+Duration:\s+(\d{1,}:\d{1,})\s+Score:\s+(\d{1,}) (\d{1,})'

class LogScreen(ConcertoScreen):
    
    def __init__(self,CApp):
        super().__init__(CApp)
        self.sessions = {}
        self.matches = {}
        self.players = {}
        #self.buildLog()

    def buildLog(self,file='BattleLog.txt'):
        self.sessions = {}
        self.matches = {}
        self.players = {}
        #builds the internal data based on the battlelog.
        last_session = None
        with open(PATH + file,'r',encoding='utf-8') as f:
            for i in f.readlines():
                if len(i) > 10: #basic way to skip empty lines
                    result = re.search(session_row,i)
                    if result != None:
                        s = Session(result.group(1),result.group(2),
                        result.group(3),result.group(4))
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
                            result.group(9),result.group(10),result.group(11),
                            session=last_session)
                            last_session.add_match(m)
                            self.matches[result.group(1) + ' ' + result.group(2)] = m
                        else:
                            pass

    def buildMatchup(self,p1=None,p2=None,c1='All',c2='All'):
        #builds the UI using info from the battlelog.
        pass


class Match():

    def __init__(self,date,time,p1,p2,c1,c2,r1,r2,d,s1,s2,session=None):
        self.date = date
        self.time = time
        self.p1 = p1
        self.p2 = p2
        self.c1 = c1
        self.c2 = c2
        self.r1 = r1
        self.r2 = r2
        self.d = d
        self.s1 = s1
        self.s2 = s2
        self.session = session

class Session():

    def __init__(self,date,time,p1,p2,chars=([],[]),matches=[],final=(0,0)):
        self.date = date
        self.time = time
        self.p1 = p1
        self.p2 = p2
        self.chars = chars
        self.final = final
        self.matches = None
        if matches != []:
            for i in matches:
                self.add_match(i)
        self.duration = None #calc during add_match

    def add_match(self,match):
        #add chars, add up duration, update final
        self.matches.append(match)
        if match.c1 not in self.chars[0]:
            self.chars[0].append(match.c1)
        if match.c2 not in self.chars[1]:
            self.chars[1].append(match.c2)
        self.final[0] + match.s1
        self.final[1] + match.s2
        #TODO add duration

    def get_player_summary(self,player):
        pass
        #like get_summary, but only for specified player

    def get_summary(self):
        pass
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