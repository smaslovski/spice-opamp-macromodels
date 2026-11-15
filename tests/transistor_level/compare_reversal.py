#!/usr/bin/env python3
# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
"""Phase reversal: OPAMP_FULL against three minimal transistor-level op amps (ngspice).

    cd tests/transistor_level && python3 compare_reversal.py

A (opa_npn.lib): npn input pair, +/-15 V; reverses at the top (base-collector junction).
B (opa_pjfet.lib): p-JFET input pair, +/-15 V; reverses at the bottom (gate-drain junction).
C (opa_pmos.lib): p-MOS input pair, +/-2.5 V; no reversal, the output stops at the edge.

A and B: unity-gain followers into 10 kOhm, driven through a source resistance Rs
of 0, 10k and 100k. The script prints, for the transistor circuit and for the
macromodel, the input voltage at which the output flips in a DC sweep, the input
current at the end of the sweep, the output slope after a fast step beyond the
range, and the recovery delay when the input returns to 0 V after 40 us
in reversal (from the input step to 10 % of the output's return).
C: a follower into 100 kOhm driven by a slow triangle beyond the top of the range;
the script prints where the output stops.
It writes reversal_compare.png. Decks and data go to out/.
"""
import os, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
LIB = os.path.join(HERE, '..', '..', 'models', 'opamp_full.lib')
os.makedirs(OUT, exist_ok=True)

# Macromodel parameters fitted to the references. A0, GBW, FP2/FP3 (from the phase
# margin), SRR/SRF and the swing (VHD/VLD) come from characterize.py; CMRR and PSRR
# are kept flat (FCMRR = FPSRR = 1G), since their roll-off was not characterized; ICMHI/ICMLO/VK from the follower's linear
# range; the junction parameters (PRHI/PRLO, VPRHI/VPRLO, IPR) from the Rs = 0 DC
# sweep and the step response.
CASES = {
    'A': dict(lib='opa_npn.lib', sub='OPA_NPN', vs=15, rl='10k', lo=13.5, hi=15.6, step=15.3,
              mm='A0=5.4k GBW=1.78Meg FP2=4.8Meg FP3=16Meg SRR=0.54Meg SRF=0.66Meg VHD=0.67 VLD=0.72 ICMHI=0.1 ICMLO=1.5 '
                 'IB=49n IOS=0 RID=1.05Meg PRHI=3.5 VPRHI=0.03 IPR=20u'),
    'B': dict(lib='opa_pjfet.lib', sub='OPA_PJFET', vs=15, rl='10k', lo=-15.6, hi=-13.5, step=-15.3,
              mm='A0=8.7k GBW=4.83Meg FP2=35Meg FP3=118Meg SRR=11.9Meg SRF=11.9Meg VHD=0.71 VLD=0.72 ICMHI=1 ICMLO=2.8 VK=0.5 '
                 'IB=15p IOS=0 RID=1T RIC=1T PRLO=1.6 VPRLO=0.15 IPR=200u'),
    'C': dict(lib='opa_pmos.lib', sub='OPA_PMOS', vs=2.5, rl='100k',
              mm='VCCN=2.5 VEEN=-2.5 A0=31k GBW=9.9Meg FP2=57Meg FP3=189Meg SRR=6.45Meg SRF=6.82Meg VHD=0.04 VLD=0.01 VXO=0 '
                 'ICMHI=0.734 ICMLO=-0.1 VK=0.01 IB=0 IOS=0 RID=1T RIC=1T'),
}
RS_DC = (0, 10e3, 100e3)
RS_TR = (0, 10e3)


def deck(case, kind, an, rs, data):
    c = CASES[case]
    if kind == 'tl':
        inc = f".include {os.path.join(HERE, 'devices.lib')}\n.include {os.path.join(HERE, c['lib'])}\n"
        x = f"X1 inp out vcc vee out {c['sub']}"
    else:
        inc = f".include {LIB}\n"
        x = f"X1 inp out vcc vee out OPAMP_FULL PARAMS: {c['mm']}"
    if an == 'dc':
        src, ctl = 'Vin in 0 0', f"dc Vin {c['lo']} {c['hi']} 0.005"
    elif an == 'step':
        src, ctl = f"Vin in 0 PULSE(0 {c['step']} 5u 10n 10n 1 2)", 'tran 2n 40u'
    elif an == 'rec':     # into reversal at 5 us, back to 0 V at 45 us
        src, ctl = f"Vin in 0 PULSE(0 {c['step']} 5u 10n 10n 40u 1)", 'tran 2n 100u'
    else:  # slow triangle beyond the top of the range (C)
        src, ctl = 'Vin in 0 PWL(0 1.5 1m 2.5 2m 1.5)', 'tran 0.1u 2m'
    return (f"* {case} {kind} {an} Rs={rs:g}\n{inc}Vcc vcc 0 {c['vs']}\nVee vee 0 {-c['vs']}\n{src}\n"
            f"Rs in m {max(rs, 1e-3):g}\nVs m inp 0\n{x}\nRL out 0 {c['rl']}\n"
            f".control\n{ctl}\nwrdata {data} v(out) i(Vs) v(in)\n.endc\n.end\n")


def run(case, kind, an, rs=0):
    name = f'{case}_{kind}_{an}_{int(rs)}'
    cir, data = os.path.join(OUT, name + '.cir'), os.path.join(OUT, name + '.txt')
    open(cir, 'w').write(deck(case, kind, an, rs, data))
    subprocess.run(['ngspice', '-b', cir], cwd=OUT, capture_output=True, text=True)
    d = np.loadtxt(data)
    return d[:, 0], d[:, 1], d[:, 3], d[:, 5]     # x (or t), v(out), i(Vs) into the pin, v(in)


def flip(x, v):
    s = np.where(np.diff(np.sign(v)) != 0)[0]
    return x[s[0]] if len(s) else None


def slope(t, v):
    v0, v1 = v[np.searchsorted(t, 4.9e-6)], v[-1]
    s = np.sign(v1 - v0)
    a, b = v0 + 0.1 * (v1 - v0), v0 + 0.9 * (v1 - v0)
    ia, ib = np.argmax(s * v > s * a), np.argmax(s * v > s * b)
    return 0.8 * (v1 - v0) / (t[ib] - t[ia]) / 1e6


def label(kind, rs=None):
    s = 'transistor' if kind == 'tl' else 'model'
    return s if rs is None else f'{s}, Rs = {rs/1e3:g}k'


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(3, 3, figsize=(16, 11))
    print('A and B: follower beyond the input range, from a source resistance Rs')
    print(f"{'':3s} {'Rs':>7s} {'flip at, V':>21s} {'input current, uA':>21s}")
    print(f"{'':3s} {'':>7s} {'transistor':>10s} {'model':>10s} {'transistor':>10s} {'model':>10s}")
    for j, case in enumerate('AB'):
        for rs, col in zip(RS_DC, ('C0', 'C1', 'C2')):
            row = []
            for kind, ls in (('tl', '-'), ('mm', '--')):
                x, v, i, _ = run(case, kind, 'dc', rs)
                ax[0, j].plot(x, v, ls, color=col, label=label(kind, rs))
                ax[1, j].plot(x, i * 1e6, ls, color=col)
                xf = flip(x, v)
                row += [f'{xf:10.3f}' if xf is not None else f"{'none':>10s}", i[-1 if case == 'A' else 0] * 1e6]
            print(f"{case:3s} {rs/1e3:6g}k {row[0]} {row[2]} {row[1]:10.2f} {row[3]:10.2f}")
        for rs, col in zip(RS_TR, ('C0', 'C1')):
            sl = []
            for kind, ls in (('tl', '-'), ('mm', '--')):
                t, v, _, _ = run(case, kind, 'step', rs)
                ax[2, j].plot(t * 1e6, v, ls, color=col, label=label(kind, rs))
                sl.append(slope(t, v))
            print(f"{case:3s} step 0 -> {CASES[case]['step']} V, Rs = {rs/1e3:g}k: output slope "
                  f"transistor {sl[0]:6.2f} V/us, model {sl[1]:6.2f} V/us")
        rd = []
        for kind, ls in (('tl', '-'), ('mm', '--')):
            t, v, _, _ = run(case, kind, 'rec')
            k = np.searchsorted(t, 44.9e-6)
            v0, v1 = v[k], v[-1]
            i10 = k + np.argmax(np.sign(v1 - v0) * (v[k:] - v0) > 0.1 * abs(v1 - v0))
            rd.append((t[i10] - 45e-6) * 1e6)
            ax[2, 2].plot(t * 1e6, v, ls, color='C3' if case == 'A' else 'C4', label=f'{case}, {label(kind)}')
        print(f"{case:3s} recovery after 40 us in reversal: delay transistor {rd[0]:5.2f} us, model {rd[1]:5.2f} us")
        ax[0, j].set_title(f"{case}: follower, DC sweep: output, V", loc='left')
        ax[1, j].set_title(f'{case}: input current (into the pin), µA', loc='left')
        ax[2, j].set_title(f"{case}: step 0 → {CASES[case]['step']} V at 5 µs: output, V", loc='left')
        ax[0, j].set_xlabel('input, V'); ax[1, j].set_xlabel('input, V'); ax[2, j].set_xlabel('t, µs')
        ax[0, j].legend(fontsize=8); ax[2, j].legend(fontsize=8)
    print('\nC: follower into 100 kOhm, slow triangle 1.5 -> 2.5 -> 1.5 V')
    for kind, ls in (('tl', '-'), ('mm', '--')):
        t, v, _, vin = run('C', kind, 'tri')
        ax[0, 2].plot(vin, v, ls, color='C0', label=label(kind))
        ax[1, 2].plot(t * 1e3, v, ls, color='C0', label=label(kind))
        print(f"    {label(kind):10s}: output stops at {v.max():.3f} V; reversal: {'yes' if v.min() < 0 else 'none'}")
    ax[1, 2].plot(t * 1e3, vin, ':', color='#777777', label='input')
    ax[0, 2].set_title('C: follower, slow triangle: output vs input, V', loc='left')
    ax[1, 2].set_title('C: output and input vs time, V', loc='left')
    ax[0, 2].set_xlabel('input, V'); ax[1, 2].set_xlabel('t, ms')
    ax[0, 2].legend(fontsize=8); ax[1, 2].legend(fontsize=8)
    ax[2, 2].set_title('A, B: 40 µs in reversal, then back to 0 V: output, V', loc='left')
    ax[2, 2].set_xlabel('t, µs'); ax[2, 2].legend(fontsize=8)
    for a in ax.flat:
        a.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(os.path.join(HERE, 'reversal_compare.png'), dpi=90)
    print('\nwrote reversal_compare.png')


if __name__ == '__main__':
    main()
