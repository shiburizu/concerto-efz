from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label 
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from ui.modals import GameModal
from functools import partial
import ui.lang 

class OptionRow(BoxLayout):

    def __init__(self, **kwargs):
        super(OptionRow, self).__init__(**kwargs)
        self.size_hint_x = 1
        self.size_hint_y = None
        self.height = 30
        self.inptype = None
        self.inp = None

    def int_filter(self,txt,from_undo=False):
        try:
            int(txt)
            return txt
        except:
            return ''
    
    def name_filter(self,txt,from_undo=False):
        if len(self.inp.text+txt) <= 20:
            return txt
        else:
            return ''

    def create_opt(self,k,v,inptype='string',lbltxt=None,vals=[],hint=None):
        if lbltxt:
            lbl = Label(text=lbltxt)
        else:
            lbl = Label(text=k)
        self.add_widget(lbl)

        self.inptype = inptype

        if inptype == 'int':
            inp = TextInput(text=v,multiline=False,input_filter=self.int_filter)
            self.add_widget(inp)
        elif inptype == 'bool' or inptype == 'boolint':
            inp = CheckBox()
            if v == "True" or v == "1":
                inp.active = True
            self.add_widget(inp)
        elif inptype == 'spinner':
            spinnerbox = BoxLayout()
            inp = Spinner(values=vals,text=v)
            spinnerbox.add_widget(inp)
            self.add_widget(spinnerbox)
        else:
            if k == "Name":
                self.height=33
                inp = TextInput(text=v,multiline=False,input_filter=self.name_filter,font_name='res/notosansjp.otf',font_size=14)
            else:
                inp = TextInput(text=v,multiline=False)
            self.add_widget(inp)

        self.inp = inp

        if hint:
            lbl.size_hint_x = 0.50
            if inptype == 'spinner':
                spinnerbox.size_hint_x = 0.42
            else:
                self.inp.size_hint_x = 0.42
            btn = Button(text="( ? )",size_hint_x=0.08,outline_width=2,background_normal='',background_color=(0,0,0,0))
            btn.bind(on_release=partial(self.hint,hint))
            self.add_widget(btn)

    def hint(self,msg,*args):
        popup = GameModal()
        popup.modal_txt.text = msg
        popup.close_btn.disabled = False
        popup.bind_btn(popup.dismiss)
        popup.close_btn.text = ui.lang.localize("TERM_DISMISS")
        popup.open()
            
        