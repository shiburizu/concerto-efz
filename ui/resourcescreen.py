from ui.concertoscreen import ConcertoScreen
from ui.modals import MatchupModal, GameModal
from config import PATH
import os

class ResourceScreen(ConcertoScreen):

    def __init__(self,CApp):
        super().__init__(CApp)
        if PATH in self.ids['char'].source:
            self.ids['credit'].text = ""

    def checkLog(self):
        if os.path.exists("BattleLog.txt"):
            return True
        else:
            msg = GameModal('BattleLog.txt not found.')
            msg.bind_btn(msg.dismiss())
            msg.open()
            return False

    def openMatchups(self):
        if self.checkLog():
            modal = MatchupModal()
            modal.submit_search.bind(on_release=self.searchMatchup)
            self.active_pop = modal
            modal.open()

    def searchMatchup(self,obj=None):
        if self.checkLog():
            p1 = self.active_pop.p1_input.text.strip()
            p2 = self.active_pop.p2_input.text.strip()
            p1c = self.active_pop.p1_char.text
            p2c = self.active_pop.p2_char.text
            if p2 == '':
                p2 = None
            if p1 != '' and p2 != '':
                search = self.app.LogScreen.buildMatchup(p1,p2,p1c,p2c)
                if search['result'] == 'success':
                    self.app.LogScreen.buildUI(search)
                    self.dismiss_active_pop()
                    self.app.sm.current = 'Log'
                else:
                    self.dismiss_active_pop()
                    msg = GameModal(search['result'])
                    msg.bind_btn(msg.dismiss())
                    msg.open()
            
    def battleLog(self):
        if self.checkLog():
            self.app.LogScreen.buildLog()
            self.app.LogOnlyScreen.buildUI()
            self.app.sm.current = 'LogOnly'