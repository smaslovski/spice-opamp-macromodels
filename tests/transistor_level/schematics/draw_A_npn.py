# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
# Draws schematic A_npn (needs schemdraw >= 0.19): python3 draw_A_npn.py
import os, sys; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from schematic_common import *
s=S(); d=s.d
VCC,VEE=14.0,0.0
NPN=lambda: elm.BjtNpn(circle=False)
PNP=lambda: elm.BjtPnp(circle=False)
XB,X1,XT,X2,XC,XS,XO,XQ13=0.0,3.0,4.5,6.0,8.9,10.8,14.0,7.6
XL=XB+1.5                        # diode link of the bias transistor Q11
XL13=(XQ13+XS)/2                 # diode link of Q13
XJ=(XS+XO-0.75)/2                # jog to the output-stage bases
XOUT=XO+1.85
# pnp mirror Q3/Q4
q3=s.dev(PNP().reverse(),'emitter',(X1,12.6)); s.name(q3,'Q3','l',x=X1)
q4=s.dev(PNP(),'emitter',(X2,12.6)); s.name(q4,'Q4','r',x=X2)
s.w(q3['base'],q4['base']); s.dot((XT,q3['base'][1]))
s.w((XT,q3['base'][1]),(XT,10.6),(X1,10.6)); s.dot((X1,10.6))
s.w(q3['emitter'],(X1,VCC)); s.w(q4['emitter'],(X2,VCC))
# input pair Q1/Q2
q1=s.dev(NPN(),'collector',(X1,9.4)); s.name(q1,'Q1','r',x=X1)
q2=s.dev(NPN().reverse(),'collector',(X2,9.4)); s.name(q2,'Q2','l',x=X2)
s.w(q3['collector'],q1['collector']); s.w(q4['collector'],q2['collector'])
yb=q1['base'][1]
s.w(q1['base'],(1.3,yb)); s.dot((1.3,yb),open=True); s.lab((1.3,yb+0.35),'inn',h='center',v='bottom')
s.w(q2['base'],(7.2,yb)); s.dot((7.2,yb),open=True); s.lab((7.2,yb+0.35),'inp',h='center',v='bottom')
s.w(q1['emitter'],(X1,7.2),(X2,7.2),q2['emitter']); s.dot((XT,7.2)); s.lab((XT+0.2,7.35),'t',v='bottom',size=10,color='#666')
# tail Q10 and bias Ib/Q11
q10=s.dev(NPN(),'collector',(XT,6.2)); s.name(q10,'Q10','r',x=XT)
s.w((XT,7.2),q10['collector'])
s.two(elm.Resistor,q10['emitter'],(XT,VEE),label='R10\n10k')
s.two(elm.SourceI,(XB,VCC),(XB,7.4),label='Ib\n20 µA')
q11=s.dev(NPN().reverse(),'collector',(XB,6.2)); s.name(q11,'Q11','l',x=XB)
s.w((XB,7.4),q11['collector'])
s.w(q11['base'],q10['base']); s.dot((XL,q11['base'][1]))
s.w((XL,q11['base'][1]),(XL,6.8),(XB,6.8)); s.dot((XB,6.8))
s.two(elm.Resistor,q11['emitter'],(XB,VEE),label='R11\n10k')
# second stage Q5 with Miller capacitor
yc2=10.2
s.dot((X2,yc2))
q5=s.dev(PNP(),'base',(XS-0.75,yc2)); s.name(q5,'Q5','r',x=XS)
s.w((X2,yc2),q5['base']); s.dot((XC,yc2))
s.w(q5['emitter'],(XS,VCC))
yo2=7.6
s.two(elm.Capacitor,(XC,yc2),(XC,yo2),label='Cc\n30p')
s.w((XC,yo2),(XS,yo2)); s.w(q5['collector'],(XS,yo2)); s.dot((XS,yo2))
s.lab((XS+0.2,yo2+0.15),'o2',v='bottom',size=10,color='#666')
# class-AB bias diodes and current-source load Q12
s.two(elm.Diode,(XS,yo2),(XS,6.2),label='D1',loc='lft'); s.two(elm.Diode,(XS,6.2),(XS,4.8),label='D2',loc='lft')
s.dot((XS,4.8))
q12=s.dev(NPN(),'collector',(XS,4.0)); s.name(q12,'Q12','r',x=XS)
s.w((XS,4.8),q12['collector'])
s.two(elm.Resistor,q12['emitter'],(XS,VEE),label='R12\n1k')
# separate bias for Q12
q13=s.dev(NPN().reverse(),'collector',(XQ13,4.0)); s.name(q13,'Q13','l',x=XQ13)
s.w(q13['base'],q12['base']); s.dot((XL13,q13['base'][1]))
s.w((XL13,q13['base'][1]),(XL13,4.5),(XQ13,4.5)); s.dot((XQ13,4.5))
s.two(elm.SourceI,(XQ13,6.4),(XQ13,4.5),label='Ib2\n20 µA')
s.at(elm.Vdd().label('vcc',fontsize=10),(XQ13,6.4))
s.w(q13['collector'],(XQ13,4.5))
s.two(elm.Resistor,q13['emitter'],(XQ13,VEE),label='R13\n10k',loc='lft')
# output stage
q7=s.dev(NPN(),'emitter',(XO,7.6)); s.name(q7,'Q7','r',x=XO)
s.w((XS,yo2),(XJ,yo2),(XJ,q7['base'][1]),q7['base'])
q8=s.dev(PNP(),'emitter',(XO,3.4)); s.name(q8,'Q8','r',x=XO)
s.w((XS,4.8),(XJ,4.8),(XJ,q8['base'][1]),q8['base'])
s.w(q7['collector'],(XO,VCC)); s.w(q8['collector'],(XO,VEE))
s.two(elm.Resistor,q7['emitter'],(XO,5.5),label='R7\n25'); s.two(elm.Resistor,q8['emitter'],(XO,5.5),label='R8\n25')
s.dot((XO,5.5)); s.w((XO,5.5),(XOUT,5.5)); s.dot((XOUT,5.5),open=True); s.lab((XOUT+0.25,5.5),'out')
# rails
s.w((XB,VCC),(XO,VCC)); s.w((XB,VEE),(XO,VEE))
for x in (X1,X2,XS): s.dot((x,VCC))
for x in (XT,XQ13,XS): s.dot((x,VEE))
s.supplies(XB,VCC,VEE,'15')
s.lab((-4.25,15.5),'A — bipolar op amp with an npn input pair',size=13)
s.lab((-4.25,-1.0),'Q7, Q8, Q12: area 10.  Phase reversal at the top: when inp > vcc − 0.04 V the Q2 base–collector junction conducts.',size=10,color='#444',v='top')
s.save(os.path.join(HERE, 'A_npn.png')); s.save(os.path.join(HERE, 'A_npn.svg'))
