from tornado.ioloop import IOLoop
from helpFunc import *
import socket,select
from streamBase import streamBase

class UStreamServer(streamBase):
    def __init__(self,upper,listenPort,salt,rate,pushAhead,packLimit):
        streamBase.__init__(self,upper,rate,pushAhead,packLimit,True)
        self.sockMap = {}
        self.ip = con_listenIp
        for i in listenPort:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((self.ip,i))
            self.sockMap[sock] = {}
        self.salt = salt
        
    def deal_rec(self,l):
        re = []
        reSocks = []
        for one in l:
            data, addr = one.recvfrom(recLen)
            uuid ,ss = checkPackValid_server(data,self.salt)
            if not uuid :
                continue
            addPackSta(self.maxRec,len(data))
            self.sockMap[one]['uuid'] = uuid
            self.sockMap[one]['addr'] = addr
            re.append(ss)
            reSocks.append(one)
        return re,reSocks
         
    def  sendData(self,re,l):
        co = -1
        for sock in l:
            co += 1
            data = makePack_server(re[co], self.sockMap[sock]['uuid'], self.salt)
            sock.sendto(data,self.sockMap[sock]['addr'])    
            addPackSta(self.maxSendL,len(data))         
            
    def doWork(self):
        while True:
            if getRunningTime()-self.updatedTime>con_closeTime:
                import os
                os._exit(0)         
            r = select.select(self.sockMap.keys(),[],[],1)
            if r[0]==[]:
                continue
            re,reSocks = self.deal_rec(r[0])
            self.deal_data_back(re)     
            self.read()
            self.write()
            re = self.get_data_to_send(len(reSocks)) 
            self.sendData(re,reSocks) 
            if getRunningTime()-self.staTime>1:
                self.staTime = getRunningTime()  
                self.rRaw = self.wRaw = self.rNet = self.wNet = 0
                self.totalRec = self.blankRec = self.totalSend = self.blankSend = self.statusSend = self.statusRev = 0    
                clearPackSta(self.maxSendL)          
                clearPackSta(self.maxRec)          
                clearPackSta(self.peerMaxRec)          
                clearPackSta(self.peerMaxSend)            
                print (len(self.maxSendL),len(self.maxRec),len(self.peerMaxSend),len(self.peerMaxRec))
                
if __name__ == "__main__":
    import threading
    from testStream import ts
    import logging
    logging.basicConfig(filename='runlog.txt',filemode='w',level=logging.DEBUG)
    ioloop = IOLoop.current()
    upper = ts(ioloop)
    serverIp = con_serverIp
    listenPort = list(range(10000,10000+maxPortNum))
    rate = con_minRate
    pushAhead = con_pushAhead
    packLimit = con_packLimit
    salt = b'salt'
    u = UStreamServer(upper,listenPort,salt,rate,pushAhead,packLimit)
    t = threading.Thread(target=u.doWork)
    t.setDaemon(True)
    IOLoop.current().add_callback(t.start)
    IOLoop.current().start()