import hashlib, binascii,time,uuid,json
import struct,random,string
import time
import json,uuid

con_listenIp = '0.0.0.0'
recLen = 10240
bufferSize = 59000
con_streamBufferSize = 10*1024*1024
eachConnWriteLimit = 1024*1024
tcpManagerCacheSize = 500*1024*1024
connCheckTime = 1
packetsStatisTime=1
maxSendConfig=[{'small':0,'big':0.05,'slope':1,'maxSend':3},
               {'small':0.05,'big':0.1,'slope':1.5,'maxSend':3},
               {'small':0.1,'big':0.4,'slope':2,'maxSend':4},
               {'small':0.4,'big':0.6,'slope':3,'maxSend':5},
               {'small':0.6,'big':0.8,'slope':4,'maxSend':8},
               {'small':0.8,'big':1,'slope':5,'maxSend':10},]

def getRunningTime():
    return time.monotonic()

def getPackStaBigV(m):
    mv = 0
    for k,v in m.items():
        if getRunningTime()-v['time']<packetsStatisTime and v['v']>mv:
            mv = v['v']
    return mv

def clearPackSta(m):
    k = list(m.keys())
    for i in k:
        if m[i]['time']<getRunningTime()-packetsStatisTime:
            del m[i]
            
def addPackSta(m,v,ti=0):
    if ti==0 or ti==float('inf'):
        ti = getRunningTime()
    m[str(uuid.uuid1())] = {'time':ti,'v':v}
    
def createCommandFile():
    f = open('commandIn.txt','w')
    f.close()
    f = open('commandOut.txt','w')
    f.close()    
    
def createLog():
    f = open('mylog.txt','w')
    f.close()
    
    
def writeLog(con):
    t1 = getRunningTime()
    f = open('mylog.txt')
    s = f.read()
    f.close()
    if s=='':
        s = json.dumps({})
    try:
        m = json.loads(s)
    except:
        print("use time",getRunningTime()-t1,getRunningTime())
        return
    for k in list(m.keys()):
        v = m[k]['createTime']
        if v<getRunningTime()-10 and len(m)>10:
            del m[k]
    if type(con)==type([]):
        for one in con:
            m[str(uuid.uuid1())]={'createTime':getRunningTime(),'con':one}
    else:
        m[str(uuid.uuid1())]={'createTime':getRunningTime(),'con':con}
    j = json.dumps(m)
    f = open('mylog.txt','w')
    f.write(j)
    f.close()
    print("use time",getRunningTime()-t1,getRunningTime())
    
def readLog():
    f = open('mylog.txt')
    s = f.read()
    f.close()   
    try:
        m = json.loads(s)
    except:
        return {}
    mm = {}
    for k,v in m.items():
        mm[k]=v['con']
    return mm

class structWrapper():
    def __init__(self,s=b''):
        self.data = s
        self.pos = 0
    def writeByte(self,b):
        self.data += struct.pack('b',b)
        self.pos += 1
    def writeWord(self,b):
        self.data += struct.pack('H',b)
        self.pos += 2    
    def writeDouble(self,b):
        self.data += struct.pack('d',b)
        self.pos += 8
    def readByte(self):
        r = struct.unpack('b',self.data[self.pos:self.pos+1])[0]
        self.pos += 1
        return r
    def readWord(self):
        r = struct.unpack('H',self.data[self.pos:self.pos+2])[0]
        self.pos += 2
        return r
    def readDouble(self):
        r = struct.unpack('d',self.data[self.pos:self.pos+8])[0]
        self.pos += 8
        return r    
    def getLeftData(self):
        return self.data[self.pos:]
    
def randomStringDigits(stringLength=6):
    lettersAndDigits = string.ascii_letters + string.digits
    return ''.join(random.choice(lettersAndDigits) for i in range(stringLength))


class TOUMsg():
    def __init__(self,m = {},s=b''):
        self.m_json = m
        self.strContetn = s
        self.length = 0
        
    def pack(self):
        j = json.dumps(self.m_json)
        j = bytes(j,encoding='utf8')
        jL = len(j)
        cL = len(self.strContetn)
        self.length = 16+jL+cL      
        return struct.pack('q',jL)+j+struct.pack('q',cL)+self.strContetn
    
    def unpack(self,s):
        if len(s)<16:
            return False,s
        jL = struct.unpack('q',s[:8])[0]
        if len(s)<16+jL:
            return False,s
        cL = struct.unpack('q',s[8+jL:16+jL])[0]
        if len(s)<16+jL+cL:
            return False,s
        st = str(s[8:8+jL],encoding='utf8')
        self.m_json = json.loads(st)
        self.strContetn = s[16+jL:16+jL+cL]
        self.length = 16+jL+cL
        return True,s[16+jL+cL:]
    
def makePack(s,salt):
    u = str(uuid.uuid1())
    u = u.replace('-','')
    u2 = binascii.unhexlify(u)
    s1 = u2+s
    dk = hashlib.pbkdf2_hmac('md5', s1, salt, 2)
    s2 = s1+dk
    return u,s2

def checkPackValid(s,u,salt):
    if len(s)<16:
        return b''
    s1 = s[-16:]
    s2 = s[:-16]
    uuid = binascii.unhexlify(u)
    dk = hashlib.pbkdf2_hmac('md5', s2, salt, 2)
    if dk != s1:
        return b''
    if s2[:16] != uuid:
        return b''
    return s2[16:]

def checkPackValid2(s,salt):
    if len(s)<16:
        return '',b''
    s1 = s[-16:]
    s2 = s[:-16]
    dk = hashlib.pbkdf2_hmac('md5', s2, salt, 2)
    if dk != s1:
        return '',b''
    u = s2[:16]
    con = s2[16:]
    return str(binascii.hexlify(u),encoding='utf8'),con

def circleBig(a,b,bs=bufferSize):
    if a==b:
        return a
    if a>b and (a-b)<(bs/2):
        return a
    if a<b and (b-a)>(bs/2):
        return a
    return b

def circleRange(a,b,bs=bufferSize):  # return [,)  same as range
    temp = a
    ret = []
    while True:
        if temp== circleBig(b,temp,bs):
            break
        ret.append(temp)
        temp = circleAdd(temp,1,bs)
    return ret

def circleMax(l,bs=bufferSize):
    ret = None
    k = l.keys()
    for i in k:
        if ret==None:
            ret = i
        ret = circleBig(i,ret,bs)
    return ret

def circleAddOne(a,bs=bufferSize):
    if a == bs-1:
        return 0
    return a+1

def circleAdd(a,b,bs=bufferSize):
    ret = a
    for i in range(b):
        ret = circleAddOne(ret,bs)
    return ret


if __name__ == '__main__':
    u,s = makePack(b'sdfew',b'salt')
    print (u,s)
    s2 = checkPackValid(s, u, b'salt')
    print (s2)

          