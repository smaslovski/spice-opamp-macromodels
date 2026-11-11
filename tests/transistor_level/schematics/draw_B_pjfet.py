# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
# Draws schematic B_pjfet (needs schemdraw >= 0.19): python3 draw_B_pjfet.py
import os, sys; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from schematic_common import *
s=S(); d=s.d
VCC,VEE=14.0,0.0
NPN=lambda: elm.BjtNpn(circle=False)
PNP=lambda: elm.BjtPnp(circle=False)
JP=lambda: elm.JFetN()  # schemdraw draws the outward (p-channel) gate arrow with this class
XB,X1,XT,X2,XC,XS,XO,XQ13=0.0,3.0,4.5,6.0,8.9,10.8,14.0,7.6
XL=XB+1.5                        # diode link of the bias transistor Q11
XL13=(XQ13+XS)/2                 # diode link of Q13
XJ=(XS+XO-0.75)/2                # jog to the output-stage bases
XOUT=XO+1.85
# bias Q11/Ib and tail Q10
q11=s.dev(PNP().reverse(),'emitter',(XB,9.6)); s.name(q11,'Q11','l',x=XB)
s.two(elm.Resistor,q11['emitter'],(XB,VCC),label='R11\n2k',loc='lft')
s.w(q11['collector'],(XB,7.8)); s.dot((XB,7.8))
s.w(q11['base'],(XL,q11['base'][1]),(XL,7.8),(XB,7.8)); s.dot((XL,q11['base'][1]))
s.two(elm.SourceI,(XB,7.8),(XB,VEE),label='Ib\n200 µA')
q10=s.dev(PNP(),'emitter',(XT,9.6)); s.name(q10,'Q10','r',x=XT)
s.two(elm.Resistor,q10['emitter'],(XT,VCC),label='R10\n2k')
s.w((XL,q11['base'][1]),q10['base'])
s.w(q10['collector'],(XT,7.4)); s.w((X1,7.4),(X2,7.4)); s.dot((XT,7.4)); s.lab((XT+0.2,7.25),'t',v='top',size=10,color='#666')
# input pair (p-JFET)
j1=s.dev(JP().flip().reverse(),'source',(X1,6.8)); s.name(j1,'J1','r',x=X1)
j2=s.dev(JP().flip(),'source',(X2,6.8)); s.name(j2,'J2','l',x=X2)
s.w((X1,7.4),j1['source']); s.w((X2,7.4),j2['source'])
yg=j1['gate'][1]
s.w(j1['gate'],(1.3,yg)); s.dot((1.3,yg),open=True); s.lab((1.3,yg-0.35),'inn',h='center',v='top')
s.w(j2['gate'],(7.2,yg)); s.dot((7.2,yg),open=True); s.lab((7.2,yg-0.35),'inp',h='center',v='top')
# npn mirror Q3/Q4
q3=s.dev(NPN().reverse(),'collector',(X1,3.6)); s.name(q3,'Q3','l',x=X1)
q4=s.dev(NPN(),'collector',(X2,3.6)); s.name(q4,'Q4','r',x=X2)
s.w(q3['base'],q4['base']); s.dot((XT,q3['base'][1]))
s.w((XT,q3['base'][1]),(XT,4.2),(X1,4.2)); s.dot((X1,4.2))
s.w(j1['drain'],q3['collector']); s.w(j2['drain'],q4['collector'])
s.w(q3['emitter'],(X1,VEE)); s.w(q4['emitter'],(X2,VEE))
# second stage Q5 with Miller capacitor
yd2=4.6
s.dot((X2,yd2)); s.lab((X2+0.2,yd2+0.15),'d2',v='bottom',size=10,color='#666')
q5=s.dev(NPN(),'base',(XS-0.75,yd2)); s.name(q5,'Q5','r',x=XS)
s.w((X2,yd2),q5['base']); s.dot((XC,yd2))
s.w(q5['emitter'],(XS,VEE))
yo2=7.0
s.two(elm.Capacitor,(XC,yd2),(XC,yo2),label='Cc\n15p')
s.w((XC,yo2),(XS,yo2)); s.w(q5['collector'],(XS,yo2)); s.dot((XS,yo2))
s.lab((XS+0.2,yo2-0.15),'o2',v='top',size=10,color='#666')
# class-AB bias diodes and current-source load Q12
yot=9.8
s.two(elm.Diode,(XS,yot),(XS,8.4),label='D1',loc='lft'); s.two(elm.Diode,(XS,8.4),(XS,yo2),label='D2',loc='lft')
s.dot((XS,yot))
q12=s.dev(PNP(),'collector',(XS,10.6)); s.name(q12,'Q12','r',x=XS)
s.w(q12['collector'],(XS,yot))
s.two(elm.Resistor,q12['emitter'],(XS,VCC),label='R12\n400')
# separate bias for Q12
q13=s.dev(PNP().reverse(),'collector',(XQ13,10.6)); s.name(q13,'Q13','l',x=XQ13)
s.two(elm.Resistor,q13['emitter'],(XQ13,VCC),label='R13\n2k',loc='lft')
s.w(q13['base'],q12['base']); s.dot((XL13,q13['base'][1]))
s.w((XL13,q13['base'][1]),(XL13,10.1),(XQ13,10.1)); s.dot((XQ13,10.1))
s.w(q13['collector'],(XQ13,10.1))
s.two(elm.SourceI,(XQ13,10.1),(XQ13,8.2),label='Ib2\n200 µA')
s.at(elm.Vss(),(XQ13,8.2)); s.lab((XQ13+0.3,7.75),'vee',size=10)
# output stage
q7=s.dev(NPN(),'base',(XO-0.75,yot)); s.name(q7,'Q7','r',x=XO)
s.w((XS,yot),q7['base'])
q8=s.dev(PNP(),'emitter',(XO,6.2)); s.name(q8,'Q8','r',x=XO)
s.w((XS,yo2),(XJ,yo2),(XJ,q8['base'][1]),q8['base'])
s.w(q7['collector'],(XO,VCC)); s.w(q8['collector'],(XO,VEE))
yout=(q7['emitter'][1]+6.2)/2
s.two(elm.Resistor,q7['emitter'],(XO,yout),label='R7\n25'); s.two(elm.Resistor,(XO,6.2),(XO,yout),label='R8\n25')
s.dot((XO,yout)); s.w((XO,yout),(XOUT,yout)); s.dot((XOUT,yout),open=True); s.lab((XOUT+0.25,yout),'out')
# rails
s.w((XB,VCC),(XO,VCC)); s.w((XB,VEE),(XO,VEE))
for x in (XT,XQ13,XS): s.dot((x,VCC))
for x in (X1,X2,XS): s.dot((x,VEE))
s.supplies(XB,VCC,VEE,'15')
s.lab((-4.25,15.5),'B — JFET op amp with a p-JFET input pair (TL071-like input stage)',size=13)
s.lab((-4.25,-1.0),'Q7, Q8: area 10; Q12: area 5.  Phase reversal at the bottom: when inp < vee + 0.13 V the J2 gate–drain junction conducts.',size=10,color='#444',v='top')
s.save(os.path.join(HERE, 'B_pjfet.png')); s.save(os.path.join(HERE, 'B_pjfet.svg'))
