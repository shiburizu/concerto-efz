from kivy.uix.modalview import ModalView
from kivy.properties import ObjectProperty
from kivy.uix.button import Button

class GameModal(ModalView):
    modal_txt = ObjectProperty(None)
    close_btn = ObjectProperty(None)
    btn_row = ObjectProperty(None)

    def __init__(self,msg='',btntext='Dismiss',btnaction=None):
        super().__init__()
        self.modal_txt.text=msg
        self.close_btn.text=btntext
        if btnaction:
            self.close_btn.bind(on_release=btnaction)
        else:
            self.close_btn.bind(on_release=self.dismiss)

    def bind_btn(self,btnaction=None):
        if btnaction:
            self.close_btn.bind(on_release=btnaction)

    def bind_secondary(self,btnaction=None,lbl="button"):
        if btnaction:
            second = Button(text=lbl,outline_width=2,font_name='res/texgyreheros-bolditalic.otf')
            second.bind(on_release=btnaction)
            self.btn_row.add_widget(second) 

class ProgressModal(ModalView):
    modal_txt = ObjectProperty(None)
    prog_bar = ObjectProperty(None)


class ChoiceModal(ModalView):
    modal_txt = ObjectProperty(None)
    btn_1 = ObjectProperty(None)
    btn_2 = ObjectProperty(None)


class DirectModal(ModalView):
    join_ip = ObjectProperty(None)
    connect_txt = ObjectProperty(None)
    screen = None

class FrameModal(ModalView):
    frame_txt = ObjectProperty(None)
    d_input = ObjectProperty(None)
    start_btn = ObjectProperty(None)
    close_btn = ObjectProperty(None)