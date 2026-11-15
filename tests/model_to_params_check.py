#!/usr/bin/env python3
# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
"""Check of the model-to-params skill (decks + log_to_params.py) with ngspice.

    python3 tests/model_to_params_check.py

1. Round trip: OPAMP_FULL with known parameters is characterized with the
   ngspice decks and converted; the recovered values are compared with the
   true ones.
2. The four transistor-level references of tests/transistor_level are
   characterized; the fitted OPAMP_FULL is characterized again with the same
   decks, and the main measurements of the reference and of its fit are
   printed side by side (closure).
Decks and logs go to tests/xsim_out/m2p/.
"""
import os, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'skills', 'model-to-params'))
import make_char_decks as mk
import rejection as rj
import log_to_params as lp

OUT = os.path.join(HERE, 'xsim_out', 'm2p')
LIB = os.path.abspath(os.path.join(ROOT, 'models', 'opamp_full.lib'))
TL = os.path.abspath(os.path.join(HERE, 'transistor_level'))
os.makedirs(OUT, exist_ok=True)


def characterize(tag, include, xline, vxo=2e-3, **hdr):
    logs = []
    for kind in ('ac', 'fast', 'slow'):
        cir = os.path.join(OUT, f'{tag}_{kind}.cir')
        open(cir, 'w').write(mk.deck('ngspice', kind, part=tag, include=include, xline=xline, **hdr))
        out = subprocess.run(['ngspice', '-b', cir], cwd=OUT, capture_output=True, text=True).stdout
        open(os.path.join(OUT, f'{tag}_{kind}.log'), 'w').write(out)
        logs.append(lp.parse(out))
    P, src, notes = lp.derive(*logs, vxo=vxo)
    return P, notes, logs


def instance(P, vxo):
    return 'OPAMP_FULL PARAMS: ' + ' '.join(f'{k}={P[k]:.6g}' for k in lp.ORDER if k in P) + f' VXO={vxo:g}'


# ---- 1. round trips -------------------------------------------------------------
TRUE = {
    'defaults': ('', {}, 2e-3),
    'npn_rev': ('A0=5.4k GBW=1.78Meg FP2=4.8Meg FP3=16Meg SRR=0.54Meg SRF=0.66Meg VHD=0.67 VLD=0.72 ICMHI=0.1 '
                'ICMLO=1.5 IB=49n IOS=0 RID=1.05Meg PRHI=3.5 VPRHI=0.03 IPR=20u ROUT=33 ROUTDC=2850',
                dict(GBWN='1.8Meg', SRN='0.6Meg', W=2), 2e-3),
    'pjfet_rev': ('A0=8.7k GBW=4.83Meg FP2=35Meg FP3=118Meg SR=11.9Meg VHD=0.71 VLD=0.72 ICMHI=1 ICMLO=2.8 VK=0.5 '
                  'IB=15p IOS=0 RID=1T RIC=1T PRLO=1.6 VPRLO=0.15 IPR=200u',
                  dict(GBWN='5Meg', SRN='12Meg', W=4), 2e-3),
    'cmos_rr': ('A0=100k GBW=5Meg SR=5Meg FP2=15Meg FP3=50Meg VOS=2m IB=1p IOS=0.5p RID=1T CID=2p RIC=2T CIC=1.5p '
                'CMRR=10k FCMRR=5k PSRR=10k FPSRR=1k VCCN=5 VEEN=0 ICCQ=1m VHD=0.05 VLD=0.05 '
                'ICMHI=-0.1 ICMLO=-0.1 VK=0.05 ROUT=100 ISRC=40m ISNK=40m VXO=0 COUT=2p',
                dict(VCC=5, VEE=0, VCM=2.5, GBWN='5Meg', SRN='5Meg', VSTEP=3, VSS='20m', W=1, OVR=0.3), 0),
    'jump_clamp': ('KJUMP=0.27 SRR=0.4Meg SRF=0.6Meg VCLMP=0.7 RCLMP=100 IB=-200n IOS=10n CMRR=100k '
                   'PSRRP=50k PSRRN=20k FPSRRP=30 FPSRRN=300 VOS=-0.5m', {}, 2e-3),
    'jump_pnp': ('KJUMP=-0.3 SR=2Meg ICMHI=1.2 ICMLO=0.9 VK=0.05', dict(SRN='2Meg'), 2e-3),
}
# the defaults of OPAMP_FULL that a round trip should return when not set
# (CMRR, PSRRP, PSRRN are replaced in truth() by what the rejection rules give)
DEF = dict(A0=200e3, GBW=1e6, VOS=1e-3, IB=80e-9, IOS=20e-9, RID=2e6, CID=1.4e-12, RIC=400e6, CIC=0.75e-12,
           CMRR=31.6e3, PSRRP=31.6e3, PSRRN=31.6e3, ICCQ=1.7e-3, ICMHI=2, ICMLO=2, VK=0.15, VHD=2, VLD=2,
           ROUT=75, ISRC=25e-3, ISNK=25e-3)
# parameters that can only be found as limits (or are model-internal)
SKIP = {'FP2', 'FP3', 'COUT', 'VXO', 'FCMRR', 'FPSRR', 'VCCN', 'VEEN'}


def truth(params):
    t = dict(DEF)
    for kv in params.split():
        k, v = kv.split('=')
        t[k] = lp.num(v)
    # CMRR, PSRRP, PSRRN: the effective values of the rejection rules (model 1.6)
    v = rj.evaluate(dict(kv.split('=') for kv in params.split()))
    for k, q in (('CMRR', 'C'), ('PSRRP', 'P'), ('PSRRN', 'N')):
        t[k] = 1 / abs(v[f'T{q}0'])
    if 'SR' in t and 'SRR' not in t:
        t['SR'] = t['SR']
    elif 'SRR' in t:
        t['SR'] = 0.5 * (t['SRR'] + t['SRF'])
    else:
        t['SR'] = 0.5e6
    return t


def roundtrips():
    print('1. Round trip: OPAMP_FULL with known parameters (worst relative error per case)')
    bad = 0
    for tag, (params, hdr, vxo) in TRUE.items():
        P, notes, _ = characterize('rt_' + tag, f'.include {LIB}', 'XV inp inn vcc vee out OPAMP_FULL ' +
                                   (f'PARAMS: {params}' if params else ''), vxo=vxo, **hdr)
        t = truth(params)
        errs = []
        for k, v in P.items():
            if k in SKIP or k not in t:
                continue
            if k in ('RID', 'RIC') and t[k] >= 1e12:
                continue                         # beyond what 1 mHz resolves
            if k in ('ISRC', 'ISNK') and 'VHD=0.05' in params:
                continue                         # limited by the swing, not by ISRC
            if k == 'VK' and ('PRHI' in params or 'PRLO' in params):
                continue                         # one edge next to a junction: checked by the closure
            if k in ('IB', 'IOS') and abs(t[k]) < 1e-10:
                continue                         # pA: the RIC current (to mid-supply) adds to it
            ref = t[k]
            e = abs(v - ref) / max(abs(ref), 1e-15) if k not in ('VOS', 'IOS', 'ICMHI', 'ICMLO', 'VPRHI', 'VPRLO') \
                else abs(v - ref) / max(abs(ref), 0.05 if k.startswith(('ICM', 'VPR')) else abs(t.get('IB', 1)) if k == 'IOS' else 1e-3)
            errs.append((e, k, v, ref))
        errs.sort(reverse=True)
        worst = ', '.join(f'{k} {v:.4g} ({ref:.4g})' for e, k, v, ref in errs[:3])
        flag = 'ok ' if errs[0][0] < 0.08 else 'BAD'
        bad += flag == 'BAD'
        print(f'  {flag} {tag:11s} max {errs[0][0] * 100:5.1f} %   largest: {worst}')
    return bad


# ---- 2. transistor-level references and closure ---------------------------------
REFS = {
    'A npn': ('opa_npn.lib', 'OPA_NPN', dict(GBWN='1.7Meg', SRN='0.6Meg', W=2), 2e-3),
    'B pjfet': ('opa_pjfet.lib', 'OPA_PJFET', dict(GBWN='4.8Meg', SRN='12Meg', W=4), 2e-3),
    'C pmos': ('opa_pmos.lib', 'OPA_PMOS', dict(VCC=2.5, VEE=-2.5, RL='100k', GBWN='10Meg', SRN='6.5Meg',
                                                VSTEP=2, VSS='20m', W=1.5, ILOAD='10u'), 0),
    'D ua741': ('opa_ua741.lib', 'OPA_UA741', dict(GBWN='0.6Meg', SRN='0.5Meg', W=3), 2e-3),
}
SHOW = [('a0_db', 'A0, dB', 1), ('fu', 'fu, MHz', 1e-6), ('ph_fu', 'phase at fu', 1), ('cmrr_db', 'CMRR, dB', 1),
        ('vos', 'VOS, mV', 1e3), ('ibp', 'IB(+), nA', 1e9), ('iq', 'Iq, mA', 1e3), ('voh_rl', 'swing +, V', 1),
        ('vol_rl', 'swing -, V', 1), ('ss_max', 'small step max, V', 1), ('vf1t', 'follower +10 mV top, V', 1),
        ('vf1b', 'follower +10 mV bottom, V', 1), ('vstopt', 'follower stop top, V', 1),
        ('vstopb', 'follower stop bottom, V', 1), ('vipt', 'flip top, V', 1), ('vipb', 'flip bottom, V', 1),
        ('iendt', 'pin current, top end, uA', 1e6), ('iendb', 'pin current, bottom end, uA', 1e6)]
FSHOW = [('t50ri', 't85ri', 'SR rising (inverter), V/us'), ('t50fi', 't85fi', 'SR falling (inverter), V/us'),
         ('rt_t1', 'rt_t2', 'reversed slope top, V/us'), ('rb_t1', 'rb_t2', 'reversed slope bottom, V/us')]


def closure():
    print('\n2. Transistor-level references: measured, and measured again on the fitted OPAMP_FULL')
    for name, (lib, sub, hdr, vxo) in REFS.items():
        inc = f'.include {TL}/devices.lib\n.include {TL}/{lib}'
        tag = 'tl_' + name.split()[0]
        P, notes, logs = characterize(tag, inc, f'XV inp inn vcc vee out {sub}', vxo=vxo, **hdr)
        inst = instance(P, vxo)
        P2, _, logs2 = characterize(tag + '_fit', f'.include {LIB}', 'XV inp inn vcc vee out ' + inst, vxo=vxo, **hdr)
        print(f'\n  {name}: X1 inp inn vcc vee out {inst}')
        for n in notes:
            print('    - ' + n)
        m1, m2 = {**logs[0], **logs[1], **logs[2]}, {**logs2[0], **logs2[1], **logs2[2]}
        print(f"    {'quantity':30s} {'reference':>11s} {'fitted model':>13s}")
        for k, lab, sc in SHOW:
            if k in ('vipt', 'vipb') and ('VPRHI' if k == 'vipt' else 'VPRLO') not in P:
                continue
            a, b = m1.get(k), m2.get(k)
            if a is None and b is None:
                continue
            fa = f'{a * sc:11.4g}' if a is not None else f"{'-':>11s}"
            fb = f'{b * sc:13.4g}' if b is not None else f"{'-':>13s}"
            print(f'    {lab:30s} {fa} {fb}')
        for k1, k2, lab in FSHOW:
            row = []
            for m in (m1, m2):
                if k1 in m and k2 in m:
                    span = 0.35 * m['vstep'] if 'SR' in lab else 0.4 * (m['vcm'] - m['vee'] if 'top' in lab else m['vcc'] - m['vcm'])
                    row.append(span / (m[k2] - m[k1]) * 1e-6)
                else:
                    row.append(None)
            if row[0] is None and row[1] is None:
                continue
            print(f"    {lab:30s} " + ' '.join(f'{x:{w}.4g}' if x is not None else f"{'-':>{w}s}" for x, w in zip(row, (11, 13))))


if __name__ == '__main__':
    nbad = roundtrips()
    closure()
    sys.exit(1 if nbad else 0)
