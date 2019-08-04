import TOUClient
import json
from helpFunc import *
import time
f = open('service_config')
s = f.read()
f.close()
config = json.loads(s)
try:
    TOUClient.main(config)
except Exception as e:
    s = 'Exception : '+str(e)+'\n'
    writeLog(s)
    f = open('commandOut.txt','w')
    m = {'exit':True,'commandId':config['commandId'],'aliveTime':time.monotonic()}
    j = json.dumps(m)
    f.write(j)
    f.close()            