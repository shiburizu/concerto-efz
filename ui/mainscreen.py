from ui.concertoscreen import ConcertoScreen
from ui.modals import GameModal
import ui.lang
import config
import threading

class MainScreen(ConcertoScreen):

    def __init__(self,CApp):
        super().__init__(CApp)
        self.ids['version'].text = "v%s" % config.CURRENT_VERSION
        if config.DEBUG_VERSION != "":
            self.ids['version'].text += " - %s" % config.DEBUG_VERSION

    def local(self, *args):
        self.offline_pop(ui.lang.localize("MAIN_MENU_LOCAL_VS"))
        threading.Thread(target=self.app.game.local,args=[self],daemon=True).start()

    def offline_pop(self, mode, tip=""):
        popup = GameModal(ui.lang.localize('OFFLINE_MENU_STARTING') % (mode,tip),ui.lang.localize('TERM_STANDBY'))
        popup.close_btn.disabled = True
        popup.open()
        self.active_pop = popup
        self.app.offline_mode = mode