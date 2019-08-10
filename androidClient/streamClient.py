from tornado.ioloop import IOLoop
import time
from helpFunc import *
from streamBase import streamBase
import socket,select
from datetime import datetime
import os
from collections import deque
import functools

class UStreamClient(streamBase):
    def __init__(self,upper,listenPort,salt,rate,pushAhead,packLimit,iniTout,serverIp,\
                 MPort,LPort,IDose,DDose,LGot,MRate,LRate,span,limit,speed,dose2,closeTime,ONum):
        streamBase.__init__(self,upper,rate,pushAhead,packLimit,False)
        self.sockMap = {}
        self.availPort = {} #must create new sockets
        self.availPort2 = {} #use sockets before
        self.cachePort = deque()
        self.LPort = LPort
        for i in listenPort:
            if len(self.availPort)>=LPort:
                self.cachePort.append(i)
                continue
            self.availPort[i] = 0
        self.salt = salt
        self.ip = serverIp
        self.statisGot = 0
        self.statisOut = 0
        self.reusedPort = {}
        self.span = span
        self.newPortLimit = limit*span
        self.newPortThisPeriod = 0
        self.newPortThisSecond = 0
        self.maxRecTime = 0
        self.maxRecTimeQ = deque()
        for i in range(20):
            self.maxRecTimeQ.append(0)        
        self.minRecTime = float('inf')
        self.newPortMap = {}
        self.iniTout = iniTout
        self.timeoutTime = iniTout
        self.decreaseDose = 0
        self.MPort = MPort
        self.DDose = DDose
        self.IDose = IDose
        self.LGot = LGot
        self.LRate  = LRate
        self.MRate  = MRate
        self.speed = speed
        self.dose2 = dose2
        self.ONum = ONum
        self.closeTime = closeTime
        self.startTime = getRunningTime()
        self.tooMuchPorts1 = False
        self.tooMuchPorts2 = False
        
    def calPara(self):
        if self.statisGot!=0:
            self.waitingTime = self.maxRecTime-self.minRecTime
            
        if self.rRaw>self.speed *1024:
            if  self.statisOut>self.ONum:
                dose = -self.dose2
            else:
                dose = 0
        else:
            dose = self.IDose

        if self.statisGot<self.LGot:
            self.sendStatusRate = self.MRate-(self.MRate-self.LRate)*(float(self.statisGot)/self.LGot)
        else:
            self.sendStatusRate = self.LRate
        if self.statisGot==0:
            self.timeoutTime = self.iniTout
        else:
            self.timeoutTime = max(self.maxRecTimeQ)+0.1
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
            if t-k>=self.span:
                del self.newPortMap[k]
        if not self.newPortMap:
            self.newPortThisPeriod = 0
        else:
            self.newPortThisPeriod = sum(self.newPortMap.values())
    
    def refreshNewPortTime(self):
        t = getRunningTime()
        if not self.newPortMap or sum(self.newPortMap.values())<self.newPortLimit:
            return t
        su = sum(self.newPortMap.values())                
        l = sorted(self.newPortMap.keys())
        for i in l:
            su-=self.newPortMap[i]
            if su<self.newPortLimit:
                return i+self.span
            
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
        if self.tooMuchPorts1 and not self.tooMuchPorts2:
            self.decreaseDose = self.DDose
            return
        if self.blankRec!=0 and self.blankSend!=0 and self.statisGot>self.LGot:        
            self.decreaseDose = self.DDose
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
            if getRunningTime()-self.updatedTime>self.closeTime:
                msg = 'work process closed'
                self.upper.ioloop.add_callback(functools.partial(self.upper.addLogCB,msg))
                self.upper.ioloop.add_callback(self.upper.quit) 
                return
     
            t = getRunningTime()
            if len(self.availPort)!=0:
                t1 = self.refreshNewPortTime()
                self.tooMuchPorts1 = True
            else:
                t1 = float('inf')
                self.tooMuchPorts2 = True
            t2 = self.refreshNextTimeout()
            mTime = min(t1,t2)
            if mTime==float('inf'):
                wt = 1
            elif t>mTime :
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
            if getRunningTime()-self.staTime>1:
                self.staTime = getRunningTime()  
                bl = self.getLog()
                t = int(getRunningTime()*1000)/1000.0
                s1 =  '%-4s [port,g,o]  %s  %s  %s  [lag,max,min]  %2.3f  %2.3f  %2.3f  [newPort]  %s'%\
                    (t,self.MPort-len(self.cachePort),self.statisGot,self.statisOut,self.statusGapTime,\
                     self.maxRecTime,self.minRecTime,self.newPortThisSecond)
                s2 = '%s %s\n'%(t,bl)
                if self.blankRec==0 or self.blankSend==0:
                    sy = '+'
                else:
                    sy = '-'
                msg = '%-4s %-5s %-4s %2.2f %5s  sr  %-4s %-4s %-4s %-4s %s\n'%\
                    (self.MPort-len(self.cachePort),self.statisGot,self.statisOut,self.statusGapTime,\
                     int(self.rRaw/1024),getPackStaBigV(self.maxSendL),getPackStaBigV(self.peerMaxRec),\
                     getPackStaBigV(self.peerMaxSend),getPackStaBigV(self.maxRec),sy)
                self.upper.ioloop.add_callback(functools.partial(self.upper.addLogCB,msg))
                self.maxRecTimeQ.append(self.maxRecTime)
                self.maxRecTimeQ.popleft()                
                dose = self.calPara()
                self.adjustPortNum(dose)                
                self.tooMuchPorts1 = False
                self.tooMuchPorts2 = False
                self.statisGot = self.statisOut = self.maxRecTime = 0
                self.minRecTime = float('inf')
                self.rRaw = self.wRaw = self.rNet = self.wNet = 0
                self.totalRec = self.blankRec = self.totalSend = self.blankSend = self.statusSend = self.statusRev = 0                 
                print (s1)
                print (s2)
                clearPackSta(self.maxSendL)          
                clearPackSta(self.maxRec)          
                clearPackSta(self.peerMaxRec)          
                clearPackSta(self.peerMaxSend)       
                
    def retireSock(self,n):
        if len(self.cachePort)>=self.MPort-self.LPort or self.decreaseDose==0:
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
                self.newPortThisSecond += 1
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
            
