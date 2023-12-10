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
import colorsys


plt.style.use('ggplot')
#sd.default.device = 'pulse'
#sd.default.device = 'hw:0,2'
fs=44000
duration = 1/30  # seconds

MSmoothness = 20 # Max Mode Smoothness
ASmoothness = 5  # Average Mode Smoothness

HELP_TEXT='''
USAGE `fft (FILE) [OPTIONS] 

OPTIONS:
#   -h Display this help menu
#   -m Mono Mode
#   -s Stereo Mode
#   -S Stereo With Average
#   -l Channel Left (mono)
#   -r Channel Right (mono)
#   -a Channel Average (mono)
#   -M
#   -A
#   -H High Smoothness
#   -L Low Smoothness
'''

FILENAME = os.path.dirname(os.path.abspath(__file__))

dataR=[]
dataL=[]

DefaultEnable = False # Use a default config when no arguments given

myrecording= np.ndarray((2,int(2)))
def hex2rgb(h):
    h=h.replace("#","")
    return (int(h[0:2],16),int(h[2:4],16),int(h[4:6],16))

# Put all OPTIONS (-hv for example) into a string for processing
options = "" 
for a in sys.argv:
    if a[0]=="-":
        options+=a[1:]

if len(sys.argv)>=2 or not DefaultEnable:
    if (len(sys.argv)==1 or sys.argv[1]=="help" or "h" in options):
        print(HELP_TEXT)
        print("THEMES:")
        files=os.listdir(FILENAME)
        for f in files:
            if f[-3:]==".th":
                print("#",f.replace(".th",""))
        exit()
        
    else:
        f=open(f"{sys.argv[1]}.th")
        T=f.read().split("\n")
        for l in T:
            exec(l)
else:
    #boxchars = ["●","●"]
    #boxchars = ["○","◒","●"]
    midchars = ""
    boxchars = [" ","▁","▂","▃","▄","▅","▆","▇","█"]
    #boxchars = [" ","│"]
    #boxchars = ["  ",["🤣 ","🙏 ","👁 ","👍 ","💪 ","⚠ "]]
    '''
    boxchars = [[" "],
                [" ","."],
                [".",","],
                [",",":"],
                [":","+"],
                ["+","#"],
                ["#","@"]]
    #'''
    channels = 10
    rows = 15
    run = True
    MonoChannel=2 # Left 1, Avg 2, Right 3
    monoMode=True 
    includeAvg = True;

    boost=10
    width = 1 # Width of each bar, for mono mode
    widthalt = 1 # Width of each bar element, width = widthalt * 3
    avgMode=True
    nobox = True # Removes boxes and frequency bars
    smoothness=4
    colourmode = 7 # Which colouring style to use?
    forceforec = True#Foreground colouring
    forcebackc = False#Background colouring
    colourfore=hex2rgb("#008800")
    colourback=hex2rgb("#00000")
    colour1=hex2rgb("#00ff00")#M2: solid, M4: bottom, M5: top right
    colour2=hex2rgb("#004000")#           M4: top,    M5: top left
    colour3=hex2rgb("#50ff50")#                       M5: bottom right
    colour4=hex2rgb("#104010")#                       M5: bottom left  
    hsv1=(0.5,1,255)#1,1,255 
    hsv2=(0.6,1,255)#1,1,255
    hueshift=-0.6
    # Decimal thresholds for where the volume effects should take effect
    volLnC =1# Linear (ax) Multiplier (a) for volume curve
    volExC =5# Exponential (ax**n) multiplier (a) for volume curve
    volExI =3# Exponential (ax**n) index (n) for volume curve
    #M6: Top High
    #M6: Top Low
    #M6: Bottom High
    #M6: Bottom Low


    #Colourmode Table
    #0 None/Foreground
    #1 Green/Yellow/Red Level Indicator
    #2 Solid Colour
    #3 G/Y/R /w dark off (LED style)
    #4 Vertical Gradient
    #5 Horizontally defined Vertical Gradient
    #6 4/VG volume dependant
    #7 Hue Shift Volume Dependant
    padding = 1 # padding each side
    upperLimit=5000
    lowerLimit=100
    startComp=1000 # Start Compenstation, prevents large bins low down, 
                        #    defines the starting frequency rate increase
    min_dB=20
    logmode = True # Use logarithmic scale

upperLimit=4000
lowerLimit=100
startComp=1000 # Start Compenstation, prevents large bins low down, 
                    #    defines the starting frequency rate increase
#min_dB=20
logmode=True
maxMode=True
avgMode=False
smoothness=30
MaxNotAvg=True # Use Max Value instead of average
#ser = serial.Serial('/dev/ttyUSB0',57600)
scaleCoefficent= ((upperLimit-lowerLimit)-(startComp))/(channels**2)


boost=10



if "m" in options:
    monoMode=True 
if "s" in options:
    monoMode=False
    includeAvg = False
if "S" in options:
    monoMode=False
    includeAvg = True

if monoMode and "L" in options:
    MonoChannel=1
if monoMode and "A" in options:
    MonoChannel=2
if monoMode and "R" in options:
    MonoChannel=3


if "A" in options:
    maxMode=False
    avgMode=True
    MaxNotAvg=False # Use Max Value instead of average
    smoothness=ASmoothness
if "M" in options:
    maxMode=True
    avgMode=False
    MaxNotAvg=True # Use Max Value instead of average
    smoothness=MSmoothness

if "n" in options:
    logmode=False
    boost=boost*2
if "g" in options:
    logmode=True

if "L" in options: # Low Smoothness
    smoothness/=2
if "H" in options: # High Smoothness
    smoothness*=2

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
    global logmode
    if logmode:
        value = (math.log(v+0.0000000001,10)+(min_dB/10))/(min_dB/10)
    else:
        value = v
    sex=""
    for i in range(width):
        value = max(min(value,1),0)
        newval = (value*rows)- row
        bindex = round(max(min(1,newval)*(len(boxchars)-1),0))
        sex+=random.choice(boxchars[bindex])
    return sex

def valueism(v,rows, row):
    #value = (math.log(value,10)+(min_dB/10))/(min_dB/10)
    global logmode
    if logmode:
        value = (math.log(v+0.0000000001,10)+(min_dB/10))/(min_dB/10)
    else:
        value = v
    value = max(min(value,1),0)
    newval = (value*rows)- row
    bindex = round(max(min(1,newval)*(len(boxchars)-1),0))
    return bindex

def logiser(v):
    global logmode
    #value = (math.log(value,10)+(min_dB/10))/(min_dB/10)
    if logmode:
        value = (math.log(v+0.0000000001,10)+(min_dB/10))/(min_dB/10)
    else:
        value = v
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
        n=valueism(V,rows,row)
        if n!=0:
            if row/rows>=0.8:
                return "\033[91m"
            elif row/rows>=0.6:
                return "\033[93m"
            elif row/rows<0.2:
                return "\033[94m"
            else:
                return "\033[92m"
        else:
            if row/rows>=0.8:
                return "\033[31m"
            elif row/rows>=0.6:
                return "\033[33m"
            elif row/rows<0.2:
                return "\033[34m"
            else:
                return "\033[32m"
    if colourmode==8:
        n=valueism(V,rows,row)
        if n>0:
            R,G,B=colour1
            R2,G2,B2=colour3
        else:
            R,G,B=colour2
            R2,G2,B2=colour4
        return f"\033[38:2:{R}:{G}:{B}m\033[48:2:{R2}:{G2}:{B2}m"
    elif colourmode==4:
        rw=row/rows
        R=round(((colour1[0]*rw)+(colour2[0]*(1-rw))))
        G=round(((colour1[1]*rw)+(colour2[1]*(1-rw))))
        B=round(((colour1[2]*rw)+(colour2[2]*(1-rw))))
        #print(rw,colour1,colour2,R,G,B)
        return f"\033[38:2:{R}:{G}:{B}m"
    elif colourmode==5 or colourmode==6 or colourmode==7:
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
    return s

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
            avg = total/count
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
                 if(avgMode or maxMode):
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
                    if(maxMode):
                        total=0
                        weight=0
                        for i in prevSamplesL[c]:
                            total=max(total*0.9,i*weight)
                            weight+=1/smoothness
                        sampleL=total
                        total=0
                        weight=0
                        for i in prevSamplesR[c]:
                            total=max(total*0.9,i*weight)
                            weight+=1/smoothness
                        sampleR=total
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
                        x=max(min(sampleA*boost,1),0) # raw
                        rw=max(min(x,1),0)
                        rwi=max(min(1-rw,1),0)
                        R=round(((colour1[0]*rw)+(colour2[0]*(rwi))))
                        G=round(((colour1[1]*rw)+(colour2[1]*(rwi))))
                        B=round(((colour1[2]*rw)+(colour2[2]*(rwi))))
                        cc1=(R,G,B) # Colour per row
                        R=round(((colour3[0]*rw)+(colour4[0]*(rwi))))
                        G=round(((colour3[1]*rw)+(colour4[1]*(rwi))))
                        B=round(((colour3[2]*rw)+(colour4[2]*(rwi))))
                        cc2=(R,G,B)
                    if colourmode==7:
                        x=max(min(logiser(sampleA*boost),1),0) # raw
                        rgb1=colorsys.hsv_to_rgb(max(min(hsv1[0]+(x*hueshift),1),0),hsv1[1],hsv1[2])
                        rgb2=colorsys.hsv_to_rgb(max(min(hsv2[0]+(x*hueshift),1),0),hsv2[1],hsv2[2])
                        R=round(((rgb1[0])))
                        G=round(((rgb1[1])))
                        B=round(((rgb1[2])))
                        cc1=(R,G,B)
                        R=round(((rgb2[0])))
                        G=round(((rgb2[1])))
                        B=round(((rgb2[2])))
                        cc2=(R,G,B)

                    
                    if(not monoMode):
                        if(includeAvg):
                            bf += rowColour(rows,row,sampleL*boost)
                            bf += boxcharism(sampleL*boost,rows,(rows-row)-1,widthalt)
                            bf += midchars
                            bf += rowColour(rows,row,sampleA*boost)
                            bf += boxcharism(sampleA*boost,rows,(rows-row)-1,widthalt)
                            bf += midchars
                            bf += rowColour(rows,row,sampleR*boost)
                            bf += boxcharism(sampleR*boost,rows,(rows-row)-1,widthalt)
                        else:
                            bf += rowColour(rows,row,sampleL*boost)
                            bf += boxcharism(sampleL*boost,rows,(rows-row)-1,widthalt)
                            bf += midchars
                            bf += rowColour(rows,row,sampleR*boost)
                            bf += boxcharism(sampleR*boost,rows,(rows-row)-1,widthalt)
                    else:
                        if(MonoChannel==1):
                            bf += rowColour(rows,row,sampleL*boost)
                            bf += boxcharism(sampleL*boost,rows,(rows-row)-1,width)
                        if(MonoChannel==2):
                            bf += rowColour(rows,row,sampleA*boost)
                            bf += boxcharism(sampleA*boost,rows,(rows-row)-1,width)
                        if(MonoChannel==3):
                            bf += rowColour(rows,row,sampleR*boost)
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

# by pine
# pine0772@gmail.com
# pine0772@protonmail.com


#┌─┐ 
#│ │
#│▅│
#│█│
#│█│
#└─┘


