from helpFunc import *
from streamServer import UStreamServer
from tornado.ioloop import IOLoop
from tornado import gen
from tornado.tcpclient import TCPClient
import functools
import json,threading
from connBase import connBase

class connServer(connBase):
    def __init__(self,listenPort,salt,rate,pushAhead,packLimit,connIp,connPort):
        ioloop = IOLoop.current()
        connBase.__init__(self,ioloop,True)     
        self.stream = u = UStreamServer(self,listenPort,salt,rate,pushAhead,packLimit)
        self.t = t = threading.Thread(target=u.doWork)
        t.setDaemon(True)
        IOLoop.current().add_callback(t.start)
        IOLoop.current().add_callback(self.checkConn)          
        self.ip = connIp
        self.port = connPort
        
    @gen.coroutine
    def checkConn(self):
        while True:
            yield self.waitIdEvent.wait()
            self.waitIdEvent.clear()
            for k in list(self.outputMap_byId.keys()):
                con = self.outputMap_byId[k]
                msg = con['msg']
                v = msg.m_json
                if v['type'] == 'conn':            
                    del self.outputMap_byId[k]                    
                    IOLoop.current().add_callback(functools.partial(self.acceptConn,k,msg))
                    
    @gen.coroutine
    def acceptConn(self,k,msg):
        v = msg.m_json
        try:
            stream = yield TCPClient().connect(self.ip, self.port)    
        except:
            if v['conn_id'] in self.writeBeforeConnMap:
                del self.writeBeforeConnMap[v['conn_id']]            
            m = {'ret':0,'id':k,'conn_id':v['conn_id']}
            msg2 = TOUMsg(m)
            yield self.addTask(msg2)
            return 
        
        print ('accept,connMap length:',len(self.connMap) ,'cache writeBeforeConnMap:',len(self.writeBeforeConnMap) )              
        conn_seq_back = v['conn_id']
        m = {'ret':1,'id':k,'conn_id':conn_seq_back}
        msg2 = TOUMsg(m)
        yield self.addTask(msg2)
        self.addConnMap(conn_seq_back)
        if conn_seq_back in self.writeBeforeConnMap:
            self.connMap[conn_seq_back]['readBuffer'] = self.writeBeforeConnMap[conn_seq_back]['buffer']
            del self.writeBeforeConnMap[conn_seq_back]        
        IOLoop.instance().add_callback(functools.partial(self.doRead,stream,conn_seq_back))
        IOLoop.instance().add_callback(functools.partial(self.doWrite,stream,conn_seq_back))                
                
if __name__ == "__main__":
    import sys
    ar = sys.argv
    lp = list(range(10000,10000+maxPortNum))
    rate = con_minRate
    pushAhead = con_pushAhead
    packLimit = con_packLimit
    salt = b'salt'
    if len(ar)>1:
        s = ar[1].encode()
        import base64,json
        j = base64.b64decode(s)
        m = json.loads(j.decode())
        lp = m['lp']
        rate = m['rate']
        pushAhead = m['pushAhead']
        packLimit = m['packLimit']
        salt = m['salt'].encode()

    t = connServer(lp,salt,rate,pushAhead,packLimit,'127.0.0.1',8080)  
    IOLoop.instance().start()
    
