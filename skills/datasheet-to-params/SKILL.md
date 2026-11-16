---
name: datasheet-to-params
description: Extract OPAMP_FULL or FDOPAMP_FULL macromodel parameters (spice-opamp-macromodels) from an op-amp or fully differential amplifier datasheet, with a source and a confidence for every value.
---

# Datasheet → OPAMP_FULL / FDOPAMP_FULL parameters

This file is a self-contained instruction set. Give it to any capable AI assistant
(as a skill, a system prompt or the first message), together with a datasheet (PDF,
text or images of its pages). It does not depend on a particular vendor of AI.

The models are the ngspice/LTspice/PSpice macromodels `OPAMP_FULL` (single-ended
op amp) and `FDOPAMP_FULL` (fully differential amplifier) from the
`spice-opamp-macromodels` repository (BSD-2-Clause, © 2026 Stanislav Maslovski).
Every parameter has a default; the goal is to replace as many defaults as the
datasheet supports, and to say honestly which values are measured, which are
derived, and which stay at their defaults.

## Version and updates

- Skill revision: **1.20** (2026-11-16)
- For model version: **1.7.1** of `OPAMP_FULL` / `FDOPAMP_FULL` (the `Version` line
  in the header of `opamp_full.lib` / `fdopamp_full.lib`)
- Model 1.7.1: `RSATH`, `RSATL` (OPAMP_FULL only): the slope of the saturated
  output headroom with the load current, when it differs from ROUT (see the
  `VHD` row). For a 1.7 library leave them out and use the swing rule without
  them.
- Model 1.7: `CMRR`, `PSRR`, `PSRRP`, `PSRRN` are signed (see their rows); enter
  datasheet values as positive. The defaults are `CMRR` = −31.6k, `PSRR` = 31.6k
  (FDA: 31.6k, 10k). For a 1.6 library the same positive values work; if you
  keep the defaults there, write nothing (1.6 defaults to 0 = not given).
- Model 1.6 has no ground node, and its supply and common-mode rejection follows
  the rules of a part without a ground pin: only two of `CMRR`, `PSRR`, `PSRRP`,
  `PSRRN` are used exactly (see their rows). `PSRR` (both supplies moved apart,
  the usual single datasheet value), `KREF` and `ROUTDC` (DC output resistance;
  `A0` is then the unloaded gain) are new in 1.6. For a 1.5.x library, map a
  single PSRR to `PSRRP` = `PSRRN`, give `CMRR` as well, use the loaded A_OL for
  `A0`, and leave out `PSRR`, `KREF` and `ROUTDC`.
- Parameters new in model 1.5 (`FPSRRP`, `FPSRRN`, `PRHI`, `PRLO`, `VPRHI`,
  `VPRLO`, `IPR`, `VCMT`, `VKT`, `DVOST`, `DIBT`, `KBAL`) are rejected by older
  libraries. If the user has an older version, leave them out of the instance line
  and give their values in the notes.
- Since model 1.5, `FP2` and `FP3` default to 0, which scales them with `GBW`, and
  `FPCM2` defaults to 0 = 4·`GBWCM` (see their rows). (In 1.5.x `FCMRR` and
  `FPSRR` did the same; since 1.6, 0 means "not given".) Older
  libraries have fixed defaults (3Meg, 10Meg, 200, 100 / 300Meg, 1G, 100k, 100k;
  FPCM2 200Meg) that suit only the default GBW and GBWCM: for an older library,
  write the scaled values explicitly whenever `GBW` or `GBWCM` differs from the
  default.
- Repository: https://github.com/smaslovski/spice-opamp-macromodels
- Latest revision of this file:
  https://github.com/smaslovski/spice-opamp-macromodels/blob/master/skills/datasheet-to-params/SKILL.md
  (raw text: https://raw.githubusercontent.com/smaslovski/spice-opamp-macromodels/master/skills/datasheet-to-params/SKILL.md)

Before you start, if you can open web pages or fetch files:
1. Fetch the latest revision above and compare its "Skill revision" with this one.
2. If it is newer, and its "For model version" is the model version the user has
   (ask if unknown; it is in the header of their library file), follow the newer
   file instead of this one, and say so in your answer.
3. Otherwise, use this skill file.

If you cannot fetch anything, use this file as it is, and say which revision you
used.

## Your task

1. Identify the part: name, single op amp or FDA, number of channels, input-stage
   type (npn bipolar, pnp bipolar, p- or n-JFET, CMOS), rail-to-rail input/output.
2. Choose ONE operating condition and use it for every value: the supply voltage
   (e.g. ±15 V, or 5 V single supply), the load (e.g. 2 kΩ) and 25 °C. Prefer the
   column or plot the user asks for; otherwise the condition used for most of the
   typical specifications. State it at the top of your answer.
3. Use **typical** values. Use min/max only if the user asks for a worst-case model,
   and say so. Read plots where the tables are silent.
4. For every table row you use, first copy it exactly as printed: MIN, TYP, MAX
   (read the column headers; a row can have a typical only, a min only, or
   several conditions), the unit, and the condition. Then convert it to the
   model's units and conventions (tables below), showing the arithmetic. Watch
   the prefix: 0.01 nA = 10 pA = `10p`, not `10n`.
   Text extracted from a PDF drops empty cells, so a row with two numbers under
   MIN TYP MAX is ambiguous. For quantities where smaller is better (offset,
   bias currents, supply sensitivity in µV/V, supply current, noise) the two
   numbers are TYP and MAX; where larger is better (gain, CMRR in dB, swing)
   they are MIN and TYP. Check against the page image if you can.
5. Run the sanity checks at the end.
6. Produce the output in the format given under "Output". Never invent a number:
   a parameter that the datasheet does not support keeps its default and is
   marked `default`.

Rules that matter:
- **One device, one data set.** If the tables and the typical-characteristics plots
  disagree strongly (factors, not percent), check the revision history: a revision
  may have moved the part to a new die while keeping the old plots. Do not mix the
  two. Report the conflict, build the set from one source (say which), and ask the
  user which one they want. Values the revision did not change (check its list)
  belong to both sets, and a table value beats a plot reading of the same
  quantity.
- **Never keep a default because one detail is unknown.** If the datasheet gives a
  value but not its sign or condition, use the value, state the assumption, and
  lower the confidence. A default that is orders of magnitude off is worse.
- **Input-stage type.** Take it from the datasheet. Look first for a simplified
  schematic or "functional block diagram" and read the input-pair symbols: a JFET
  whose gate arrow points into the channel is n-channel, out of it p-channel; a
  bipolar transistor whose emitter arrow points out is npn, in is pnp. Then the
  text. Do not infer the polarity from the input common-mode range (an n-channel
  JFET pair can include V−), and do not read a sign from plot labels like "+I_B"
  and "−I_B", which usually name the two pins. For a well-known classic part whose
  input stage is widely documented you may use general knowledge; say that you
  did.
- **Min-only specs.** If a quantity has only a min (or max) column, use that value
  and say so; check carefully which column a number is in.
- **Axis-label typos.** If a plot contradicts a table by a round factor (10³, 10⁶),
  suspect a wrong unit on the axis rather than the device, and say so (for
  example, a pulse-response time axis labelled "ms" whose slopes match the
  tabulated slew rate only if the axis is in µs).
- **No hand adjustments.** Do not round a computed value to a preferred one, scale it
  "to compensate" for the model, or pick a "compromise". Output the computed value;
  if you think it is wrong, say why in the notes and let the user decide.
- **This file contains no data for any particular part.** Its numbers are model
  defaults, formulas and broad plausibility ranges for device classes. Never copy
  them into your answer as results: every number you output must come from the
  datasheet in hand, or be a default marked `default`.
- **Edges.** A rising edge is the input going from low to high. An output jump
  from −5 V to −2.5 V is on the rising edge (KJUMP > 0); a jump from +5 V to
  +2.5 V is on the falling edge (KJUMP < 0).
- **Log-scale plots.** Read the axis labels: many plots label only every second
  decade (1, 100, 10k, 1M). Count the decades before reading a frequency.
- **Per channel.** Supply current in a dual/quad datasheet is often the total;
  divide by the number of channels.
- **Units.** SPICE suffixes: `f p n u m k Meg G T`. `M` means milli in SPICE, so
  write `Meg` for 10⁶. Slew rates are in V/s (`0.5 V/µs` → `0.5Meg`).
- **dB to ratio:** ratio = 10^(dB/20). `µV/V` to ratio: ratio = 10⁶ / (µV/V).
  `V/mV` to V/V: multiply by 1000.
- **Cite the source** of every value: table name/number and row, or figure
  number, plus the page.

## Parameter reference

Defaults are `OPAMP_FULL` / `FDOPAMP_FULL`. "–" = not available in that model.

### Gain and frequency response

| Param | Unit | Meaning | Defaults | How to get it |
|---|---|---|---|---|
| `A0` | V/V | open-loop DC gain without load | 200k / 100k | "Large-signal voltage gain" / "open-loop gain" (A_OL, A_VD). V/mV × 1000; dB → ratio. The datasheet value is at a load R_L: with `ROUTDC` set, A0 = A_OL·(R_L + ROUT + ROUTDC)/R_L; otherwise use A_OL directly. |
| `GBW` | Hz | gain-bandwidth product = unity-gain frequency of the dominant-pole response | 1Meg / 100Meg | "Gain-bandwidth product" or "unity-gain bandwidth". For a decompensated part use the GBW, not the unity-gain frequency. |
| `FP2`, `FP3` | Hz | second and third poles; 0 = 3·`GBW`, 10·`GBW` | 0, 0 / 0, 0 | Leave 0 unless the datasheet gives a phase margin or a phase-vs-frequency plot; then use the "Phase margin" table below (FP3 ≈ 3.3·FP2). With 0 the phase margin is about 70° whatever `GBW` is, as long as the output pole 1/(2π·`ROUT`·`COUT`) is above about 10·`GBW` (see sanity check 13). |
| `SR` | V/s | slew rate. FDA: slew rate of the **differential** output (each output slews at SR/2) | 0.5Meg / 200Meg | "Slew rate". For an FDA check whether the datasheet gives it per output or differential; per output → `SR` = 2 × value. |
| `SRR`, `SRF` | V/s | slew rate of the rising / falling output; 0 = `SR` | 0 / – | Only if the datasheet gives SR+ and SR− separately, or a large-signal pulse plot shows clearly different slopes (> 10 %). Leave 0 otherwise. |
| `KJUMP` | – | in an unloaded voltage follower, output jump divided by a fast input step; sign = edge: > 0 jump on the rising edge (npn/nmos input pair), < 0 on the falling edge (pnp/pmos/p-JFET pair) | 0 / 0 | From a voltage-follower large-signal pulse plot: look at the start of each output edge. If the output first moves (near-)vertically together with the input and only then continues as a sloped line, that vertical part is the jump. Measure the jump from the level before the edge to the point where the sloped part begins. KJUMP = (jump/step) × (RL + ROUT)/RL, negative if the jump is on the falling edge. Leave 0 only if both edges start with a slope. |

**Phase margin.** If the datasheet gives the open-loop phase margin (or a gain/phase
plot), choose FP2 from this table, interpolating linearly between columns (FP3 = 3.33·FP2, open loop, differential drive);
otherwise leave FP2 and FP3 at 0. Do not assume a phase margin. Above 80° the table
ends: use the 80° column and say so.

| PM | 45° | 50° | 55° | 60° | 65° | 70° | 75° | 80° |
|---|---|---|---|---|---|---|---|---|
| FP2 / GBW | 1.22 | 1.47 | 1.78 | 2.17 | 2.72 | 3.51 | 4.81 | 7.34 |
| fu / GBW | 0.82 | 0.85 | 0.89 | 0.92 | 0.94 | 0.96 | 0.98 | 0.99 |
| f₋₃dB(G=+1) / GBW | 1.42 | 1.49 | 1.55 | 1.58 | 1.56 | 1.48 | 1.35 | 1.22 |

Cross-check a phase margin read from a plot (often ±10°) with a small-signal step
response at G = +1 and light load, if the datasheet has one: overshoot 5 % ≈ 65°,
10 % ≈ 59°, 20 % ≈ 48°, 30 % ≈ 39° (second-order approximation). If the two disagree,
give both and use the one with less reading uncertainty. Use the step response only if
its step is smaller than about `SR/(2π·GBW)`: a larger "small-signal" step is partly
slew-limited (a sign of this is different overshoot on the two edges), and its
overshoot says little about the phase margin.

The measured unity-gain frequency fu is below GBW by the factor in the last row.
If the datasheet quotes only fu (unity-gain frequency) and the PM, set
GBW = fu / (that factor). If it gives no GBW but the −3 dB bandwidth of a unity-gain
follower ("closed-loop bandwidth, A_V = +1"), set GBW = f₋₃dB / (the factor in the
f₋₃dB row) for the phase margin you found (60° if none is known; say so); use this also
as a cross-check of a GBW read from a plot.

### Input: DC errors and impedance

| Param | Unit | Meaning | Defaults | How to get it |
|---|---|---|---|---|
| `VOS` | V | input offset voltage, in series with + input | 1m / 1m | "Input offset voltage" (typ). Sign is arbitrary; keep it positive unless told otherwise. |
| `IB` | A | input bias current, average of both pins; > 0 flows **into** the pins | 80n / 2u | "Input bias current". npn bipolar: positive. pnp bipolar: **negative** (current flows out). JFET/CMOS: the tiny leakage (pA); sign as the datasheet states (an explicitly signed table value or plot axis), else from the input device: p-channel JFET positive (gate leakage flows into the pins), n-channel JFET negative, CMOS positive. Input type unknown: use the datasheet magnitude as positive and say so; never keep the default. |
| `IOS` | A | I(inp) − I(inn) | 20n / 0.1u | "Input offset current". |
| `RID`, `CID` | Ω, F | differential input resistance / capacitance (between the inputs) | 2Meg, 1.4p / 1Meg, 1p | "Differential input resistance/capacitance" (r_id, C_id, Z_id). A bare "input resistance r_i" / "input capacitance C_i" is measured between the inputs with one input grounded, so it equals RID ∥ RIC and CID + CIC (per pin); in a bipolar datasheet RIC ≫ RID, so r_i is the differential value. If C_i and a common-mode C_ic are both given, CID = C_i − CIC. CMOS/JFET: use 1T if only "10^12 Ω" or "very high" is given. |
| `RIC`, `CIC` | Ω, F | common-mode input resistance / capacitance **of each pin** (RIC to mid-supply, CIC half to each rail; both look like "to ground" in a datasheet test with grounded supplies) | 400Meg, 0.75p / 200Meg, 1p | "Common-mode input impedance" r_ic ∥ C_ic → use directly. Only if the datasheet explicitly says the value is for both inputs tied together → RIC = 2·R, CIC = C/2. Never derive them from the differential RID/CID. If no common-mode value is given but a plot of I_B vs V_CM is, take RIC from its slope: RIC ≈ ΔV_CM/ΔI_B for each pin over the linear part of the input range (if the two pins differ, average their slopes, i.e. their conductances), and say so; otherwise keep the defaults. Keep the CIC default. |
| `VCLMP`, `RCLMP` | V, Ω | two anti-parallel diodes between the inputs (forward voltage at 1 mA) and their series resistance; VCLMP = 100 means no clamp | 100, 100 | Only if the datasheet shows back-to-back input protection diodes between the inputs (schematic, or "differential input voltage limited to ±0.7 V"): VCLMP ≈ 0.7. RCLMP = the total internal series resistance if given, else 100. |

### Common-mode and supply rejection

| Param | Unit | Meaning | Defaults | How to get it |
|---|---|---|---|---|
| `CMRR` | ratio | DC CMRR, signed (see "Signs" below); 0 = not given | −31.6k / 31.6k | "Common-mode rejection ratio" (dB → ratio; µV/V → ratio), entered as **positive**. |
| `PSRR` | ratio | DC PSRR with both supplies moved apart, per volt of each supply, signed; 0 = not given | 31.6k / 10k | The usual single "supply voltage rejection ratio" (k_SVR, PSRR) measured with ±V_S varied together, e.g. "V_S = ±2.5 V to ±15 V". In µV/V: ratio = 10⁶/(µV/V). If the datasheet defines it per volt of the total supply span (V_CC − V_EE) rather than per volt of each supply, divide the ratio by 2 and say so; if it does not say, use the value directly and say so. |
| `PSRRP`, `PSRRN` | ratio | DC rejection of the positive / negative supply **alone**, signed; 0 = not given | 0, 0 / 0, 0 | Only if the datasheet gives separate +PSRR and −PSRR values (each supply varied with the other fixed), entered as positive. Do not copy a single PSRR into both: use `PSRR`. |
| | | **Rules of the model** (a part without a ground pin). The errors per volt of vcc (T_P), vee (T_N) and input common mode (T_C) obey T_P + T_N + T_C = 1/A0 at DC (0 for the FDA), and PSRR = 1/(T_P − T_N), each T = 1/value with its sign. So only two of these four are independent. The model uses the first two given in the order `PSRRP`, `PSRRN`, `CMRR`, `PSRR` exactly (the defaults of `CMRR` and `PSRR` count as given) and derives the others. The same holds for the slopes above the corners, whose signs the model sets itself. **Signs:** a positive value means that a rise of that supply (of the input common mode; for `PSRR`, of both supplies apart) moves the output like a positive `VOS`. In a real part the DC sign is set by device mismatch: it differs from unit to unit and can change with temperature, so a datasheet cannot give it. Do not guess it: enter magnitudes as positive (as for `VOS`), unless a typical-unit plot of offset vs common-mode voltage or vs supply voltage shows the slope, and say which you did. To bracket the spread, the user can flip signs: equal signs of `PSRRP` and `PSRRN` give the worst derived CMRR, opposite signs the best. | | | Give the values the datasheet has (all of them; the model sorts them out), then run `python3 tools/rejection.py <params>` if you can (`--fda` for the FDA): it prints what the model makes of them and flags a given value that is not honoured (CONFLICT). In the notes, report the derived values and any conflict. Typical case, a datasheet with `CMRR` and one `PSRR`: both are honoured, and PSRR+ and PSRR− come out near PSRR, differing by the CMRR term. With `PSRRP`, `PSRRN` and `CMRR` all given, `CMRR` is derived from the two PSRRs and may differ from the table. |
| `FCMRR` | Hz | CMRR falls at 20 dB/decade above this; 0 = not given | 0 / 0 | No CMRR plot: leave 0. Otherwise, from the CMRR vs frequency plot. Most robust: take one point (f_x, CMRR_x in dB) on the sloped part, one or two decades above the bend (curves often steepen further up, where other poles act), and compute FCMRR = f_x · 10^((CMRR_x − CMRR_DC)/20), where CMRR_DC is the value you set for `CMRR` (then the model's asymptote passes through the plotted point). Read a second point one decade away and check that the two differ by about 20 dB; if not, you are on the wrong curve or misreading the axis. If the check still fails after re-reading, do not choose a value between your estimates: use the point nearest the bend, mark it low confidence, and give the other estimate in the notes. If the plot's low-frequency level differs from the table value, say so. Cross-check with the frequency where the curve is 3 dB below its DC value. Then run sanity check 12 (CMRR left at `GBW`). |
| `FPSRR` | Hz | corner of `PSRR`, and of PSRR+/PSRR− when `FPSRRP`/`FPSRRN` are 0; 0 = not given | 0 / 0 | No PSRR plot: leave 0 (the model then takes the coupling through its compensation, as in a real part, `OPAMP_FULL`; FDA: corners at 10⁻³·`GBW`). Otherwise from the PSRR vs frequency plot, with the same formula as FCMRR. A slope is used only for a quantity whose DC value is given. |
| `FPSRRP`, `FPSRRN` | Hz | separate corners of PSRR+ and PSRR− | 0, 0 / 0, 0 | If the plot shows separate +PSRR and −PSRR curves, set each from its own curve (same formula, each with its own DC value; give `PSRRP`, `PSRRN` too). |
| `KREF` | – | where the gain stages (the CM loop of the FDA) are referred: vee + KREF·(vcc − vee) | 0.5 / 0.5 | The supply it leans to couples through the compensation as 1/A(f) (above the corners and with no PSRR plot, the PSRR of that supply falls with the open-loop gain); the specified rejection totals do not depend on it. If the simplified schematic shows the compensated gain stage (the common-emitter or common-source driver with the Miller capacitor) working from V−, use 0; from V+, use 1 (say which transistor). Otherwise keep 0.5. FDA: keep 0.5. |
| `VCCN`, `VEEN` | V | nominal supplies the PSRR is referred to | 15, −15 / 5, −5 | The supply of your chosen operating condition. Single supply: VEEN = 0. |
| `VCMN` | V | input CM voltage at which VOS is specified | mid-supply | Only if the test condition says so (e.g. "V_CM = 0 V" on a single supply, or "V_CM = V_S/2"). Otherwise omit (= mid-supply). |

### Noise

| Param | Unit | Meaning | Defaults | How to get it |
|---|---|---|---|---|
| `ENOISE` | V/√Hz | white input voltage noise | 20n / 5n | "Input voltage noise density" at 1 kHz or 10 kHz (the flat part), or read the flat part of the e_n plot. |
| `FCEN` | Hz | 1/f corner of the voltage noise | 200 / 1k | Corner frequency from the plot, or from a low-frequency density: FCEN = f₁·((e_n(f₁)/ENOISE)² − 1), e.g. with e_n at 10 Hz. From the 0.1–10 Hz peak-to-peak noise: FCEN = ((Vpp/6.6/ENOISE)² − 9.9)/4.605. |
| `INOISE` | A/√Hz | white input current noise, each input | 0.5p / 1p | "Input current noise density" (flat part). JFET/CMOS: often fA/√Hz. |
| `FCIN` | Hz | 1/f corner of the current noise; 0 = white only | 0 / 0 | Only if the i_n plot or a low-frequency i_n value shows a 1/f rise; same formula as FCEN. |

### Supplies, input range and output swing

| Param | Unit | Meaning | Defaults | How to get it |
|---|---|---|---|---|
| `ICCQ` | A | quiescent supply current, vcc → vee, **per amplifier** | 1.7m / 10m | "Supply current" (I_CC, I_Q) ÷ number of channels if the value is for the whole package. |
| `ICMHI`, `ICMLO` | V | input CM range: distance below vcc / above vee where the input-stage gain has fallen to half; negative = beyond the rail | 2, 2 / 1.5, 1 | From "common-mode input voltage range" (V_ICR, V_CM): headroom = V_CC − V_CM,max (and V_CM,min − V_EE). Use the typical value if given, else the min. Set ICM ≈ headroom − 1.5·VK, where headroom is the distance from the rail to the end of the specified range (not the range itself). Rail-to-rail inputs: a small negative value (the range extends beyond the rail by that much). |
| `VK` | V | width of the gain roll-off at the input-range edges; it also sets how sharply a follower driven past the edge stops (the knee is a few `VK` wide) | 0.15 / 0.1 | Keep the default for bipolar and JFET inputs unless the datasheet plots the edge (a gradual loss of gain, e.g. offset or gain vs V_CM, may need 0.3–0.5). CMOS inputs whose range is ended by the tail current source stop sharply: use 0.01–0.02 (a transistor-level p-MOS reference gives 0.01). Rail-to-rail CMOS whose range extends beyond the rails: 0.05. A smaller `VK` moves the follower's stop point toward the half-gain point, so set `ICMHI`/`ICMLO` after choosing `VK`. |
| `PRHI`, `PRLO` | – | phase reversal through a junction of the input pair at the top / bottom: npn bipolar inputs reverse at the top (base-collector junction), p-JFET inputs at the bottom (gate-drain junction), CMOS inputs do not reverse; the output runs to the wrong rail at about `PRHI`·`SR`; 0 = none | 0, 0 / 0, 0 | Only if the datasheet shows or states that the output reverses when an input goes beyond the top (bottom) of the common-mode range: set `PRHI` (`PRLO`) = 2 (transistor-level references give 1.6–3.5). "No phase reversal", or nothing said → 0. Reversal is normally one-sided: set only the side the datasheet names. |
| `VPRHI`, `VPRLO` | V | position of the reversal: input voltage below `vcc` / above `vee` where the output flips; < 0 = beyond the rail | 0, 0 / 0, 0 | From the stated or plotted input voltage at which the output reverses (e.g. "reverses for inputs within 0.2 V of V−" → `VPRLO` = 0.2). If only "beyond the common-mode range" is said, use the headroom at the end of the specified range (V_CC − V_CM,max, or V_CM,min − V_EE). |
| `IPR` | A | input current through the conducting junction during reversal; about the tail current of the input pair | 0 (= `SR`·30 pF) / 0 (= `SR`·1 pF) | Keep 0 unless the datasheet gives the input current during reversal, or a series resistance R that prevents reversal for an overdrive V_od: then `IPR` = V_od/(0.9·R). |
| `VCMT`, `VKT` | V | rail-to-rail input crossover: position of the transition between the input pairs (distance below vcc) and its width | 1, 0.1 / 1, 0.1 | From the V_OS vs V_CM plot of a rail-to-rail input part: VCMT = V_CC − (V_CM at the middle of the step); VKT = (10 %–90 % width of the step) / 2.2. Needed only with `DVOST` or `DIBT`. |
| `DVOST` | V | offset change across the transition; `VOS` applies below it | 0 / 0 | From the same plot (typical curve): V_OS above the transition minus V_OS below it. `VOS` is then the value below the transition, where it is usually specified (e.g. V_CM = V_S/2). |
| `DIBT` | A | bias-current change across the transition, each pin | 0 / 0 | From an I_B vs V_CM plot: I_B above the transition minus I_B below it (bipolar rail-to-rail inputs often change sign). |
| `VHD`, `VLD` | V | minimum headroom between the output and vcc / vee (no load) | 2, 2 / 1.2, 1.2 | From "output voltage swing" at load RL: VHD = (V_CC − V_OH) − (V_OH/RL)·ROUT, VLD = (V_OL − V_EE) − (|V_OL|/RL)·ROUT (V_OH, V_OL measured from ground, RL to ground). Use a typical swing (with several loads, the lightest load) in preference to a min spec at the chosen load; a min-only swing gives a pessimistic VHD, so say so. For a single supply, RL usually goes to V_S/2: use that voltage instead of ground. If the result is ≤ 0, the swing spec and ROUT disagree (often because r_o is a high-frequency value): use `RSATH`/`RSATL` (next row) if the datasheet has swing at two loads or a swing-vs-current plot; otherwise set 0.05, say so, and state the swing the model will then give, (V_CC − VHD)·RL/(RL + ROUT). |
| `RSATH`, `RSATL` | Ω | saturation resistance: with the output saturated, headroom = VHD + RSATH·I_source (top), VLD + RSATL·I_sink (bottom); 0 = ROUT | 0, 0 / – | OPAMP_FULL only. From an "output voltage swing vs output current" plot (often one curve per rail, as V_CC − V_OH and V_OL − V_EE): read the headroom at two currents in the range the user will load the part (e.g. 1 mA and 10 mA, below half the short-circuit current); RSATH = Δheadroom/ΔI, and then VHD = headroom − RSATH·I (the line's intercept; a real stage bends at small currents, so it may differ from the swing without load). Or from the swing at two loads R₁, R₂ in the table: I = V_OH/R. Give them only if they differ from ROUT by more than 15 %; otherwise use the VHD rule above. CMOS rail-to-rail stages typically saturate with a far smaller slope than their small-signal r_o, bipolar ones often with a larger one. |

### Output stage (per output for the FDA)

| Param | Unit | Meaning | Defaults | How to get it |
|---|---|---|---|---|
| `ROUTDC` | Ω | additional open-loop output resistance at DC (falls away above f_d = GBW/A0) | 0 / 0 | Only if the datasheet supports it: A_OL at two loads R₁, R₂ (common for CMOS parts) gives R = ROUT + ROUTDC from A₁/A₂ = R₁(R₂ + R)/(R₂(R₁ + R)) (A₁ at R₁, A₂ at R₂), i.e. R = R₁R₂(A₂ − A₁)/(A₁R₂ − A₂R₁) with linear gains; or an open-loop Z_out plot that rises toward DC (ROUTDC = Z_out at low frequency − ROUT). Otherwise leave 0 (model 1.6 and later; not in older libraries). |
| `ROUT` | Ω | open-loop output resistance | 75 / 10 | "Open-loop output impedance/resistance" (r_o, Z_O), or the flat part of the open-loop Z_out plot. **Not** the closed-loop output impedance. Use r_o directly. (With `VXO` > 0 the model doubles the small-signal ROUT at idle; that is a model feature, not a reason to halve r_o.) |
| `COUT` | F | output capacitance (half to each rail) | 3p / 1p | Rarely given: keep the default, unless an open-loop Z_out plot shows the peak (see `LOUT`). |
| `LOUT`, `RLOUT` | H, Ω | output inductance in series with `ROUT`, and a resistance across it (Zout levels off at `ROUT` + `RLOUT`); 0 = none (`OPAMP_FULL` only) | 0, 0 / – | Only from an open-loop Z_out plot that rises above the flat `ROUT` part: `LOUT` = √(\|Z\|² − `ROUT`²)/(2πf) at a point f on the rise, well below the peak. If the curve levels off or peaks at Z_pk, `RLOUT` ≈ Z_pk − `ROUT`, and `COUT` ≈ 1/((2π f_pk)²·`LOUT`) from the peak frequency f_pk. Otherwise leave 0: most datasheets show only the closed-loop Z_out. |
| `ISRC`, `ISNK` | A | maximum source / sink current | 25m / 50m | "Short-circuit output current" (I_SC, I_OS), source and sink separately if given. |
| `VXO` | V | class-AB crossover: below about VXO/ROUT the small-signal output resistance is 2·ROUT; 0 disables | 2m / 0 | Keep 2m for bipolar class-AB parts with a visible crossover; 0 for CMOS rail-to-rail outputs and FDAs. |

### FDA only (`FDOPAMP_FULL`): common-mode loop and `vocm` pin

| Param | Unit | Meaning | Default | How to get it |
|---|---|---|---|---|
| `A0CM` | V/V | DC gain of the CM error amplifier | 10k | Rarely given; a "V_OCM gain error" e implies A0CM ≈ 1/e. |
| `GBWCM` | Hz | unity-gain frequency of the CM error amplifier | 50Meg | From "V_OCM small-signal bandwidth" f_ocm: GBWCM ≈ 0.8·f_ocm (with `FPCM2` = 0, i.e. 4·GBWCM, the closed CM bandwidth is about 1.3·GBWCM). |
| `FPCM2` | Hz | second pole of the CM loop; 0 = 4·`GBWCM` | 0 | Leave 0 unless the V_OCM response shows peaking; then lower it relative to `GBWCM`. The CM-loop phase margin depends only on FPCM2/GBWCM: 76° at 4 (the default, no peaking), 72° at 3, 65° at 2, 60° at 1.5. |
| `SRCM` | V/s | slew rate of the output CM voltage | 100Meg | "V_OCM slew rate". |
| `VOSCM` | V | output CM offset: V(out,cm) = V(vocm) + VOSCM | 1m | "Output common-mode offset" / "V_OCM offset (from V_OCM input)". |
| `KBAL` | – | output balance error: the output CM moves by KBAL × the differential output | 0 | "Output balance error" (ΔV_OC/ΔV_OD), dB → ratio 10^(dB/20); use the low-frequency value. |
| `RVOCM` | Ω | vocm pin: 2·RVOCM to each rail, i.e. RVOCM to mid-supply when the pin is open | 50k | "V_OCM input resistance" (the pin's resistance). If the datasheet's default V_OCM is not mid-supply, say so: the model always floats to mid-supply. |
| `CVOCM` | F | vocm pin capacitance | 1p | "V_OCM input capacitance", else default. |

FDA datasheets often specify noise, offset and bias currents as for a single op amp:
map them as above (input-referred, per input pin for INOISE and IB).

### Not modelled

Temperature drifts, overload recovery time, settling tails, EMI rejection,
offset changes with V_CM other than a rail-to-rail crossover step, input protection
(ESD) diodes to the rails, and changes of GBW, SR or noise across a rail-to-rail
crossover. Mention relevant
datasheet values in the notes, but do not try to map them.

## Plausibility ranges by device class

Use these only to catch reading and unit errors: if a value falls far outside the
range of its class, re-read the datasheet and redo the conversion. A value outside
the range can still be right; say so in the notes. Never use these numbers as
results.

| Quantity | General-purpose bipolar | Precision bipolar | JFET input | CMOS rail-to-rail | High-speed (VFB) | FDA |
|---|---|---|---|---|---|---|
| A0 (V/V) | 20k–1M | 300k–20M | 20k–500k | 10k–3M | 1k–100k | 1k–100k |
| GBW (Hz) | 0.3–5 M | 0.3–20 M | 1–20 M | 10k–20 M | 50 M–3 G | 50 M–5 G |
| SR (V/µs) | 0.1–3 | 0.1–5 | 3–50 | 0.003–20 | 50–5000 | 100–10000 (diff.) |
| VOS | 0.3–5 mV | 10–200 µV | 0.5–10 mV | 0.05–5 mV | 0.2–5 mV | 0.1–5 mV |
| IB (magnitude) | 10–500 nA | 0.5–50 nA | 5–500 pA | 0.1–10 pA | 0.5–20 µA | 0.1–20 µA |
| ENOISE (nV/√Hz) | 8–50 | 2–15 | 5–40 | 5–150 | 1–15 | 1–10 |
| INOISE | 0.1–2 pA/√Hz | 0.1–2 pA/√Hz | 0.5–20 fA/√Hz | 0.1–20 fA/√Hz | 1–20 pA/√Hz | 1–20 pA/√Hz |
| FCEN (Hz) | 10–1k | 1–20 | 30–3k | 100–30k | 1k–100k | 1k–100k |
| CMRR (dB) | 70–100 | 100–140 | 75–100 | 60–110 | 50–90 | 60–90 |
| ROUT, open loop (Ω) | 30–300 | 30–300 | 30–300 | 10–1000 | 1–50 | 1–30 |
| ICCQ per amplifier | 0.1–3 mA | 0.3–5 mA | 0.1–3 mA | 0.5 µA–3 mA | 2–25 mA | 2–30 mA |
| ISRC/ISNK | 10–40 mA | 10–40 mA | 10–60 mA | 5–150 mA | 30–200 mA | 30–200 mA |
| VHD, VLD | 0.8–2.5 V | 0.8–2 V | 0.8–2.5 V | 0.005–0.15 V | 0.8–2 V | 0.5–1.5 V |
| KJUMP (when visible) | 0.1–0.4 | rare | rare | rare | rare | rare |
| FCMRR | 100 Hz–10 kHz | 10 Hz–1 kHz | 100 Hz–10 kHz | 100 Hz–30 kHz | 100 kHz–10 MHz | 100 kHz–10 MHz |

## Sanity checks (do all of them; report any that fail)

1. GBW > fu, and `SR/(2π·GBW)` is between about 10 mV and 2 V. A much larger value
   usually means a wrong unit (V/µs vs V/s) or a decompensated part.
2. Slew rate against the large-signal plots, if there are any. For a "maximum peak
   output voltage vs frequency" curve, first read its test condition. Measured with an
   overdriven input (no distortion limit stated), the output becomes a slew-limited
   triangle: its knee is at f ≈ `SR/(4·Vp,max)` and above it the curve falls as
   `SR/(4f)`. Measured at a fixed distortion (e.g. "THD = 1 %"), the output is still a
   sine: the knee is at `SR/(2π·Vp,max)` and the curve falls as `SR/(2πf)`, 0.64 times
   lower.
   A follower pulse plot should show slopes of about `SR·RL/(RL+ROUT)`.
3. `ICCQ` is per amplifier.
4. `VHD + VLD` < V_CC − V_EE, and `ICMHI + ICMLO` < V_CC − V_EE.
5. `CMRR`, `PSRR`, `PSRRP`, `PSRRN` are ratios (magnitude > 1), not dB, and
   positive unless a plot gives the sign; a single datasheet PSRR goes into
   `PSRR`, not into `PSRRP` and `PSRRN`.
6. `IB` sign matches the input type.
7. Noise: `ENOISE` in V/√Hz (e.g. `9n`, not `9`), `INOISE` in A/√Hz.
8. For each value converted from a plot, give the reading uncertainty (e.g. ±10 %).
9. Consistency: every parameter has the same value in the instance line, the table
   and the notes. If a note recommends a different value, put that value in the
   instance line and the table, or explain why not.
10. Redo each unit conversion once more against the copied datasheet row.
11. Compare each extracted value with the plausibility range of the part's class;
    re-check any value far outside it.
12. CMRR left at the unity-gain frequency: `|CMRR|·FCMRR/GBW` (with `FCMRR` set; 0 is
    always fine) should be at least about 3 (10 dB), comfortably 10 (20 dB). The
    model's CMRR error source is in series with the input and grows at 20 dB/decade
    above `FCMRR`, so below about 3 a voltage follower's step response rings
    (≈ 15 % overshoot at 6 dB, ≈ 50 % at 0 dB). A lower value usually means `FCMRR`
    was read where the curve steepens (other poles), or from the wrong curve:
    re-read near the bend. If the datasheet really shows less, keep it and say that
    the follower response will overshoot.
13. Poles: with `FP2` set, `FP2/GBW` ≥ 1.2 (45° phase margin), and `FP3` ≥ `FP2`.
    The output pole 1/(2π·`ROUT`·`COUT`) should be above about 10·`GBW`; nearer, it
    takes about atan(`GBW`/f_out) from the phase margin that the FP2 table assumes
    (e.g. 14° for the default `ROUT` = 75 Ω and `COUT` = 3 pF at `GBW` = 100 MHz).
    Then choose FP2 for a correspondingly larger phase margin, or check whether
    `COUT` should be smaller for that part (it is rarely given).

## Output

Work everything out and run the sanity checks on a draft first. The answer itself
contains one final instance line and one table, with no corrections inside it.
Produce exactly these four parts.

**1. Summary line:** part, model (`OPAMP_FULL` or `FDOPAMP_FULL`), operating
condition (supply, load, 25 °C), typical/worst-case.

**2. The instance line**, ready to paste into a netlist. List only the parameters
whose value differs from the default (the table shows the rest); continuation
lines start with `+`:

```spice
* <part>, <supply>, typical, from <datasheet name, revision>
.include opamp_full.lib
X1 inp inn vcc vee out OPAMP_FULL PARAMS:
+ A0=200k GBW=1Meg SR=0.5Meg ...
```

For an FDA: `X1 inp inn vcc vee outp outn vocm FDOPAMP_FULL PARAMS: ...`.
For PSpice the same parameters work with `models/pspice/…lib`.

**3. The parameter table**, one row per model parameter (all of them, including those
left at the default):

| Param | Value | Datasheet value and condition | Source | Method | Confidence |
|---|---|---|---|---|---|
| A0 | 200k | 200 V/mV typ, RL ≥ 2 kΩ | Table 6.5, p. 5 | converted (×1000) | high |
| FP2 | 0 (= 3·GBW) | — | — | default | — |

Method is one of `direct`, `converted` (show the arithmetic), `from plot`
(figure, reading uncertainty), `derived` (formula above), `default`.
Confidence: `high` (table value), `medium` (plot or formula), `low` (rough
estimate), `—` (default).

**4. Notes:** the assumptions you made, the sanity-check results, and datasheet
features the model cannot represent. Ask the user about anything ambiguous instead
of guessing (e.g. which supply column to use).

## Verifying the result (optional)

Most assistants cannot do this; skip it unless you can run programs, or the user can.

With the repository checked out and a SPICE simulator (ngspice 42 or later; LTspice
and PSpice through `tests/cross_sim.py`), the extracted set can be checked by
simulation instead of by arithmetic alone:
- `tests/opamp_full_tests.cir` and `tests/fdopamp_full_tests.cir` measure A0, fu,
  phase margin, CMRR, PSRR, slew rate, swing, current limit, supply current and
  noise. Put the new parameters into the X instances there and compare the printed
  values with the datasheet; adjust FP2/FP3 if the phase margin is off, VHD/VLD if
  the swing is off.
- The examples in `examples/` reproduce typical datasheet plots (open-loop gain and
  phase, maximum output vs frequency, follower pulse response, noise). Running the
  matching example with the new parameters and overlaying the datasheet curve is the
  strongest check, and the way to fit KJUMP, SRR/SRF or FCMRR from a plot.

If the user runs the decks for you, ask for the printed results and compare them
with the datasheet in a short table.
