from ui.concertoscreen import ConcertoScreen
from kivy.properties import ObjectProperty
from ui.buttons import SessionBtn
from ui.modals import SessionModal
from functools import partial
import pyperclip

from kivy.uix.recycleview import RecycleView

class BattleLog(RecycleView):
    def __init__(self, **kwargs):
        super(BattleLog, self).__init__(**kwargs)
        self.data = [{'text': str(x)} for x in range(20)]

class LogOnlyScreen(ConcertoScreen):
    logList = ObjectProperty(None)
    
    def __init__(self,CApp):
        super().__init__(CApp)
        self.log = self.app.LogScreen

    def buildUI(self):
        data = []
        for s in reversed(self.log.sessions):
            i = self.log.sessions[s]
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