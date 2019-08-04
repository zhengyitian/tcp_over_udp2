import os,sys
ar = sys.argv

if len(ar)<2:
    print ('you need a passwd for ss-server')
p = ar[1]
os.system('apt install pypy')
os.system('wget https://bootstrap.pypa.io/get-pip.py')
os.system('pypy get-pip.py')
os.system('pypy -m pip install tornado')
#os.system('apt install gcc')
#os.system('apt install python-pip')
#os.system('apt install python-dev')
#os.system('apt install python-setuptools')
os.system('apt install shadowsocks-libev')
os.system('nohup ss-server -s 0.0.0.0 -p 8080 -k %s -m chacha20 -d 8.8.8.8 --fast-open -u >/dev/null &'%p)
#os.system('pip install wheel')
#os.system('pip install tornado')
os.system('nohup pypy TOUServer.py >/dev/null &')
