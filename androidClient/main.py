from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
import kivy.app
from kivy.clock  import Clock
import multiprocessing
from helpFunc import *
import time,uuid
createLog()
createCommandFile()

from collections import deque

def aa(config):
    f = open('service_config','w')
    s = json.dumps(config)
    f.write(s)
    f.close()  
    import android
    android.start_service(title='service name',
                          description='service description',
                          arg='argument to service')            
        
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty
from kivy.lang import Builder
import os,json
Builder.load_string('''
<ScrollableLabel>:
    Label:
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width, None
        text: root.text
''')

class ScrollableLabel(ScrollView):
    text = StringProperty('')
    
class SimpleApp(kivy.app.App):
    def __init__(self):
        super().__init__()
        self.commandId = ''
        self.logKeys = deque()
        self.hasStart = False
        self.log = deque()
        self.display = True   
        self.starting = False
        self.stoping = False
        self.stoped = True
        self.startTime = 0
        self.toQuit = False

    def writeCommand(self,dt):
        f = open('commandIn.txt','w')
        m = {'toStop':self.stoping,'commandId':self.commandId}
        j = json.dumps(m)
        f.write(j)
        f.close()
    
    def readCommand(self,dt):
        t1 = time.monotonic()
        if self.stoped:
            if self.toQuit:
                self.stop()
            return
        if not self.hasStart and time.monotonic()-self.startTime>5:
            self.stoping = True
            self.writeCommand(None)
            self.stoped = True
            self.sBu.bind(on_press=self.onStart)
            self.sBu.text = 'start'   
            if self.toQuit:
                self.stop()            
            return
        
        f = open('commandOut.txt')
        s = f.read()
        f.close()
        try:
            m = json.loads(s)
        except:
            return
        if m.get('commandId','')!=self.commandId:
            return
        self.hasStart = True
        
        if self.starting:
            self.starting = False
            self.sBu.bind(on_press=self.onStop)
            self.sBu.text = 'stop'
        
        if  not self.stoped and time.monotonic()-m['aliveTime']>5 and time.monotonic()-ti<0.1:
            if not self.starting and not self.stoping:
                self.sBu.unbind(on_press=self.onStop)
            self.sBu.bind(on_press=self.onStart)
            self.sBu.text = 'start'     
            self.stoped = True
            self.stoping = True
            self.writeCommand(None)            
            if self.toQuit:
                self.stop()                
        if m.get('exit',False):
            self.stoped = True
            if not self.starting and not self.stoping:
                self.sBu.unbind(on_press=self.onStop)            
            self.sBu.bind(on_press=self.onStart)
            self.sBu.text = 'start'                
            if self.toQuit:
                self.stop()        
                
    def onStop(self,b):
        self.stoping = True
        self.sBu.unbind(on_press=self.onStop)
        self.sBu.text = 'stoping'        
        
    def dealLog(self,dt):
        m = readLog()
        for k,v in m.items():
            if k not in self.logKeys:
                self.logKeys.append(k)
                self.log.append(v)
        while len(self.log)>100:
            self.log.popleft()
            self.logKeys.popleft()
        if self.display:
            self.out.text=''.join(self.log)
            
    def onClear(self,dt):
        self.log = deque()
        self.logKeys = deque()
        
    def build(self):
        l = os.listdir()
        self.con = {}
        if 'my_config.json' not in l:
            self.con={'ip':'45.195.203.220','port':19023,'key':'bigxSalt','Tout':1,'MPort':100,'LPort':10,\
               'IDose':4,'DDose':2,'LRate':0.08,'MRate':0.5,'Ahead':3000,'size':1400,\
               'span':1,'limit':100,'speed':250,'ONum':10,'dose2':1,'LGot':100,\
               'listen':9999,'close':50}
        else:
            f = open('my_config.json')
            s = f.read()
            self.con = json.loads(s)
            f.close()

        Clock.schedule_interval(self.dealLog,1)
        Clock.schedule_interval(self.readCommand,0.2)
        Clock.schedule_interval(self.writeCommand,0.2)
        
        bv = BoxLayout(orientation="vertical")
        bh1 = BoxLayout(orientation="horizontal")
        bh2 = BoxLayout(orientation="horizontal")
        t = ''
        h1b1 = BoxLayout(orientation="vertical")
        h1b2 = BoxLayout(orientation="vertical")
        self.mm = self.iniL(h1b1)
        self .out = out = ScrollableLabel(text=t)
        for k,v in self.mm.items():
            v.text=str(self.con[k])
        self.sBu = bu1 = Button(text='start')
        bu2 = Button(text='text')
        bu3 = Button(text='clear')
        self.quitB = bu4 = Button(text='quit')
        
        btt = BoxLayout(orientation="horizontal")
        btt.add_widget(bu1)
        btt.add_widget(bu4)
        bu1.bind(on_press=self.onStart)
        bu2.bind(on_press=self.onText)
        bu3.bind(on_press=self.onClear)
        bu4.bind(on_press=self.onQuit)
        bh1.add_widget(h1b1)
        bh1.add_widget(h1b2)
        h1b2.add_widget(btt)
        h1b2.add_widget(bu2)
        h1b2.add_widget(bu3)

        bv.add_widget(bh1)
        bv.add_widget(out)
        self.dealForceCLose()
        return bv   
    
    def dealForceCLose(self):
        f = open('commandOut.txt')
        s = f.read()
        f.close()
        try:
            m = json.loads(s)
        except:
            return
        if time.monotonic()- m['aliveTime']>1:
            return
        if m.get('exit',False):
            return
        
        self.commandId = m['commandId']
        self.hasStart = True
        self.stoped = False
        self.sBu.unbind(on_press=self.onStart)
        self.sBu.bind(on_press=self.onStop)
        self.sBu.text = 'stop'        
          
    def onQuit(self,b):
        self.quitB.unbind(on_press=self.onQuit)
        self.quitB.text='quiting'
        self.stoping = True
        self.writeCommand(None)
        self.toQuit = True
        
    def iniL(self,h1b1):
        mm = {}
        l = Label(text='ip')
        ipIn = TextInput()
        lih1 = BoxLayout(orientation="horizontal")
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        mm['ip'] = ipIn
        self.ip = ipIn
        
        l = Label(text='port')
        ipIn = TextInput()
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        h1b1.add_widget(lih1)
        mm['port'] = ipIn
        self.port = ipIn
        
        l = Label(text='key')
        ipIn = TextInput()
        lih1 = BoxLayout(orientation="horizontal")
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        mm['key'] = ipIn
        self.key = ipIn
        
        l = Label(text='Tout')
        ipIn = TextInput()
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        h1b1.add_widget(lih1)
        mm['Tout'] = ipIn
        self.Tout = ipIn
        
        l = Label(text='listen')
        ipIn = TextInput()
        lih1 = BoxLayout(orientation="horizontal")
        lih1.add_widget(l)
        lih1.add_widget(ipIn) 
        mm['listen'] = ipIn
        self.listen = ipIn
        
        l = Label(text='LGot')
        ipIn = TextInput()
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        h1b1.add_widget(lih1)   
        
        mm['LGot'] = ipIn
        self.LGot = ipIn
        
        l = Label(text='MPort')
        ipIn = TextInput()
        lih1 = BoxLayout(orientation="horizontal")
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        mm['MPort'] = ipIn
        self.MPort = ipIn
        
        l = Label(text='LPort')
        ipIn = TextInput()
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        h1b1.add_widget(lih1)   
        mm['LPort'] = ipIn
        self.LPort = ipIn
        
        l = Label(text='IDose')
        ipIn = TextInput()
        lih1 = BoxLayout(orientation="horizontal")
        lih1.add_widget(l)
        lih1.add_widget(ipIn) 
        mm['IDose'] = ipIn
        self.IDose = ipIn
        
        l = Label(text='DDose')
        ipIn = TextInput()
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        h1b1.add_widget(lih1)   
        mm['DDose'] = ipIn
        self.DDose = ipIn
        
        l = Label(text='LRate')
        ipIn = TextInput()
        lih1 = BoxLayout(orientation="horizontal")
        lih1.add_widget(l)
        lih1.add_widget(ipIn) 
        mm['LRate'] = ipIn
        self.LRate = ipIn
        
        l = Label(text='MRate')
        ipIn = TextInput()
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        h1b1.add_widget(lih1)   
        mm['MRate'] = ipIn
        self.MRate = ipIn
        
        l = Label(text='Ahead')
        ipIn = TextInput()
        lih1 = BoxLayout(orientation="horizontal")
        lih1.add_widget(l)
        lih1.add_widget(ipIn) 
        mm['Ahead'] = ipIn
        self.Ahead = ipIn
        
        l = Label(text='size')
        ipIn = TextInput()
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        h1b1.add_widget(lih1)   
        mm['size'] = ipIn
        self.size = ipIn
        
        l = Label(text='span')
        ipIn = TextInput()
        lih1 = BoxLayout(orientation="horizontal")
        lih1.add_widget(l)
        lih1.add_widget(ipIn) 
        mm['span'] = ipIn
        self.span = ipIn
        
        l = Label(text='limit')
        ipIn = TextInput()
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        h1b1.add_widget(lih1)   
        mm['limit'] =ipIn
        self.limit = ipIn
        
        l = Label(text='speed')
        ipIn = TextInput()
        lih1 = BoxLayout(orientation="horizontal")
        lih1.add_widget(l)
        lih1.add_widget(ipIn) 
        mm['speed'] = ipIn
        self.speed = ipIn
        
        l = Label(text='ONum')
        ipIn = TextInput()
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        h1b1.add_widget(lih1)   
        mm['ONum'] = ipIn
        self.ONum = ipIn

        l = Label(text='dose2')
        ipIn = TextInput()
        lih1 = BoxLayout(orientation="horizontal")
        lih1.add_widget(l)
        lih1.add_widget(ipIn) 
        mm['dose2'] = ipIn
        self.dose2 = ipIn
        
        l = Label(text='close')
        ipIn = TextInput()
        lih1.add_widget(l)
        lih1.add_widget(ipIn)
        h1b1.add_widget(lih1)   
        mm['close'] = ipIn
        self.close = ipIn
        return mm
       

    def onText(self,b):
        self.display = not self.display 
        
    def on_pause(self):
        return True
    def onStart(self, btn):
        self.sBu.unbind(on_press=self.onStart)
        self.sBu.text = 'starting'
        self.stoped = self.stoping = False
        self.starting = True
        self.hasStart = False
        self.startTime = time.monotonic()
        
        config = {}
        for k,v in self.mm.items():
            if k in ['ip','key']:
                config[k]=v.text
            elif k in ['Tout','LRate','MRate','span']:
                config[k]=float(v.text)
            else:
                config[k]=abs(int(float(v.text)))
        f = open('commandOut.txt','w')
        f.close()
        self.commandId = u = str(uuid.uuid1())
        config['commandId'] = u        
        j = json.dumps(config)
        f = open('my_config.json','w')
        f.write(j)
        f.close()        
        aa(config)
        
if __name__ == "__main__":
    simpleApp = SimpleApp()
    simpleApp.run()