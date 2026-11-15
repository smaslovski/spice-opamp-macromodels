#!/usr/bin/env python3
# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
"""Simulation cost of OPAMP_FULL against the transistor-level uA741 (D), in ngspice.

    cd tests/transistor_level && python3 benchmark_speed.py [--repeat 3]

Both op amps are run in the same follower bench (+/-15 V, 2 kOhm || 100 pF load)
through the same analyses. OPAMP_FULL uses its defaults with KJUMP=0.27 (a 741-like
set). For each analysis the script prints the best analysis time of several runs, the
Newton iterations, and the circuit size (equations, matrix non-zeros). Times depend on
the machine; the ratios are what matter.
"""
import os, re, subprocess, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
LIB = os.path.join(HERE, '..', '..', 'models', 'opamp_full.lib')
os.makedirs(OUT, exist_ok=True)

DUT = {
    'OPAMP_FULL': (f'.include {LIB}', 'X1 p out vcc vee out OPAMP_FULL PARAMS: KJUMP=0.27'),
    'uA741 (D)': (f".include {os.path.join(HERE, 'opa_ua741.lib')}", 'X1 p out vcc vee out OPA_UA741'),
}
ANALYSES = [
    ('operating point', 'op'),
    ('DC sweep, 2001 points', 'dc Vin -10 10 0.01'),
    ('AC, 351 points', 'ac dec 50 1 100Meg'),
    ('noise, 121 points', 'noise v(out) Vin dec 20 1 1Meg'),
    ('transient, step <= 10 ns', 'tran 10n 200u'),
    ('transient, adaptive step', 'tran 0.1u 200u 0 10u'),
]


def run(inc, x, an):
    cir = os.path.join(OUT, 'bench.cir')
    open(cir, 'w').write(f"""* benchmark
{inc}
Vcc vcc 0 15
Vee vee 0 -15
Vin in 0 DC 0 AC 1 PULSE(-5 5 10u 10n 10n 50u 100u)
Vs in p 0
{x}
RL out 0 2k
CL out 0 100p
.control
{an}
rusage all
.endc
.end
""")
    o = subprocess.run(['ngspice', '-b', cir], cwd=OUT, capture_output=True, text=True).stdout
    g = lambda pat: (re.findall(pat, o) or ['nan'])[-1]
    return (float(g(r'Total analysis time \(seconds\) = ([\d.]+)')), g(r'Total iterations = (\d+)'),
            g(r'Circuit Equations = (\d+)'), g(r'original non-zeroes = (\d+)'))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--repeat', type=int, default=3)
    a = ap.parse_args()
    names = list(DUT)
    res = {}
    for n in names:
        for lab, an in ANALYSES:
            runs = [run(*DUT[n], an) for _ in range(a.repeat)]
            res[n, lab] = (min(r[0] for r in runs),) + runs[0][1:]
    eq = {n: res[n, ANALYSES[0][0]][2:] for n in names}
    for n in names:
        print(f'{n}: {eq[n][0]} circuit equations (whole bench), {eq[n][1]} matrix non-zeros')
    print(f"\n{'analysis':28s} " + ' '.join(f'{n:>22s}' for n in names) + '   ratio')
    for lab, _ in ANALYSES:
        cells = [f'{res[n, lab][0]:8.3f} s {res[n, lab][1]:>7s} it' for n in names]
        r = res[names[0], lab][0] / max(res[names[1], lab][0], 1e-4)
        print(f'{lab:28s} ' + ' '.join(f'{c:>22s}' for c in cells) + f'   {r:5.2f}')
    print('\nratio = OPAMP_FULL time / uA741 time')


if __name__ == '__main__':
    main()
