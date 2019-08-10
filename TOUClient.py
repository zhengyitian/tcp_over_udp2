import socket,select
from helpFunc import *
import uuid,json
mySalt = serviceSaltKey.encode()
from connClient import connClient
id = str(uuid.uuid1())
ports2 = []
gSalt = b''

while True:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    m = {'sign':id}
    m['rate'] = con_minRate
    m['pushAhead'] = con_pushAhead
    m['packLimit'] = con_packLimit
    m['salt'] = randomStringDigits()
    gSalt = m['salt'].encode()
    m['num'] = maxPortNum
    j = json.dumps(m)
    j = j.encode()
    u ,s2 = makePack(j,mySalt)    
    sock.sendto(s2, (con_serverIp, servicePort))
    r = select.select([sock],[],[],timeoutTime)
    if r[0]==[]:
        sock.close()
        continue
    j = sock.recv(recLen)
    s2 = checkPackValid(j,u,mySalt)
    if not s2:
        sock.close()
        continue 
    ports = []
    st = structWrapper(s2)    
    for i in range(maxPortNum):
        ports.append(st.readWord())
    print ('server starts:',ports)
    ports2 = ports
    sock.close()
    break

import time
from tornado.ioloop import IOLoop
serverListenPort = ports2
rate = con_minRate
pushAhead = con_pushAhead
packLimit = con_packLimit
salt = gSalt
clientListenIp = '0.0.0.0'
clientListenPort = 9999
time.sleep(1)
t = connClient(serverListenPort,salt,rate,pushAhead,packLimit,clientListenIp,clientListenPort)
IOLoop.instance().start()

