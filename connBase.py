from tornado.ioloop import IOLoop
from tornado import gen
from tornado.iostream import StreamClosedError
import functools
from tornado.ioloop import PeriodicCallback
from helpFunc import *
import threading
from tornado.locks import Event
from datetime import timedelta
class connBase():
    def __init__(self,ioloop,isServer):    
        self.ioloop = ioloop
        self.rEvent = Event()
        self.wEvent = Event()
        self.writeLock = threading.Lock()
        self.readLock = threading.Lock()
        self.writeBuffer = b''
        self.readBuffer = b''            
        PeriodicCallback(self.calOutputSize,10000).start()
        IOLoop.instance().add_callback(self.toStream)
        IOLoop.instance().add_callback(self.stream_to_map)
        self.outputMap_byId = {}
        self.outputSize = 0
        self.outputSizeDownEvent = Event()
        self.connMap = {}
        self.eachConnWriteLimit = eachConnWriteLimit
        self.addTaskSeq = 0
        self.addTaskMap = {}
        self.waitIdMap = {}
        self.waitIdEvent = Event()
        self.streamCloseSign = {}
        self.isServer = isServer
        if isServer:
            self.writeBeforeConnMap = {}
            PeriodicCallback(self.deal_writeBeforeConnMap,1000).start()
            
    def checkStreamClose(self,conn_seq,stream):
        self.streamCloseSign[conn_seq] -= 1
        if self.streamCloseSign[conn_seq]==0:
            del self.streamCloseSign[conn_seq]
            try:
                stream.close()
            except:
                pass
            
    def deal_writeBeforeConnMap(self):
        for k in list(self.writeBeforeConnMap.keys()):
            v = self.writeBeforeConnMap[k]
            if v['createTime']<getRunningTime()-100:
                del self.writeBeforeConnMap[k]       
                
    def calOutputSize(self):
        co = 0
        for k,v in self.connMap.items():
            co += len(v['readBuffer'])
        for k,v in self.outputMap_byId.items():
            co += v['msg'].length
        if co<self.outputSize:
            self.outputSizeDownEvent.set()
        self.outputSize = co      
        
    def addConnMap(self,conn_seq):
        m={}
        m['readError'] = False
        m['writeError'] = False
        m['writeNotBack'] = 0
        m['readBuffer'] = b''
        m['rEvent'] = Event()
        self.connMap[conn_seq] = m   
        self.streamCloseSign[conn_seq] = 2
    @gen.coroutine
    def toStream(self):
        while True:
            yield self.wEvent.wait()
            self.wEvent.clear()                
            self.writeLock.acquire()
            l = sorted(self.addTaskMap.keys())
            for i in l:
                msg = self.addTaskMap[i]['con']
                e = self.addTaskMap[i]['event']
                self.writeBuffer += msg.pack()
                e.set()
                del self.addTaskMap[i]
                if len(self.writeBuffer)>con_streamBufferSize:
                    break
            self.writeLock.release()  
                       
    @gen.coroutine
    def addTask(self,msg):
        self.addTaskSeq += 1
        e = Event()
        self.addTaskMap[self.addTaskSeq] = {'con':msg,'event':e}
        yield e.wait()

    def checkDelConn(self,conn_seq):
        if self.connMap[conn_seq]['writeError'] and self.connMap[conn_seq]['readError']:
            self.connMap[conn_seq]['rEvent'].set()
            del self.connMap[conn_seq]        
            
    @gen.coroutine
    def doWrite(self,stream,conn_seq):
        while True:
            if conn_seq not in self.connMap:
                self.checkStreamClose(conn_seq, stream)
                return 
            closeSign = False
            try:
                data = yield  gen.with_timeout (timedelta(seconds=connCheckTime),\
                        stream.read_bytes(eachConnWriteLimit,partial = True), quiet_exceptions=(StreamClosedError))
            except StreamClosedError:  
                closeSign = True            
            except gen.TimeoutError:
                try:
                    IOLoop.current().remove_handler(stream.socket)
                    state = (stream._state & ~IOLoop.current().READ)
                    stream._state = None
                    stream._read_callback = None
                    stream._read_future = None
                    stream._add_io_state(state)   
                    data = b''
                except:
                    closeSign = True                                
            except :
                raise Exception
            if closeSign:
                pack = {'type':'readError','conn_seq':conn_seq}
                msg = TOUMsg(pack,b'')
                yield self.addTask(msg)
                if conn_seq not in self.connMap:
                    self.checkStreamClose(conn_seq, stream)
                    return                
                self.connMap[conn_seq]['writeError'] = True
                self.checkDelConn(conn_seq)              
                self.checkStreamClose(conn_seq, stream)
                return
            
            if conn_seq not in self.connMap :
                self.checkStreamClose(conn_seq, stream)
                return 
            while True:
                if conn_seq not in self.connMap :
                    self.checkStreamClose(conn_seq, stream)
                    return  
                if self.connMap[conn_seq]['writeError']:
                    self.checkStreamClose(conn_seq, stream)
                    return
                if self.connMap[conn_seq]['writeNotBack']<self.eachConnWriteLimit:
                    break
                yield self.connMap[conn_seq]['rEvent'].wait()
                if conn_seq not in self.connMap :
                    self.checkStreamClose(conn_seq, stream)
                    return                  
                self.connMap[conn_seq]['rEvent'].clear()
            if data == b'':
                continue
            con = {'type':'write','conn_seq':conn_seq}
            msg = TOUMsg(con,data)
            self.connMap[conn_seq]['writeNotBack'] = self.connMap[conn_seq]['writeNotBack']+len(data)
            yield self.addTask(msg)
            
    @gen.coroutine
    def doRead(self,stream,conn_seq):    
        while True:
            if conn_seq not in self.connMap :
                self.checkStreamClose(conn_seq, stream)
                return 
            if self.connMap[conn_seq]['readBuffer'] ==b'' and self.connMap[conn_seq]['readError'] :
                self.checkStreamClose(conn_seq, stream)
                return
            if self.connMap[conn_seq]['readBuffer'] ==b'' :
                yield self.connMap[conn_seq]['rEvent'].wait()
                if conn_seq not in self.connMap :
                    self.checkStreamClose(conn_seq, stream)
                    return                  
                self.connMap[conn_seq]['rEvent'].clear()
                continue
                       
            s = self.connMap[conn_seq]['readBuffer']
            self.connMap[conn_seq]['readBuffer'] = b''
            
            try:             
                yield stream.write(s)                
                con = {'type':'writeBack','conn_seq':conn_seq,'length':len(s)}
                msg = TOUMsg(con,b'')
                yield self.addTask(msg)

            except StreamClosedError:
                pack = {'type':'writeError','conn_seq':conn_seq}
                msg = TOUMsg(pack,b'')
                yield self.addTask(msg)   
                if conn_seq not in self.connMap:
                    self.checkStreamClose(conn_seq, stream)
                    return                
                self.connMap[conn_seq]['readError'] = True
                self.checkDelConn(conn_seq)
                self.checkStreamClose(conn_seq, stream)
                return                
            except :
                raise Exception

    @gen.coroutine
    def stream_to_map(self):
        while True:
            yield self.rEvent.wait()
            self.rEvent.clear()
            while True:       
                while self.outputSize > tcpManagerCacheSize:
                    yield self.outputSizeDownEvent.wait()
                    self.outputSizeDownEvent.clear()                    
                msg = TOUMsg()
                self.readLock.acquire()
                r,self.readBuffer = msg.unpack(self.readBuffer)
                self.readLock.release()
                if not r:
                    break
                
                json = msg.m_json
                if 'conn_seq' not in json:
                    if not self.isServer and json['id'] in self.waitIdMap:
                        self.outputMap_byId[json['id']] = {'msg':msg,'createTime':getRunningTime()}
                        self.waitIdMap[json['id']]['event'].set()                                              
                    elif self.isServer:
                        self.outputMap_byId[json['id']] = {'msg':msg,'createTime':getRunningTime()}
                        self.waitIdEvent.set()   
                    continue
    
                ty = json['type']
                conn_seq = json['conn_seq']
                if conn_seq not in self.connMap:
                    if not self.isServer:
                        continue
                    if conn_seq not in self.writeBeforeConnMap:
                        m = {'createTime':getRunningTime(),'buffer':b''}
                        self.writeBeforeConnMap[conn_seq] = m                    
                    self.writeBeforeConnMap[conn_seq]['buffer'] = self.writeBeforeConnMap[conn_seq]['buffer']+msg.strContetn
                    continue
                e = self.connMap[conn_seq]['rEvent']
                e.set()
                if ty == 'write':
                    self.connMap[conn_seq]['readBuffer'] = self.connMap[conn_seq]['readBuffer']+msg.strContetn
                elif ty == 'readError':
                    self.connMap[conn_seq]['readError'] = True
                elif ty == 'writeBack':
                    self.connMap[conn_seq]['writeNotBack'] = self.connMap[conn_seq]['writeNotBack'] -json['length']
                elif ty == 'writeError':
                    self.connMap[conn_seq]['writeError'] = True 
                self.checkDelConn(conn_seq)
            
          

