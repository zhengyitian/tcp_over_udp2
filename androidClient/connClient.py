from tornado.ioloop import IOLoop
from tornado import gen
from tornado.tcpserver import TCPServer
import functools,time
from streamClient import UStreamClient
import uuid
from helpFunc import *
from connBase import connBase
import threading
from tornado.ioloop import PeriodicCallback
from tornado.locks import Event

class connClient(TCPServer,connBase):
    def __init__(self,serverPort,salt,rate,pushAhead,packLimit,listenIp,listenPort,timeoutTime,serverIp,\
                 MPort,LPort,IDose,DDose,LGot,MRate,LRate,span,limit,speed,dose2,closeTime,ONum,commandId):
        TCPServer.__init__(self)
        ioloop = IOLoop.current()
        connBase.__init__(self,ioloop,False)     
        self.stream = u = UStreamClient(self,serverPort,salt,rate,pushAhead,packLimit,timeoutTime,serverIp,\
                                        MPort,LPort,IDose,DDose,LGot,MRate,LRate,span,limit,speed,dose2,closeTime,ONum)
        self.t = t = threading.Thread(target=u.doWork)
        t.setDaemon(True)
        IOLoop.current().add_callback(t.start)
        self.listen(listenPort,listenIp)
        self.connId = 0
        self.startTime = getRunningTime()
        self.commandId = commandId
        PeriodicCallback(self.readCommand,200).start()
        PeriodicCallback(self.writeCommand,200).start()
        self.exit = False
        
    def readCommand(self):
        if self.outputSize >= tcpManagerCacheSize:
            writeLog('too much cache,process exits!!\n')
            self.quit()
            return
        
        f = open('commandIn.txt')
        s = f.read()
        f.close()
        try:
            m = json.loads(s)
        except:
            return
        if m.get('commandId','')!=self.commandId:
            return

        if m.get('toStop',False):            
            self.quit()
            return

    def quit(self):
        self.exit = True
        self.writeCommand()        
        import os
        os._exit(0)   

    def writeCommand(self):
        f = open('commandOut.txt','w')
        m = {'exit':self.exit,'commandId':self.commandId,'aliveTime':time.monotonic()}
        j = json.dumps(m)
        f.write(j)
        f.close()             
        

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
        wbl = len(self.writeBuffer)/1024
        self.writeLock.release()
        s = 'conn add  %s, conn:%s,in:%s,out:%s,oById:%s,addTask:%s,waitId:%s'%\
            (conn_id,len(self.connMap),self.outputSize/1024,wbl,len(self.outputMap_byId),\
            len(self.addTaskMap),len(self.waitIdMap))
        t = int(getRunningTime()*1000)/1000.0
        msg = '%s  %s\n' %( t,s)
        print (msg)
        t = int((getRunningTime()-self.startTime)*100)/100.0
        ss = '#######  %ss  ##  conn sent  %s  %s\n'%(t,conn_id,len(self.connMap))
        writeLog(ss)        
        
        yield e.wait()
        msg = self.outputMap_byId[id]['msg']
        del self.outputMap_byId[id]
        del self.waitIdMap[id]

        back = msg.m_json
        t = int(getRunningTime()*1000)/1000.0
        s = '%s  conn reply %s, conn:%s ,ret:%s\n'%(t,back['conn_id'],len(self.connMap),back['ret'])
        print (s)

        t = int((getRunningTime()-self.startTime)*100)/100.0
        ss = '#######  %ss  ##  conn back  %s  %s\n'%(t,back['conn_id'],len(self.connMap))
        writeLog(ss)
        if back['ret'] == 0:
            del self.connMap[back['conn_id']]                  
              