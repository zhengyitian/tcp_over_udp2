import hashlib, binascii,time,uuid,json
import struct,random,string
import socket
from contextlib import closing
import platform,time,sys

#how to config this program

#---timeoutTime---:
#the longest possible travle time between the server and the client.
#big value will not be a problem.
#for example, if ping time is 0.05s, it can be 1.

#---con_serverIp---:
#server ip

#---minPackGot---:
#the program will try to get at least this many udp packets per second, no matter how much work there is.
#I set it to 100.

#---maxPortNum,minPortNum,con_portIncreaseDose,con_portDecreaseDose---:
#the most sockets number open at the same time is maxPortNum.
#windows limit is 508, linux is about 800
#the least sockets the program will use at any time is minPortNum.
#the program starts using this many sockets.
#I set minPortNum to the number to get minPackGot packets.
#for example, if ping time is 0.1s(actually,it is the time for a socket to send and receive a packet,
#it will be slightly bigger than ping time), average packet loss rate is 0.2, minPackGot is 100, this number is x,
#then x * (1/0.1)*(1-0.2)=100, x=13
#portNum increases/decreases at most con_portIncreaseDose/con_portDecreaseDose per second
#for a 260KB/s server,I set the four numbers to 100,13,2,2
#for a  1MB/s  server,I set the four numbers to 300,20,10,5

#---con_minRate,con_maxRate---
#some packets are status packets, some are data packets
#this configs the status rate. for example, you get 100 packets per second, and rate is 0.05,
#you get 5 status packets per second. the response time is 0.2s.
#the rate will change between the two parametres acrroding to how many packets you get.
#I set those to 0.05,0.5 

#---con_pushAhead---
#how many packets it buffers. the status packet size will be likely 100+this/8. I set it to 3000.

#---con_packLimit---
#data packet size. less than 1400

#---regulateTimeSpan,perSecondPortsLimit,getCustomPortsLimit---
#the most important one. when there is work to do, the program will increase packets sent until the packets lost number
#per second reaches perSecondPortsLimit. when there is no work, the program decreases packets sent until minPackGot or minPortNum.
#when reaching a limit,no matter how many sent, the speed will not change, and more will be lost, and the program will get slow, 
#because there are more sockets to deal with.
#to find out the limit number for perSecondPortsLimit , 
#you can start the program with different perSecondPortsLimit and push much work to it,
#like watching a 1080p video. Then see the program output on the client.
#the program logs to run.log in the same directory, and it prints the same information to the console.
#there is a '[raw,net](r/w)' part in the output. The four numbers following it means how many raw bytes got from server,
#how many raw bytes wrote to server, how many tcp flow got from server,how many tcp flow wrote to server, in KB/s.
#when the raw speeds don't increase when you increase perSecondPortsLimit, it is roughly the limit.
#when a packet is lost, a new socket will be created. in some situation, too many new sockets will make you and others in  
#your LAN unable to use ordinary http. if you don't want it to happen, set perSecondPortsLimit to the threshold.
#at my home, the threshold is like 20. in my company, this does not happen, and I set it to 50 when I use the server from yisu.com,
#and set it to 300 when using a Japan server from vultr.com.
#regulateTimeSpan is how long to calculate the new sockets created, it can be less than 1.
#the function 'getCustomPortsLimit' lets you decide how you want  perSecondPortsLimit and portNum to change, based on 
#how many sockets already exist,how many packets got and lost,raw read/write speed(both now and history data).
#it returns two values, the first is the new perSecondPortsLimit, the second is how many to change portNum, 
#it should be an integre(positive to increase, negative to decrease, 0 not to change). 
#you can let it return perSecondPortsLimit,con_portIncreaseDose if you don't need it.

#---maxSendConfig---
#the program will send a packet more than once at the same time, trying to decrease response time in case it gets lost.
#and it will try to send packets in the front of the buffer first and more. the 'slope' configs how much more.
#a packet will not be send more than 'maxSend' at the same time.
#these two should change according to the loss rate, 'big' and 'small' are the loss rate range.
#you can leave it as it is in the file

#---con_closeTime---
#the process(both server and client) will exit when no udp received in this long time(in seconds).
#I set it to 50

#---bufferSize---
#must be less than 60000 and more than 2*con_pushAhead. I set it to 59000

#---others---
#i never change other parameters, so i will not make notes on those.
#the program is not big, you can find the usage in the source code if you need.

#the parameters below must be the same on the server and on the client
con_listenIp = '0.0.0.0'
recLen = 10240
bufferSize = 59000
con_streamBufferSize = 10*1024*1024
eachConnWriteLimit = 1024*1024
tcpManagerCacheSize = 500*1024*1024
servicePort = 19023
serviceSaltKey = 'bigxSalt'
packetsStatisTime = 1
connCheckTime = 1

#the following parameters can be changed on the client alone, you don't need to change them on the server.
timeoutTime = 1
con_serverIp = '45.15.11.249'
#con_serverIp = '202.182.122.187'
#con_serverIp =  '192.168.100.60'
maxPortNum = 100
minPortNum = 10
con_portIncreaseDose = 3
con_portDecreaseDose = 1
minPackGot = 100
con_minRate = 0.08
con_maxRate = 0.5
con_pushAhead = 2000
con_packLimit = 1400
regulateTimeSpan = 0.3
perSecondPortsLimit = 30
def getCustomPortsLimit(currentPortNum,gotPacketsNum,lostPacketsNum,rawReadSpeed,rawWriteSpeed):
    if rawReadSpeed>250*1024:
        if  lostPacketsNum>10:
            return perSecondPortsLimit,-1
        else:
            return perSecondPortsLimit,0
    return perSecondPortsLimit,con_portIncreaseDose


maxSendConfig=[{'small':0,'big':0.05,'slope':1,'maxSend':3},
               {'small':0.05,'big':0.1,'slope':1.5,'maxSend':3},
               {'small':0.1,'big':0.4,'slope':2,'maxSend':4},
               {'small':0.4,'big':0.6,'slope':3,'maxSend':5},
               {'small':0.6,'big':0.8,'slope':4,'maxSend':8},
               {'small':0.8,'big':1,'slope':5,'maxSend':10},]
con_closeTime = 50

######################  THIS IS THE END OF THE CONFIG PART  ######################

platformName = platform.system()
pyV = sys.version_info[0]
def getRunningTime():    
    if pyV == 3:
        return time.monotonic()
    if platformName=='Windows':
        return time.clock()
    elif platformName=='Linux':
        with open('/proc/uptime') as f:
            return float(f.read().split()[0])
    else:
        return time.time()
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
    
def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(s.getsockname()[1])

def findNPorts(n):
    l = []
    while len(l)!=n:
        i = find_free_port()
        if i not in l:
            l.append(i)
    return l

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
        j = j.encode()
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
        self.m_json = json.loads(s[8:8+jL])
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

def makePack_server(s,u,salt):
    u2 = binascii.unhexlify(u)
    s1 = u2+s
    dk = hashlib.pbkdf2_hmac('md5', s1, salt, 2)
    s2 = s1+dk
    return s2

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
    return (binascii.hexlify(u)).decode(),con

def checkPackValid_server(s,salt):
    if len(s)<16:
        return '',b''
    s1 = s[-16:]
    s2 = s[:-16]
    dk = hashlib.pbkdf2_hmac('md5', s2, salt, 2)
    if dk != s1:
        return '',b''
    if len(s2)<16:
        return '',b''
    return (binascii.hexlify(s2[:16])).decode() ,s2[16:]

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
    print (circleAddOne(8,10))
    print (circleAddOne(9,10))
    print (circleRange(98,2,100))
    u,s = makePack(b'sdfew',b'salt')
    print (u,s)
    s2 = checkPackValid(s, u, b'salt')
    print (s2)

          