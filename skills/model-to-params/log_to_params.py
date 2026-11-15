#!/usr/bin/env python3
# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
"""Convert the output of the model-to-params characterization decks into
OPAMP_FULL parameters (the optional companion of skills/model-to-params/SKILL.md).

    python3 log_to_params.py AC_LOG FAST_LOG SLOW_LOG [--vxo 2m] [--name OPA]

Each log is what the simulator wrote for one deck: the ngspice console output
(ngspice -b char_ac.cir > ac.log), the LTspice .log file, or the PSpice .out
file. The format is recognised automatically. The script prints an OPAMP_FULL
instance line and a table with the measured quantity behind every value.
It implements the formulas of the skill exactly; it needs only Python 3.
"""
import math, re, sys, argparse

VT = 1.380649e-23 * 300.15 / 1.602176634e-19       # thermal voltage at 27 C
SUF = {'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3, 'k': 1e3,
       'meg': 1e6, 'g': 1e9, 't': 1e12}


def num(s):
    """A SPICE number with an optional suffix (1Meg, 10k, 2.5m, 1e-3)."""
    s = s.strip().lower()
    m = re.match(r'^([-+]?[0-9.]+(?:e[-+]?\d+)?)(meg|[fpnumkgt])?', s)
    if not m:
        raise ValueError(s)
    return float(m.group(1)) * SUF.get(m.group(2) or '', 1)


# ---- parsers: every log becomes {name: value} with the ngspice names and units ----
WHEN = {'fu', 'f40', 'f20', 'fcm3', 'fcm20', 'fpsp3', 'fpsp20', 'fpsn3', 'fpsn20',
        't50r', 't85r', 't50f', 't85f', 't50ri', 't85ri', 't50fi', 't85fi', 'rt_t1', 'rt_t2', 'rb_t1', 'rb_t2'}
DB = {'a0_db', 'cmrr_db', 'cmrr_gbw', 'psrrp_db', 'psrrn_db'}


def parse_ngspice(txt):
    r = {}
    for m in re.finditer(r'^\s*([a-z][a-z0-9_]*)\s+=\s+([-+0-9.eE]+)', txt, re.M):
        r[m.group(1)] = float(m.group(2))
    for m in re.finditer(r'^x?([a-z]+) = ([-+0-9.eE]+)$', txt, re.M):   # print of parameters
        r[m.group(1)] = float(m.group(2))
    return r


def parse_ltspice(txt):
    r = {}
    for line in txt.splitlines():
        m = re.match(r'^\s*([a-z][a-z0-9_]*):\s*(.*)$', line.strip(), re.I)
        if not m or 'FAIL' in line.upper():
            continue
        name, rest = m.group(1).lower(), m.group(2)
        cplx = re.search(r'\(([-+0-9.eE]+)dB,([-+0-9.eE]+)\S*\)', rest)
        at = re.search(r'\bAT\s+([-+0-9.eE]+)', rest, re.I)
        if name in WHEN and at:
            r[name] = float(at.group(1))
        elif cplx:
            db, ph = float(cplx.group(1)), float(cplx.group(2))
            if name in DB:
                r[name] = db
            elif name == 'ph_fu':
                r[name] = ph
            else:            # a real quantity printed in polar form
                r[name] = 10 ** (db / 20) * math.cos(math.radians(ph))
        else:
            v = re.search(r'=\s*([-+0-9.eE]+)', rest) or re.match(r'\s*([-+0-9.eE]+)', rest)
            if v:
                r[name] = float(v.group(1))
    for k in DB:             # mag() of a real gain ratio printed without dB
        if k in r and r[k] > 0 and '(' not in txt.split(k + ':')[-1].split('\n')[0]:
            r[k] = 20 * math.log10(r[k])
    return r


def pspice_tables(txt):
    """{column name: [values]} from the .PRINT tables of a PSpice .out file."""
    cols, x = {}, None
    lines = txt.splitlines()
    i = 0
    while i < len(lines):
        h = lines[i].split()
        if h and h[0] in ('FREQ', 'TIME'):
            names = [n.lower() for n in h]
            rows = []
            i += 1
            while i < len(lines):
                p = lines[i].split()
                if not p:
                    if rows:
                        break
                    i += 1
                    continue
                try:
                    rows.append([float(v) for v in p])
                except ValueError:
                    break
                i += 1
            for j, n in enumerate(names):
                cols[n] = [row[j] for row in rows if len(row) == len(names)]
            continue
        i += 1
    return cols


def pspice_params(txt):
    """The .PARAM values of the deck, from the netlist echo of the .out file."""
    p = {}
    for line in txt.splitlines():
        if line.strip().lower().startswith('.param'):
            for k, v in re.findall(r'(\w+)\s*=\s*([^\s{}]+)(?=\s|$)', line):
                try:
                    p[k.lower()] = num(v)
                except ValueError:
                    pass
    p['ts'] = 4 * p['vstep'] / p['srn'] + 5 / p['gbwn'] if 'vstep' in p else None
    if 'w' in p:
        p['tr'] = (p['w'] + p['ovr']) * 1e4 / p['srn'] + 1e4 / p['gbwn']
        p['vsh'] = min(1, 0.2 * (p['vcc'] - p['vee']))
        p['vcl'] = min(1.5, 0.9 * (p['vcc'] - p['vcm']))
    return p


def interp_x(x, y, level, sense, start=0.0, logx=False):
    """First x >= start where y crosses level (sense +1 rising, -1 falling)."""
    for k in range(1, len(x)):
        if x[k] < start:
            continue
        a, b = y[k - 1] - level, y[k] - level
        if sense * a < 0 <= sense * b:
            t = a / (a - b)
            if logx:
                return 10 ** (math.log10(x[k - 1]) + t * (math.log10(x[k]) - math.log10(x[k - 1])))
            return x[k - 1] + t * (x[k] - x[k - 1])
    return None


def interp_y(x, y, x0, logx=False):
    for k in range(1, len(x)):
        if x[k] >= x0:
            if logx:
                t = (math.log10(x0) - math.log10(x[k - 1])) / (math.log10(x[k]) - math.log10(x[k - 1]))
            else:
                t = (x0 - x[k - 1]) / (x[k] - x[k - 1])
            return y[k - 1] + t * (y[k] - y[k - 1])
    return None


def window(x, y, a, b, fn):
    v = [yy for xx, yy in zip(x, y) if a <= xx <= b]
    return fn(v) if v else None


def avg(v):
    return sum(v) / len(v)


def parse_pspice(txt):
    """The ngspice measurements, computed from the PSpice tables."""
    c, p = pspice_tables(txt), pspice_params(txt)
    r = {k: v for k, v in p.items() if v is not None}
    if 'freq' in c:
        f = c['freq']
        ag = c['vdb(o1)']
        ph = c['vp(o1)']
        r['a0_db'] = ag[0]
        r['fu'] = interp_x(f, ag, 0, -1, logx=True)
        r['f40'] = interp_x(f, ag, 40, -1, logx=True)
        r['f20'] = interp_x(f, ag, 20, -1, logx=True)
        # continuous phase
        un, off = [], 0.0
        for k, v in enumerate(ph):
            if k and v - ph[k - 1] > 180:
                off -= 360
            elif k and v - ph[k - 1] < -180:
                off += 360
            un.append(v + off)
        if r['fu']:
            r['ph_fu'] = interp_y(f, un, r['fu'], logx=True)
        for key, col in (('cmrr', 'vdb(o2)'), ('psrrp', 'vdb(o3)'), ('psrrn', 'vdb(o4)')):
            cur = [a - b for a, b in zip(ag, c[col])]
            r[key + '_db'] = cur[0]
            tag = {'cmrr': 'fcm', 'psrrp': 'fpsp', 'psrrn': 'fpsn'}[key]
            r[tag + '3'] = interp_x(f, cur, cur[0] - 3, -1, logx=True)
            r[tag + '20'] = interp_x(f, cur, cur[0] - 20, -1, logx=True)
            if key == 'cmrr':
                r['cmrr_gbw'] = interp_y(f, cur, p['gbwn'], logx=True)
            pcol = 'vp(' + col[4:]
            if pcol in c:      # sign: Re(V(ox)/V(o1)) at the first frequency
                r[key + '_sg'] = math.cos(math.radians(c[pcol][0] - ph[0]))
        g = p['gbwn']
        for k, fx in (('zo_a', g / 100), ('zo_b', g / 10), ('zo_c', g)):
            r[k] = interp_y(f, c['vm(o5)'], fx, logx=True)
        r['zo_dc'] = c['vm(o5)'][0]
        if 'vdb(o8)' in c:
            r['a0u_db'] = c['vdb(o8)'][0]
        r['zd_re0'], r['zc_re0'] = c['vr(p6)'][0], c['vr(p7)'][0]
        r['zd_im0'], r['zc_im0'] = c['vi(p6)'][0], c['vi(p7)'][0]
        r['zd_re'] = interp_y(f, c['vr(p6)'], g / 10, logx=True)
        r['zd_im'] = interp_y(f, c['vi(p6)'], g / 10, logx=True)
        r['zc_re'] = interp_y(f, c['vr(p7)'], g / 10, logx=True)
        r['zc_im'] = interp_y(f, c['vi(p7)'], g / 10, logx=True)
    elif 'v(o2)' in c:
        t, ts, vcm = c['time'], p['ts'], p['vcm']
        a, b = 0.5 * ts, 0.9 * ts
        r['vos'] = window(t, c['v(o1,mid)'], a, b, avg)
        r['ibp'] = window(t, c['i(vp1)'], a, b, avg)
        r['ibn'] = window(t, c['i(vn1)'], a, b, avg)
        r['iq'] = -window(t, c['i(vcc1)'], a, b, avg)
        o2, o3 = c['v(o2)'], c['v(o3)']
        r['t50r'] = interp_x(t, o2, vcm, 1)
        r['t85r'] = interp_x(t, o2, vcm + 0.35 * p['vstep'], 1)
        r['t50f'] = interp_x(t, o2, vcm, -1, 2 * ts)
        r['t85f'] = interp_x(t, o2, vcm - 0.35 * p['vstep'], -1, 2 * ts)
        oi = c['v(o2i)']
        r['t50fi'] = interp_x(t, oi, vcm, -1)
        r['t85fi'] = interp_x(t, oi, vcm - 0.35 * p['vstep'], -1)
        r['t50ri'] = interp_x(t, oi, vcm, 1, 2 * ts)
        r['t85ri'] = interp_x(t, oi, vcm + 0.35 * p['vstep'], 1, 2 * ts)
        r['vo2_lo'], r['vo2_hi'] = window(t, o2, a, b, avg), window(t, o2, 2.5 * ts, 2.9 * ts, avg)
        r['vj_r'], r['vj_f'] = interp_y(t, o2, 1.011 * ts), interp_y(t, o2, 3.012 * ts)
        r['ss_lo'], r['ss_hi'] = window(t, o3, a, b, avg), window(t, o3, 2.5 * ts, 2.9 * ts, avg)
        r['ss_max'], r['ss_min'] = window(t, o3, ts, 3 * ts, max), window(t, o3, 3 * ts, 5 * ts, min)
        for k, col in (('rl', 'v(o4)'), ('nl', 'v(o5)')):
            r['voh_' + k] = window(t, c[col], 2 * ts, 2.4 * ts, avg)
            r['vol_' + k] = window(t, c[col], 4.5 * ts, 4.9 * ts, avg)
        r['isrc'] = window(t, c['i(v6)'], 2 * ts, 2.4 * ts, avg)
        r['isnk'] = window(t, c['i(v6)'], 4.5 * ts, 4.9 * ts, avg)
        vcc, vee = p['vcc'], p['vee']
        r['rt_t1'] = interp_x(t, c['v(o7)'], vcm - 0.2 * (vcm - vee), -1)
        r['rt_t2'] = interp_x(t, c['v(o7)'], vcm - 0.6 * (vcm - vee), -1)
        r['rb_t1'] = interp_x(t, c['v(o8)'], vcm + 0.2 * (vcc - vcm), 1)
        r['rb_t2'] = interp_x(t, c['v(o8)'], vcm + 0.6 * (vcc - vcm), 1)
        r['rt_end'] = interp_y(t, c['v(o7)'], 2.9 * ts)
        r['rb_end'] = interp_y(t, c['v(o8)'], 2.9 * ts)
        r['vcl1'] = window(t, c['v(p9,mid)'], a, b, avg)
        r['icl1'] = window(t, c['v(c9,p9)'], a, b, avg) / 100
        r['vcl2'] = window(t, c['v(p10,mid)'], a, b, avg)
        r['icl2'] = window(t, c['v(c9,p10)'], a, b, avg) / 1000
    elif 'v(int)' in c:
        t, tr, vcm = c['time'], p['tr'], p['vcm']
        dm = [x - y for x, y in zip(c['v(pam,nam)'], c['v(pbm,nbm)'])]
        dt = [x - y for x, y in zip(c['v(pat,nat)'], c['v(pbt,nbt)'])]
        db = [x - y for x, y in zip(c['v(pab,nab)'], c['v(pbb,nbb)'])]
        r['dmid'] = avg(dm)
        r['dt0'], r['db0'] = dt[0], db[0]
        for side, d, vin in (('t', dt, c['v(int)']), ('b', db, c['v(inb)'])):
            for k, n in (('5', 2), ('q', 4)):
                tt = interp_x(t, [x - n * r['dmid'] for x in d], 0, 1)
                r[f'vw{k}{side}'] = interp_y(t, vin, tt) if tt is not None else None
        r['vstopt'], r['vstopb'] = max(c['v(oft)']), min(c['v(ofb)'])
        for side, vin, vo, sg in (('t', c['v(int)'], c['v(oft)'], 1), ('b', c['v(inb)'], c['v(ofb)'], -1)):
            e = [a - b for a, b in zip(vin, vo)]
            r['ef' + side + '0'] = e[0]
            for k, dd in (('1', 0.01), ('2', 0.1)):
                tt = interp_x(t, e, e[0] + sg * dd, sg)
                if tt is not None:
                    r[f'vf{k}{side}'], r[f'of{k}{side}'] = interp_y(t, vin, tt), interp_y(t, vo, tt)
        r['vendt'], r['vendb'] = c['v(oft)'][-1], c['v(ofb)'][-1]
        r['iendt'], r['iendb'] = c['i(vft)'][-1], c['i(vfb)'][-1]
        r['it0'], r['ib0'] = c['i(vft)'][0], c['i(vfb)'][0]
        tt = interp_x(t, c['i(vft)'], r['it0'] + 0.9 * (r['iendt'] - r['it0']), 1)
        if tt is not None:
            r['vipt'] = interp_y(t, c['v(int)'], tt)
        tt = interp_x(t, c['i(vfb)'], r['ib0'] + 0.9 * (r['iendb'] - r['ib0']), -1)
        if tt is not None:
            r['vipb'] = interp_y(t, c['v(inb)'], tt)
        tt = interp_x(t, c['v(oft)'], r['vstopt'] - 0.05 * (r['vstopt'] - vcm), -1)
        if tt is not None:
            r['vflt'], r['iflt'] = interp_y(t, c['v(int)'], tt), interp_y(t, c['i(vft)'], tt)
        tt = interp_x(t, c['v(ofb)'], r['vstopb'] + 0.05 * (vcm - r['vstopb']), 1)
        if tt is not None:
            r['vflb'], r['iflb'] = interp_y(t, c['v(inb)'], tt), interp_y(t, c['i(vfb)'], tt)
    return {k: v for k, v in r.items() if v is not None}


def parse(txt):
    if 'PSpice' in txt or '**** CIRCUIT DESCRIPTION' in txt:
        return parse_pspice(txt)
    if 'No. of Data Rows' in txt or re.search(r'^\w+\s+=\s', txt, re.M):
        return parse_ngspice(txt)
    return parse_ltspice(txt)


# ---- conversion -------------------------------------------------------------------
def sig(x, n=3):
    """A value in SPICE notation, n significant digits."""
    if x == 0:
        return '0'
    for s, f in (('T', 1e12), ('G', 1e9), ('Meg', 1e6), ('k', 1e3), ('', 1), ('m', 1e-3),
                 ('u', 1e-6), ('n', 1e-9), ('p', 1e-12), ('f', 1e-15)):
        if abs(x) >= f * 0.9995:
            v = float(f'{x / f:.{n}g}')
            return (f'{v:g}' + s)
    return f'{x:.{n}g}'


def logit(p):
    return math.log(p / (1 - p))


def pm_model(fp2, gbw, a0, fout):
    """Phase margin and unity-gain frequency of the OPAMP_FULL differential gain, FP3 = 3.33*FP2."""
    fp1, fp3 = gbw / a0, 3.33 * fp2

    def a(f):
        z = complex(a0)
        for p in (fp1, fp2, fp3, fout):
            z /= complex(1, f / p)
        return z
    lo, hi = gbw * 1e-3, gbw * 10
    for _ in range(100):
        m = math.sqrt(lo * hi)
        if abs(a(m)) > 1:
            lo = m
        else:
            hi = m
    ph = math.degrees(math.atan(lo / fp1) + math.atan(lo / fp2) + math.atan(lo / fp3) + math.atan(lo / fout))
    return 180 - ph, lo


def derive(ac, fast, slow, vxo=2e-3):
    P, notes = {}, []
    src = {}

    def put(k, v, s):
        P[k], src[k] = v, s
    vcc, vee, vcm, rl = fast['vcc'], fast['vee'], fast['vcm'], fast['rl']
    put('VCCN', vcc, 'deck supply')
    put('VEEN', vee, 'deck supply')
    if abs(vcm - 0.5 * (vcc + vee)) > 1e-6:
        put('VCMN', vcm, 'deck VCM')
    # output resistance first: it corrects the loaded measurements
    rout = ac['zo_b']
    put('ROUT', rout, f"|Zout| at GBWN/10 = {sig(ac['zo_b'])} ohm (GBWN/100: {sig(ac['zo_a'])}, GBWN: {sig(ac['zo_c'])})")
    if max(ac['zo_a'], ac['zo_c']) > 2 * min(ac['zo_a'], ac['zo_c']):
        notes.append('ROUT: the open-loop output impedance varies by more than 2x between GBWN/100 and GBWN; the value at GBWN/10 is used.')
    reff = (2 if vxo > 0 else 1) * rout             # small-signal ROUT at idle (VXO > 0 doubles it)
    kl = (rl + reff) / rl
    # DC output resistance and unloaded gain: from the gain with and without the
    # load (both at idle, where the model's small-signal ROUT is REFF), so that
    # A0*RL/(RL+REFF+ROUTDC) is the loaded gain. Below 10 % of ROUT it is not set.
    zdc = ac.get('zo_dc')
    if ac.get('a0u_db') is not None:
        ratio = 10 ** ((ac['a0u_db'] - ac['a0_db']) / 20)
        rodc = rl * (ratio - 1) - reff
        rodc = rodc if rodc > 0.1 * rout else 0.0
        how = (f"gain at 1 mHz {ac['a0u_db']:.2f} dB without load, {ac['a0_db']:.2f} dB into RL: "
               f"RL*(ratio-1) - {'2*' if vxo > 0 else ''}ROUT")
    else:      # older log: |Zout| at 1 mHz (at the DC load ILOAD) beyond ROUT
        rodc = zdc - rout if zdc is not None and zdc > 1.1 * rout else 0.0
        how = f"|Zout| at 1 mHz = {sig(zdc) if zdc is not None else '-'} ohm, minus ROUT"
    if rodc > 0:
        put('ROUTDC', rodc, how)
        if zdc is not None and abs((zdc - rout) - rodc) > 0.3 * rodc:
            notes.append(f'ROUTDC: |Zout| at 1 mHz with the DC load ILOAD gives {sig(zdc - rout)} ohm, the gains at idle '
                         f'{sig(rodc)} ohm: the output resistance depends on the load current; the idle value is used.')
    kdc = (rl + reff + rodc) / rl
    a0 = 10 ** (ac['a0_db'] / 20) * kdc
    put('A0', a0, f"gain at 1 mHz {ac['a0_db']:.2f} dB, times (RL+{'2*' if vxo > 0 else ''}ROUT"
                  f"{'+ROUTDC' if rodc > 0 else ''})/RL (unloaded gain)")
    gbw40 = 100 * ac['f40'] * kl
    pm = 180 + ac['ph_fu']
    while pm > 180:
        pm -= 360
    while pm <= -180:
        pm += 360
    cout = 3e-12
    fout = 1 / (2 * math.pi * (reff * rl / (reff + rl)) * cout)
    # FP2/GBW from the phase margin, then GBW so that the model's unity-gain
    # frequency is the measured one (a few passes; FP3 = 3.33*FP2)
    gbw, far = gbw40, False
    for _ in range(8):
        if pm_model(1000 * gbw, gbw, a0, fout)[0] < pm:
            fp2, far = 1000 * gbw, True
        else:
            lo, hi = 0.05 * gbw, 1000 * gbw
            for _ in range(100):
                m = math.sqrt(lo * hi)
                if pm_model(m, gbw, a0, fout)[0] < pm:
                    lo = m
                else:
                    hi = m
            fp2 = lo
        gbw *= ac['fu'] / pm_model(fp2, gbw, a0, fout)[1]
    put('GBW', gbw, f"unity-gain frequency {sig(ac['fu'])} Hz with the phase margin (from 100*f(40 dB): {sig(gbw40)} Hz)")
    if abs(gbw / gbw40 - 1) > 0.05:
        notes.append(f"GBW: the gain at 40 dB gives {sig(gbw40)} Hz, {abs(gbw / gbw40 - 1) * 100:.0f} % off the value that matches the unity-gain frequency; the latter is used (the model's mid-band gain is then {abs(gbw / gbw40 - 1) * 100:.0f} % {'high' if gbw > gbw40 else 'low'}).")
    if far:
        put('FP2', fp2, f'PM {pm:.1f} deg is above what two extra poles allow; FP2 set far out')
        notes.append('FP2: the phase margin is higher than the model reaches; FP2 = 1000*GBW (FP3 = 3330*GBW).')
    else:
        put('FP2', fp2, f"phase at fu ({sig(ac['fu'])} Hz) {ac['ph_fu']:.1f} deg: PM {pm:.1f} deg, FP3 = 3.33*FP2")
    put('FP3', 3.33 * P['FP2'], '3.33 * FP2')
    # common-mode and supply rejection
    for key, name, fz, tag in (('cmrr', 'CMRR', 'FCMRR', 'fcm'), ('psrrp', 'PSRRP', 'FPSRRP', 'fpsp'),
                               ('psrrn', 'PSRRN', 'FPSRRN', 'fpsn')):
        db = ac[key + '_db']
        if db > 160:
            notes.append(f'{name}: {db:.0f} dB, i.e. the vendor model has no such coupling; take {name} and {fz} from the datasheet (or keep the defaults).')
            continue
        sg = ac.get(key + '_sg')
        if sg is None:
            put(name, 10 ** (db / 20), f'{db:.1f} dB at 1 mHz (sign not measured: deck older than rev 1.3, entered as positive)')
        else:
            s = 1 if sg >= 0 else -1
            put(name, s * 10 ** (db / 20), f"{db:.1f} dB at 1 mHz, sign {'+' if s > 0 else '-'} (Re of the response "
                                           f"over the differential gain)")
        if tag + '20' in ac:
            put(fz, ac[tag + '20'] / 10, f"falls 20 dB at {sig(ac[tag + '20'])} Hz: corner = that / 10 (3 dB at {sig(ac.get(tag + '3', float('nan')))} Hz)")
            r = ac[tag + '20'] / ac.get(tag + '3', ac[tag + '20'] / 10)
            if not 7 < r < 14:
                notes.append(f"{fz}: the 3 dB and 20 dB points are {r:.1f}x apart, not about 10x: the roll-off is not a single zero; the 20 dB point is used.")
        elif tag + '3' in ac:
            put(fz, ac[tag + '3'], f"falls 3 dB at {sig(ac[tag + '3'])} Hz (never 20 dB)")
        else:
            put(fz, 1e9, 'flat up to 100 GHz')
    if all(k in P for k in ('CMRR', 'PSRRP', 'PSRRN', 'A0')):
        # a model without a ground node obeys 1/PSRRP + 1/PSRRN + 1/CMRR = 1/A0
        # (unloaded gain); OPAMP_FULL derives CMRR from PSRRP and PSRRN
        tc = 1 / P['A0'] - 1 / P['PSRRP'] - 1 / P['PSRRN']
        err = 20 * math.log10(abs(tc * P['CMRR'])) if tc else float('inf')
        if abs(err) > 1 or tc * P['CMRR'] < 0:
            notes.append(f"CMRR: PSRRP, PSRRN and A0 imply CMRR = {sig(1 / tc) if tc else 'inf'} ({err:+.1f} dB from the measured value"
                         f"{', opposite sign' if tc * P['CMRR'] < 0 else ''}). The vendor model does not obey the identity of a part "
                         "without a ground pin (it refers something to node 0); the signs are then conventions of that model. "
                         "OPAMP_FULL uses PSRRP and PSRRN and derives CMRR; to keep the measured CMRR instead, drop PSRRP or PSRRN.")
    if 'CMRR' in P and abs(P['CMRR']) * P['FCMRR'] / gbw < 3:
        notes.append(f"|CMRR|*FCMRR/GBW = {abs(P['CMRR']) * P['FCMRR'] / gbw:.2f} < 3: a follower step will ring in the model (sanity check of the skill).")
    # input impedance: Y(+ pin) - Y(common mode) = differential admittance
    yd0 = 1 / complex(ac['zd_re0'], ac.get('zd_im0', 0.0))
    yc0 = 1 / complex(ac['zc_re0'], ac.get('zc_im0', 0.0))
    gd = yd0.real - yc0.real
    put('RIC', min(1 / yc0.real, 1e15) if yc0.real > 0 else 1e15, 'Re(Y) of one pin, common mode, at 1 mHz')
    put('RID', 1 / gd if gd > 0 else 1e12, 'Re(Y) of the + pin at 1 mHz, minus the common-mode part')
    if gd <= 0 or 1 / gd > 1e12:
        P['RID'] = min(P['RID'], 1e12)
        notes.append('RID: the differential resistance is too high to measure (>= 1 Tohm); 1T is used.')
    if P['RIC'] > 1e13:
        notes.append('RIC: above 10 Tohm, the measurement only gives a lower limit; any value of 10T or more behaves the same.')
    f10 = ac['gbwn'] / 10
    yd = 1 / complex(ac['zd_re'], ac['zd_im'])
    yc = 1 / complex(ac['zc_re'], ac['zc_im'])
    cic = yc.imag / (2 * math.pi * f10)
    put('CIC', cic, f'Im(Y) of one pin, common mode, at GBWN/10 = {sig(f10)} Hz')
    put('CID', yd.imag / (2 * math.pi * f10) - cic, 'Im(Y) of the + pin at GBWN/10, minus CIC')
    for k in ('CIC', 'CID'):
        if P[k] < 1e-15:
            del P[k]
            notes.append(f'{k}: the vendor model has (almost) no input capacitance here; keep the default or take it from the datasheet.')
    # DC errors and supply current
    put('VOS', fast['vos'], 'follower at VCM: Vout - Vin')
    put('IB', 0.5 * (fast['ibp'] + fast['ibn']), f"mean of the pin currents {sig(fast['ibp'])}, {sig(fast['ibn'])} A (into the pins)")
    put('IOS', fast['ibp'] - fast['ibn'], 'I(+) - I(-)')
    put('ICCQ', fast['iq'], 'unloaded follower at VCM')
    # slew rates, from the inverter (output slope corrected for the load divider;
    # the inverter's load is RL in parallel with its 10 kohm feedback resistor)
    vstep, ts = fast['vstep'], fast['ts']
    kr = (rl + rout) / rl
    rli = rl * 10e3 / (rl + 10e3)
    ki = (rli + rout) / rli
    srr = 0.35 * vstep / (fast['t85ri'] - fast['t50ri']) * ki
    srf = 0.35 * vstep / (fast['t85fi'] - fast['t50fi']) * ki
    if abs(srr - srf) / (srr + srf) * 2 < 0.1:
        put('SR', 0.5 * (srr + srf), f'inverter, step {vstep:g} V: rising {sig(srr)}, falling {sig(srf)} V/s (50 -> 85 %)')
    else:
        put('SR', 0.5 * (srr + srf), 'mean of SRR and SRF')
        put('SRR', srr, f'inverter, step {vstep:g} V, rising output, 50 -> 85 %')
        put('SRF', srf, 'falling output, 50 -> 85 %')
    # follower jump: the follower's output TS/100 after each input edge, less what
    # slewing at the follower's own rate gives in that time (not with an input
    # clamp: its current drags the output). A slew rate that falls along the edge
    # leaves only a few per cent here, where extrapolating the slewing line back
    # to the edge would show a false jump.
    sfr = 0.35 * vstep / (fast['t85r'] - fast['t50r'])
    sff = 0.35 * vstep / (fast['t85f'] - fast['t50f'])
    jr = (fast['vj_r'] - fast['vo2_lo'] - sfr * 0.0105 * ts) / vstep
    jf = (fast['vo2_hi'] - fast['vj_f'] - sff * 0.0105 * ts) / vstep
    clamp = fast['icl1'] > 1e-6 + 10 * abs(fast['ibp'] + fast['ibn'])
    if max(jr, jf) >= 0.05 and not clamp:
        k = jr if jr >= jf else -jf
        put('KJUMP', k * kr, f'follower output jumps {abs(k) * 100:.0f} % of the step on the {"rising" if k > 0 else "falling"} edge; times (RL+ROUT)/RL')
    elif max(jr, jf) >= 0.05:
        notes.append(f'KJUMP: the follower output jumps {max(jr, jf) * 100:.0f} % of the step, but the input clamp conducts during the step; KJUMP is left at 0 (check the datasheet pulse response).')
    os_r = (fast['ss_max'] - fast['ss_hi']) / (fast['ss_hi'] - fast['ss_lo']) * 100
    os_f = (fast['ss_lo'] - fast['ss_min']) / (fast['ss_hi'] - fast['ss_lo']) * 100
    notes.append(f'Check: follower small-step overshoot {os_r:.1f} % rising, {os_f:.1f} % falling; the fitted model should give about the same.')
    # swing and output current
    voh, vol = fast['voh_rl'], fast['vol_rl']
    vhd = (vcc - voh) - (voh - vcm) / rl * rout
    vld = (vol - vee) - (vcm - vol) / rl * rout
    for k, v, w, nl in (('VHD', vhd, voh, vcc - fast['voh_nl']), ('VLD', vld, vol, fast['vol_nl'] - vee)):
        if v <= 0:
            notes.append(f'{k}: the loaded swing and ROUT give {v:.3f} V; 0.05 is used.')
            v = 0.05
        put(k, v, f'swing into RL {w:.3f} V, corrected by ROUT (unloaded headroom {nl:.3f} V)')
    put('ISRC', fast['isrc'], 'open loop, output shorted to VCM')
    put('ISNK', -fast['isnk'], 'open loop, output shorted to VCM')
    for k, lim in (('ISRC', (vcc - P['VHD'] - vcm) / rout), ('ISNK', (vcm - vee - P['VLD']) / rout)):
        if abs(P[k] / lim - 1) < 0.05:
            notes.append(f'{k}: the short-circuit current {sig(P[k])} A equals the swing limit / ROUT; the current limit itself is higher and not seen. Take {k} from the datasheet (or keep the default).')
    # input clamp: V = N*VT*ln(I/IS) + R*I through two points
    i1, i2, v1, v2 = fast['icl1'], fast['icl2'], fast['vcl1'], fast['vcl2']
    if i1 > 1e-6 + 10 * abs(P['IB']) and i2 > 0:
        l1, l2 = VT * math.log(i1 / 1e-15), VT * math.log(i2 / 1e-15)
        det = l1 * i2 - l2 * i1
        n, rc = (v1 * i2 - v2 * i1) / det, (l1 * v2 - l2 * v1) / det
        if rc < 0:
            rc, n = 0.0, v2 / l2
        put('VCLMP', n * VT * math.log(1e-3 / 1e-15), f'clamp current {sig(i1)} A at {v1:.3f} V, {sig(i2)} A at {v2:.3f} V')
        put('RCLMP', max(rc, 1e-3), 'series resistance from the same two points')
    # phase reversal: the flip is where the pin current reaches 0.9 of its rise
    # (the model's definition: J = 1/2); the output must end on the wrong side
    srv = 0.5 * (srr + srf)
    ipr, jun = [], {}
    for side, vip, vfl, i0, ie, t1, t2, step in (
            ('HI', 'vipt', 'vflt', 'it0', 'iendt', 'rt_t1', 'rt_t2', vcc + fast['ovr']),
            ('LO', 'vipb', 'vflb', 'ib0', 'iendb', 'rb_t1', 'rb_t2', vee - fast['ovr'])):
        end = slow.get('vendt' if side == 'HI' else 'vendb')
        if end is None or not ((end < vcm) if side == 'HI' else (end > vcm)):
            continue
        vf = slow.get(vip)
        how = 'pin current at 0.9 of its rise'
        if vf is None:
            vf, how = slow[vfl], 'output 5 % below its maximum (pin current did not rise)'
            notes.append(f'VPR{side}: the pin current shows no step; the flip is taken from the output.')
        put('VPR' + side, vcc - vf if side == 'HI' else vf - vee, f'follower flips at {vf:.3f} V ({how})')
        ipr.append(abs(slow[ie] - slow[i0]))
        if t1 in fast and t2 in fast:
            span = 0.4 * ((vcm - vee) if side == 'HI' else (vcc - vcm))
            slope = span / (fast[t2] - fast[t1]) * kr
            od = (step - vf) if side == 'HI' else (vf - step)
            j = 0.5 * (1 + math.tanh(od * 0.5 / VT))
            pr = slope / srv
            for _ in range(20):
                pr = slope / (srv * j ** (1 + max(math.log2(max(pr, 1e-3)), 0)))
            put('PR' + side, pr, f'reversed output slope {sig(slope)} V/s after a step to {step:g} V, / SR')
        else:
            put('PR' + side, 1.0, 'reversal in the slow ramp, but not after the step: slope unknown')
            notes.append(f'PR{side}: the follower step to {step:g} V did not reverse the output; PR{side} = 1 is a guess.')
        jun[side] = (vf, P['PR' + side])
    if ipr:
        put('IPR', sum(ipr) / len(ipr), 'rise of the pin current over the slow ramp' + (' (mean of both edges)' if len(ipr) > 1 else ''))
        if len(ipr) > 1 and max(ipr) > 1.5 * min(ipr):
            notes.append(f'IPR: the two edges give {sig(ipr[0])} and {sig(ipr[1])} A; the model has one IPR, the mean is used.')
    # input common-mode range: relative gain 0.5 and 0.25 on each edge. A junction
    # of the reversal (if any) takes out (1-J)^2 of the gain and adds a negative
    # transconductance of its own; both are removed before the window is solved.
    gm_k = srv / (2 * math.pi * gbw)        # IMAX/GM0
    vks, anchors, beyond = [], {}, {}
    vref = 0.5 * (vcc + vee)
    # the model's gain in these followers (into RL, outside the crossover)
    afl = a0 * rl / (rl + rout + P.get('ROUTDC', 0.0))
    for side in ('t', 'b'):
        v5, v1_ = slow.get('vw5' + side), slow.get('vwq' + side)
        nm = 'ICMHI' if side == 't' else 'ICMLO'
        sg = 1 if side == 't' else -1
        # 1) the follower's tracking error, +10 mV and +100 mV beyond its value at
        #    the ramp start, unless the output swing limits the follower first. In
        #    the model w = (Vout-Vref)/(A*d + Vout_start-Vref) exactly, with A the
        #    gain into RL: the gain stages are referred to Vref = mid-supply
        #    (KREF = 0.5), and RL returns to VCM = Vref.
        f1, f2 = slow.get('vf1' + side), slow.get('vf2' + side)
        o1, o2 = slow.get('of1' + side), slow.get('of2' + side)
        swing = fast['voh_rl'] if side == 't' else fast['vol_rl']
        if f1 is not None and f2 is not None and sg * (swing - o1) > 0.05:
            vin0 = (vcc - slow['w']) if side == 't' else (vee + slow['w'])
            ost = vin0 - slow['ef' + side + '0']
            zz, vv = [], []
            for vi, vo, dd in ((f1, o1, 0.01), (f2, o2, 0.1)):
                w = (vo - vref) / (afl * sg * dd + ost - vref)
                zz.append(logit(min(max(w, 1e-9), 0.999)))
                dtot = vi - vo
                vv.append(0.5 * (vi + vo) - sg * 0.5 * math.sqrt(dtot * dtot + 1e-4))
            vk = 2 * sg * (vv[1] - vv[0]) / (zz[0] - zz[1])
            if vk < 0.005:
                notes.append(f'{nm}: the follower stops abruptly (computed VK {vk * 1e3:.1f} mV); VK = 5 mV is the sharpest knee kept.')
                vk = 0.005
            anchors[side] = (vv[0], zz[0], f'follower error +10 mV at {f1:.4f} V, +100 mV at {f2:.4f} V (input)')
            vks.append(vk)
            continue
        if v5 is None or v1_ is None:
            beyond[side] = True
            notes.append(f"{nm}: neither the follower (before the output swing limit) nor the input-stage gain shows an edge on the ramp; the range reaches at least {fast['ovr']:g} V beyond the rail, and the edge is put further out.")
            continue
        vp = [v5 - sg * 0.005, v1_ - sg * 0.005]          # the smooth min/max of the inputs
        targets = []
        for v, w in zip((v5, v1_), (0.5, 0.25)):
            jn = jun.get('HI' if side == 't' else 'LO')
            if jn:
                vf, pr = jn
                j = 0.5 * (1 + math.tanh(sg * (v - vf) * 0.5 / VT))
                lp = max(math.log2(max(pr, 1e-3)), 0)
                w = (w + gm_k * pr * (1 + lp) * j ** (1 + lp) * (1 - j) / VT) / (1 - j) ** 2
            targets.append(w)
        ok = all(0 < x < 0.999 for x in targets) and targets[0] > targets[1]
        if ok:
            z5, z1 = logit(targets[0]), logit(targets[1])
            vk = 2 * sg * (vp[1] - vp[0]) / (z5 - z1)
        if not ok or vk <= 0:
            notes.append(f"{nm}: with the reversal junction taken out, the measured gain drop at this edge is smaller than the junction alone gives; the edge is solved without the junction correction (the model's gain then falls a little earlier than the part's).")
            z5, z1 = 0.0, logit(0.25)
            vk = 2 * sg * (vp[1] - vp[0]) / (z5 - z1)
        anchors[side] = (vp[0], z5, f'follower swing-limited; input-stage gain 0.5 at {v5:.4f} V, 0.25 at {v1_:.4f} V')
        vks.append(vk)
    vk = sum(vks) / len(vks) if vks else 0.15
    if vks:
        put('VK', vk, 'edge width' + (f' (top {vks[0]:.3f}, bottom {vks[1]:.3f} V; mean)' if len(vks) > 1 else ''))
        if len(vks) > 1 and max(vks) > 2 * min(vks):
            notes.append(f'VK: the two edges differ ({vks[0]:.3f} V top, {vks[1]:.3f} V bottom); the model has one VK, the mean is used, and each edge is placed with it through its first point.')
    # each edge through its first point, with the common VK
    for side, nm, sg in (('t', 'ICMHI', 1), ('b', 'ICMLO', -1)):
        if side in anchors:
            v, z, how = anchors[side]
            edge = v + sg * z * vk / 2
            put(nm, (vcc - edge) if side == 't' else (edge - vee), how)
        elif side in beyond:
            put(nm, -(fast['ovr'] + 0.1 + 2 * vk), f"no edge up to {fast['ovr']:g} V beyond the rail")
    notes.append(f"Follower on the slow ramps: output stops at {slow['vstopt']:.3f} V (top) and {slow['vstopb']:.3f} V (bottom).")
    return P, src, notes


ORDER = ['A0', 'GBW', 'FP2', 'FP3', 'SR', 'SRR', 'SRF', 'KJUMP', 'VOS', 'IB', 'IOS', 'RID', 'CID', 'RIC', 'CIC',
         'VCLMP', 'RCLMP', 'CMRR', 'FCMRR', 'PSRRP', 'PSRRN', 'FPSRRP', 'FPSRRN', 'VCCN', 'VEEN', 'VCMN',
         'ICCQ', 'ICMHI', 'ICMLO', 'VK', 'PRHI', 'PRLO', 'VPRHI', 'VPRLO', 'IPR', 'VHD', 'VLD', 'ROUT',
         'ROUTDC', 'ISRC', 'ISNK']


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('ac'), ap.add_argument('fast'), ap.add_argument('slow')
    ap.add_argument('--vxo', default='2m', help='VXO of the fitted model (2m bipolar class AB, 0 CMOS rail-to-rail)')
    ap.add_argument('--name', default='OPA')
    a = ap.parse_args()
    logs = [parse(open(f, errors='replace').read()) for f in (a.ac, a.fast, a.slow)]
    P, src, notes = derive(*logs, vxo=num(a.vxo))
    vals = ' '.join(f'{k}={sig(P[k])}' for k in ORDER if k in P)
    print(f'X{a.name} inp inn vcc vee out OPAMP_FULL PARAMS: {vals} VXO={a.vxo}\n')
    print(f"{'param':7s} {'value':>10s}  from")
    for k in ORDER:
        if k in P:
            print(f'{k:7s} {sig(P[k]):>10s}  {src[k]}')
    print('\nNot measured (datasheet or defaults): ENOISE, FCEN, INOISE, FCIN, COUT, VXO, VCMT/VKT/DVOST/DIBT.')
    for n in notes:
        print('- ' + n)


if __name__ == '__main__':
    main()
