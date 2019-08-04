# tcp_over_udp2

needs python2(or pypy),tornado(a python framework)

helpFunc.py is where the config is. 

there are notes in that file to tell you how to set the parameters. 

run TOUServer.py on the server(tested on linux)

run TOUClient.py on the client(tested on linux and windows)

if everything goes well, the program will print "got conn" on the client,

otherwise, restart the program on the client side after a few seconds.

then what you connect to tcp client:9999 is directed to tcp server:8080

the client and the server communicate using udp

pypy is prefered than python, it can make the program faster.

the client can also run on android. see the androidClient directory.

i made this because i found tcp connection to my server was blocked but udp not.
