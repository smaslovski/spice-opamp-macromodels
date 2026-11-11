# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
# Draws schematic C_pmos (needs schemdraw >= 0.19): python3 draw_C_pmos.py
import os, sys; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from schematic_common import *
s=S(); d=s.d
VCC,VEE=14.0,0.0
# analog MOSFET symbols with a bulk arrow (out of the channel: p-MOS, into it: n-MOS);
# gate on the right, .reverse(): gate on the left
PF=lambda: elm.AnalogPFet(bulk=True, offset_gate=False)
NF=lambda: elm.AnalogNFet(bulk=True, offset_gate=False)
def strap(m):
    # tie the bulk to the source, on the side away from the gate
    xs, yb = m['bulk']; ys = m['source'][1]
    xo = xs + (0.4 if m['gate'][0] < xs else -0.4)
    s.w((xs, yb), (xo, yb), (xo, ys), m['source']); s.dot(m['source'])
XB,X1,XT,X2,XC,XS=-1.5,2.5,4.5,6.5,8.8,10.4
# bias Mb/Ib and tail M10
mb=s.dev(PF(),'source',(XB,12.4)); s.name(mb,'Mb\n20/2','l',x=XB-0.4)
yg=mb['gate'][1]
s.w(mb['gate'],(0.6,yg)); s.dot((0.6,yg))
s.w((0.6,yg),(0.6,10.4),(XB,10.4)); s.w(mb['drain'],(XB,10.4)); s.dot((XB,10.4))
s.two(elm.SourceI,(XB,10.4),(XB,VEE),label='Ib\n20 µA')
m10=s.dev(PF().reverse(),'source',(XT,12.4)); s.name(m10,'M10\n20/2','r',x=XT+0.4)
s.w((0.6,yg),m10['gate'])
s.w(m10['drain'],(XT,9.8)); s.w((X1,9.8),(X2,9.8)); s.dot((XT,9.8)); s.lab((XT+0.2,9.95),'t',v='bottom',size=10,color='#666')
# input pair M1/M2
m1=s.dev(PF().reverse(),'source',(X1,9.2)); s.name(m1,'M1\n40/1','r',x=X1+0.4)
m2=s.dev(PF(),'source',(X2,9.2)); s.name(m2,'M2\n40/1','l',x=X2-0.4)
s.w((X1,9.8),m1['source']); s.w((X2,9.8),m2['source'])
yi=m1['gate'][1]
s.w(m1['gate'],(0.6,yi)); s.dot((0.6,yi),open=True); s.lab((0.35,yi),'inn',h='right')
s.w(m2['gate'],(8.3,yi)); s.dot((8.3,yi),open=True); s.lab((8.3,yi-0.35),'inp',h='center',v='top')
# n-MOS mirror M3/M4
m3=s.dev(NF(),'drain',(X1,5.0)); s.name(m3,'M3\n10/2','l',x=X1-0.4)
m4=s.dev(NF().reverse(),'drain',(X2,5.0)); s.name(m4,'M4\n10/2','r',x=X2+0.4)
s.w(m3['gate'],m4['gate']); s.dot((XT,m3['gate'][1]))
s.w((XT,m3['gate'][1]),(XT,5.5),(X1,5.5)); s.dot((X1,5.5))
s.w(m1['drain'],m3['drain']); s.w(m2['drain'],m4['drain'])
s.w(m3['source'],(X1,VEE)); s.w(m4['source'],(X2,VEE))
# second stage M5 (load M6) with Miller capacitor
yd2=6.0
s.dot((X2,yd2)); s.lab((X2+0.2,yd2+0.15),'d2',v='bottom',size=10,color='#666')
m5=s.dev(NF().reverse(),'gate',(XS-0.92,yd2)); s.name(m5,'M5\n40/1','r',x=XS+0.4)
s.w((X2,yd2),m5['gate']); s.dot((XC,yd2))
yout=9.0
s.two(elm.Capacitor,(XC,yd2),(XC,yout),label='Cc\n3p')
m6=s.dev(PF().reverse(),'source',(XS,12.4)); s.name(m6,'M6\n100/2','r',x=XS+0.4)
s.dot((1.6,yg)); s.w((1.6,yg),(1.6,13.3),(8.3,13.3),(8.3,m6['gate'][1]),m6['gate'])
s.w(m6['drain'],m5['drain']); s.w((XC,yout),(XS,yout)); s.dot((XS,yout))
s.w((XS,yout),(12.0,yout)); s.dot((12.0,yout),open=True); s.lab((12.25,yout),'out')
s.w(m5['source'],(XS,VEE))
for m in (mb,m10,m1,m2,m3,m4,m5,m6): strap(m)
# rails
s.w((XB,VCC),(XS,VCC)); s.w((XB,VEE),(XS,VEE))
for p in (mb,m10,m6): s.w(p['source'],(p['source'][0],VCC))
s.dot((XT,VCC))
for x in (X1,X2): s.dot((x,VEE))
s.supplies(XB,VCC,VEE,'2.5')
s.lab((-5.0,15.5),'C — CMOS two-stage op amp with a p-MOS input pair',size=13)
s.lab((-5.0,-1.0),'W/L in µm. Each bulk is tied to its source.  No phase reversal:\nnear vcc − 0.7 V the tail M10 leaves saturation; a follower output stops there (1.80 V, light load).',size=10,color='#444',v='top')
s.save(os.path.join(HERE, 'C_pmos.png')); s.save(os.path.join(HERE, 'C_pmos.svg'))
