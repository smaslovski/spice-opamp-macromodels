---
name: model-to-params
description: Characterize a vendor op-amp SPICE model (ngspice, LTspice or PSpice) and convert the results into OPAMP_FULL macromodel parameters (spice-opamp-macromodels), with the measurement behind every value.
---

# Vendor SPICE model → OPAMP_FULL parameters

This file is a self-contained instruction set. Give it to any capable AI assistant
(as a skill, a system prompt or the first message). It does not depend on a
particular vendor of AI, and the assistant does not need to run anything: the
user runs three small simulation decks once, in their own simulator, and pastes
or attaches the output.

The target is the macromodel `OPAMP_FULL` from the `spice-opamp-macromodels`
repository (BSD-2-Clause, © 2026 Stanislav Maslovski), for ngspice, LTspice and
PSpice. The source is a vendor's SPICE model of an op amp (a `.lib`, `.cir`,
`.mod` or `.sub` file with a `.SUBCKT`). The decks measure the vendor model the
way a characterization lab would measure the chip, and the formulas below turn
the numbers into parameters. Where the vendor model shows an effect that
`OPAMP_FULL` has (phase reversal, a follower jump, separate slew rates, input
clamp diodes, a sharp input-range edge), the parameters reproduce it.

Use the companion skill `datasheet-to-params` for what a vendor model rarely
models well or at all: noise, temperature behaviour, and the fully differential
`FDOPAMP_FULL`.

## Version and updates

- Skill revision: **1.3** (2026-11-15)
- For model version: **1.7** of `OPAMP_FULL` (the `Version` line in the header
  of `opamp_full.lib`). For 1.6, give `CMRR`, `PSRRP` and `PSRRN` as magnitudes
  (1.6 accepts no sign and chooses the signs itself). For 1.5.x, the values are
  the same as for 1.6, except that 1.5.x has no `ROUTDC` (leave it out and use
  the loaded gain for `A0`); there `FCMRR`, `FPSRRP` and `FPSRRN` of 0 mean
  scaled defaults, so always write them out (as this file does).
- Repository: https://github.com/smaslovski/spice-opamp-macromodels
- Latest revision of this file:
  https://github.com/smaslovski/spice-opamp-macromodels/blob/master/skills/model-to-params/SKILL.md
  (raw text: https://raw.githubusercontent.com/smaslovski/spice-opamp-macromodels/master/skills/model-to-params/SKILL.md)
- Ready-made decks: `skills/model-to-params/decks/<simulator>/char_{ac,fast,slow}.cir`
  in the repository (the same text as below, with an example header).
- Optional converter: `skills/model-to-params/log_to_params.py` (Python 3, no
  extra packages) does every calculation of this file from the three logs.

Before you start, if you can open web pages or fetch files:
1. Fetch the latest revision above and compare its "Skill revision" with this one.
2. If it is newer, and its "For model version" is the model version the user has
   (ask if unknown; it is in the header of their library file), follow the newer
   file instead of this one, and say so in your answer.
3. Otherwise, use this file.

If you cannot fetch anything, use this file as it is, and say which revision you
used.

## Your task

1. **Get the model.** Ask the user for the vendor model file (attached), or at
   least its `.SUBCKT` line with the pin list and the comment lines that name
   the pins, and the file name. Find the pin order: most vendor models list it
   in a comment ("non-inverting input, inverting input, positive supply,
   negative supply, output" or a pin-number table). Never guess the pin order:
   if the file does not say, ask. Extra pins (enable/shutdown, a second output,
   a compensation or "Vocm" pin) must be tied in the wrapper (step 4); read the
   comments for what each needs.
2. **Choose the simulator** with the user:
   - an encrypted PSpice model (`$CDNENCSTART`, or the vendor says it is
     encrypted) runs only in PSpice; use the PSpice decks;
   - otherwise prefer LTspice (free, reads PSpice syntax) or ngspice. For a
     PSpice-syntax model in ngspice, the user puts `set ngbehavior=ps` in a file
     `.spiceinit` next to the decks.
   - PSpice demo/student versions limit the circuit size; the decks hold up to
     ten copies of the part and need a full PSpice. The free PSpice for TI has no
     such limit as far as I know.
3. **Choose one operating condition**, as for a datasheet table: supply (`VCC`,
   `VEE`), input common-mode voltage `VCM` (normally mid-supply), load `RL`
   (to `VCM`), 27 °C (the simulator default). Prefer the condition the user
   asks for, else the one of the datasheet's main table.
4. **Fill in the header** (template below) and write the three decks: header +
   circuit + the measurement block of the chosen simulator + `.end`. Copy the
   circuit and measurement blocks exactly; only the header changes.
5. **Tell the user how to run them** ("Running the decks") and wait for the
   three outputs.
6. **Convert** the numbers with the formulas ("From measurements to parameters").
   If you can run Python, run `log_to_params.py` instead and check its notes; if
   not, do the arithmetic yourself and show it.
7. Run the sanity checks, and produce the output in the format under "Output".

Rules that matter:
- **The measurements decide.** Do not adjust a computed value towards the
  datasheet or towards a preferred number. If the vendor model disagrees with the
  datasheet, say so in the notes; the user decides which to follow.
- **A failed measurement means something.** ngspice prints `failed`, LTspice
  `FAIL`, and in PSpice a level is never crossed. Each formula below says what a
  missing value means (usually: the effect is absent, or lies beyond the tested
  range).
- **Never invent a number.** A parameter that no measurement supports keeps its
  default or comes from the datasheet, and is marked so.
- **Units.** SPICE suffixes: `f p n u m k Meg G T`; `M` is milli. Slew rates in
  V/s (`0.5Meg` = 0.5 V/µs). Times in the logs are in seconds, frequencies in Hz.

## The header

The header is the only part you write. `{...}` are expressions the simulator
evaluates; leave the "derived" lines as they are.

<!-- BEGIN header -->
```spice
* <PART> characterization deck <AC|FAST|SLOW> (model-to-params skill rev 1.3)
.include <vendor model file>
* the part, with the pins in the order inp inn vcc vee out
.subckt DUT inp inn vcc vee out
XV inp inn vcc vee out <VENDOR_SUBCKT>
.ends DUT
* operating condition (datasheet): supplies, input common-mode voltage, load
.param VCC=15 VEE=-15 VCM=0 RL=10k
* nominal values from the datasheet; they set time scales and test levels only
.param GBWN=1Meg SRN=0.5Meg VSTEP=10 VSS=50m OVR=0.2 W=3 ILOAD=1m
* derived (do not edit)
.param TS={4*VSTEP/SRN+5/GBWN} TR={(W+OVR)*1e4/SRN+1e4/GBWN}
.param VSH={min(1,0.2*(VCC-VEE))} VCL={min(1.5,0.9*(VCC-VCM))}
```
<!-- END header -->

- `.include` (`.LIB` in PSpice): the vendor file name, in quotes if it has spaces.
  The user keeps it next to the decks, or gives the full path.
- `XV ...`: the vendor subcircuit with its pins in the vendor's order, using the
  wrapper's node names `inp inn vcc vee out`. Example: the vendor line
  `.SUBCKT OPA123 1 2 3 4 5` with pins (+in, −in, V+, V−, out) in a different
  order, say `.SUBCKT OPA123 OUT V- +IN -IN V+` → `XV out vee inp inn vcc OPA123`.
  Tie extra pins inside the wrapper: an enable pin to `vcc` (or as its comment
  says), and so on. A model that needs a ground reference may use node `0`.
- `VCC`, `VEE`, `VCM`, `RL`: the operating condition. Single supply: `VEE=0`,
  `VCM` = mid-supply (or the datasheet's `V_CM` condition).
- `GBWN`, `SRN`: the datasheet's typical GBW and slew rate (a rough value is
  enough; they only set time scales and test frequencies).
- `VSTEP`: the large-signal step, about half the output swing range, kept inside
  the input common-mode range with 0.5 V to spare: ±15 V → 10; ±5 V → 4;
  5 V single supply → 3; ±2.5 V → 2.
- `VSS`: the small step, linear: 10–50 mV and at most `0.2*SRN/(2*pi*GBWN)`.
- `OVR`: how far beyond each rail the slow ramps and the reversal steps go:
  0.2 V (0.3 V for a rail-to-rail input). Never more than 0.3 V: the vendor's
  ESD diodes would conduct.
- `W`: the slow ramps start `W` inside each rail. It must exceed the distance
  from the rail to the end of the datasheet's input range by at least 1 V
  (bipolar ±15 V: 2–3; JFET: 4; rail-to-rail: 1), and stay below half the supply.
- `ILOAD`: DC current drawn from the output while its impedance is measured:
  1 mA, or about a tenth of the short-circuit current for a low-power part.

## The circuits

Each deck is a set of separate test circuits, each with its own copy of the
part, all in one run. AC: open-loop gain and phase, common-mode and supply
gains, output and input impedance. FAST (transient, about five times `TS`):
offset, bias currents, supply current, slew rates in an inverter, follower jump,
small-step overshoot, output swing and current limit, the reversed output after
a step beyond each rail, input clamp. SLOW (transient, slow ramps near each
rail): input common-mode range and phase reversal.

### AC circuit

<!-- BEGIN circuit_ac -->
```spice
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
```
<!-- END circuit_ac -->

### FAST circuit

<!-- BEGIN circuit_fast -->
```spice
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
```
<!-- END circuit_fast -->

### SLOW circuit

<!-- BEGIN circuit_slow -->
```spice
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
```
<!-- END circuit_slow -->

## Measurement blocks

Append the block of the chosen simulator after the circuit, then `.end`.

### ngspice

AC:
<!-- BEGIN ngspice_ac -->
```spice
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
```
<!-- END ngspice_ac -->

FAST:
<!-- BEGIN ngspice_fast -->
```spice
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
```
<!-- END ngspice_fast -->

SLOW:
<!-- BEGIN ngspice_slow -->
```spice
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
```
<!-- END ngspice_slow -->

### LTspice

AC:
<!-- BEGIN ltspice_ac -->
```spice
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
```
<!-- END ltspice_ac -->

FAST:
<!-- BEGIN ltspice_fast -->
```spice
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
```
<!-- END ltspice_fast -->

SLOW:
<!-- BEGIN ltspice_slow -->
```spice
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
```
<!-- END ltspice_slow -->

### PSpice

PSpice has no `.meas` in the netlist; the decks print tables into the `.out`
file, and you read the same quantities from them (see "Reading PSpice tables").
If your PSpice rejects the expressions in `.TRAN`, replace them by numbers
(`TS` and `TR` from the header formulas).

AC:
<!-- BEGIN pspice_ac -->
```spice
.OPTIONS NUMDGT=8 NOPAGE
.AC DEC 10 1m 100G
.PRINT AC VDB(o1) VP(o1) VDB(o2) VDB(o3) VDB(o4) VDB(o8)
.PRINT AC VP(o2) VP(o3) VP(o4)
.PRINT AC VM(o5) VR(p6) VI(p6) VR(p7) VI(p7)
```
<!-- END pspice_ac -->

FAST:
<!-- BEGIN pspice_fast -->
```spice
.OPTIONS NUMDGT=8 NOPAGE
.TRAN {TS/100} {5*TS} 0 {TS/500}
.PRINT TRAN V(o1,mid) I(Vp1) I(Vn1) I(Vcc1) V(o2) V(o2i) V(o3)
.PRINT TRAN V(o4) V(o5) I(V6) V(o7) V(o8)
.PRINT TRAN V(p9,mid) V(c9,p9) V(p10,mid) V(c9,p10)
```
<!-- END pspice_fast -->

SLOW:
<!-- BEGIN pspice_slow -->
```spice
.OPTIONS NUMDGT=8 NOPAGE
.TRAN {TR/400} {TR} 0 {TR/4000}
.PRINT TRAN V(int) V(pam,nam) V(pbm,nbm) V(pat,nat) V(pbt,nbt) V(oft) I(Vft)
.PRINT TRAN V(inb) V(pab,nab) V(pbb,nbb) V(ofb) I(Vfb)
```
<!-- END pspice_slow -->

## Running the decks

Give the user the three files (`char_ac.cir`, `char_fast.cir`, `char_slow.cir`)
and these instructions for their simulator:

- **ngspice:** in the folder with the decks and the model,
  `ngspice -b char_ac.cir > ac.log` (likewise `fast`, `slow`). For a PSpice-syntax
  model first create `.spiceinit` there with the line `set ngbehavior=ps`.
  Paste the three logs (the lines `name = value` are enough) or attach them.
- **LTspice:** open each deck (File → Open, files of type netlist), run it, and
  open View → SPICE Error Log; LTspice also writes it as `char_ac.log` next to the
  deck. Paste or attach the three logs.
- **PSpice:** simulate each deck (in Capture: a "simulation profile" pointing at
  the netlist, or PSpice A/D: File → Open, Simulation → Run). Attach the three
  `.out` files: the tables are long.

Expect seconds to a few minutes per deck. If a deck does not converge, see
"Troubleshooting".

## From measurements to parameters

The names below are the measurement names in the logs (ngspice and LTspice
print them directly; for PSpice see "Reading PSpice tables"). Header values
(`VCC`, `VEE`, `VCM`, `RL`, `TS`, `VSTEP`, `OVR`, `W`, `GBWN`) are also printed
in the logs. Work in volts, amps, seconds, hertz.

Constants: `VT = 0.025864` V (thermal voltage at 27 °C).

### Choose VXO first

`VXO` (class-AB crossover) is not measured. Keep `VXO=2m` (the default) for a
bipolar class-AB output; use `VXO=0` for a CMOS rail-to-rail output (the swing
reaches within about 50 mV of the rails) or when the user prefers. Then
`REFF = 2*ROUT` if `VXO > 0`, else `REFF = ROUT` (with `VXO > 0` the model's
small-signal output resistance is doubled at idle, which the gain test sees).

### AC deck

| Param | Formula | Notes |
|---|---|---|
| `ROUT` | `zo_b` | open-loop output impedance at GBWN/10. If `zo_a` and `zo_c` differ from it by more than 2×, say so. |
| `ROUTDC` | `RL*(10^((a0u_db - a0_db)/20) - 1) - REFF` | the extra open-loop output resistance at DC, from the gain at 1 mHz without load (`a0u_db`) and with it (`a0_db`), both at idle. Set it only if it exceeds 0.1·`ROUT`; otherwise leave it out (0). Cross-check: `zo_dc - ROUT` (\|Zout\| at 1 mHz, at the DC load ILOAD); if the two differ by more than 30 %, the output resistance depends on the load current: say so and keep the idle value. (Model 1.6 and later; for 1.5.x leave it out and use the loaded gain for A0.) |
| `A0` | `10^(a0_db/20) * (RL + REFF + ROUTDC)/RL` | `a0_db`: gain at 1 mHz, with the load; `A0` is the unloaded gain (`10^(a0u_db/20)` when `ROUTDC` is set). |
| `FP2`, `FP3`, `GBW` | see below | from `fu` and `ph_fu` |
| `CMRR` | `sign(cmrr_sg) * 10^(cmrr_db/20)` | DC CMRR (at 1 mHz), signed: `cmrr_sg` is the real part of the common-mode response over the differential gain, so the sign says whether a rising input common mode moves the output like a positive (+) or negative (−) offset. Model 1.7 takes signed DC values; they reproduce this vendor model, which is one unit (in real parts the sign is set by mismatch and differs from unit to unit). Above 160 dB (likewise for PSRR) the vendor model has no such coupling: take CMRR and FCMRR from the datasheet. |
| `FCMRR` | `fcm20/10` | the frequency where the CMRR has fallen 20 dB, divided by 10 (single-zero roll-off). If `fcm20` failed, use `fcm3`; if both failed, the CMRR is flat: use `1G`. If `fcm20/fcm3` is not between 7 and 14, the roll-off is not single-zero: still use `fcm20/10` and say so. |
| `PSRRP`, `FPSRRP` | `sign(psrrp_sg) * 10^(psrrp_db/20)`, `fpsp20/10` | as CMRR; positive supply |
| `PSRRN`, `FPSRRN` | `sign(psrrn_sg) * 10^(psrrn_db/20)`, `fpsn20/10` | negative supply. Give `FPSRRP` and `FPSRRN`, not `FPSRR`. The slopes above the corners get their signs from the model's rules (they are systematic), so only the DC values carry a sign. |
| | | Only two of CMRR, PSRR+ and PSRR− are independent (a part without a ground pin: the three signed errors per volt, 1/CMRR + 1/PSRRP + 1/PSRRN, add up to 1/A0 unloaded). With all three given, the model uses PSRRP and PSRRN exactly and derives CMRR. A vendor model or a part measured here obeys the identity too, with its unloaded gain, which is the model's A0 when `ROUTDC` is set. If the identity fails by more than 1 dB, or the signs do not fit it, the vendor model refers something to node 0 (typical of older macromodels): its signs are then conventions of that model; say so. `python3 tools/rejection.py <params>` shows the derived CMRR; report it with the measured one. |
| `RIC` | `1/Gc0` | `Gc0 = zc_re0/(zc_re0^2 + zc_im0^2)`; one pin, common mode, 1 mHz. Above 10 TΩ it is only a lower limit; cap at `1e15`. |
| `RID` | `1/(Gd0 - Gc0)` | `Gd0 = zd_re0/(zd_re0^2 + zd_im0^2)`. If `Gd0 - Gc0 <= 0` or the result exceeds 1 TΩ: `1T`. |
| `CIC` | `Bc/(2*pi*f10)` | `Bc = -zc_im/(zc_re^2 + zc_im^2)`, `f10 = GBWN/10` |
| `CID` | `Bd/(2*pi*f10) - CIC` | `Bd = -zd_im/(zd_re^2 + zd_im^2)`. A result below 1 fF (or negative) for CID or CIC: the vendor model has no input capacitance; keep the default or the datasheet value. |

**Phase margin, GBW, FP2, FP3.** `PM = 180 + ph_fu` (degrees; bring it into
−180…180). The output pole of the load: `f_out = 1/(2*pi*RP*3p)` with
`RP = REFF*RL/(REFF + RL)`. Correct the margin for it:
`PMc = PM + atan(fu/f_out)` (degrees; negligible unless `f_out < 30*fu`). Read
`r = FP2/GBW` and `g = fu/GBW` from this table at `PMc`, interpolating linearly
between columns (OPAMP_FULL, differential drive, FP3 = 3.33·FP2):

| PMc | 40° | 45° | 50° | 55° | 60° | 65° | 70° | 75° | 80° | 85° |
|---|---|---|---|---|---|---|---|---|---|---|
| r = FP2/GBW | 1.02 | 1.22 | 1.47 | 1.78 | 2.18 | 2.72 | 3.51 | 4.81 | 7.34 | 14.85 |
| g = fu/GBW | 0.777 | 0.816 | 0.852 | 0.885 | 0.915 | 0.940 | 0.961 | 0.978 | 0.990 | 0.998 |

Then `GBW = fu/g`, `FP2 = r*GBW`, `FP3 = 3.33*FP2`. Above 85°: `FP2 = 1000*GBW`,
`GBW = fu`, and say that the part's margin is higher than the model reaches.
Below 40°: extrapolate, low confidence. Cross-check: `100*f40*(RL+REFF)/RL`
should be within about 5 % of `GBW`; if not, the response is not single-pole
between 40 dB and 0 dB; report both and keep the fu-based value (it sets the
step response).

### FAST deck

| Param | Formula | Notes |
|---|---|---|
| `VOS` | `vos` | follower at VCM: Vout − Vin |
| `IB` | `(ibp + ibn)/2` | currents into the pins (> 0 into the pin, as the model's IB) |
| `IOS` | `ibp - ibn` | |
| `ICCQ` | `iq` | unloaded follower at VCM |
| `SRR` | `0.35*VSTEP/(t85ri - t50ri) * KI` | inverter, rising output; `KI = (RLI + ROUT)/RLI`, `RLI = RL*10k/(RL + 10k)` |
| `SRF` | `0.35*VSTEP/(t85fi - t50fi) * KI` | falling output |
| `SR` | `(SRR + SRF)/2` | if SRR and SRF differ by less than 10 % of SR, give `SR` only; otherwise give all three |
| `KJUMP` | see below | follower jump |
| `VHD` | `(VCC - voh_rl) - (voh_rl - VCM)/RL * ROUT` | open-loop swing into RL. If ≤ 0: `0.05`, and say so. Compare with the unloaded `VCC - voh_nl`. |
| `VLD` | `(vol_rl - VEE) - (VCM - vol_rl)/RL * ROUT` | likewise |
| `ISRC` | `isrc` | output shorted to VCM. If it equals `(VCC - VHD - VCM)/ROUT` within 5 %, the current limit was not reached: take ISRC from the datasheet or keep the default. |
| `ISNK` | `-isnk` | likewise with `(VCM - VEE - VLD)/ROUT` |
| `VCLMP`, `RCLMP` | see below | input clamp |
| `PRHI`, `PRLO` | see "SLOW deck" | slope of the reversed output |

**Follower jump (KJUMP).** From the follower's step (not the inverter's), with its
own slew rates `sr = 0.35*VSTEP/(t85r - t50r)` and `sf = 0.35*VSTEP/(t85f - t50f)`:
`jr = (vj_r - vo2_lo - sr*0.0105*TS)/VSTEP` (rising edge) and
`jf = (vo2_hi - vj_f - sf*0.0105*TS)/VSTEP` (falling edge). `vj_r` and `vj_f` are the
output TS/100 after each input edge; `jr` and `jf` are the fractions of the step that
the output jumps at the edge, beyond what slewing gives in that time. If the larger is
at least 0.05: `KJUMP = +jr*(RL + ROUT)/RL` if `jr` is larger, else
`KJUMP = -jf*(RL + ROUT)/RL`. Otherwise `KJUMP` stays 0. (Do not extrapolate the
slewing line back to the edge instead: a slew rate that falls along the edge then
looks like a jump.) If the part has an input clamp (below),
the clamp current drags a follower's output during a large step: leave `KJUMP = 0`
and say so.

**Input clamp.** A clamp is present if `icl1 > 1u + 10*|IB|` (A). Then, with
`L1 = VT*ln(icl1/1e-15)`, `L2 = VT*ln(icl2/1e-15)`,
`det = L1*icl2 - L2*icl1`:
`N = (vcl1*icl2 - vcl2*icl1)/det`, `RCLMP = (L1*vcl2 - L2*vcl1)/det`,
`VCLMP = N*VT*27.631`. If `RCLMP < 0`: `RCLMP = 0`, `N = vcl2/L2`. No clamp:
leave `VCLMP` at its default (100 = none).

**Check (not a parameter):** small-step overshoot
`(ss_max - ss_hi)/(ss_hi - ss_lo)` (rising) and `(ss_lo - ss_min)/(ss_hi - ss_lo)`
(falling). Report them; the fitted model should give about the same.

### SLOW deck

**Phase reversal, top edge.** The follower's output reverses if `vendt < VCM`
(it ends below VCM although the input is above the top rail). Then:
- `VPRHI = VCC - vipt` (`vipt`: the input where the pin current has risen to
  0.9 of its rise over the ramp; that is the model's definition of the flip). If
  `vipt` failed, use `VCC - vflt` and say so.
- `IPR = iendt - it0` (the rise of the pin current).
- `PRHI = slope/SR`, with `slope = 0.4*(VCM - VEE)/(rt_t2 - rt_t1) * (RL + ROUT)/RL`
  (the reversed output after the step to `VCC + OVR`) and `SR` the mean slew rate.
  This holds if `VCC + OVR - vipt >= 0.12` V. If it is less, the junction is not
  fully on at the step: compute `J = 0.5*(1 + tanh((VCC + OVR - vipt)/(2*VT)))`
  and iterate `PRHI = slope/(SR * J^(1 + max(log2(PRHI), 0)))` a few times. If
  `rt_t1` or `rt_t2` failed, `PRHI = 1` (low confidence).

**Bottom edge:** reverses if `vendb > VCM`; `VPRLO = vipb - VEE`,
`IPR = |iendb - ib0|`, `PRLO` likewise with `rb_t1`, `rb_t2`,
`slope = 0.4*(VCC - VCM)/(rb_t2 - rb_t1) * (RL + ROUT)/RL`, step to `VEE - OVR`,
`J` with `vipb - (VEE - OVR)`. If both edges reverse, `IPR` is the mean of the
two (the model has one IPR); say so if they differ by more than 1.5×.

No reversal: leave `PRHI`/`PRLO` at 0 (and `VPR*`, `IPR` at their defaults).

**Input common-mode range (ICMHI, ICMLO, VK).** For each edge, take one of two
methods, then place both edges with one common `VK`. Below, `s = +1` for the top
edge and `-1` for the bottom; `A0` is the value found above.

1. *Follower method* (preferred, as in a datasheet). Use it if `vf1t`, `vf2t`
   (`vf1b`, `vf2b`) exist and the follower's output there is not at the swing
   limit: `of1t < voh_rl - 0.05` (bottom: `of1b > vol_rl + 0.05`). The follower's
   tracking error has grown by 10 mV at the input `vf1` (output `of1`) and by
   100 mV at `vf2` (`of2`). With `ost = (VCC - W) - eft0` (bottom:
   `(VEE + W) - efb0`) and `d1 = 0.01*s`, `d2 = 0.1*s`:
   - relative gain `w_k = (of_k - VREF)/(AF*d_k + ost - VREF)`, `z_k = ln(w_k/(1 - w_k))`,
     where `VREF = (VCC + VEE)/2` (the model's gain stages are referred to
     mid-supply) and `AF = A0*RL/(RL + ROUT + ROUTDC)` is the gain into RL;
   - effective input `V_k = (vf_k + of_k)/2 - s*0.5*sqrt((vf_k - of_k)^2 + 1e-4)`;
   - edge width `VK_e = 2*s*(V_2 - V_1)/(z_1 - z_2)`; if it is below 0.005, use
     0.005 (the follower stops abruptly; the sharpest knee kept).
2. *Gain method* (when the follower is swing-limited first). `vw5` is the input
   where the input stage's gain has fallen to half, `vwq` to a quarter. Take
   `V_1 = vw5 - s*0.005`, `z_1 = 0`; `V_2 = vwq - s*0.005`, `z_2 = -1.0986`, and
   `VK_e` as above. If the edge has a reversal junction within about 0.15 V,
   the junction itself removes gain; the converter script corrects for it. By
   hand, use the uncorrected values and lower the confidence.
3. If neither shows an edge (both failed, or the gain method's points failed),
   the range reaches beyond the ramp end: `ICMHI = -(OVR + 0.1 + 2*VK)` (bottom
   the same for `ICMLO`).

Then `VK` = the mean of the edge widths found (`0.15` if none). Say so if they
differ by more than 2×. Place each edge through its first point with this `VK`:
`ICMHI = VCC - (V_1 + z_1*VK/2)` (top),
`ICMLO = (V_1 - z_1*VK/2) - VEE` (bottom).

**Report (not parameters):** where the follower stops (`vstopt`, `vstopb`).

### Supply references

`VCCN = VCC`, `VEEN = VEE` (the model's PSRR reference). If `VCM` is not
mid-supply, also `VCMN = VCM`.

### Not measured

`ENOISE`, `FCEN`, `INOISE`, `FCIN` (noise: vendor models often have none or a
rough one; take them from the datasheet with `datasheet-to-params`), `COUT`,
`VXO`, and the rail-to-rail crossover `VCMT`, `VKT`, `DVOST`, `DIBT`. Keep their
defaults unless the datasheet gives them.

## Reading PSpice tables

Each `.PRINT` gives a table in the `.out` file: a header line starting with
`FREQ` or `TIME`, the column names, then the rows. Interpolate linearly between
rows (for frequencies: linear in log f). The quantities named above are:

- AC (first row = 1 mHz): `a0_db` = `VDB(o1)` in the first row, `a0u_db` = `VDB(o8)` in
  the first row; `fu`, `f40`,
  `f20`: where `VDB(o1)` crosses 0, 40, 20 dB; `ph_fu` = `VP(o1)` at `fu` (if the
  phase column wraps through ±180°, unwrap it first). CMRR(f) =
  `VDB(o1) - VDB(o2)` per row: `cmrr_db` in the first row, `fcm3`/`fcm20` where it
  has fallen 3/20 dB. PSRR+ with `VDB(o3)`, PSRR− with `VDB(o4)`. Signs: `cmrr_sg`
  = cos(`VP(o2)` − `VP(o1)`) in the first row (only its sign is used), `psrrp_sg`
  and `psrrn_sg` likewise with `VP(o3)` and `VP(o4)`. `zo_a/b/c` =
  `VM(o5)` at GBWN/100, GBWN/10, GBWN; `zo_dc` = `VM(o5)` in the first row.
  `zd_re0`, `zd_im0` = `VR(p6)`, `VI(p6)` in the first row, `zd_re`, `zd_im` at GBWN/10; `zc_*` likewise with `p7`.
- FAST: averages over a window are the mean of the rows in it. `vos` =
  `V(o1,mid)`, `ibp` = `I(Vp1)`, `ibn` = `I(Vn1)`, `iq` = −`I(Vcc1)`, all over
  0.5·TS…0.9·TS. `t50ri`: first time after 2·TS where `V(o2i)` rises through VCM;
  `t85ri`: through VCM + 0.35·VSTEP; `t50fi`, `t85fi`: first falls through VCM and
  VCM − 0.35·VSTEP (from 0). `t50r`, `t85r`, `t50f`, `t85f` likewise with `V(o2)`
  (rising from 0, falling after 2·TS). `vj_r`, `vj_f`: `V(o2)` at 1.011·TS and
  3.012·TS. `ss_lo`, `ss_hi`: `V(o3)` over 0.5…0.9·TS
  and 2.5…2.9·TS; `ss_max` = max of `V(o3)` over TS…3·TS, `ss_min` = min over
  3·TS…5·TS (the table is coarse: low confidence). `voh_rl`, `vol_rl`: `V(o4)` over
  2…2.4·TS and 4.5…4.9·TS; `voh_nl`, `vol_nl`: `V(o5)` likewise; `isrc`, `isnk`:
  `I(V6)` likewise. `rt_t1`, `rt_t2`: where `V(o7)` falls through
  VCM − 0.2·(VCM − VEE) and VCM − 0.6·(VCM − VEE); `rb_t1`, `rb_t2`: where `V(o8)`
  rises through VCM + 0.2·(VCC − VCM) and VCM + 0.6·(VCC − VCM). `vcl1` =
  `V(p9,mid)`, `icl1` = `V(c9,p9)`/100; `vcl2` = `V(p10,mid)`, `icl2` =
  `V(c9,p10)`/1000 (over 0.5…0.9·TS).
- SLOW: `dm` = `V(pam,nam) - V(pbm,nbm)` (its mean is `dmid`), `dt` =
  `V(pat,nat) - V(pbt,nbt)`, `db` = `V(pab,nab) - V(pbb,nbb)`. `vw5t`/`vwqt`: `V(int)`
  where `dt` rises through 2·`dmid` / 4·`dmid`; `vw5b`/`vwqb` likewise with `db`
  and `V(inb)`. Follower error `et = V(int) - V(oft)`, `eft0` its first value;
  `vf1t`/`of1t`: `V(int)`/`V(oft)` where `et` first rises through `eft0` + 0.01,
  `vf2t`/`of2t` through `eft0` + 0.1. Bottom: `eb = V(inb) - V(ofb)`, falls through
  `efb0` − 0.01 and − 0.1. `vstopt` = max of `V(oft)`, `vendt` = last `V(oft)`,
  `it0`, `iendt` = first and last `I(Vft)`, `vipt` = `V(int)` where `I(Vft)`
  first rises through `it0` + 0.9·(`iendt` − `it0`), `vflt` = `V(int)` where
  `V(oft)` first falls through `vstopt` − 0.05·(`vstopt` − VCM). Bottom: `vstopb`
  = min of `V(ofb)`, `vendb`, `ib0`, `iendb`, `vipb` (falls through), `vflb`
  (rises through `vstopb` + 0.05·(VCM − `vstopb`)).

## Sanity checks (do all of them; report any that fail)

1. **Log consistency.** The header values printed in the logs are the ones you
   wrote. `dt0`, `db0` (gain-method values at the ramp starts) are within 10 % of
   `dmid`; if not, `W` is too small (the ramp starts beyond an edge): ask the
   user to rerun SLOW with a larger `W`.
2. **Settled levels.** `vo2_lo ≈ VCM - VSTEP/2`, `vo2_hi ≈ VCM + VSTEP/2`
   (within 1 %): otherwise VSTEP leaves the linear range; reduce it and rerun FAST.
3. **Phase margin and overshoot agree.** Overshoot 5 % ≈ 65°, 10 % ≈ 59°,
   20 % ≈ 48°, 30 % ≈ 39° (second-order estimate; CMRR roll-off adds overshoot in
   a follower).
4. **|CMRR|·FCMRR/GBW ≥ 3.** Below that, a follower step rings in the model (the
   CMRR error is in series with the input). If the vendor model is like that,
   report it; do not change FCMRR.
5. **FP2 ≥ 1.2·GBW**, and the output pole `f_out ≥ 10·GBW`. If not, warn that
   the model's phase margin depends on the load.
6. **Swing vs edges.** If an input edge lies outside the swing (follower method
   impossible on both edges), say that the follower clips at the output first.
7. **Plausibility.** A value orders of magnitude off its class (see the
   `datasheet-to-params` skill's ranges) usually means a failed measurement read
   as a number, or a wrong pin order (an inverting follower!). Check
   `vo2_hi > vo2_lo` and `A0 > 1000`; a negative `a0_db` or a falling follower
   output means `inp` and `inn` are swapped in the wrapper.

## Output

Work everything out and run the sanity checks on a draft first. The answer itself
contains one final instance line and one table, with no corrections inside it.

**1. Summary line:** part, vendor model (file, version line), simulator,
operating condition (supply, VCM, load, 27 °C).

**2. The instance line**, ready to paste. List the parameters that differ from
the defaults; continuation lines start with `+`:

```spice
* <part>, <supply>, from the vendor model <file> (<simulator>), model-to-params 1.0
.include opamp_full.lib
X1 inp inn vcc vee out OPAMP_FULL PARAMS:
+ A0=... GBW=... FP2=... FP3=... SR=... ...
```

For PSpice the same parameters work with `models/pspice/opamp_full.lib`.

**3. The parameter table**, one row per parameter set or measured:

| Param | Value | Measurement | Formula / note | Confidence |
|---|---|---|---|---|
| A0 | 5.5k | a0_db = 74.75 dB | ×(RL+2·ROUT)/RL | high |
| ICMHI | 0.715 | vf1t = 1.810 V, vf2t = 1.900 V | follower method; VK clamped to 5 mV | medium |
| ENOISE | 20n | — | not measured: default (or datasheet) | — |

Confidence: `high` (a direct measurement), `medium` (a measurement through a
model assumption, e.g. FCMRR from a non-single-zero roll-off, an edge near a
junction), `low` (a guess or fallback), `—` (default).

**4. Notes:** what the vendor model shows that `OPAMP_FULL` cannot (the
converter's notes say most of it), failed measurements and what they mean, the
sanity-check results, and the parameters still to take from the datasheet.

## Troubleshooting

- **No convergence / "timestep too small".** Ask the user for the simulator's
  message. Try, in order: `.options gmin=1e-10` (ngspice/LTspice) or
  `.OPTIONS GMIN=1e-10` (PSpice); `.options method=gear`; a smaller `VSTEP` or
  `OVR`. A model that will not converge with ten copies may converge with fewer:
  the user can comment out tests (their measurements then fail; say which
  parameters are missing).
- **Measurements failing in AC.** `fu` failed: the gain never reaches 0 dB
  below 100 GHz (wrong pins, or the model needs a supply pin it does not get).
  `fcm*`, `fps*` failed: flat CMRR/PSRR (fine).
- **Bias current zero, CMRR or PSRR infinite (`inf`, or > 200 dB).** The vendor
  model leaves that effect out: use the datasheet value and say so.
- **Ideal vendor models.** Some vendor models are simple (no input range, no
  swing limit, no slew asymmetry). Report what they lack instead of
  over-reading tiny effects: the model inherits the vendor model's simplicity
  only where the measurements show it.

## Verifying the result (optional)

If the user can run the decks again: put the fitted instance into the wrapper
(`XV inp inn vcc vee out OPAMP_FULL PARAMS: ...`, with `.include opamp_full.lib`)
and run the three decks once more. The logs of the vendor model and of the fit
should agree on gain, phase at fu, CMRR, offset, bias current, supply current,
swing, slew rates, follower edges (`vf1t`, `vf1b`), flips and reversed slopes;
compare them in a short table. The repository's
`tests/model_to_params_check.py` does this for four transistor-level reference
op amps, one of them the textbook µA741.
