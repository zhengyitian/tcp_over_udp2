from tornado.ioloop import IOLoop
import time
from helpFunc import *
from streamBase import streamBase
import socket,select
from datetime import datetime
import os,logging
from collections import deque
runningPath = os.path.split(os.path.realpath(__file__))[0]
logging.basicConfig(filename=runningPath+'/run.log',filemode='w',level=logging.DEBUG)

class UStreamClient(streamBase):
    def __init__(self,upper,listenPort,salt,rate,pushAhead,packLimit):
        streamBase.__init__(self,upper,rate,pushAhead,packLimit,False)
        self.sockMap = {}
        self.availPort = {} #must create new sockets
        self.availPort2 = {} #use sockets before
        self.cachePort = deque()
        for i in listenPort:
            if len(self.availPort)>=minPortNum:
                self.cachePort.append(i)
                continue
            self.availPort[i] = 0
        self.salt = salt
        self.ip = con_serverIp
        self.statisGot = 0
        self.statisOut = 0
        self.reusedPort = {}
        self.newPortLimit = perSecondPortsLimit*regulateTimeSpan
        self.newPortThisPeriod = 0
        self.maxRecTime = 0
        self.minRecTime = float('inf')
        self.nextTimeout = getRunningTime()
        self.newPortTime = getRunningTime()
        self.newPortMap = {}
        self.timeoutTime = timeoutTime
        self.decreaseDose = 0
        self.startTime = getRunningTime()
    def calPara(self):
        if self.statisGot!=0:
            self.waitingTime = self.maxRecTime-self.minRecTime
        lim,dose = getCustomPortsLimit(maxPortNum-len(self.cachePort),self.statisGot,self.statisOut,self.rRaw,self.wRaw)        
        self.newPortLimit = lim * regulateTimeSpan        
        if self.statisGot<minPackGot:
            self.sendStatusRate = con_maxRate-(con_maxRate-con_minRate)*(float(self.statisGot)/minPackGot)
        else:
            self.sendStatusRate = con_minRate
        if self.statisGot==0:
            self.timeoutTime = timeoutTime
        else:
            self.timeoutTime = self.maxRecTime+0.1
        lossRate = 1
        if self.statisGot+self.statisOut!=0:
            lossRate = float(self.statisOut)/(self.statisGot+self.statisOut)
        for m in maxSendConfig:
            if lossRate>=m['small'] and lossRate<=m['big']:
                self.slope = m['slope']
                self.maxSend = m['maxSend']
                break                    
        return dose
    def calNewPortThisPeriod(self):        
        t = getRunningTime()
        for k in list(self.newPortMap.keys()):
            if t-k>=regulateTimeSpan:
                del self.newPortMap[k]
        if not self.newPortMap:
            self.newPortThisPeriod = 0
        else:
            self.newPortThisPeriod = sum(self.newPortMap.values())
    
    def refreshNewPortTime(self):
        t = getRunningTime()
        if not self.newPortMap or sum(self.newPortMap.values())<self.newPortLimit:
            return float('inf')
        su = sum(self.newPortMap.values())                
        l = sorted(self.newPortMap.keys())
        for i in l:
            su-=self.newPortMap[i]
            if su<self.newPortLimit:
                return i
            
    def refreshNextTimeout(self):
        t = getRunningTime()
        if not self.sockMap:
            return float('inf')
        minT = t
        for k,v in self.sockMap.items():
            if v['createTime']<minT:
                minT = v['createTime']
        return minT+self.timeoutTime
    
    def adjustPortNum(self,dose):
        if self.newPortTime!=float('inf'):
            self.decreaseDose = con_portDecreaseDose
            return
        if self.blankRec!=0 and self.blankSend!=0 and self.statisGot>minPackGot:        
            self.decreaseDose = con_portDecreaseDose
            return   
        if dose<0:
            self.decreaseDose = abs(dose)
            return               
        for i in range(dose):
            if  self.cachePort :
                n = self.cachePort.popleft()
                self.availPort[n] = 0

    def doWork(self):        
        while True:    
            if getRunningTime()-self.updatedTime>con_closeTime:
                import os
                os._exit(0)       
            t = getRunningTime()
            mTime = min(self.nextTimeout,self.newPortTime)
            if t>mTime or mTime==float('inf'):
                wt = 0         
            else:
                wt = mTime-t       
            if not self.sockMap:
                time.sleep(wt)
            else:
                r = select.select(self.sockMap.keys(),[],[],wt)              
                re = self.deal_rec(r[0])
                self.deal_data_back(re)         
            self.read()              
            self.write()        
            self.deal_timeout() 
            self.calNewPortThisPeriod()
            l = len(self.availPort)         
            if l+self.newPortThisPeriod>self.newPortLimit:
                l = int(self.newPortLimit-self.newPortThisPeriod)
                if l<0:
                    l=0
            sendNum = l+len(self.availPort2)
            re = self.get_data_to_send(sendNum)                   
            self.sendData(re)
            self.newPortTime = self.refreshNewPortTime()
            self.nextTimeout = self.refreshNextTimeout()         
            if getRunningTime()-self.staTime>1:
                self.staTime = getRunningTime()  
                bl = self.getLog()
                t = int((getRunningTime()-self.startTime)*1000)/1000.0
                s1 =  '%s [port,g,o]  %s  %s  %s  [lag,max,min]  %2.3f  %2.3f  %2.3f  [newPort]  %s  [s,r]  %s  %s  %s  %s'%\
                    (t,maxPortNum-len(self.cachePort),self.statisGot,self.statisOut,self.statusGapTime,\
                     self.maxRecTime,self.minRecTime,int(self.newPortThisPeriod/regulateTimeSpan),\
                     getPackStaBigV(self.maxSendL),getPackStaBigV(self.peerMaxRec),getPackStaBigV(self.peerMaxSend),getPackStaBigV(self.maxRec))
                s2 = '%s %s\n'%(t,bl)
                
                dose = self.calPara()
                self.newPortTime = self.refreshNewPortTime()
                self.adjustPortNum(dose)                
                
                self.statisGot = self.statisOut = self.maxRecTime = 0
                self.minRecTime = float('inf')
                self.rRaw = self.wRaw = self.rNet = self.wNet = 0
                self.totalRec = self.blankRec = self.totalSend = self.blankSend = self.statusSend = self.statusRev = 0                 
                clearPackSta(self.maxSendL)          
                clearPackSta(self.maxRec)          
                clearPackSta(self.peerMaxRec)          
                clearPackSta(self.peerMaxSend)          
                print s1
                print s2
                logging.debug(s1)
                logging.debug(s2)
                
    def retireSock(self,n):
        if len(self.cachePort)>=maxPortNum-minPortNum or self.decreaseDose==0:
            return False
        self.decreaseDose -= 1
        self.cachePort.append(n)    
        return True
    
    def sendData(self,re):
        co = -1
        l = len(re)
        ft = float(getRunningTime())
        for k in list(self.availPort2.keys())+list(self.availPort.keys()):
            co += 1
            if co==l:
                return
            data = re[co]
            sock = None
            if k in self.reusedPort:
                sock = self.reusedPort[k]
                del self.reusedPort[k]
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
                if ft in self.newPortMap:
                    self.newPortMap[ft]+=1
                else:
                    self.newPortMap[ft]=1
                
            self.sockMap[sock] = {'num':k,'createTime':getRunningTime()}
            u ,s2 = makePack(data,self.salt)
            self.sockMap[sock]['uuid'] = u
            sock.sendto(s2, (self.ip, k))
            addPackSta(self.maxSendL,len(s2))   
            self.wRaw += len(s2)
            if k in self.availPort:
                del self.availPort[k]
            else:
                del self.availPort2[k]
               
    def  deal_timeout(self):
        for sock in list(self.sockMap.keys()):
            v = self.sockMap[sock]
            if v['createTime']+self.timeoutTime<getRunningTime():
                sock.close()
                n = self.sockMap[sock]['num']
                del self.sockMap[sock]
                if not self.retireSock(n):
                    self.availPort[n] = 0
                self.statisOut += 1
            
    def deal_rec(self,l):
        re = []
        for sock in l:
            j = sock.recv(recLen)
            self.rRaw += len(j)
            u,con = checkPackValid2(j,self.salt)    
            ub = self.sockMap[sock]['uuid']
            n = self.sockMap[sock]['num']
            ti = self.sockMap[sock]['createTime']
            if u != ub:
                sock.close()
                del self.sockMap[sock]
                self.availPort[n] = 0
                self.statisOut += 1
                continue          
            else:
                addPackSta(self.maxRec,len(j))
                recT = getRunningTime()-ti
                if recT>self.maxRecTime:
                    self.maxRecTime = recT
                if recT<self.minRecTime:
                    self.minRecTime = recT    
                if self.retireSock(n):
                    sock.close()
                else:
                    self.availPort2[n] = 0
                    self.reusedPort[n] = sock
                del self.sockMap[sock]
                self.statisGot += 1
                re.append(con)
        return re
            

if __name__ == "__main__":
    import threading
    from testStream import ts
    ioloop = IOLoop.current()
    upper = ts(ioloop)
    serverIp = con_serverIp
    listenPort = range(10000,10000+maxPortNum)
    rate = con_minRate
    pushAhead = con_pushAhead
    packLimit = con_packLimit
    salt = 'salt'
    u = UStreamClient(upper,listenPort,salt,rate,pushAhead,packLimit)
    t = threading.Thread(target=u.doWork)
    t.setDaemon(True)
    IOLoop.current().add_callback(t.start)
    IOLoop.current().start()

