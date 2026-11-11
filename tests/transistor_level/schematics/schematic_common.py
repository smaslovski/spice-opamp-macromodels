# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
# Shared helpers for the schematic drawing scripts (schemdraw).
import schemdraw, schemdraw.elements as elm
schemdraw.config(fontsize=11, lw=1.1)
# The drawing scripts place everything in layout units; P() converts them to drawing
# units. SPREAD > 1 would spread the layout while symbols and fonts keep their size
# (wires drawn to fixed coordinates then need adjusting); the drawings use 1.
SPREAD = 1.0
def P(p): return (p[0]*SPREAD, p[1]*SPREAD)
class S:
    def __init__(s):
        s.d=schemdraw.Drawing(show=False)
    def at(s, e, xy):   # place a one-terminal element (Vdd, Vss, ...) at a layout point
        return s.d.add(e.at(P(xy)))
    def dev(s, e, term, xy, label=None, loc='right', ofst=None):
        x=s.d.add(e.theta(0).at(P(xy)).anchor(term))
        a={k:(v[0]/SPREAD, v[1]/SPREAD) for k,v in x.absanchors.items()}
        if label:
            c=a['center']
            s.d.add(elm.Label().at(P((c[0]+(0.45 if loc=='right' else -0.45), c[1]+(ofst or 0)))).label(label, halign='left' if loc=='right' else 'right', fontsize=10))
        return {k:(float(v[0]),float(v[1])) for k,v in a.items()}
    def name(s, q, t, side='r', dy=0.0, x=None):
        """Label transistor q: beside its collector/emitter (drain/source) line."""
        cx = x if x is not None else q['center'][0]
        if side == 'r': s.lab((cx+0.35, q['center'][1]+dy), t, h='left', snap=False)
        else: s.lab((cx-0.35, q['center'][1]+dy), t, h='right', snap=False)
    def w(s, *pts, dots=()):
        for p,q in zip(pts,pts[1:]):
            s.d.add(elm.Line().at(P(p)).to(P(q)))
        for p in dots: s.d.add(elm.Dot().at(P(p)))
    def hv(s,p,q):  # horizontal then vertical
        s.w(p,(q[0],p[1]),q)
    def vh(s,p,q):
        s.w(p,(p[0],q[1]),q)
    def dot(s,p,open=False): s.d.add(elm.Dot(open=open).at(P(p)))
    def lab(s,p,t,h='left',v='center',size=11,color='black',snap=True):
        if snap: p=(round(p[0]*4)/4, round(p[1]*4)/4)   # 0.25-unit label grid
        s.d.add(elm.Label().theta(0).at(P(p)).label(t,halign=h,valign=v,fontsize=size,color=color))
    def supplies(s, xl, VCC, VEE, volts):
        # batteries left of the rails: +volts to vcc, -volts to vee, midpoint grounded
        xb=xl-3.25; mid=(VCC+VEE)/2
        s.w((xb,VCC),(xl,VCC)); s.w((xb,VEE),(xl,VEE)); s.dot((xl,VCC)); s.dot((xl,VEE))
        s.d.add(elm.Battery().theta(0).endpoints(P((xb,VCC-3.0)),P((xb,mid+1.0))))
        s.d.add(elm.Battery().theta(0).endpoints(P((xb,mid-1.0)),P((xb,VEE+3.0))))
        s.w((xb,VCC),(xb,VCC-3.0)); s.w((xb,mid+1.0),(xb,mid-1.0)); s.w((xb,VEE+3.0),(xb,VEE))
        s.dot((xb,mid)); s.w((xb,mid),(xb-0.75,mid)); s.d.add(elm.Ground().theta(0).at(P((xb-0.75,mid))))
        ym1=(VCC-3.0+mid+1.0)/2; ym2=(mid-1.0+VEE+3.0)/2
        for ym in (ym1,ym2):   # the long (+) plate sits 0.34 above the battery centre
            s.lab((xb+0.6,ym),f'{volts} V',snap=False)
            s.lab((xb-0.45,ym+0.34),'+',h='right',size=12,snap=False)
        s.lab((xb+0.25,VCC+0.25),'vcc',h='left',v='bottom'); s.lab((xb+0.25,VEE-0.25),'vee',h='left',v='top')
        return xb
    def two(s, cls, p, q, label=None, loc='rgt', **kw):
        e=s.d.add(cls(**kw).endpoints(P(p),P(q)))
        if label:
            mx,my=(p[0]+q[0])/2,(p[1]+q[1])/2
            if abs(p[0]-q[0])<0.1:   # vertical
                off=0.75 if cls is elm.SourceI else 0.5
                dx=off if loc=='rgt' else -off
                s.lab((mx+dx,my),label,h='left' if loc=='rgt' else 'right',size=10)
            else:
                dy=0.4 if loc!='bot' else -0.4
                s.lab((mx,my+dy),label,h='center',v='bottom' if loc!='bot' else 'top',size=10)
        return e
    def save(s,fn):
        s.d.save(fn, dpi=160)
