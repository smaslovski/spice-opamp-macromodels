#!/usr/bin/env python3
# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
"""Characterization decks of the model-to-params skill.

    python3 tools/make_char_decks.py

Writes the complete example decks to skills/model-to-params/decks/<simulator>/
and copies the deck sections into skills/model-to-params/SKILL.md (between the
<!-- BEGIN name --> and <!-- END name --> markers), so that the skill text and
the files never differ.

There are three decks: AC (open-loop gain and phase, CMRR, PSRR, input and
output impedance), FAST (DC errors, supply current, slew rates, overshoot,
swing, output current limit, reversal slope, input clamp) and SLOW (input
common-mode range and phase reversal, with slow ramps near each rail). Each
deck is one header (filled in by the assistant), one circuit (the same for all
simulators) and one measurement block per simulator:
ngspice (.control with meas), LTspice (.meas), PSpice (.PRINT tables).
"""
import os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SKILL = os.path.join(ROOT, 'skills', 'model-to-params')
REV = '1.3'

HEADER = """\
* {part} characterization deck {kind} (model-to-params skill rev {rev})
{include}
* the part, with the pins in the order inp inn vcc vee out
.subckt DUT inp inn vcc vee out
{xline}
.ends DUT
* operating condition (datasheet): supplies, input common-mode voltage, load
.param VCC={VCC} VEE={VEE} VCM={VCM} RL={RL}
* nominal values from the datasheet; they set time scales and test levels only
.param GBWN={GBWN} SRN={SRN} VSTEP={VSTEP} VSS={VSS} OVR={OVR} W={W} ILOAD={ILOAD}
* derived (do not edit)
.param TS={{4*VSTEP/SRN+5/GBWN}} TR={{(W+OVR)*1e4/SRN+1e4/GBWN}}
.param VSH={{min(1,0.2*(VCC-VEE))}} VCL={{min(1.5,0.9*(VCC-VCM))}}
"""

# ---- circuits (identical in all simulators) ---------------------------------
AC = """\
Vcc vcc 0 {VCC}
Vee vee 0 {VEE}
Vmid mid 0 {VCM}
* Every instance is a follower at DC: an E source drives the - input from a
* low-pass copy (1e18 ohm, 1 F: corner 2e-19 Hz) of the output. At the analysis
* frequencies (1 mHz and up) the low-pass output is zero and the loop is open.
* (No giant L and C: their admittance would swamp the tiny currents of CMOS inputs.)
* 1: open-loop differential gain; the inputs get +0.5 V and -0.5 V AC
Va1 a1 mid AC 0.5
X1 a1 n1 vcc vee o1 DUT
Ed1 d1 0 o1 mid 1
Rd1 d1 s1 1e18
Cd1 s1 0 1
E1 n1x mid s1 0 1
Vb1 n1 n1x AC 0.5 180
R1 o1 mid {RL}
* 2: common-mode gain (the - input follows the + input at AC)
Va2 a2 mid AC 1
X2 a2 n2 vcc vee o2 DUT
Ed2 d2 0 o2 a2 1
Rd2 d2 s2 1e18
Cd2 s2 0 1
Ec2 c2 0 a2 0 1
E2 n2 c2 s2 0 1
R2 o2 mid {RL}
* 3, 4: positive and negative supply gain
Vcc3 vcc3 0 {VCC} AC 1
X3 mid n3 vcc3 vee o3 DUT
Ed3 d3 0 o3 mid 1
Rd3 d3 s3 1e18
Cd3 s3 0 1
E3 n3 mid s3 0 1
R3 o3 mid {RL}
Vee4 vee4 0 {VEE} AC 1
X4 mid n4 vcc vee4 o4 DUT
Ed4 d4 0 o4 mid 1
Rd4 d4 s4 1e18
Cd4 s4 0 1
E4 n4 mid s4 0 1
R4 o4 mid {RL}
* 5: open-loop output impedance, at a DC load current ILOAD (sourced)
X5 mid n5 vcc vee o5 DUT
Ed5 d5 0 o5 mid 1
Rd5 d5 s5 1e18
Cd5 s5 0 1
E5 n5 mid s5 0 1
I5 o5 mid DC {ILOAD} AC 1
* 8: open-loop differential gain without load (with 1: the DC output resistance)
Va8 a8 mid AC 0.5
X8 a8 n8 vcc vee o8 DUT
Ed8 d8 0 o8 mid 1
Rd8 d8 s8 1e18
Cd8 s8 0 1
E8 n8x mid s8 0 1
Vb8 n8 n8x AC 0.5 180
* 6, 7: input impedance. The + pin is fed by an AC current of 1 A; its DC bias
*    comes from Gb6 (Gb7), a 1 mS conductance to VCM through the same low-pass.
* 6: - pin at VCM for AC: the + pin sees the differential and its own
*    common-mode impedance
X6 p6 n6 vcc vee o6 DUT
Ed6 d6 0 o6 mid 1
Rd6 d6 s6 1e18
Cd6 s6 0 1
E6 n6 mid s6 0 1
Eb6 b6 0 p6 mid 1
Rb6 b6 sb6 1e18
Cb6 sb6 0 1
Gb6 p6 mid sb6 0 1m
I6 mid p6 AC 1
R6 o6 mid {RL}
* 7: - pin follows the + pin for AC: the + pin sees its common-mode impedance only
X7 p7 n7 vcc vee o7 DUT
Ed7 d7 0 o7 p7 1
Rd7 d7 s7 1e18
Cd7 s7 0 1
Ec7 c7 0 p7 0 1
E7 n7 c7 s7 0 1
Eb7 b7 0 p7 mid 1
Rb7 b7 sb7 1e18
Cb7 sb7 0 1
Gb7 p7 mid sb7 0 1m
I7 mid p7 AC 1
R7 o7 mid {RL}
"""

FAST = """\
Vcc vcc 0 {VCC}
Vee vee 0 {VEE}
Vmid mid 0 {VCM}
* 1: follower at VCM, own supplies, no load: offset, bias currents, supply current
Vcc1 vcc1 0 {VCC}
Vee1 vee1 0 {VEE}
Vp1 mid p1 0
Vn1 o1 n1 0
X1 p1 n1 vcc1 vee1 o1 DUT
* 2: large step VCM-VSTEP/2 -> VCM+VSTEP/2 at TS and back at 3*TS: slew rates in
*    an inverter (G = -1, 10 kohm), where input clamp diodes carry little current,
*    and the follower jump in a follower
Vin2 in2 0 PULSE({VCM-VSTEP/2} {VCM+VSTEP/2} {TS} {TS/1000} {TS/1000} {2*TS} {10*TS})
X2 in2 o2 vcc vee o2 DUT
R2 o2 mid {RL}
Rg2 in2 s2 10k
Rf2 s2 o2i 10k
X2i mid s2 vcc vee o2i DUT
R2i o2i mid {RL}
* 3: follower, small step of VSS
Vin3 in3 0 PULSE({VCM-VSS/2} {VCM+VSS/2} {TS} {TS/1000} {TS/1000} {2*TS} {10*TS})
X3 in3 o3 vcc vee o3 DUT
R3 o3 mid {RL}
* 4, 5, 6: open loop, overdriven by +0.5 V, then -0.5 V from 2.5*TS:
*    swing into RL (4), unloaded (5), and the output current into a short to VCM (6)
Vd4 d4 mid PULSE(0.5 -0.5 {2.5*TS} {TS/100} {TS/100} {10*TS} {20*TS})
X4 d4 mid vcc vee o4 DUT
R4 o4 mid {RL}
X5 d4 mid vcc vee o5 DUT
X6 d4 mid vcc vee o6 DUT
V6 o6 mid 0
* 7, 8: follower stepped from VCM to OVR beyond the top (7) and bottom (8) rail at TS
Vin7 in7 0 PULSE({VCM} {VCC+OVR} {TS} {TS/1000} {TS/1000} {2*TS} {10*TS})
X7 in7 o7 vcc vee o7 DUT
R7 o7 mid {RL}
Vin8 in8 0 PULSE({VCM} {VEE-OVR} {TS} {TS/1000} {TS/1000} {2*TS} {10*TS})
X8 in8 o8 vcc vee o8 DUT
R8 o8 mid {RL}
* 9, 10: VCL between the inputs through 100 ohm (9) and 1 kohm (10): input clamp
Vc9 c9 mid {VCL}
R9 c9 p9 100
X9 p9 mid vcc vee o9 DUT
R10 c9 p10 1k
X10 p10 mid vcc vee o10 DUT
"""

SLOW = """\
Vcc vcc 0 {VCC}
Vee vee 0 {VEE}
Vmid mid 0 {VCM}
* Pairs of instances whose outputs an ideal level shifter holds at VCM+VSH (a)
* and VCM-VSH (b) while both inputs sit at the input voltage: the difference of
* their differential inputs is 2*VSH/gain, so its ratio to the value at VCM
* gives the relative gain of the input stage at that common-mode voltage.
* m: at VCM
Xam pam nam vcc vee oam DUT
Vam pam mid 0
Eam nam oam vshm 0 1
Xbm pbm nbm vcc vee obm DUT
Vbm pbm mid 0
Ebm nbm obm vshp 0 1
Vshp vshp 0 {VSH}
Vshm vshm 0 {-VSH}
* t: slow ramp from VCC-W to VCC+OVR
Vint int 0 PWL(0 {VCC-W} {TR} {VCC+OVR})
Xat pat nat vcc vee oat DUT
Vat int pat 0
Eat nat oat int mshp 1
Xbt pbt nbt vcc vee obt DUT
Vbt int pbt 0
Ebt nbt obt int mshm 1
Vmshp mshp 0 {VCM+VSH}
Vmshm mshm 0 {VCM-VSH}
* b: slow ramp from VEE+W to VEE-OVR
Vinb inb 0 PWL(0 {VEE+W} {TR} {VEE-OVR})
Xab pab nab vcc vee oab DUT
Vab inb pab 0
Eab nab oab inb mshp 1
Xbb pbb nbb vcc vee obb DUT
Vbb inb pbb 0
Ebb nbb obb inb mshm 1
* followers into RL on the same ramps: tracking error, reversal, input current
Vft int pft 0
Xft pft oft vcc vee oft DUT
Rft oft mid {RL}
Vfb inb pfb 0
Xfb pfb ofb vcc vee ofb DUT
Rfb ofb mid {RL}
"""

# ---- measurement blocks --------------------------------------------------------
# ngspice: .csparam exports the parameters to the .control section
NG_AC = """\
.csparam gbwn={GBWN}
.control
set noaskquit
ac dec 20 1m 100G
let ag = vdb(o1)
let ph = 180/pi*cph(v(o1))
meas ac a0_db find ag at=1m
meas ac a0u_db find vdb(o8) at=1m
meas ac fu when ag=0
meas ac ph_fu find ph when ag=0
meas ac f40 when ag=40
meas ac f20 when ag=20
let cmr = vdb(o1)-vdb(o2)
let psp = vdb(o1)-vdb(o3)
let psn = vdb(o1)-vdb(o4)
meas ac cmrr_db find cmr at=1m
let x3 = cmrr_db-3
let x20 = cmrr_db-20
meas ac fcm3 when cmr=$&x3 fall=1
meas ac fcm20 when cmr=$&x20 fall=1
meas ac cmrr_gbw find cmr at=$&gbwn
meas ac psrrp_db find psp at=1m
let x3 = psrrp_db-3
let x20 = psrrp_db-20
meas ac fpsp3 when psp=$&x3 fall=1
meas ac fpsp20 when psp=$&x20 fall=1
meas ac psrrn_db find psn at=1m
let x3 = psrrn_db-3
let x20 = psrrn_db-20
meas ac fpsn3 when psn=$&x3 fall=1
meas ac fpsn20 when psn=$&x20 fall=1
let cmsg = real(v(o2)/v(o1))
let pssp = real(v(o3)/v(o1))
let pssn = real(v(o4)/v(o1))
meas ac cmrr_sg find cmsg at=1m
meas ac psrrp_sg find pssp at=1m
meas ac psrrn_sg find pssn at=1m
let fz1 = gbwn/100
let fz2 = gbwn/10
meas ac zo_dc find vm(o5) at=1m
meas ac zo_a find vm(o5) at=$&fz1
meas ac zo_b find vm(o5) at=$&fz2
meas ac zo_c find vm(o5) at=$&gbwn
meas ac zd_re0 find vr(p6) at=1m
meas ac zd_im0 find vi(p6) at=1m
meas ac zd_re find vr(p6) at=$&fz2
meas ac zd_im find vi(p6) at=$&fz2
meas ac zc_re0 find vr(p7) at=1m
meas ac zc_im0 find vi(p7) at=1m
meas ac zc_re find vr(p7) at=$&fz2
meas ac zc_im find vi(p7) at=$&fz2
print gbwn
.endc
"""

NG_FAST = """\
.csparam xvcc={VCC} xvee={VEE} xvcm={VCM} rl={RL} ts={TS} vstep={VSTEP} vss={VSS} ovr={OVR} vcl={VCL}
.control
set noaskquit
let tmax = ts/500
let tstop = 5*ts
tran $&tmax $&tstop 0 $&tmax
let a = 0.5*ts
let b = 0.9*ts
let vo1 = v(o1)-v(mid)
meas tran vos avg vo1 from=$&a to=$&b
meas tran ibp avg i(vp1) from=$&a to=$&b
meas tran ibn avg i(vn1) from=$&a to=$&b
let iqv = -i(vcc1)
meas tran iq avg iqv from=$&a to=$&b
let l50 = xvcm
let l85r = xvcm+0.35*vstep
let l85f = xvcm-0.35*vstep
meas tran t50r when v(o2)=$&l50 rise=1
meas tran t85r when v(o2)=$&l85r rise=1
let tdf = 2*ts
meas tran t50f when v(o2)=$&l50 fall=1 td=$&tdf
meas tran t85f when v(o2)=$&l85f fall=1 td=$&tdf
meas tran t50fi when v(o2i)=$&l50 fall=1
meas tran t85fi when v(o2i)=$&l85f fall=1
meas tran t50ri when v(o2i)=$&l50 rise=1 td=$&tdf
meas tran t85ri when v(o2i)=$&l85r rise=1 td=$&tdf
let c = 2.5*ts
let d = 2.9*ts
let e = 4.5*ts
let f = 4.9*ts
let g = 3*ts
meas tran vo2_lo avg v(o2) from=$&a to=$&b
meas tran vo2_hi avg v(o2) from=$&c to=$&d
let tj = 1.011*ts
meas tran vj_r find v(o2) at=$&tj
let tj = 3.012*ts
meas tran vj_f find v(o2) at=$&tj
meas tran ss_lo avg v(o3) from=$&a to=$&b
meas tran ss_hi avg v(o3) from=$&c to=$&d
meas tran ss_max max v(o3) from=$&ts to=$&g
meas tran ss_min min v(o3) from=$&g to=$&tstop
let c = 2*ts
let d = 2.4*ts
meas tran voh_rl avg v(o4) from=$&c to=$&d
meas tran vol_rl avg v(o4) from=$&e to=$&f
meas tran voh_nl avg v(o5) from=$&c to=$&d
meas tran vol_nl avg v(o5) from=$&e to=$&f
meas tran isrc avg i(v6) from=$&c to=$&d
meas tran isnk avg i(v6) from=$&e to=$&f
let l1 = xvcm-0.2*(xvcm-xvee)
let l2 = xvcm-0.6*(xvcm-xvee)
meas tran rt_t1 when v(o7)=$&l1 fall=1
meas tran rt_t2 when v(o7)=$&l2 fall=1
let d = 2.9*ts
meas tran rt_end find v(o7) at=$&d
let l1 = xvcm+0.2*(xvcc-xvcm)
let l2 = xvcm+0.6*(xvcc-xvcm)
meas tran rb_t1 when v(o8)=$&l1 rise=1
meas tran rb_t2 when v(o8)=$&l2 rise=1
meas tran rb_end find v(o8) at=$&d
let v9 = v(p9)-v(mid)
let i9 = (v(c9)-v(p9))/100
let v10 = v(p10)-v(mid)
let i10 = (v(c9)-v(p10))/1000
meas tran vcl1 avg v9 from=$&a to=$&b
meas tran icl1 avg i9 from=$&a to=$&b
meas tran vcl2 avg v10 from=$&a to=$&b
meas tran icl2 avg i10 from=$&a to=$&b
print xvcc
print xvee
print xvcm
print rl
print ts
print vstep
print vss
print ovr
print vcl
.endc
"""

NG_SLOW = """\
.csparam xvcc={VCC} xvee={VEE} xvcm={VCM} rl={RL} tr={TR} w={W} ovr={OVR} vsh={VSH}
.control
set noaskquit
let tmax = tr/4000
tran $&tmax $&tr 0 $&tmax
let dm = v(pam)-v(nam)-v(pbm)+v(nbm)
let dt = v(pat)-v(nat)-v(pbt)+v(nbt)
let db = v(pab)-v(nab)-v(pbb)+v(nbb)
meas tran dmid avg dm from=0 to=$&tr
let q5t = dt-2*dm
let qqt = dt-4*dm
let q5b = db-2*dm
let qqb = db-4*dm
meas tran dt0 find dt at=0
meas tran db0 find db at=0
meas tran vw5t find v(int) when q5t=0 rise=1
meas tran vwqt find v(int) when qqt=0 rise=1
meas tran vw5b find v(inb) when q5b=0 rise=1
meas tran vwqb find v(inb) when qqb=0 rise=1
let eft = v(int)-v(oft)
let efb = v(inb)-v(ofb)
meas tran eft0 find eft at=0
meas tran efb0 find efb at=0
let l = eft0+0.01
meas tran vf1t find v(int) when eft=$&l rise=1
meas tran of1t find v(oft) when eft=$&l rise=1
let l = eft0+0.1
meas tran vf2t find v(int) when eft=$&l rise=1
meas tran of2t find v(oft) when eft=$&l rise=1
let l = efb0-0.01
meas tran vf1b find v(inb) when efb=$&l fall=1
meas tran of1b find v(ofb) when efb=$&l fall=1
let l = efb0-0.1
meas tran vf2b find v(inb) when efb=$&l fall=1
meas tran of2b find v(ofb) when efb=$&l fall=1
meas tran vstopt max v(oft) from=0 to=$&tr
meas tran vendt find v(oft) at=$&tr
meas tran it0 find i(vft) at=0
meas tran iendt find i(vft) at=$&tr
let lit = it0+0.9*(iendt-it0)
meas tran vipt find v(int) when i(vft)=$&lit rise=1
let lft = vstopt-0.05*(vstopt-xvcm)
meas tran vflt find v(int) when v(oft)=$&lft fall=1
meas tran iflt find i(vft) when v(oft)=$&lft fall=1
meas tran vstopb min v(ofb) from=0 to=$&tr
meas tran vendb find v(ofb) at=$&tr
meas tran ib0 find i(vfb) at=0
meas tran iendb find i(vfb) at=$&tr
let lib = ib0+0.9*(iendb-ib0)
meas tran vipb find v(inb) when i(vfb)=$&lib fall=1
let lfb = vstopb+0.05*(xvcm-vstopb)
meas tran vflb find v(inb) when v(ofb)=$&lfb rise=1
meas tran iflb find i(vfb) when v(ofb)=$&lfb rise=1
print xvcc
print xvee
print xvcm
print rl
print tr
print w
print ovr
print vsh
.endc
"""

# LTspice: AC results are printed as (dB,degrees); a measurement can use earlier ones
LT_AC = """\
.ac dec 20 1m 100G
.meas ac a0_db find mag(V(o1)) at=1m
.meas ac a0u_db find mag(V(o8)) at=1m
.meas ac fu when mag(V(o1))=1
.meas ac ph_fu find V(o1) when mag(V(o1))=1
.meas ac f40 when mag(V(o1))=100
.meas ac f20 when mag(V(o1))=10
.meas ac cmrr_db find mag(V(o1)/V(o2)) at=1m
.meas ac fcm3 when mag(V(o1)/V(o2))=cmrr_db/sqrt(2) fall=1
.meas ac fcm20 when mag(V(o1)/V(o2))=cmrr_db/10 fall=1
.meas ac cmrr_gbw find mag(V(o1)/V(o2)) at={GBWN}
.meas ac psrrp_db find mag(V(o1)/V(o3)) at=1m
.meas ac fpsp3 when mag(V(o1)/V(o3))=psrrp_db/sqrt(2) fall=1
.meas ac fpsp20 when mag(V(o1)/V(o3))=psrrp_db/10 fall=1
.meas ac psrrn_db find mag(V(o1)/V(o4)) at=1m
.meas ac fpsn3 when mag(V(o1)/V(o4))=psrrn_db/sqrt(2) fall=1
.meas ac fpsn20 when mag(V(o1)/V(o4))=psrrn_db/10 fall=1
.meas ac cmrr_sg find re(V(o2)/V(o1)) at=1m
.meas ac psrrp_sg find re(V(o3)/V(o1)) at=1m
.meas ac psrrn_sg find re(V(o4)/V(o1)) at=1m
.meas ac zo_dc find mag(V(o5)) at=1m
.meas ac zo_a find mag(V(o5)) at={GBWN/100}
.meas ac zo_b find mag(V(o5)) at={GBWN/10}
.meas ac zo_c find mag(V(o5)) at={GBWN}
.meas ac zd_re0 find re(V(p6)) at=1m
.meas ac zd_im0 find im(V(p6)) at=1m
.meas ac zd_re find re(V(p6)) at={GBWN/10}
.meas ac zd_im find im(V(p6)) at={GBWN/10}
.meas ac zc_re0 find re(V(p7)) at=1m
.meas ac zc_im0 find im(V(p7)) at=1m
.meas ac zc_re find re(V(p7)) at={GBWN/10}
.meas ac zc_im find im(V(p7)) at={GBWN/10}
.meas ac gbwn param {GBWN}
"""

LT_FAST = """\
.options plotwinsize=0
.tran 0 {5*TS} 0 {TS/500}
.meas tran vos avg V(o1)-V(mid) from={0.5*TS} to={0.9*TS}
.meas tran ibp avg I(Vp1) from={0.5*TS} to={0.9*TS}
.meas tran ibn avg I(Vn1) from={0.5*TS} to={0.9*TS}
.meas tran iq avg -I(Vcc1) from={0.5*TS} to={0.9*TS}
.meas tran t50r when V(o2)={VCM} rise=1
.meas tran t85r when V(o2)={VCM+0.35*VSTEP} rise=1
.meas tran t50f when V(o2)={VCM} td={2*TS} fall=1
.meas tran t85f when V(o2)={VCM-0.35*VSTEP} td={2*TS} fall=1
.meas tran t50fi when V(o2i)={VCM} fall=1
.meas tran t85fi when V(o2i)={VCM-0.35*VSTEP} fall=1
.meas tran t50ri when V(o2i)={VCM} td={2*TS} rise=1
.meas tran t85ri when V(o2i)={VCM+0.35*VSTEP} td={2*TS} rise=1
.meas tran vo2_lo avg V(o2) from={0.5*TS} to={0.9*TS}
.meas tran vo2_hi avg V(o2) from={2.5*TS} to={2.9*TS}
.meas tran vj_r find V(o2) at={1.011*TS}
.meas tran vj_f find V(o2) at={3.012*TS}
.meas tran ss_lo avg V(o3) from={0.5*TS} to={0.9*TS}
.meas tran ss_hi avg V(o3) from={2.5*TS} to={2.9*TS}
.meas tran ss_max max V(o3) from={TS} to={3*TS}
.meas tran ss_min min V(o3) from={3*TS} to={5*TS}
.meas tran voh_rl avg V(o4) from={2*TS} to={2.4*TS}
.meas tran vol_rl avg V(o4) from={4.5*TS} to={4.9*TS}
.meas tran voh_nl avg V(o5) from={2*TS} to={2.4*TS}
.meas tran vol_nl avg V(o5) from={4.5*TS} to={4.9*TS}
.meas tran isrc avg I(V6) from={2*TS} to={2.4*TS}
.meas tran isnk avg I(V6) from={4.5*TS} to={4.9*TS}
.meas tran rt_t1 when V(o7)={VCM-0.2*(VCM-VEE)} fall=1
.meas tran rt_t2 when V(o7)={VCM-0.6*(VCM-VEE)} fall=1
.meas tran rt_end find V(o7) at={2.9*TS}
.meas tran rb_t1 when V(o8)={VCM+0.2*(VCC-VCM)} rise=1
.meas tran rb_t2 when V(o8)={VCM+0.6*(VCC-VCM)} rise=1
.meas tran rb_end find V(o8) at={2.9*TS}
.meas tran vcl1 avg V(p9)-V(mid) from={0.5*TS} to={0.9*TS}
.meas tran icl1 avg (V(c9)-V(p9))/100 from={0.5*TS} to={0.9*TS}
.meas tran vcl2 avg V(p10)-V(mid) from={0.5*TS} to={0.9*TS}
.meas tran icl2 avg (V(c9)-V(p10))/1000 from={0.5*TS} to={0.9*TS}
.meas tran vcc param {VCC}
.meas tran vee param {VEE}
.meas tran vcm param {VCM}
.meas tran rl param {RL}
.meas tran ts param {TS}
.meas tran vstep param {VSTEP}
.meas tran vss param {VSS}
.meas tran ovr param {OVR}
.meas tran vcl param {VCL}
"""

LT_SLOW = """\
.options plotwinsize=0
.tran 0 {TR} 0 {TR/4000}
.meas tran dmid avg V(pam)-V(nam)-V(pbm)+V(nbm) from=0 to={TR}
.meas tran dt0 find V(pat)-V(nat)-V(pbt)+V(nbt) at=0
.meas tran db0 find V(pab)-V(nab)-V(pbb)+V(nbb) at=0
.meas tran vw5t find V(int) when V(pat)-V(nat)-V(pbt)+V(nbt)=2*dmid rise=1
.meas tran vwqt find V(int) when V(pat)-V(nat)-V(pbt)+V(nbt)=4*dmid rise=1
.meas tran vw5b find V(inb) when V(pab)-V(nab)-V(pbb)+V(nbb)=2*dmid rise=1
.meas tran vwqb find V(inb) when V(pab)-V(nab)-V(pbb)+V(nbb)=4*dmid rise=1
.meas tran eft0 find V(int)-V(oft) at=0
.meas tran efb0 find V(inb)-V(ofb) at=0
.meas tran vf1t find V(int) when V(int)-V(oft)=eft0+0.01 rise=1
.meas tran of1t find V(oft) when V(int)-V(oft)=eft0+0.01 rise=1
.meas tran vf2t find V(int) when V(int)-V(oft)=eft0+0.1 rise=1
.meas tran of2t find V(oft) when V(int)-V(oft)=eft0+0.1 rise=1
.meas tran vf1b find V(inb) when V(inb)-V(ofb)=efb0-0.01 fall=1
.meas tran of1b find V(ofb) when V(inb)-V(ofb)=efb0-0.01 fall=1
.meas tran vf2b find V(inb) when V(inb)-V(ofb)=efb0-0.1 fall=1
.meas tran of2b find V(ofb) when V(inb)-V(ofb)=efb0-0.1 fall=1
.meas tran vstopt max V(oft) from=0 to={TR}
.meas tran vendt find V(oft) at={TR}
.meas tran it0 find I(Vft) at=0
.meas tran iendt find I(Vft) at={TR}
.meas tran vipt find V(int) when I(Vft)=it0+0.9*(iendt-it0) rise=1
.meas tran vflt find V(int) when V(oft)=vstopt-0.05*(vstopt-{VCM}) fall=1
.meas tran iflt find I(Vft) when V(oft)=vstopt-0.05*(vstopt-{VCM}) fall=1
.meas tran vstopb min V(ofb) from=0 to={TR}
.meas tran vendb find V(ofb) at={TR}
.meas tran ib0 find I(Vfb) at=0
.meas tran iendb find I(Vfb) at={TR}
.meas tran vipb find V(inb) when I(Vfb)=ib0+0.9*(iendb-ib0) fall=1
.meas tran vflb find V(inb) when V(ofb)=vstopb+0.05*({VCM}-vstopb) rise=1
.meas tran iflb find I(Vfb) when V(ofb)=vstopb+0.05*({VCM}-vstopb) rise=1
.meas tran vcc param {VCC}
.meas tran vee param {VEE}
.meas tran vcm param {VCM}
.meas tran rl param {RL}
.meas tran tr param {TR}
.meas tran w param {W}
.meas tran ovr param {OVR}
.meas tran vsh param {VSH}
"""

# PSpice: no .meas in the netlist; the tables in the .out file are read instead.
PS_AC = """\
.OPTIONS NUMDGT=8 NOPAGE
.AC DEC 10 1m 100G
.PRINT AC VDB(o1) VP(o1) VDB(o2) VDB(o3) VDB(o4) VDB(o8)
.PRINT AC VP(o2) VP(o3) VP(o4)
.PRINT AC VM(o5) VR(p6) VI(p6) VR(p7) VI(p7)
"""

PS_FAST = """\
.OPTIONS NUMDGT=8 NOPAGE
.TRAN {TS/100} {5*TS} 0 {TS/500}
.PRINT TRAN V(o1,mid) I(Vp1) I(Vn1) I(Vcc1) V(o2) V(o2i) V(o3)
.PRINT TRAN V(o4) V(o5) I(V6) V(o7) V(o8)
.PRINT TRAN V(p9,mid) V(c9,p9) V(p10,mid) V(c9,p10)
"""

PS_SLOW = """\
.OPTIONS NUMDGT=8 NOPAGE
.TRAN {TR/400} {TR} 0 {TR/4000}
.PRINT TRAN V(int) V(pam,nam) V(pbm,nbm) V(pat,nat) V(pbt,nbt) V(oft) I(Vft)
.PRINT TRAN V(inb) V(pab,nab) V(pbb,nbb) V(ofb) I(Vfb)
"""

CIRCUITS = {'ac': AC, 'fast': FAST, 'slow': SLOW}
MEAS = {
    'ngspice': {'ac': NG_AC, 'fast': NG_FAST, 'slow': NG_SLOW},
    'ltspice': {'ac': LT_AC, 'fast': LT_FAST, 'slow': LT_SLOW},
    'pspice': {'ac': PS_AC, 'fast': PS_FAST, 'slow': PS_SLOW},
}

EXAMPLE = dict(part='<PART>', include='.include <vendor model file>',
               xline='XV inp inn vcc vee out <VENDOR_SUBCKT>',
               VCC=15, VEE=-15, VCM=0, RL='10k', GBWN='1Meg', SRN='0.5Meg',
               VSTEP=10, VSS='50m', OVR=0.2, W=3, ILOAD='1m')


def deck(sim, kind, **h):
    """A complete deck. h: the header fields of EXAMPLE."""
    hh = dict(EXAMPLE, **h)
    if sim == 'pspice':
        hh['include'] = hh['include'].replace('.include', '.LIB')
    return (HEADER.format(kind=kind.upper(), rev=REV, **hh) + '\n' + CIRCUITS[kind] + '\n'
            + MEAS[sim][kind] + '.end\n')


def main():
    for sim in MEAS:
        d = os.path.join(SKILL, 'decks', sim)
        os.makedirs(d, exist_ok=True)
        for kind in CIRCUITS:
            open(os.path.join(d, f'char_{kind}.cir'), 'w').write(deck(sim, kind))
    sk = os.path.join(SKILL, 'SKILL.md')
    if os.path.exists(sk):
        txt = open(sk).read()
        parts = {'header': HEADER.format(kind='<AC|FAST|SLOW>', rev=REV, **EXAMPLE)}
        for kind, c in CIRCUITS.items():
            parts[f'circuit_{kind}'] = c
            for sim in MEAS:
                parts[f'{sim}_{kind}'] = MEAS[sim][kind]
        for name, body in parts.items():
            txt = re.sub(rf'(<!-- BEGIN {name} -->\n```spice\n).*?(```\n<!-- END {name} -->)',
                         lambda m: m.group(1) + body + m.group(2), txt, flags=re.S)
        open(sk, 'w').write(txt)
    print('decks written to', os.path.relpath(os.path.join(SKILL, 'decks'), ROOT))


if __name__ == '__main__':
    main()
