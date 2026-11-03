#!/usr/bin/env python3
# Copyright (c) 2026 Stanislav Maslovski. SPDX-License-Identifier: BSD-2-Clause
"""Run all example netlists with ngspice (batch mode), print the key results
and draw the figures used in docs/ (needs ngspice, numpy, matplotlib).

    cd examples && python3 run_examples.py
"""
import os, re, subprocess, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter
PLAIN = FuncFormatter(lambda v, _: f'{v:g}')

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, '..', 'docs', 'figures')
os.makedirs(FIG, exist_ok=True)
os.chdir(HERE)

C = ['#2a78d6', '#d9622b', '#2f9e57', '#7a6fd6', '#555555']
plt.rcParams.update({'font.size': 12, 'axes.grid': True, 'grid.color': '#e3e2dd',
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'legend.frameon': False, 'savefig.dpi': 160})


LOCS = ['upper right', 'upper left', 'lower left', 'lower right', 'center right',
        'center left', 'upper center', 'lower center', 'center']


def _hits(fig, ax, leg):
    """number of plotted data points (densified line segments) inside the legend box"""
    bb = leg.get_window_extent(fig.canvas.get_renderer()).expanded(1.02, 1.05)
    n = 0
    for ln in ax.lines:
        x, y = ln.get_xdata(orig=False), ln.get_ydata(orig=False)
        if len(x) == 0:
            continue
        p = ln.get_transform().transform(np.column_stack([np.asarray(x, float), np.asarray(y, float)]))
        p = p[np.all(np.isfinite(p), axis=1)]
        if len(p) > 1:   # densify so that steep segments are caught too
            seg = np.linspace(0, 1, 12)[:, None, None]
            p = (p[:-1][None] * (1 - seg) + p[1:][None] * seg).reshape(-1, 2)
        n += np.count_nonzero((p[:, 0] > bb.x0) & (p[:, 0] < bb.x1) & (p[:, 1] > bb.y0) & (p[:, 1] < bb.y1))
    return n


def legend(ax, **kw):
    """place the legend where it covers no curve; remember the request for save()"""
    ax._leg_kw = kw
    ax.legend(**kw)


def _place_legends(fig):
    fig.canvas.draw()
    for ax in fig.axes:
        kw = getattr(ax, '_leg_kw', None)
        if kw is None:
            continue
        kw = dict(kw)
        n_items = len(ax.get_legend_handles_labels()[0])
        # 1) any free spot inside the axes?
        # 2) linear y axis: make head-room above the curves and put the legend in one or two rows there
        trials = [(loc, kw.get('ncol', 1), 0) for loc in LOCS]
        if ax.get_yscale() == 'linear':
            for grow in (1, 2, 3, 4):
                for ncol in (min(n_items, 3), min(n_items, 2), n_items):
                    trials += [(loc, ncol, grow) for loc in ('upper center', 'upper left', 'upper right')]
        y0, y1 = ax.get_ylim()
        for loc, ncol, grow in trials:
            ax.set_ylim(y0, y1 + 0.15 * grow * (y1 - y0))
            k = {**kw, 'ncol': ncol}
            leg = ax.legend(loc=loc, **k)
            fig.canvas.draw()
            if _hits(fig, ax, leg) == 0:
                ax._leg_kw = k
                ax._leg_done = (loc, grow)
                break
        else:
            ax.set_ylim(y0, y1)
            ax.legend(loc='best', **kw)
            print(f'  WARNING: legend of {ax.get_ylabel()!r} still overlaps a curve')


def run(deck):
    out = subprocess.run(['ngspice', '-b', deck], capture_output=True, text=True).stdout
    keep = [l for l in out.splitlines()
            if re.match(r'(CL =|Rs|Vocm =|[a-c]\)|f = |\s+No\. Harmonics|10 mV|\d[\d.]*(k|meg)?\s{2,})', l)]
    print('==', deck); print('\n'.join(keep)); print()
    return out


def load(fn, ncol):
    """wrdata file: x y1 x y2 ... (real) -> x, [y1, y2, ...]"""
    d = np.loadtxt(fn)
    return d[:, 0], [d[:, 2 * k + 1] for k in range(ncol)]


def save(fig, name):
    fig.tight_layout(); _place_legends(fig); fig.tight_layout()
    fig.canvas.draw()
    for ax in fig.axes:   # re-check after the final layout
        if getattr(ax, '_leg_kw', None) and ax.get_legend() and _hits(fig, ax, ax.get_legend()):
            print('  WARNING: legend overlaps after layout:', name)
    fig.savefig(os.path.join(FIG, name), facecolor='white'); plt.close(fig)


# --- 1. op-amp follower with capacitive load ------------------------------------------
log = run('01_opamp_cload_stability.cir')
f, (db0, ph0, db1, ph1, db2, ph2, tv1) = load('ex01_loopgain.txt', 7)
lab = ['CL = 3 pF', 'CL = 1 nF, idle (2·ROUT)', 'CL = 1 nF, 1 mA load']
pm = [float(x) for x in re.findall(r'PM = ([-\d.]+) deg', log)]
fig, ax = plt.subplots(2, 1, figsize=(7.4, 6.0), sharex=True)
for k, (d, p) in enumerate([(db0, ph0), (db1, ph1), (db2, ph2)]):
    ax[0].semilogx(f, d, color=C[k], lw=2, label=f'{lab[k]}: PM {pm[k]:.0f}°')
    ax[1].semilogx(f, p, color=C[k], lw=2)
ax[0].semilogx(f, tv1, color=C[1], lw=1.2, ls='--', label='$T_V$ only (1 nF, idle): wrong near and above $f_c$')
ax[0].axhline(0, color='k', lw=.8); ax[0].set_ylim(-40, 110); ax[0].set_ylabel('|T|, dB'); legend(ax[0], fontsize=10)
ax[1].axhline(-180, color='k', lw=.8); ax[1].set_ylim(-270, 0); ax[1].set_yticks([0, -90, -180, -270])
ax[1].set_ylabel('∠T, deg'); ax[1].set_xlabel('f, Hz'); ax[1].set_xlim(10, 1e8)
save(fig, 'ex01_loopgain.png')
fig, ax = plt.subplots(figsize=(7.4, 3.2))
for fn, k, l in [('ex01_step_idle.txt', 1, 'idle'), ('ex01_step_load.txt', 2, '1 mA DC load')]:
    t, (v,) = load(fn, 1); ax.plot(t * 1e6, (v - v[0]) * 1e3, color=C[k], lw=2, label=l)
ax.set_xlabel('t, µs'); ax.set_ylabel('ΔVout, mV'); ax.set_xlim(1, 12); legend(ax)
save(fig, 'ex01_step.png')

# --- 2. FDA DM and CM loop gains ----------------------------------------------------
log = run('02_fda_dm_cm_stability.cir')
fig, ax = plt.subplots(2, 1, figsize=(7.4, 6.0), sharex=True)
for k, cl in enumerate(['1p', '220p', '1n']):
    f, (dmdb, dmph, cmdb, cmph) = load(f'ex02_loopgain_{cl}.txt', 4)
    ax[0].semilogx(f, dmdb, color=C[k], lw=2, label=f'DM, CL = {cl}F')
    ax[0].semilogx(f, cmdb, color=C[k], lw=2, ls='--', label=f'CM, CL = {cl}F')
    ax[1].semilogx(f, dmph, color=C[k], lw=2); ax[1].semilogx(f, cmph, color=C[k], lw=2, ls='--')
ax[0].axhline(0, color='k', lw=.8); ax[0].set_ylim(-40, 100); ax[0].set_ylabel('|T|, dB'); legend(ax[0], fontsize=9.5, ncol=2)
ax[1].axhline(-180, color='k', lw=.8); ax[1].set_ylim(-270, 0); ax[1].set_yticks([0, -90, -180, -270])
ax[1].set_ylabel('∠T, deg'); ax[1].set_xlabel('f, Hz'); ax[1].set_xlim(1e3, 3e9)
save(fig, 'ex02_loopgain.png')

# --- 3. noise -----------------------------------------------------------------------
log = run('03_opamp_noise.cir')
fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
for k, r in enumerate(['100', '40k', '1meg']):
    f, (sim, th) = load(f'ex03_noise_{r}.txt', 2)
    ax[0].loglog(f, sim * 1e9, color=C[k], lw=2, label=f'Rs = {r.replace("meg", "M")}Ω')
    ax[0].loglog(f[::4], th[::4] * 1e9, 'o', ms=4, mfc='none', color=C[k])
ax[0].plot([], [], 'o', ms=4, mfc='none', color='k', label='theory')
ax[0].yaxis.set_major_formatter(PLAIN); ax[0].yaxis.set_minor_formatter(NullFormatter()); ax[0].set_yticks([20, 50, 100, 200, 500])
ax[0].set_xlabel('f, Hz'); ax[0].set_ylabel('input-referred noise, nV/√Hz'); legend(ax[0], fontsize=10)
rows = re.findall(r'^(\d[\d.]*(?:k|meg)?)\s+([\d.]+)\s+([\d.]+)', log, re.M)
rs = np.array([float(a.replace('meg', 'e6').replace('k', 'e3')) for a, _, _ in rows])
ax[1].semilogx(rs, [float(b) for _, b, _ in rows], 'o-', color=C[0], lw=2, label='simulated')
rr = np.logspace(3, 6, 100); kt = 4.1435e-21
ax[1].semilogx(rr, 10 * np.log10(1 + (400e-18 * 1.2 + (0.5e-12 * rr) ** 2) / (4 * kt * rr)), color='k', lw=1, ls='--', label='theory')
ax[1].axvline(40e3, color=C[1], lw=1); ax[1].text(43e3, 13, '$R_{opt} = e_n/i_n$ = 40 kΩ', color=C[1], fontsize=10)
ax[1].set_xlabel('Rs, Ω'); ax[1].set_ylabel('NF at 1 kHz, dB'); legend(ax[1], fontsize=10)
save(fig, 'ex03_noise.png')

# --- 4. large signal ------------------------------------------------------------------
log = run('04_opamp_large_signal.cir')
fq = [float(x.replace('k', 'e3')) for x in re.findall(r'^f = (\S+)', log, re.M)]
thd = [float(x) for x in re.findall(r'THD: ([\d.eE+-]+) %', log)]
fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
t, (vi, vo) = load('ex04a_12k.txt', 2)
ax[0].plot(t * 1e6, vi, color='#999', lw=1.2, label='input'); ax[0].plot(t * 1e6, vo, color=C[0], lw=2, label='output')
ax[0].set_xlim(250, 500); ax[0].set_xlabel('t, µs'); ax[0].set_ylabel('V'); legend(ax[0], fontsize=10)
ax[0].set_title('follower, 10 V peak, 12 kHz: slew 0.5 V/µs', fontsize=11, loc='left')
ax[1].loglog(np.array(fq[1:]) / 1e3, thd[1:], 'o-', color=C[1], lw=2)
ax[1].axvline(0.5e6 / (2 * np.pi * 10) / 1e3, color='k', lw=1, ls='--'); ax[1].text(8.1, 0.003, 'SR/(2π$V_p$)', fontsize=10)
ax[1].xaxis.set_major_formatter(PLAIN); ax[1].xaxis.set_minor_formatter(NullFormatter()); ax[1].set_xticks([2, 4, 6, 8, 10])
ax[1].yaxis.set_major_formatter(PLAIN)
ax[1].set_xlabel('f, kHz'); ax[1].set_ylabel('THD, %'); ax[1].set_title('THD vs frequency, 10 V peak', fontsize=11, loc='left')
t, (vb, ob, oc, icc, iee) = load('ex04bc.txt', 5)
m = t > 1e-3
ax[2].plot(t[m] * 1e3, -10 * vb[m], color='#999', lw=1.2, label='$-10\\,V_{in}$ (ideal)')
ax[2].plot(t[m] * 1e3, ob[m], color=C[2], lw=2, label='output, 2k load')
ax[2].set_xlabel('t, ms'); ax[2].set_ylabel('V'); legend(ax[2], fontsize=10)
ax[2].set_title('gain −10, overdriven: clipping at ±12.44 V', fontsize=11, loc='left')
save(fig, 'ex04_large_signal.png')

# --- 5. FDA swing vs Vocm ---------------------------------------------------------------
log = run('05_fda_swing_vocm.cir')
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
for k, v in enumerate(['0', '1.5']):
    t, (s, op, on, vod, voc) = load(f'ex05_vocm_{v}.txt', 5)
    m = t > 10e-6
    a = ax[k]
    a.plot(t[m] * 1e6, 4 * s[m], color='#999', lw=1.2, label='ideal $V_{od} = 4\\,V_{in}$')
    a.plot(t[m] * 1e6, vod[m], color=C[0], lw=2, label='$V_{od}$')
    a.plot(t[m] * 1e6, op[m], color=C[1], lw=1.4, label='outp'); a.plot(t[m] * 1e6, on[m], color=C[2], lw=1.4, label='outn')
    a.plot(t[m] * 1e6, voc[m], color='k', lw=1.2, ls='--', label='output CM')
    a.set_title(f'Vocm = {v} V', fontsize=12, loc='left'); a.set_xlabel('t, µs')
ax[0].set_ylabel('V'); legend(ax[0], fontsize=9.5, ncol=2)
save(fig, 'ex05_fda_swing.png')
print('figures written to', os.path.normpath(FIG))
