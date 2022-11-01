from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label 
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.textinput import TextInput
from kivy.graphics import Color
from kivy.graphics import Rectangle

from ui.buttons import DummyBtn
import ui.lang 

class OptionRow(BoxLayout):

    def __init__(self, **kwargs):
        super(OptionRow, self).__init__(**kwargs)
        self.size_hint_x = 1
        self.size_hint_y = None
        self.height = 28
        self.inptype = None
        self.inp = None

    def create_opt(self,k,v,inptype='string',lbltxt=None,vals=[],hint=None):
        if lbltxt:
            lbl = Label(text=lbltxt)
        else:
            lbl = Label(text=k)
        self.add_widget(lbl)

        self.inptype = inptype

        if inptype == 'int':
            inp = TextInput(text=v,multiline=False,input_filter='int')
        elif inptype == 'bool' or inptype == 'boolint':
            inp = CheckBox()
        elif inptype == 'spinner':
            spinnerbox = BoxLayout()
            inp = Spinner(values=vals)
        else:
            inp = TextInput(text=v,multiline=False)

        self.inp = inp
        self.add_widget(inp)