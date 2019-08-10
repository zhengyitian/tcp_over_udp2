from tornado.ioloop import IOLoop
from tornado import gen
from tornado.tcpserver import TCPServer
import functools,time
from streamClient import UStreamClient
import uuid
from helpFunc import *
from connBase import connBase
import threading,logging
from tornado.locks import Event

class connClient(TCPServer,connBase):
    def __init__(self,serverPort,salt,rate,pushAhead,packLimit,listenIp,listenPort):
        TCPServer.__init__(self)
        ioloop = IOLoop.current()
        connBase.__init__(self,ioloop,False)     
        self.stream = u = UStreamClient(self,serverPort,salt,rate,pushAhead,packLimit)
        self.t = t = threading.Thread(target=u.doWork)
        t.setDaemon(True)
        IOLoop.current().add_callback(t.start)
        self.listen(listenPort,listenIp)
        self.connId = 0
        self.startTime = getRunningTime()
        
    @gen.coroutine
    def handle_stream(self, stream, address):
        id = str(uuid.uuid1())
        conn_id = str(self.connId)
        self.connId += 1
        self.addConnMap(conn_id)   
        IOLoop.instance().add_callback(functools.partial(self.doRead,stream,conn_id))
        IOLoop.instance().add_callback(functools.partial(self.doWrite,stream,conn_id))        
        pack = {'type':'conn','id':id,'conn_id':conn_id}        
        msg = TOUMsg(pack, b'')
        e = Event()
        self.waitIdMap[id] = {'event':e}        
        yield self.addTask(msg)
        
        self.writeLock.acquire()
        wbl = int(len(self.writeBuffer)/1024)
        self.writeLock.release()
        s = 'conn add  %s, conn:%s,in:%s,out:%s,oById:%s,addTask:%s,waitId:%s,checkConn:%s'%\
            (conn_id,len(self.connMap),int(self.outputSize/1024),wbl,len(self.outputMap_byId),\
            len(self.addTaskMap),len(self.waitIdMap),len(self.streamCloseSign))
        t = int((getRunningTime()-self.startTime)*1000)/1000.0
        msg = '%s  %s\n' %( t,s)
        print (msg)
        logging.debug(msg)
      
        yield e.wait()
        msg = self.outputMap_byId[id]['msg']
        del self.outputMap_byId[id]
        del self.waitIdMap[id]

        back = msg.m_json
        t = int((getRunningTime()-self.startTime)*1000)/1000.0
        s = '%s  conn reply %s, conn:%s ,ret:%s\n'%(t,back['conn_id'],len(self.connMap),back['ret'])
        print (s)
        logging.debug(s)
        
        if back['ret'] == 0:
            del self.connMap[back['conn_id']]  
       
if __name__ == "__main__":
    serverListenPort = range(10000,10000+maxPortNum)
    rate = con_minRate
    pushAhead = con_pushAhead
    packLimit = con_packLimit
    salt = b'salt'
    clientListenIp = '0.0.0.0'
    clientListenPort = 9999
    t = connClient(serverListenPort,salt,rate,pushAhead,packLimit,clientListenIp,clientListenPort)
    IOLoop.instance().start()
    
