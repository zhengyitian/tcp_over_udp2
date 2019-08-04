import socket,select
from helpFunc import *
import uuid,json
from connClient import connClient
g_t = None

def main(mm):
    id = str(uuid.uuid1())
    ports2 = []
    gSalt = ''
    mySalt = mm['key']
    mySalt = bytes(mySalt,encoding='utf8')
    
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        m = {'sign':id}
        m['rate'] = mm['LRate']
        m['pushAhead'] = mm['Ahead']
        m['packLimit'] = mm['size']
        m['salt'] = randomStringDigits()
        gSalt = m['salt']
        MPort = m['num'] = mm['MPort']
        j = json.dumps(m)
        j = bytes(j,encoding='utf8')
        
        u ,s2 = makePack(j,mySalt) 
        sIp = mm['ip']
        sPort = mm['port']
        sock.sendto(s2, (sIp, sPort))
        timeoutTime = mm['Tout']
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
        for i in range(MPort):
            ports.append(st.readWord())
        s = 'server starts: '+str(ports)+'\n'
        print (s)
        writeLog(s)
        ports2 = ports
        sock.close()
        break
    
    import time
    from tornado.ioloop import IOLoop
    rate = mm['LRate']
    pushAhead = mm['Ahead']
    packLimit = mm['size']
    MPort = mm['MPort']
    LPort = mm['LPort']
    DDose = mm['DDose']
    IDose = mm['IDose']
    LGot = mm['LGot']
    MRate = mm['MRate']
    LRate = mm['LRate']
    span = mm['span']
    limit = mm['limit']
    speed = mm['speed']
    dose2 = mm['dose2']
    closeTime = mm['close']
    ONum = mm['ONum']
    sIp = mm['ip']
    sPort = mm['port']
    timeoutTime = mm['Tout']
    serverListenPort = ports2
    salt = bytes(gSalt,encoding='utf8')
    clientListenIp = '0.0.0.0'
    clientListenPort = mm['listen']
    time.sleep(1)
    serverIp = mm['ip']
    commandId = mm['commandId']

    t = connClient(serverListenPort,salt,rate,pushAhead,packLimit,clientListenIp,clientListenPort,timeoutTime,serverIp,\
                   MPort,LPort,IDose,DDose,LGot,MRate,LRate,span,limit,speed,dose2,closeTime,ONum,commandId)
    global g_t
    g_t = t
    IOLoop.instance().start()
if __name__ == '__main__':
    createLog()
    import os
    l = os.listdir()
    if 'my_config.json' not in l:
        print ('no config found !!!')
    else:
        f = open('my_config.json')
        s = f.read()
        f.close()
        main(json.loads(s))    

