# androidClient

this contains the client files for andorid.

needs python3,kivy,tornado. i use buildozer to build a .apk.

a few tips about installing buildozer: don't do it as root,

use python3, create a virtual environment, use pip to install kivy,pillow,pygame,

buildozer,cython,python-for-android,don't put "==version" when installing

cython, as some posts on the web say.

in the .spec file, add android,tornado to the requirements, change "android.permissions" part,

as I did in buildozer.spec. 

i only built and tested the debug version. i tested it on my huaweiP20. 

When installing, give the program permission to read/write files.

open the program your installed(its name is"My Applicati..."something), you will see 

four buttons "start","quit","text","clear", and some blanks in the letf asking for parameters,

and a log output area in the bottom.

it will be filled with default parameters when it runs for the first time. Later, they will

be filled with the parameters you have changed. Every parameter has a corresponding one in the helpFunc.py

in the desktop version, you can find notes on how to change them in that file.

"ip,port,key,Tout,listen,LGot,MPort,LPort,IDose,DDose,MRate,LRate,Ahead,size,span,limit,speed,ONum,dose2,close"

mean "con_serverIp,servicePort,serviceSaltKey,timeoutTime,9999,minPackGot,maxPortNum,

minPortNum,con_portIncreaseDose,con_portDecreaseDose,con_maxRate,con_minRate,

con_pushAhead,con_packLimit,regulateTimeSpan,perSecondPortsLimit,250,10,-1(absolute value),con_closeTime" in helpFunc.py

(250,10,-1 are in getCustomPortsLimit function).

'ip','key' are strings, 'Tout','LRate','MRate','span' are positive floats, others are positive integres.

if you tap the "start" button and no log came out, restart the program.

"text" button freezes the log so you can inspect it, "clear" button clears the log.

there are two kinds of log. one kind is "conn sent" or "conn back" followed by conn id and how many connections there are,

it also shows how long the program has run.the other kind has 9 numbers, meaning 

"port number, packets got this second, packets lost this second, the response time, the raw download speed(KB/s),

the maxium packet size this second of client sent, server received, server sent,client received.'+' means there is lot of data,

'-' means there are blank packets being sent.

if there is a shadowsocks client or some other same thing running on the phone, don't forget to let the program circumvent it,

otherwise no udps would get out of your phone. i tested it using both wlan and phone network(中国移动,中国电信).

when using phone network, sometimes the speed gets very slow, turning the phone into "flying mode" and then back would boost the speed.

when using 中国电信, I set 'Ahead','size' to 800,900.

to allow it to run in background, go to setting->application->application management->"app name"->

power usage details->app start up management->allow auto start and allow running in background. 

If you find it not work because of any reason or bugs, restart it.

