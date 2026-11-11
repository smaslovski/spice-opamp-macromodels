#!/usr/bin/env python3
# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
"""Characterize the three transistor-level reference op amps (ngspice).

    cd tests/transistor_level && python3 characterize.py

For each reference it prints the quantities a datasheet would give, and from which
the OPAMP_FULL parameters in compare_reversal.py were taken:
open-loop DC gain and unity-gain frequency, phase margin, slew rates (follower,
step of half the supply span), output swing (load 10 kOhm; 100 kOhm for C), supply current, input bias current
(into the + pin of a follower at 0 V), and the
linear input range of a follower and the input voltage at which its output reverses
(slow triangle, 0 Ohm source).
Each measurement uses its own deck, with one op amp in it.
Decks and data go to out/.
"""
import os, re, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

# library, subcircuit, supply (+/-), load. C has a weak output stage (it sources
# only about 100 uA), so it is measured with a 100 kOhm load.
REFS = {
    'A': ('opa_npn.lib', 'OPA_NPN', 15.0, '10k'),
    'B': ('opa_pjfet.lib', 'OPA_PJFET', 15.0, '10k'),
    'C': ('opa_pmos.lib', 'OPA_PMOS', 2.5, '100k'),
}


def run(case, tag, body, control):
    """Run one ngspice deck with the reference op amp <case> and return stdout."""
    lib, sub, vs, rl = REFS[case]
    cir = os.path.join(OUT, f'char_{case}_{tag}.cir')
    open(cir, 'w').write(
        f"* {sub}: {tag}\n.include {os.path.join(HERE, 'devices.lib')}\n.include {os.path.join(HERE, lib)}\n"
        f"Vcc vcc 0 {vs}\nVee vee 0 {-vs}\n{body.format(sub=sub, rl=rl)}\n.control\n{control}\n.endc\n.end\n")
    return subprocess.run(['ngspice', '-b', cir], cwd=OUT, capture_output=True, text=True).stdout


def characterize(case):
    lib, sub, vs, rl = REFS[case]
    st = round(vs / 2, 3)
    r = {}
    # open loop: the DC operating point is held by a 1 GH / 1 GF servo, AC drive via 1 GF
    t = run(case, 'ac', "X1 0 n1 vcc vee o1 {sub}\nLf o1 n1 1e9\nCf n1 0 1e9\nVac a 0 0 AC 1\nCa a n1 1e9\nRL o1 0 {rl}",
            "op\nlet iq = -i(vcc)\nprint iq\nac dec 40 1 300Meg\nlet g = vdb(o1)-vdb(n1)\n"
            "let ph = 180/pi*cph(v(o1)/v(n1))\nmeas ac a0 find g at=1\nmeas ac fu when g=0\nmeas ac phu find ph when g=0")
    r.update(iq=num(t, 'iq'), a0=num(t, 'a0'), fu=num(t, 'fu'), pm=num(t, 'phu') % 360)
    # follower at 0 V: input bias current (into the + pin)
    t = run(case, 'ib', "Vin in 0 0\nVs in p 0\nX5 p o5 vcc vee o5 {sub}\nRL o5 0 {rl}",
            "op\nlet ib = i(Vs)\nprint ib")
    r['ib'] = num(t, 'ib')
    # follower, step of half the supply each way: slew rates
    t = run(case, 'step', f"Vst st 0 PULSE({-st} {st} 10u 10n 10n 40u 80u)\nX3 st o3 vcc vee o3 {{sub}}\nRL o3 0 {{rl}}",
            "tran 10n 80u\nmeas tran vlo find v(o3) at=9u\nmeas tran vhi find v(o3) at=49u\n"
            "let lo = vlo + 0.1*(vhi-vlo)\nlet hi = vlo + 0.9*(vhi-vlo)\n"
            "meas tran t1 when v(o3)=lo rise=1\nmeas tran t2 when v(o3)=hi rise=1\n"
            "meas tran t3 when v(o3)=hi fall=1\nmeas tran t4 when v(o3)=lo fall=1\n"
            "let srr = 0.8*(vhi-vlo)/(t2-t1)/1e6\nlet srf = 0.8*(vhi-vlo)/(t4-t3)/1e6\nprint srr srf")
    r.update(srr=num(t, 'srr'), srf=num(t, 'srf'))
    # open loop, overdriven by +/-0.1 V: output swing (load 10 kOhm; 100 kOhm for C)
    t = run(case, 'swing', "Vd d 0 0\nX4 d 0 vcc vee o4 {sub}\nRL o4 0 {rl}",
            "dc Vd -0.1 0.1 0.01\nmeas dc swmax max v(o4)\nmeas dc swmin min v(o4)")
    r.update(swmax=num(t, 'swmax'), swmin=num(t, 'swmin'))
    # follower driven by a slow triangle across the whole supply (0 -> +vs -> -vs -> 0
    # in 40 ms, 1.5 V/ms for +/-15 V): a transient, not a DC sweep, because in C the
    # high-impedance node d2 is undefined at DC once the tail current is cut off
    data = os.path.join(OUT, f'char_{case}_follower.txt')
    run(case, 'follower', f"Vin in 0 PWL(0 0 10m {vs} 30m {-vs} 40m 0)\nX2 in o2 vcc vee o2 {{sub}}\nRL o2 0 {{rl}}",
        f"tran 2u 40m\nwrdata {data} v(in) v(o2)")
    d = np.loadtxt(data)
    x, v = d[:, 1], d[:, 3]
    # linear range: output within 10 mV of the input
    ok = np.abs(v - x) < 0.01
    r['lin'] = (x[ok].min(), x[ok].max())
    # reversal: the input is beyond half the supply and the output has the opposite sign
    rev = (np.abs(x) > vs / 2) & (np.sign(v) == -np.sign(x))
    r['rev'] = sorted({round(float(x[i]), 2) for i in np.where(rev & ~np.roll(rev, 1))[0]})
    return r


def num(txt, name):
    m = re.search(r'^\s*' + name + r'\s*=\s*([-+0-9.eE]+)', txt, re.M)
    return float(m.group(1)) if m else float('nan')


def main():
    print(f"{'':2s} {'A0':>6s} {'fu':>6s} {'PM':>5s} {'SR+':>6s} {'SR-':>6s} {'Vo,max':>7s} {'Vo,min':>7s} {'Iq':>6s} {'IB':>8s}  {'follower linear':>17s}  reverses at")
    print(f"{'':2s} {'dB':>6s} {'MHz':>6s} {'deg':>5s} {'V/us':>6s} {'V/us':>6s} {'V':>7s} {'V':>7s} {'mA':>6s} {'nA':>8s}  {'range, V':>17s}")
    for case in REFS:
        r = characterize(case)
        rev = ', '.join(f'{x:+.3f} V' for x in r['rev']) or 'no reversal'
        print(f"{case:2s} {r['a0']:6.1f} {r['fu']/1e6:6.2f} {r['pm']:5.1f} {r['srr']:6.2f} {r['srf']:6.2f} "
              f"{r['swmax']:7.2f} {r['swmin']:7.2f} {r['iq']*1e3:6.3f} {r['ib']*1e9:8.3f}  {r['lin'][0]:+8.3f}..{r['lin'][1]:+7.3f}  {rev}")


if __name__ == '__main__':
    main()
