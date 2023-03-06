
import serial
import time
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import socket
import threading
import time
import math
import matplotlib.pyplot as plt
import os
import random
import sys

def hex2rgb(h):
    h=h.replace("#","")
    return (int(h[0:2],16),int(h[2:4],16),int(h[4:6],16))

#sd.default.device = 'pulse' # Device to use, Comment for default
fs=44000 # Sample rate
duration = 1/30  # Duration of each FFT sample


# ---------- SETTINGS ---------- #

# 'boxchars' defines what character to use when
#    displaying a bar. values range from 0-1 where
#    middle values represent the tops of the bars.
#    Using arrays instead of strings adds a random choice
#    between each character in the subarrays.
# 'midchars' defines the character used between bars
#    in stereo mode.


#boxchars = ["●","●"] # LED style 1
#boxchars = ["○","◒","●"] # LED style 2
midchars = ""
boxchars = [" ","▁","▂","▃","▄","▅","▆","▇","█"] # Bar style
#boxchars = [" ","│"]
'''
boxchars = [[" "],
            [" ","."],
            [".",","],
            [",",":"],
            [":","+"],
            ["+","#"],
            ["#","@"]] # Char style
#'''





MonoChannel=2 # Which channel to use? Left 1, Avg 2, Right 3
monoMode=True # 1 Mono Bar?
includeAvg = False; # 3 Bar stereo
boost=5 # Boosts volume linearly.
width = 1 # Width of each bar, for mono mode
widthalt = 1 # Width of each bar element, width = widthalt * 3
avgMode=True
nobox = True # Removes boxes and frequency bars
smoothness=4 # Averages value between n samples
colourmode = 6 # Which colouring style to use?
forceforec = True#Foreground colouring
forcebackc = False#Background colouring
colourfore=hex2rgb("#008800") # Foreground colour
colourback=hex2rgb("#00000") # Background colour
colour1=hex2rgb("#00ff00")# M2: solid, M4: bottom, M5: top right
colour2=hex2rgb("#004000")#            M4: top,    M5: top left
colour3=hex2rgb("#50ff50")#                        M5: bottom right
colour4=hex2rgb("#104010")#                        M5: bottom left  
# M6: Top High
# M6: Top Low
# M6: Bottom High
# M6: Bottom Low
# Colourmode Table
#   0 None/Foreground
#   1 Green/Yellow/Red Level Indicator
#   2 Solid Colour
#   3 G/Y/R /w dark off (LED style)
#   4 Vertical Gradient
#   5 Horizontally defined Vertical Gradient
#   6 4/VG volume dependant (NOT IMPLEMENTED)  

# Decimal thresholds for where the volume effects should take effect
volLnC =1# Linear (ax) Multiplier (a) for volume curve
volExC =5# Exponential (ax**n) multiplier (a) for volume curve
volExI =3# Exponential (ax**n) index (n) for volume curve

padding = 1 # space padding each side of bar section

upperLimit=10000
lowerLimit=60

startComp=1000 
# ^Start Compenstation, prevents large bins low down, 
#    defines the starting frequency rate increase
min_dB=15 # The low end of the volume scale to show


# ---------- SETTINGS ---------- #






run = True
dataR=[]
dataL=[]
plt.style.use('ggplot')
myrecording= np.ndarray((2,int(2)))

channels = 5
rows = 5
# ^ Defined during runtime





#ser = serial.Serial('/dev/ttyUSB0',57600)
scaleCoefficent= ((upperLimit-lowerLimit)-(startComp))/(channels**2)

if not nobox and monoMode==False and includeAvg==False:
    width=(widthalt*2)+len(midchars)
if not nobox and monoMode==False and includeAvg==True:
    width=(widthalt*3)+len(midchars)
if nobox and monoMode==False and includeAvg==False:
    width=(widthalt*2)
if nobox and monoMode==False and includeAvg==True:
    width=(widthalt*3)

#def send(a,b):
#    ser.write((str(a)+";"+str(b)+"\n").encode('ascii', 'replace'))
elwidth = (width+int(padding*2))

if nobox:
    elwidth = (width+int(padding))
def boxcharism(v,rows, row,width):
    value = (math.log(v+0.0000000001,10)+(min_dB/10))/(min_dB/10)
    sex=""
    for i in range(width):
        value = max(min(value,1),0)
        newval = (value*rows)- row
        bindex = round(max(min(1,newval)*(len(boxchars)-1),0))
        sex+=random.choice(boxchars[bindex])
    return sex

def valueism(v,rows, row):
    #value = (math.log(value,10)+(min_dB/10))/(min_dB/10)
    value = (math.log(v+0.0000000001,10)+(min_dB/10))/(min_dB/10)
    value = max(min(value,1),0)
    newval = (value*rows)- row
    bindex = round(max(min(1,newval)*(len(boxchars)-1),0))
    return bindex

def logiser(v):
    #value = (math.log(value,10)+(min_dB/10))/(min_dB/10)
    value = (math.log(v+0.0000000001,10)+(min_dB/10))/(min_dB/10)
    value = max(min(value,1),0)
    return value

def rec_thread():
    try:
        global dataR
        global dataL
        global myrecording
        stream=sd.InputStream(samplerate=fs, channels=2)
        stream.start()
        while True:
            stream=sd.InputStream(samplerate=fs, channels=2)
            stream.start()
            for i in range(fs):
                #print("threadist")
                #myrecording= np.ndarray((2,int(2)))
                #myrecording = sd.rec(int(44100*5000), samplerate=fs, channels=2,dtype='float64')
                #sd.wait()
                #sample=[]
                
                samples=stream.read(int(fs*duration))[0]
                R=[]
                L=[]
                for sample in samples:
                    #if(len(dataR)>fs):
                        #dataR.pop(1)
                    #if(len(dataL)>fs):
                        #dataL.pop(1)
                    R.append(sample[0])
                    L.append(sample[1])
                dataR = R
                dataL = L

            stream.stop()
            time.sleep(0.05)
    except Exception as e:
        print(e)

x = threading.Thread(target=rec_thread, args=())


frequencyIndexes = [500,1000,1500,2000]


def sample(data, freq):
    N = len(data)
    
    Y_k = np.fft.fft(data)[0:int(N/2)]/N # FFT function from numpy
    Y_k[1:] = 2*Y_k[1:] # need to take the single-sided spectrum only
    Pxx = np.abs(Y_k) # be sure to get rid of imaginary part

    f = fs*np.arange((N/2))/N; # frequency vector
    
    findex = 0
    for i in range (0,len(f)):
        
        if f[i] >= freq:
            #print(f[i], freq)
            findex = i
            break 
    return Pxx[i]

def sampleArr(data):
    N = len(data)
    
    Y_k = np.fft.fft(data)[0:int(N/2)]/N # FFT function from numpy
    Y_k[1:] = 2*Y_k[1:] # need to take the single-sided spectrum only
    Pxx = np.abs(Y_k) # be sure to get rid of imaginary part

    f = fs*np.arange((N/2))/N; # frequency vector
    
    findex = 0
    s=[]
    for i in range (0,len(f)):
        s.append(Pxx[i])
    return (s,f)

#send(0,0)

def rowColour(rows,r,V):
    global colour1
    global colour2
    row = (rows-r)-1
    if colourmode==1:
        if row/rows>=0.8:
            return "\033[91m"
        elif row/rows>=0.6:
            return "\033[93m"
        else:
            return "\033[92m"
    elif colourmode==2:
        R,G,B=colour1
        #return "\033[38:5:202m"
        return f"\033[38:2:{R}:{G}:{B}m"
    if colourmode==3:
        n=valueism(V,rows,(rows-row)-1)
        if n!=0:
            if row/rows>=0.8:
                return "\033[91m"
            elif row/rows>=0.6:
                return "\033[93m"
            else:
                return "\033[92m"
        else:
            if row/rows>=0.8:
                return "\033[31m"
            elif row/rows>=0.6:
                return "\033[33m"
            else:
                return "\033[32m"
    elif colourmode==4:
        rw=row/rows
        R=round(((colour1[0]*rw)+(colour2[0]*(1-rw))))
        G=round(((colour1[1]*rw)+(colour2[1]*(1-rw))))
        B=round(((colour1[2]*rw)+(colour2[2]*(1-rw))))
        #print(rw,colour1,colour2,R,G,B)
        return f"\033[38:2:{R}:{G}:{B}m"
    elif colourmode==5 or colourmode==6:
        global cc1
        global cc2
        rw=row/rows
        R=round(((cc1[0]*rw)+(cc2[0]*(1-rw))))
        G=round(((cc1[1]*rw)+(cc2[1]*(1-rw))))
        B=round(((cc1[2]*rw)+(cc2[2]*(1-rw))))
        return f"\033[38:2:{R}:{G}:{B}m"
    #elif colourmode==6:
    #    val=logiser(V)
    #    return ""
    else:
        return ""

def resetColour():
    global forceforec
    global forcebackc
    global colourfore
    global colourback
    s=""
    if forceforec:
        R1,G1,B1=colourfore
        s+=f"\033[38:2:{R1}:{G1}:{B1}m"
    if forcebackc:
        R2,G2,B2=colourback
        s+=f"\033[48:2:{R2}:{G2}:{B2}m"
    else:
        return "\033[00m"+s

os.system("clear")
x.start()

def freqout(fr):
    fr = int(fr)
    if fr>=1000:
        return str(round(fr/1000))+"k"
    elif fr>=1000000:
        return str(round(fr/1000000))+"M"
    else:
        return str(fr)

size = os.get_terminal_size()
oldsize = size
def scale(x):
    global lowerLimit
    global scaleCoefficent
    global startComp
    return (scaleCoefficent*(x**2))+lowerLimit+((x*startComp)/channels)

def getdata(d, channels):
    data= sampleArr(d)[0]
    f = sampleArr(d)[1]
    chns = []
    lastfreq = 0 
    freq=0
    lastindex=0
    for c in range(channels):
        lastfreq = freq
        freq = scale(c)#(((c+2)/channels)**2)*UpperLimit
        total=0
        count=0
        for i in range(lastindex,len(f)):
            if f[i] >= freq:
                lastindex=i
                break
            else:
                count+=1
                total+=data[i]
        if(count>0):
            avg = total#/count
        chns.append(avg)
    return chns
        
        
prevSamplesR=[]
prevSamplesL=[]

for c in range(0,100):
    prevSamplesR.append([])
    prevSamplesL.append([])

run=True



dR = []
dL = []
def processThread():
    global data
    global dR
    global dL
    global run
    global dataR
    global dataL
    global channels
    print("processing")
    while run:
        if len(dataR)>0:
            dR = getdata(dataR,channels)
            #print(dR)
        if len(dataL)>0:
            dL = getdata(dataL,channels)


pT = threading.Thread(target=processThread, args=())
pT.start()
while run:
    try:
        time.sleep(0.05)
        while True:
            size = os.get_terminal_size()
            if size != oldsize:
                os.system("clear")
            oldsize = size
            if not nobox:
                channels = math.floor((size[0]-4)/(elwidth+3))
            else:
                channels = math.floor((size[0])/(elwidth))
            if not nobox:
                rows = size[1]-3
            else:
                rows = size[1]
            scaleCoefficent= ((upperLimit-lowerLimit)-(startComp))/(channels**2)
            #print()
            bf = ""
            if not nobox:
                bf +="    "
                bf += (("┌"+("─"*elwidth)+"┐ ")*channels)+"\n"
            #data = getdata(dataR,channels)
            dR = getdata(dataR,channels)
            dL = getdata(dataL,channels)
            #print("epoint",dR)
            for c in range(channels):
                 if(avgMode):
                    #print(prevSamplesL)
                    prevSamplesL[c].append(dL[c])
                    prevSamplesR[c].append(dR[c])
                    if(len(prevSamplesL[c])>smoothness):
                        prevSamplesL[c].pop(0)
                    if(len(prevSamplesR[c])>smoothness):
                        prevSamplesR[c].pop(0)
            for row in range(rows):
                if not nobox:
                    bf +="    "
                for c in range(channels):
                    freq = (((c+1)/channels)**2)*10000
                    sampleL = dL[c]
                    sampleR = dR[c]
                    #sampleA = (sampleL + sampleR) / 2
                    #print("\n\n\n\n")
                    #print(sampleL)
                    if(avgMode):

                        total=0
                        count=0
                        for i in prevSamplesL[c]:
                            total+=i
                            count+=1
                        sampleL=total/count
                        total=0
                        count=0
                        for i in prevSamplesR[c]:
                            total+=i
                            count+=1
                        sampleR=total/count
                    sampleA = (sampleL + sampleR) / 2
                    if not nobox:
                        bf += "│"
                    bf += " "*padding

                    if colourmode==5:
                        rw=c/channels
                        R=round(((colour1[0]*rw)+(colour2[0]*(1-rw))))
                        G=round(((colour1[1]*rw)+(colour2[1]*(1-rw))))
                        B=round(((colour1[2]*rw)+(colour2[2]*(1-rw))))
                        cc1=(R,G,B)
                        R=round(((colour3[0]*rw)+(colour4[0]*(1-rw))))
                        G=round(((colour3[1]*rw)+(colour4[1]*(1-rw))))
                        B=round(((colour3[2]*rw)+(colour4[2]*(1-rw))))
                        cc2=(R,G,B)
                    if colourmode==6:
                        x=max(min(logiser(sampleA),1),0) # raw
                        rw=max(min((volExC*(x**volExI))+(volLnC*x),1),0)
                        rwi=max(min(1-rw,1),0)
                        R=round(((colour1[0]*rw)+(colour2[0]*(rwi))))
                        G=round(((colour1[1]*rw)+(colour2[1]*(rwi))))
                        B=round(((colour1[2]*rw)+(colour2[2]*(rwi))))
                        cc1=(R,G,B)
                        R=round(((colour3[0]*rw)+(colour4[0]*(rwi))))
                        G=round(((colour3[1]*rw)+(colour4[1]*(rwi))))
                        B=round(((colour3[2]*rw)+(colour4[2]*(rwi))))
                        cc2=(R,G,B)
                    
                    if(not monoMode):
                        if(includeAvg):
                            bf += rowColour(rows,row,sampleL)

                            bf += boxcharism(sampleL*boost,rows,(rows-row)-1,widthalt)
                            bf += midchars
                            bf += rowColour(rows,row,sampleA)
                            bf += boxcharism(sampleA*boost,rows,(rows-row)-1,widthalt)
                            bf += midchars
                            bf += rowColour(rows,row,sampleR)
                            bf += boxcharism(sampleR*boost,rows,(rows-row)-1,widthalt)
                        else:
                            bf += rowColour(rows,row,sampleL)
                            bf += boxcharism(sampleL*boost,rows,(rows-row)-1,widthalt)
                            bf += midchars
                            bf += rowColour(rows,row,sampleR)
                            bf += boxcharism(sampleR*boost,rows,(rows-row)-1,widthalt)
                    else:
                        if(MonoChannel==1):
                            bf += rowColour(rows,row,sampleL)
                            bf += boxcharism(sampleL*boost,rows,(rows-row)-1,width)
                        if(MonoChannel==2):
                            bf += rowColour(rows,row,sampleA)
                            bf += boxcharism(sampleA*boost,rows,(rows-row)-1,width)
                        if(MonoChannel==3):
                            bf += rowColour(rows,row,sampleR)
                            bf += boxcharism(sampleR*boost,rows,(rows-row)-1,width)
                    bf += resetColour()
                    if not nobox:
                        bf += " "*padding
                        bf += "│ "
                if not nobox or row!=rows-1:
                    bf += "\n"
            if not nobox:
                bf +="    "
                bf += (("└"+("─"*elwidth)+"┘ ")*channels)+"\n"
                bf +=" Hz "
                for c in range(channels):
                    freq = scale(c)#(((c+1)/channels)**2)*8000
                    wdt = elwidth+1
                    bf+=" "+("   "+freqout(freq)+" ")[-wdt:-1]+"  "
            print("\033[0;0f"+bf,end="")
            
               
            #time.sleep(1/30)


    except IndexError as e:
        print("Index error, Skip: ",e)
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        continue
    except ValueError as e:
        print("Value error, Skip: ",e)
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        continue
    #except TypeError as e:
    #    print("Type Error, Skip",e)
    #except IndexError as e:
    #    print("Index error, Skip",e)
    #except Exception as e:
    #    run = False
    #    print(type(e).__name__)
    #    print(e)
    #    print("Exit")
    time.sleep(0.1)

x.join()
pT.join()


# Dont mind the stupid function names and shitty coding
#   wasnt expecting to release this project.
#   not my problem :)