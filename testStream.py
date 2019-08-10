import threading
from tornado.locks import Event
from tornado.ioloop import IOLoop
from tornado import gen
from helpFunc import *
import time

class ts():
    def __init__(self,ioloop):
        self.ioloop = ioloop
        self.rEvent = Event()
        self.wEvent = Event()
        self.writeLock = threading.Lock()
        self.readLock = threading.Lock()
        self.writeBuffer = ''
        self.readBuffer = ''
        IOLoop.current().add_callback(self.doRead)
        IOLoop.current().add_callback(self.doWrite)
        
    @gen.coroutine
    def doRead(self):
        co = 0
        while True:
            yield self.rEvent.wait()
            self.rEvent.clear()
            while True:
                msg = TOUMsg()
                self.readLock.acquire()
                r,self.readBuffer = msg.unpack(self.readBuffer)
                self.readLock.release()
                if not r:
                    break
                co += 1
                if co%10==0:
                    print ('co1',co,getRunningTime())      
    @gen.coroutine
    def doWrite(self):
        co = 0
        while True:
            yield self.wEvent.wait()
            self.wEvent.clear()     
            while True:
                if len(self.writeBuffer)>con_streamBufferSize:
                    break
                yield gen.sleep(random.randint(3,20)/10.0)
                msg = TOUMsg({},'s'*random.randint(10,2000))
                self.writeLock.acquire()
                self.writeBuffer += msg.pack()
                self.writeLock.release()
                co += 1
                if co%10==0:
                    print ('co2',co,getRunningTime())                        