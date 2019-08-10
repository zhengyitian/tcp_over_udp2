from helpFunc import *
import os,time,json
import sys

from collections import deque
runningPath = os.path.split(os.path.realpath(__file__))[0]
print (runningPath)  
mySalt = serviceSaltKey.encode()
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0',servicePort))
usedMap = {}
usedQ = deque()

while True:
    data, addr = sock.recvfrom(recLen)
    uuid ,ss = checkPackValid_server(data,mySalt)
    if not uuid :
        continue
    m = json.loads(ss)
    sign = m['sign']
    num = m['num']
    r = ''
    if sign not in usedMap:
        ports = findNPorts(num)
        time.sleep(0.1)
        m ['lp'] = ports
        import base64,json
        j = json.dumps(m)
        s = base64.b64encode(j)
        ex = sys.executable
        os.system('nohup %s %s/connServer.py %s >/dev/null &'%(ex,runningPath,s))
        print ('start server:',ports)
        import struct
        re = ''
        for one in ports:
            re+= struct.pack('H',one)
        m2 = {'con':re,'createTime':getRunningTime()}
        usedMap[sign] = m2
        usedQ.append(sign)
        if len(usedMap)>10000:
            ss = usedQ.popleft()
            del usedMap[ss]
            
    m = usedMap[sign]
    j = m['con']
    j = j.encode()
    data = makePack_server(j, uuid, mySalt)
    sock.sendto(data,addr)
