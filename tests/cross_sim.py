#!/usr/bin/env python3
# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
"""Cross-simulator check: run the same measurement circuits in ngspice and LTspice
and compare the results (DC, AC, noise, transient, for OPAMP_FULL and FDOPAMP_FULL).

    cd tests && python3 cross_sim.py               # ngspice only (prints results)
    cd tests && python3 cross_sim.py --ltspice PATH/LTspice.exe

LTspice is run in batch mode (-b), natively on Windows or through wine elsewhere.
Without --ltspice the script looks in the usual install locations and in $LTSPICE.
The decks and logs are written to tests/xsim_out/.
"""
import argparse, glob, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'xsim_out')
MODELS = os.path.normpath(os.path.join(HERE, '..', 'models'))

SUP15 = "Vcc vcc 0 15\nVee vee 0 -15\n"
SUP5 = "Vcc vcc 0 5\nVee vee 0 -5\n"
FDGAIN4 = "R1 ip a 1k\nR2 in b 1k\nR3 a outn 4k\nR4 b outp 4k\n"

# name: (library, circuit, analysis, [(measure, kind, expression, tolerance)])
#   kind: dc | ac (dB of the complex value) | noise (V/rtHz or A/rtHz) | tran
#   tolerance: relative (dc, noise, tran) or absolute dB (ac)
CASES = {
    'dc_follow': ('opamp_full.lib', SUP15 + "Vin in 0 0.1\nX1 in out vcc vee out OPAMP_FULL\n",
                  ".dc Vin 0 0.2 0.05", [('vo', 'dc', 'V(out)@0.1', 1e-5)]),
    'dc_window': ('opamp_full.lib', SUP15 + "Vin in 0 13.5\nX1 in out vcc vee out OPAMP_FULL\n",
                  ".dc Vin 13 14 0.25", [('vwin', 'dc', 'V(out)@13.5', 1e-5)]),
    'dc_ilim': ('opamp_full.lib', SUP15 + "Vin in 0 5\nX1 in out vcc vee out OPAMP_FULL\nRL out 0 10\n",
                ".dc Vin 4 6 0.5", [('vlim', 'dc', 'V(out)@5', 1e-5), ('icc', 'dc', 'I(Vcc)@5', 1e-5)]),
    'ac_inv': ('opamp_full.lib', SUP15 + "Vin in 0 DC 0 AC 1\nR1 in m 1k\nR2 m out 10k\n"
               "X1 0 m vcc vee out OPAMP_FULL\n", ".ac dec 50 10 100Meg",
               [('g10k', 'ac', 'V(out)@10k', 1e-3), ('g100k', 'ac', 'V(out)@100k', 1e-3),
                ('g1m', 'ac', 'V(out)@1Meg', 1e-3)]),
    'ac_psrr': ('opamp_full.lib', "Vcc vcc 0 DC 15 AC 1\nVee vee 0 -15\nX1 0 out vcc vee out OPAMP_FULL\n",
                ".ac dec 20 10 10Meg", [('ps1k', 'ac', 'V(out)@1k', 1e-3), ('ps100k', 'ac', 'V(out)@100k', 1e-3)]),
    'tran_slew': ('opamp_full.lib', SUP15 + "Vin in 0 PULSE(-5 5 1u 1n 1n 50u 100u)\n"
                  "X1 in out vcc vee out OPAMP_FULL\n", ".tran 10n 40u",
                  [('t90', 'tran', 'V(out)=4', 1e-3), ('vend', 'tran', 'V(out)@30u', 1e-4)]),
    'tran_clip': ('opamp_full.lib', SUP15 + "Vin in 0 PULSE(0 -2 1u 1n 1n 20u 100u)\nR1 in m 1k\n"
                  "R2 m out 10k\nX1 0 m vcc vee out OPAMP_FULL\n", ".tran 10n 60u",
                  [('vslew', 'tran', 'V(out)@15u', 1e-3)]),
    'fd_dc': ('fdopamp_full.lib', SUP5 + "Vip ip 0 0.25\nVin in 0 -0.25\nVocm vocm 0 1\n" + FDGAIN4 +
              "X1 a b vcc vee outp outn vocm FDOPAMP_FULL\n", ".dc Vip 0 0.5 0.125",
              [('vop', 'dc', 'V(outp)@0.25', 1e-5), ('von', 'dc', 'V(outn)@0.25', 1e-3)]),
    'fd_ac': ('fdopamp_full.lib', SUP5 + "Vip ip 0 DC 0 AC 0.5\nVin in 0 DC 0 AC -0.5\n" + FDGAIN4 +
              "X1 a b vcc vee outp outn 0 FDOPAMP_FULL\n", ".ac dec 50 1k 1G",
              [('g1m', 'ac', 'V(outp)@1Meg', 1e-3), ('g20m', 'ac', 'V(outp)@20Meg', 1e-2)]),
    'fd_tran': ('fdopamp_full.lib', SUP5 + "Vip ip 0 SIN(0 2 100k)\nVin in 0 SIN(0 -2 100k)\nVocm vocm 0 0.5\n" +
                FDGAIN4 + "X1 a b vcc vee outp outn vocm FDOPAMP_FULL\n", ".tran 5n 20u",
                [('opmax', 'tran', 'max V(outp)', 2e-3), ('opmin', 'tran', 'min V(outp)', 2e-3)]),
}
# noise cases: follower (e_n) or 100k source (i_n); output noise at 10 Hz, 1 kHz, 10 kHz
for name, par, rs in (('n_en_white', 'FCEN=0 FCIN=0', '1m'), ('n_en_flicker', 'FCEN=200 FCIN=0', '1m'),
                      ('n_in_white', 'FCEN=0 FCIN=0 ENOISE=1p', '100k'),
                      ('n_in_flicker', 'FCEN=0 FCIN=100 ENOISE=1p', '100k')):
    CASES[name] = ('opamp_full.lib', SUP15 + f"Vin in 0 DC 0 AC 1\nRs in p {rs}\n"
                   f"X1 p out vcc vee out OPAMP_FULL PARAMS: {par}\n", ".noise V(out) Vin dec 10 1 100k",
                   [(f'on{f}', 'noise', f'@{f}', 1e-4) for f in ('10', '1k', '10k')])
CASES['n_gain11'] = ('opamp_full.lib', SUP15 + "Vin in 0 DC 0 AC 1\nRs in p 100k\n"
                     "X1 p m vcc vee out OPAMP_FULL PARAMS: FCIN=100 FCEN=200\nR1 m 0 1k\nR2 m out 10k\n",
                     ".noise V(out) Vin dec 10 1 100k", [(f'on{f}', 'noise', f'@{f}', 1e-4) for f in ('10', '1k')])
CASES['n_fda'] = ('fdopamp_full.lib', SUP5 + "Vip ip 0 DC 0 AC 1\nVin in 0 0\n" + FDGAIN4 +
                  "X1 a b vcc vee outp outn 0 FDOPAMP_FULL PARAMS: FCIN=1k\n",
                  ".noise V(outp,outn) Vip dec 10 1 100k", [(f'on{f}', 'noise', f'@{f}', 1e-4) for f in ('10', '1k')])


def split(expr):
    return expr.split('@') if '@' in expr else (expr, None)


def deck(name, sim):
    lib, ckt, an, meas = CASES[name]
    L = [f'* {name}', f'.include {os.path.join(MODELS, lib)}', ckt.strip()]
    if an.startswith('.noise'):
        out, src = an.split()[1], an.split()[2]
        if sim == 'ng':
            L += ['.control', 'noise ' + ' '.join(an.split()[1:]), 'setplot previous',
                  f'wrdata {name}.dat onoise_spectrum', '.endc']
        else:
            L.append(an)
            L += [f'.meas noise {m} find V(onoise) at {e[1:]}' for m, _, e, _ in meas]
    else:
        L.append(an)
        kind = an.split()[0][1:]
        for m, k, e, _ in meas:
            if k == 'tran' and e.startswith(('max', 'min')):
                L.append(f'.meas tran {m} {e} from=10u to=20u')
            elif k == 'tran' and '=' in e:
                L.append(f'.meas tran {m} when {e} rise=1')
            else:
                v, at = split(e)
                if k == 'ac' and sim == 'ng':
                    v = 'vdb' + v[1:]          # vdb(out); LTspice reports V() in dB already
                L.append(f'.meas {kind} {m} find {v} at={at}')
        if sim == 'ng':
            L.append(f'.print {kind} all')
    L.append('.end')
    return '\n'.join(L) + '\n'


def run_ng(name):
    cir = os.path.join(OUT, f'ng_{name}.cir')
    open(cir, 'w').write(deck(name, 'ng'))
    log = subprocess.run(['ngspice', '-b', os.path.basename(cir)], cwd=OUT, capture_output=True, text=True).stdout
    res = {}
    if CASES[name][2].startswith('.noise'):
        import numpy as np
        d = np.loadtxt(os.path.join(OUT, f'{name}.dat'))
        for m, _, e, _ in CASES[name][3]:
            f = float(e[1:].replace('k', 'e3'))
            res[m] = float(np.exp(np.interp(np.log(f), np.log(d[:, 0]), np.log(d[:, 1]))))
    else:
        for m in re.findall(r'^(\w+)\s+=\s+([-0-9.eE+]+)', log, re.M):
            res[m[0]] = float(m[1])
    return res


def run_lt(name, exe):
    cir = os.path.join(OUT, f'lt_{name}.cir')
    open(cir, 'w').write(deck(name, 'lt'))
    cmd = ([exe] if os.name == 'nt' else ['wine', exe]) + ['-b', os.path.basename(cir)]
    subprocess.run(cmd, cwd=OUT, capture_output=True, timeout=300)
    raw = open(cir[:-4] + '.log', 'rb').read()
    txt = raw.decode('utf-16-le') if raw[1:2] == b'\x00' else raw.decode('latin-1')
    res = {m: float(v) for m, v in re.findall(r'^(\w+): .*?=\(?([-0-9.eE+]+)', txt, re.M)}
    res.update({m: float(v) for m, v in re.findall(r'^(\w+): .*? AT ([-0-9.eE+]+)', txt, re.M)})  # 'when'
    res['_floating'] = len(re.findall('is floating', txt))
    return res


def find_ltspice(arg):
    cands = [arg, os.environ.get('LTSPICE'),
             os.path.expandvars(r'%LOCALAPPDATA%\Programs\ADI\LTspice\LTspice.exe'),
             r'C:\Program Files\ADI\LTspice\LTspice.exe',
             os.path.expanduser('~/.wine/drive_c/Program Files/ADI/LTspice/LTspice.exe')]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--ltspice', help='path to LTspice.exe')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    lt = find_ltspice(a.ltspice)
    if lt and os.name != 'nt' and not shutil.which('wine'):
        lt = None
    print(f'LTspice: {lt or "not found (ngspice results only)"}\n')
    print(f'{"case":14s} {"measure":8s} {"ngspice":>14s} {"LTspice":>14s}  diff')
    bad = 0
    for name in CASES:
        r1 = run_ng(name)
        r2 = run_lt(name, lt) if lt else {}
        if r2.get('_floating'):
            print(f'{name:14s} LTspice reports {r2["_floating"]} floating nodes'); bad += 1
        for m, kind, _, tol in CASES[name][3]:
            x, y = r1.get(m), r2.get(m)
            if x is None:
                print(f'{name:14s} {m:8s}  ngspice measurement failed'); bad += 1; continue
            if y is None:
                print(f'{name:14s} {m:8s} {x:14.6g} {"-":>14s}' + ('  LTspice measurement failed' if lt else ''))
                bad += bool(lt); continue
            d = abs(x - y) if kind == 'ac' else abs(x - y) / max(abs(x), 1e-30)
            ok = d <= tol
            bad += not ok
            print(f'{name:14s} {m:8s} {x:14.6g} {y:14.6g}  {d:.1e}{" dB" if kind == "ac" else ""}'
                  f'{"" if ok else "  <-- exceeds " + str(tol)}')
    print('\n' + ('all comparisons within tolerance' if lt and not bad else
                  f'{bad} problem(s)' if bad else 'ngspice run complete'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
