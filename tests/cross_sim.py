#!/usr/bin/env python3
# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
"""Cross-simulator check: run the same measurement circuits in ngspice, LTspice and
PSpice and compare the results with ngspice (DC, AC, noise, transient, for OPAMP_FULL
and FDOPAMP_FULL). PSpice uses the port in models/pspice/.

    cd tests && python3 cross_sim.py               # ngspice only (prints results)
    cd tests && python3 cross_sim.py --ltspice PATH/LTspice.exe --pspice PATH/pspice.exe

LTspice runs in batch mode (-b), PSpice with -r -e; both natively on Windows or
through wine elsewhere. Without the options the script looks in the usual install
locations and in $LTSPICE / $PSPICE. Decks and logs are written to tests/xsim_out/.
$LTSPICE_WINEPREFIX / $PSPICE_WINEPREFIX choose a wine prefix per simulator.
PSpice 9.1 (the 1999 student/evaluation version) is enough.
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
    'dc_vcmn': ('opamp_full.lib', SUP15 + "Vin in 0 5\nX1 in out vcc vee out OPAMP_FULL PARAMS: VCMN=5 CMRR=1k\n",
                ".dc Vin 4 6 0.5", [('vo', 'dc', 'V(out)@5', 1e-5)]),
    'dc_clamp': ('opamp_full.lib', SUP15 + "Vin in 0 2\nRs in p 1k\nX1 p 0 vcc vee out OPAMP_FULL PARAMS: VCLMP=0.7 RCLMP=100\nRL out 0 10k\n",
                 # diode at 1 mA: the DC sweep converges only to ~1e-4 (ngspice .op vs .dc differ by 9e-5)
                 ".dc Vin 1 3 0.5", [('vp', 'dc', 'V(p)@2', 3e-4), ('vo', 'dc', 'V(out)@2', 1e-5)]),
    'dc_rr': ('opamp_full.lib', "Vcc vcc 0 5\nVee vee 0 0\nVin in 0 4.9\nX1 in out vcc vee out OPAMP_FULL PARAMS: "
              "GBW=10Meg SR=10Meg VCCN=5 VEEN=0 VHD=0.05 VLD=0.05 ICMHI=-0.1 ICMLO=-0.1 VK=0.05 ROUT=100 VXO=0\n"
              "RL out 0 1k\n", ".dc Vin 4.8 5 0.05", [('vo', 'dc', 'V(out)@4.9', 1e-5)]),
    'ac_inv': ('opamp_full.lib', SUP15 + "Vin in 0 DC 0 AC 1\nR1 in m 1k\nR2 m out 10k\n"
               "X1 0 m vcc vee out OPAMP_FULL\n", ".ac dec 50 10 100Meg",
               [('g10k', 'ac', 'V(out)@10k', 1e-3), ('g100k', 'ac', 'V(out)@100k', 1e-3),
                ('g1m', 'ac', 'V(out)@1Meg', 1e-3)]),
    'ac_psrr': ('opamp_full.lib', "Vcc vcc 0 DC 15 AC 1\nVee vee 0 -15\nX1 0 out vcc vee out OPAMP_FULL\n",
                ".ac dec 20 10 10Meg", [('ps1k', 'ac', 'V(out)@1k', 1e-3), ('ps100k', 'ac', 'V(out)@100k', 1e-3)]),
    'ac_psrrp2': ('opamp_full.lib', "Vcc vcc 0 DC 15 AC 1\nVee vee 0 -15\n"
                  "X1 0 out vcc vee out OPAMP_FULL PARAMS: FPSRRP=10 FPSRRN=1k\n",
                  ".ac dec 20 10 10Meg", [('psp10k', 'ac', 'V(out)@10k', 1e-3)]),
    'ac_psrrn2': ('opamp_full.lib', "Vcc vcc 0 15\nVee vee 0 DC -15 AC 1\n"
                  "X1 0 out vcc vee out OPAMP_FULL PARAMS: FPSRRP=10 FPSRRN=1k\n",
                  ".ac dec 20 10 10Meg", [('psn10k', 'ac', 'V(out)@10k', 1e-3)]),
    'tran_slew': ('opamp_full.lib', SUP15 + "Vin in 0 PULSE(-5 5 1u 1n 1n 50u 100u)\n"
                  "X1 in out vcc vee out OPAMP_FULL\n", ".tran 10n 40u",
                  [('t90', 'tran', 'V(out)=4', 1e-3), ('vend', 'tran', 'V(out)@30u', 1e-4)]),
    'tran_tail': ('opamp_full.lib', SUP15 + "Vin in 0 PULSE(-5 5 1u 20n 20n 44.6u 200u)\n"
                  "X1 in out vcc vee out OPAMP_FULL PARAMS: KJUMP=0.27\nRL out 0 2k\nCL out 0 100p\n", ".tran 10n 70u",
                  [('vjump', 'tran', 'V(out)@1.3u', 2e-3), ('vrise', 'tran', 'V(out)@10u', 5e-3),
                   ('vfall', 'tran', 'V(out)@52u', 5e-3)]),
    'tran_tailneg': ('opamp_full.lib', SUP15 + "Vin in 0 PULSE(-5 5 1u 20n 20n 44.6u 200u)\n"
                     "X1 in out vcc vee out OPAMP_FULL PARAMS: KJUMP=-0.27\nRL out 0 2k\nCL out 0 100p\n", ".tran 10n 70u",
                     [('vrise', 'tran', 'V(out)@5u', 5e-3), ('vjumpf', 'tran', 'V(out)@45.9u', 2e-3),
                      ('vfall', 'tran', 'V(out)@55u', 5e-3)]),
    'tran_srasym': ('opamp_full.lib', SUP15 + "Vin in 0 PULSE(-5 5 1u 1n 1n 30u 100u)\n"
                    "X1 in out vcc vee out OPAMP_FULL PARAMS: SRR=0.5Meg SRF=1Meg\nRL out 0 2k\n", ".tran 10n 60u",
                    [('vrise', 'tran', 'V(out)@8u', 2e-3), ('vfall', 'tran', 'V(out)@35u', 5e-3)]),
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
    subprocess.run(cmd, cwd=OUT, capture_output=True, timeout=300, env=wine_env('LTSPICE'))
    if not os.path.exists(cir[:-4] + '.log'):
        return {'_errors': ['no log file (LTspice did not run)']}
    raw = open(cir[:-4] + '.log', 'rb').read()
    txt = raw.decode('utf-16-le') if raw[1:2] == b'\x00' else raw.decode('latin-1')
    res = {m: float(v) for m, v in re.findall(r'^(\w+): .*?=\(?([-0-9.eE+]+)', txt, re.M)}
    res.update({m: float(v) for m, v in re.findall(r'^(\w+): .*? AT ([-0-9.eE+]+)', txt, re.M)})  # 'when'
    res['_floating'] = len(re.findall('is floating', txt))
    return res


def wine_env(sim):
    """$LTSPICE_WINEPREFIX / $PSPICE_WINEPREFIX select a wine prefix per simulator"""
    env = dict(os.environ)
    if os.environ.get(sim + '_WINEPREFIX'):
        env['WINEPREFIX'] = os.environ[sim + '_WINEPREFIX']
    env.setdefault('WINEDEBUG', '-all')
    return env


def ps_name(v):
    """V(out) -> V([out]); node names in brackets (needed by PSpice 9 under wine)"""
    return re.sub(r'V\((\w+)\)', r'V([\1])', v)


def ps_deck(name):
    lib, ckt, an, meas = CASES[name]
    rel = os.path.relpath(os.path.join(MODELS, 'pspice', lib), OUT).replace('/', '\\')
    L = [f'* {name}', f'.INC {rel}']
    for ln in ckt.strip().split('\n'):          # PSpice 9: 132 characters per line
        while len(ln) > 100:
            cut = ln.rfind(' ', 0, 100)
            L.append(ln[:cut])
            ln = '+' + ln[cut:]
        L.append(ln)
    L.append('.OPTIONS NUMDGT=8')
    w = an.split()
    if w[0] == '.noise':
        out = w[1]
        m = re.match(r'V\((\w+)(?:,(\w+))?\)', out)
        node = f'V([{m.group(1)}],[{m.group(2)}])' if m.group(2) else f'V([{m.group(1)}])'
        L += [f'.AC {" ".join(w[3:])}', f'.NOISE {node} {w[2]}', '.PRINT NOISE ONOISE']
        cols = ['ONOISE']
    else:
        kind = w[0][1:]
        cols = []
        for _, k, e, _ in meas:
            v = split(e)[0] if '@' in e else (e.split('=')[0] if '=' in e else e.split()[1])
            v = ps_name(v)
            if k == 'ac':
                v = 'VDB' + v[1:]
            if v not in cols:
                cols.append(v)
        if kind == 'tran':
            L.append(f'.TRAN {w[1]} {w[2]} 0 {w[1]}')
        else:
            L.append(an.upper().replace('MEG', 'Meg'))
        L.append(f'.PRINT {kind.upper()} ' + ' '.join(cols))
    L.append('.END')
    return '\r\n'.join(L) + '\r\n', cols


def run_ps(name, exe):
    import numpy as np
    txt, cols = ps_deck(name)
    cir = os.path.join(OUT, f'ps_{name}.cir')
    open(cir, 'w', newline='').write(txt)
    outf = cir[:-4] + '.out'
    if os.path.exists(outf):
        os.remove(outf)
    cmd = ([exe] if os.name == 'nt' else ['wine', exe]) + ['-r', '-e', os.path.basename(cir)]
    subprocess.run(cmd, cwd=OUT, capture_output=True, timeout=600, env=wine_env('PSPICE'))
    res = {}
    if not os.path.exists(outf):
        return res
    lines = open(outf, errors='ignore').read().replace('\r', '').split('\n')
    if any(l.startswith('ERROR') for l in lines):
        res['_errors'] = [l for l in lines if l.startswith('ERROR')]
        return res
    rows = []
    for l in lines:
        t = l.split()
        if len(t) == len(cols) + 1:
            try:
                rows.append([float(x) for x in t])
            except ValueError:
                pass
    if not rows:
        return res
    d = np.array(rows)
    x = d[:, 0]
    for m, k, e, _ in CASES[name][3]:
        if k == 'noise':
            f = float(e[1:].replace('k', 'e3'))
            res[m] = float(np.exp(np.interp(np.log(f), np.log(x), np.log(d[:, 1]))))
        elif k == 'tran' and e.startswith(('max', 'min')):
            y = d[:, 1 + cols.index(ps_name(e.split()[1]))]
            sel = (x >= 10e-6) & (x <= 20e-6)
            res[m] = float(y[sel].max() if e.startswith('max') else y[sel].min())
        elif k == 'tran' and '@' not in e:
            v, lvl = e.split('=')
            y = d[:, 1 + cols.index(ps_name(v))]
            i = np.where((y[:-1] < float(lvl)) & (y[1:] >= float(lvl)))[0][0]
            res[m] = float(x[i] + (float(lvl) - y[i]) * (x[i + 1] - x[i]) / (y[i + 1] - y[i]))
        else:
            v, at = split(e)
            at = float(at.lower().replace('meg', 'e6').replace('k', 'e3').replace('u', 'e-6'))
            c = ps_name(v)
            if k == 'ac':
                c = 'VDB' + c[1:]
            y = d[:, 1 + cols.index(c)]
            res[m] = float(np.interp(np.log(at), np.log(x), y) if k == 'ac' else np.interp(at, x, y))
    return res


def find_pspice(arg):
    cands = [arg, os.environ.get('PSPICE'), r'C:\\Program Files\\OrCAD_Demo\\PSpice\\pspice.exe',
             r'C:\\Program Files (x86)\\OrCAD_Demo\\PSpice\\pspice.exe',
             os.path.expanduser('~/.wine/drive_c/Program Files/OrCAD_Demo/PSpice/pspice.exe'),
             os.path.expanduser('~/.wine/drive_c/Program Files (x86)/OrCAD_Demo/PSpice/pspice.exe')]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


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
    ap.add_argument('--pspice', help='path to pspice.exe (PSpice A/D)')
    ap.add_argument('cases', nargs='*', help='run only these cases')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    wine_ok = os.name == 'nt' or shutil.which('wine')
    sims = []
    lt = find_ltspice(a.ltspice)
    if lt and wine_ok:
        sims.append(('LTspice', lambda n: run_lt(n, lt)))
    ps = find_pspice(a.pspice)
    if ps and wine_ok:
        sims.append(('PSpice', lambda n: run_ps(n, ps)))
    print(f'LTspice: {lt or "not found"}\nPSpice:  {ps or "not found"}\n')
    print(f'{"case":14s} {"measure":8s} {"ngspice":>14s}' + ''.join(f' {s:>14s}  diff    ' for s, _ in sims))
    bad = 0
    for name in (a.cases or CASES):
        r1 = run_ng(name)
        rs = [(s, f(name)) for s, f in sims]
        for s, r in rs:
            if r.get('_floating'):
                print(f'{name:14s} {s} reports {r["_floating"]} floating nodes'); bad += 1
            for e in r.get('_errors', []):
                print(f'{name:14s} {s}: {e}'); bad += 1
        for m, kind, _, tol in CASES[name][3]:
            x = r1.get(m)
            if x is None:
                print(f'{name:14s} {m:8s}  ngspice measurement failed'); bad += 1; continue
            line = f'{name:14s} {m:8s} {x:14.6g}'
            for s, r in rs:
                y = r.get(m)
                if y is None:
                    line += f' {"failed":>14s}          '; bad += 1; continue
                d = abs(x - y) if kind == 'ac' else abs(x - y) / max(abs(x), 1e-30)
                ok = d <= tol
                bad += not ok
                line += f' {y:14.6g}  {d:.1e}{"dB" if kind == "ac" else "  "}{" " if ok else "!"} '
            print(line)
    print('\n' + (f'{bad} problem(s) (! = outside tolerance)' if bad else
                  'all comparisons within tolerance' if sims else 'ngspice run complete'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
