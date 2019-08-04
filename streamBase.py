from helpFunc import *
import struct,uuid

class streamBase():
    def __init__(self,upper,rate,pushAhead,packLimit,isServer):
        self.upper = upper
        self.staTime = 0
        self.sendPackMap = {}
        self.recPackMap = {}
        self.sendSelfPos = 0
        self.sendPeerPos = 0
        self.recPos = 0
        self.sendStatusRate = rate
        self.notRecInfo = {}
        self.peerNotRecInfo = {}        
        self.sockMap = {}
        self.statusGapTime = float('inf')
        self.pushAhead = pushAhead
        l = circleRange(0,self.pushAhead)
        for i in l:
            self.notRecInfo[i]=0
        self.newPeerTime = -float('inf')
        self.peerMyTime = -float('inf')
        self.hasStart = False
        self.maxSend = 1
        self.slope = 1
        self.packLimit = packLimit
        self.updatedTime = getRunningTime()
        self.calStaNum = 0
        self.waitingTime = 0
        self.rRaw = self.wRaw = self.rNet = self.wNet = 0
        self.totalRec = self.blankRec = self.totalSend = self.blankSend = self.statusSend = self.statusRev = 0 
        self.isServer = isServer
        self.maxSendL = {}
        self.maxRec = {}
        self.peerMaxSend = {}
        self.peerMaxRec = {}
          
    def getLog(self):
        s = '[rate,slope,max]  %2.2f  %s  %s  [raw,net](r/w)  %s  %s  %s  %s  [to,sta,null](r/w)  %s  %s  %s  %s  %s  %s'%\
            (self.sendStatusRate,self.slope,self.maxSend,int(self.rRaw/1024),int(self.wRaw/1024),int(self.rNet/1024),int(self.wNet/1024),\
             self.totalRec,self.statusRev,self.blankRec,self.totalSend,self.statusSend,self.blankSend)
        return s
        
    def dealStatusBack(self,re):
        self.updatedTime = getRunningTime()
        s = structWrapper(re)
        s.readByte()
        peerTime = s.readDouble()
        if  peerTime<self.newPeerTime:
            return
        
        self.newPeerTime =peerTime
        peerMyTime = s.readDouble()
        self.peerMyTime = peerMyTime
        if self.isServer:
            self.sendStatusRate = s.readDouble()
            self.slope = s.readDouble()
            self.maxSend = s.readDouble()     
            self.waitingTime = s.readDouble()    
        else:
            s.readDouble()   
            s.readDouble()   
            s.readDouble()   
            s.readDouble()   
        pms = s.readWord()
        pmr = s.readWord()            
        addPackSta(self.peerMaxSend,pms,peerMyTime+self.statusGapTime/2)
        addPackSta(self.peerMaxRec,pmr,peerMyTime+self.statusGapTime/2)         
        peerPos = s.readWord()
        self.peerNotRecInfo = {}        
        self.sendPeerPos = peerPos   
        st = s.getLeftData()
        ss = ''
        for i in range(len(st)):
            j = struct.unpack('B',st[i:i+1])[0]
            s = format(j,'b')
            ss += (8-len(s))*'0'+s
        co = 0

        l = circleRange(peerPos,circleAdd(peerPos,self.pushAhead))
        for one in l:
            if ss[co]=='1':
                self.peerNotRecInfo[one]=0
            co += 1
            
    def dealPushBack(self,re):
        s = structWrapper(re)
        s.readByte()      
        num =  s.readWord()
        if num in self.notRecInfo:
            del self.notRecInfo[num]
            self.recPackMap[num] = s.getLeftData()

    def deal_data_back(self,l):
        for re in l:
            ty = struct.unpack('b',re[0:1] )[0]
            self.totalRec += 1
            if ty == 0:                
                self.dealStatusBack(re)
                self.statusRev += 1
            elif ty==1:
                self.dealPushBack(re)
            else:
                self.blankRec += 1
        if self.peerMyTime!=float('-inf'):
            self.statusGapTime = getRunningTime()-self.peerMyTime
            if not self.hasStart :
                print ('got conn')
                self.hasStart = True

    def rCallback(self):
        self.upper.rEvent.set()
        
    def wCallback(self):
        self.upper.wEvent.set() 
    
    def read(self):
        if not self.hasStart:
            return          
        if self.recPos not in self.recPackMap:
            return                 
        l = circleRange(self.recPos,circleAdd(self.recPos,self.pushAhead))
        s = []
        self.upper.readLock.acquire()
        bufferL = len(self.upper.readBuffer)
        
        for one in l:
            if one not in self.recPackMap:
                break
            if bufferL>con_streamBufferSize:
                break
            s .append( self.recPackMap[one])
            bufferL += len(self.recPackMap[one])
            del self.recPackMap[one]
            self.recPos = circleAddOne(one)
            self.notRecInfo[circleAdd(one,self.pushAhead)] = 0
                     
        if  s or self.upper.readBuffer:
            ss = b''.join(s) 
            self.rNet += len(ss)
            self.upper.readBuffer += ss            
            self.upper.ioloop.add_callback(self.rCallback) 
        self.upper.readLock.release()          
            
    def write(self):
        if not self.hasStart:
            return  
        
        self.upper.writeLock.acquire()        
        lB = len(self.upper.writeBuffer)
        newPos = 0        
        while True:
            if lB == 0:
                break
            if circleBig(circleAdd(self.sendPeerPos,self.pushAhead),self.sendSelfPos) == self.sendSelfPos:    
                break             
            s1 = self.upper.writeBuffer[newPos:newPos+self.packLimit]

            newPos += self.packLimit
            self.sendPackMap[self.sendSelfPos] = {'sendRecording':{},'con':s1}
            self.wNet += len(s1)
            self.sendSelfPos = circleAddOne(self.sendSelfPos)
            if  newPos>=lB:
                break
            
        self.upper.writeBuffer = self.upper.writeBuffer[newPos:]
        if not  self.upper.writeBuffer:
            self.upper.ioloop.add_callback(self.wCallback)                         
        self.upper.writeLock.release()                          
            
    def get_data_to_send(self,n):
        self.totalSend += n
        self.clearRecording()
        if not self.hasStart:
            statusNum = n
        else:
            self.calStaNum += n
            statusNum = int(self.calStaNum*self.sendStatusRate)
            if statusNum>n:
                statusNum=n
            self.calStaNum-=statusNum/self.sendStatusRate
        st = self.getOneStatus()
        l = self.findNPack(n-statusNum)
        self.statusSend += statusNum
        ret = []
        for i in range(statusNum):
            ret.append(st)
        ret = ret+l
        for i in range(n-statusNum-len(l)):
            re = struct.pack('b',2)
            ret.append(re)
            self.blankSend += 1
        return ret

    def getOneStatus(self):
        re = struct.pack('b',0)
        re += struct.pack('d',getRunningTime())
        re += struct.pack('d',self.newPeerTime)
        re += struct.pack('d',self.sendStatusRate)
        re += struct.pack('d',self.slope)
        re += struct.pack('d',self.maxSend)
        re += struct.pack('d',self.waitingTime)    
        re += struct.pack('H',getPackStaBigV(self.maxSendL))   
        re += struct.pack('H',getPackStaBigV(self.maxRec))                 
        re += struct.pack('H',self.recPos)     
        co = 0
        ss = ''              
        l = circleRange(self.recPos,circleAdd(self.recPos,self.pushAhead))
        for i in l:
            if i not in self.notRecInfo:
                ss+='0'
            else:
                ss+='1'
            co += 1
            if co==8:
                re += struct.pack('B',int(ss,2))  
                co = 0
                ss = ''       
        ss += (8-len(ss))*'0'
        re += struct.pack('B',int(ss,2))  
        return re
           
    def clearRecording(self):
        for i in circleRange(self.sendPeerPos,self.sendSelfPos):
            if i not in self.peerNotRecInfo:
                continue
            m = self.sendPackMap[i]['sendRecording']
            for k in list(m.keys()):
                v = m[k]
                if v<getRunningTime()-self.statusGapTime-self.waitingTime:
                    del self.sendPackMap[i]['sendRecording'][k]
                
    def findNPack(self,n):
        if n==0:
            return []
        m = {}
        co = 0
        for i in circleRange(self.sendPeerPos,self.sendSelfPos):
            if i not in self.peerNotRecInfo:
                continue
            m[co] = {'originNum':i,'times':len(self.sendPackMap[i]['sendRecording']),'realTimes':len(self.sendPackMap[i]['sendRecording'])}
            co += 1
        l = len(m)
        if l==0:
            return []        
        perGap = self.slope/float(l)
        for k in m.keys():
            m[k]['times'] = m[k]['times']+k*perGap
        def findMinTimes():
            mi = float('inf')
            k = -1
            for i,j in m.items():
                if j['times']<mi and j['realTimes']<self.maxSend:
                    mi = j['times']
                    k = i
            return k      
        ret = []
        while True:
            k = findMinTimes()
            if k == -1:          
                return ret            
            m[k]['times'] =  m[k]['times']+1
            m[k]['realTimes'] =  m[k]['realTimes']+1
            u = str(uuid.uuid1())
            ori = m[k]['originNum']
            self.sendPackMap[ori]['sendRecording'][u] = getRunningTime()
            re = struct.pack('b',1) + struct.pack('H',ori)+self.sendPackMap[ori]['con']
            ret.append(re)
            n -= 1
            if n == 0:            
                return ret
