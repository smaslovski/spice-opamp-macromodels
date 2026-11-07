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

- Skill revision: **1.13** (2026-11-06)
- For model version: **1.4** of `OPAMP_FULL` / `FDOPAMP_FULL` (the `Version` line
  in the header of `opamp_full.lib` / `fdopamp_full.lib`)
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
| `A0` | V/V | open-loop DC gain | 200k / 100k | "Large-signal voltage gain" / "open-loop gain" (A_OL, A_VD). V/mV × 1000; dB → ratio. |
| `GBW` | Hz | gain-bandwidth product = unity-gain frequency of the dominant-pole response | 1Meg / 100Meg | "Gain-bandwidth product" or "unity-gain bandwidth". For a decompensated part use the GBW, not the unity-gain frequency. |
| `FP2`, `FP3` | Hz | second and third poles | 3Meg, 10Meg / 300Meg, 1G | Keep the defaults unless the datasheet gives a phase margin or a phase-vs-frequency plot; then use the "Phase margin" table below (FP3 ≈ 3.3·FP2). |
| `SR` | V/s | slew rate. FDA: slew rate of the **differential** output (each output slews at SR/2) | 0.5Meg / 200Meg | "Slew rate". For an FDA check whether the datasheet gives it per output or differential; per output → `SR` = 2 × value. |
| `SRR`, `SRF` | V/s | slew rate of the rising / falling output; 0 = `SR` | 0 / – | Only if the datasheet gives SR+ and SR− separately, or a large-signal pulse plot shows clearly different slopes (> 10 %). Leave 0 otherwise. |
| `KJUMP` | – | in an unloaded voltage follower, output jump divided by a fast input step; sign = edge: > 0 jump on the rising edge (npn/nmos input pair), < 0 on the falling edge (pnp/pmos/p-JFET pair) | 0 / 0 | From a voltage-follower large-signal pulse plot: look at the start of each output edge. If the output first moves (near-)vertically together with the input and only then continues as a sloped line, that vertical part is the jump. Measure the jump from the level before the edge to the point where the sloped part begins. KJUMP = (jump/step) × (RL + ROUT)/RL, negative if the jump is on the falling edge. Leave 0 only if both edges start with a slope. |

**Phase margin.** If the datasheet gives the open-loop phase margin (or a gain/phase
plot), choose FP2 from this table, interpolating linearly between columns (FP3 = 3.33·FP2, open loop, differential drive);
otherwise keep the defaults. Do not assume a phase margin.

| PM | 45° | 50° | 55° | 60° | 65° | 70° | 75° | 80° |
|---|---|---|---|---|---|---|---|---|
| FP2 / GBW | 1.22 | 1.47 | 1.78 | 2.17 | 2.72 | 3.51 | 4.81 | 7.34 |
| fu / GBW | 0.82 | 0.85 | 0.89 | 0.92 | 0.94 | 0.96 | 0.98 | 0.99 |

Cross-check a phase margin read from a plot (often ±10°) with a small-signal step
response at G = +1 and light load, if the datasheet has one: overshoot 5 % ≈ 65°,
10 % ≈ 59°, 20 % ≈ 48°, 30 % ≈ 39° (second-order approximation). If the two disagree,
give both and use the one with less reading uncertainty.

The measured unity-gain frequency fu is below GBW by the factor in the last row.
If the datasheet quotes only fu (unity-gain frequency) and the PM, set
GBW = fu / (that factor).

### Input: DC errors and impedance

| Param | Unit | Meaning | Defaults | How to get it |
|---|---|---|---|---|
| `VOS` | V | input offset voltage, in series with + input | 1m / 1m | "Input offset voltage" (typ). Sign is arbitrary; keep it positive unless told otherwise. |
| `IB` | A | input bias current, average of both pins; > 0 flows **into** the pins | 80n / 2u | "Input bias current". npn bipolar: positive. pnp bipolar: **negative** (current flows out). JFET/CMOS: the tiny leakage (pA); sign as the datasheet states (an explicitly signed table value or plot axis), else from the input device: p-channel JFET positive (gate leakage flows into the pins), n-channel JFET negative, CMOS positive. Input type unknown: use the datasheet magnitude as positive and say so; never keep the default. |
| `IOS` | A | I(inp) − I(inn) | 20n / 0.1u | "Input offset current". |
| `RID`, `CID` | Ω, F | differential input resistance / capacitance (between the inputs) | 2Meg, 1.4p / 1Meg, 1p | "Differential input resistance/capacitance" (r_id, C_id, Z_id). A bare "input resistance r_i" / "input capacitance C_i" is measured between the inputs with one input grounded, so it equals RID ∥ RIC and CID + CIC (per pin); in a bipolar datasheet RIC ≫ RID, so r_i is the differential value. If C_i and a common-mode C_ic are both given, CID = C_i − CIC. CMOS/JFET: use 1T if only "10^12 Ω" or "very high" is given. |
| `RIC`, `CIC` | Ω, F | common-mode input resistance / capacitance **of each pin to ground** | 400Meg, 0.75p / 200Meg, 1p | "Common-mode input impedance" r_ic ∥ C_ic → use directly. Only if the datasheet explicitly says the value is for both inputs tied together → RIC = 2·R, CIC = C/2. Never derive them from the differential RID/CID: if no common-mode value is given, keep the defaults. |
| `VCLMP`, `RCLMP` | V, Ω | two anti-parallel diodes between the inputs (forward voltage at 1 mA) and their series resistance; VCLMP = 100 means no clamp | 100, 100 | Only if the datasheet shows back-to-back input protection diodes between the inputs (schematic, or "differential input voltage limited to ±0.7 V"): VCLMP ≈ 0.7. RCLMP = the total internal series resistance if given, else 100. |

### Common-mode and supply rejection

| Param | Unit | Meaning | Defaults | How to get it |
|---|---|---|---|---|
| `CMRR` | ratio | DC CMRR | 31.6k (90 dB) | "Common-mode rejection ratio" (dB → ratio; µV/V → ratio). |
| `FCMRR` | Hz | CMRR falls at 20 dB/decade above this | 200 / 100k | From the CMRR vs frequency plot. Most robust: take one point (f_x, CMRR_x in dB) on the sloped part, one or two decades above the bend (curves often steepen further up, where other poles act), and compute FCMRR = f_x · 10^((CMRR_x − CMRR_DC)/20), where CMRR_DC is the value you set for `CMRR` (then the model's asymptote passes through the plotted point). Read a second point one decade away and check that the two differ by about 20 dB; if not, you are on the wrong curve or misreading the axis. If the check still fails after re-reading, do not choose a value between your estimates: use the point nearest the bend, mark it low confidence, and give the other estimate in the notes. If the plot's low-frequency level differs from the table value, say so. Cross-check with the frequency where the curve is 3 dB below its DC value. |
| `PSRRP`, `PSRRN` | ratio | DC rejection of the positive / negative supply | 31.6k / 10k | "Supply voltage rejection ratio" (k_SVR, PSRR). If only one value (both supplies varied together) is given, use it for both. |
| `FPSRR` | Hz | PSRR falls at 20 dB/decade above this | 100 / 100k | From the PSRR vs frequency plot, with the same formula as FCMRR, on the lower (worse) of the two supply curves. |
| `FPSRRP`, `FPSRRN` | Hz | separate corners of PSRR+ and PSRR−; 0 = `FPSRR` | 0, 0 / 0, 0 | If the plot shows separate +PSRR and −PSRR curves whose corners (same formula, each with its own DC value) differ by more than a factor of 2, set each from its own curve and keep `FPSRR` from the worse one. Only if the user's library lists `FPSRRP`/`FPSRRN` in its header (older libraries reject them); otherwise use `FPSRR` alone and give the other corner in the notes. |
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
| `VK` | V | width of the gain roll-off at the input-range edges | 0.15 / 0.1 | Keep the default unless the datasheet plots the edge. Rail-to-rail CMOS: 0.05. |
| `VHD`, `VLD` | V | minimum headroom between the output and vcc / vee (no load) | 2, 2 / 1.2, 1.2 | From "output voltage swing" at load RL: VHD = (V_CC − V_OH) − (V_OH/RL)·ROUT, VLD = (V_OL − V_EE) − (|V_OL|/RL)·ROUT (V_OH, V_OL measured from ground, RL to ground). Use a typical swing (with several loads, the lightest load) in preference to a min spec at the chosen load; a min-only swing gives a pessimistic VHD, so say so. For a single supply, RL usually goes to V_S/2: use that voltage instead of ground. If the result is ≤ 0, the swing spec and ROUT disagree (often because r_o is a high-frequency value): take the swing from a plot, or set 0.05, say so, and state the swing the model will then give, (V_CC − VHD)·RL/(RL + ROUT). |

### Output stage (per output for the FDA)

| Param | Unit | Meaning | Defaults | How to get it |
|---|---|---|---|---|
| `ROUT` | Ω | open-loop output resistance | 75 / 10 | "Open-loop output impedance/resistance" (r_o, Z_O), or the flat part of the open-loop Z_out plot. **Not** the closed-loop output impedance. Use r_o directly. (With `VXO` > 0 the model doubles the small-signal ROUT at idle; that is a model feature, not a reason to halve r_o.) |
| `COUT` | F | output capacitance to ground | 3p / 1p | Rarely given: keep the default. |
| `ISRC`, `ISNK` | A | maximum source / sink current | 25m / 50m | "Short-circuit output current" (I_SC, I_OS), source and sink separately if given. |
| `VXO` | V | class-AB crossover: below about VXO/ROUT the small-signal output resistance is 2·ROUT; 0 disables | 2m / 0 | Keep 2m for bipolar class-AB parts with a visible crossover; 0 for CMOS rail-to-rail outputs and FDAs. |

### FDA only (`FDOPAMP_FULL`): common-mode loop and `vocm` pin

| Param | Unit | Meaning | Default | How to get it |
|---|---|---|---|---|
| `A0CM` | V/V | DC gain of the CM error amplifier | 10k | Rarely given; a "V_OCM gain error" e implies A0CM ≈ 1/e. |
| `GBWCM` | Hz | unity-gain frequency of the CM error amplifier | 50Meg | From "V_OCM small-signal bandwidth" f_ocm: GBWCM ≈ 0.8·f_ocm (with the default FPCM2 the closed CM bandwidth is about 1.3·GBWCM). |
| `FPCM2` | Hz | second pole of the CM loop | 200Meg | Keep ≥ 4·GBWCM unless the V_OCM response shows peaking. |
| `SRCM` | V/s | slew rate of the output CM voltage | 100Meg | "V_OCM slew rate". |
| `VOSCM` | V | output CM offset: V(out,cm) = V(vocm) + VOSCM | 1m | "Output common-mode offset" / "V_OCM offset (from V_OCM input)". |
| `RVOCM` | Ω | vocm pin: 2·RVOCM to each rail, i.e. RVOCM to mid-supply when the pin is open | 50k | "V_OCM input resistance" (the pin's resistance). If the datasheet's default V_OCM is not mid-supply, say so: the model always floats to mid-supply. |
| `CVOCM` | F | vocm pin capacitance | 1p | "V_OCM input capacitance", else default. |

FDA datasheets often specify noise, offset and bias currents as for a single op amp:
map them as above (input-referred, per input pin for INOISE and IB).

### Not modelled

Temperature drifts, output balance error, overload recovery time, phase reversal,
input-range-dependent offset, settling tails, EMI rejection. Mention relevant
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
2. Slew rate against the large-signal plots, if there are any. A "maximum peak output
   voltage vs frequency" curve is measured with an overdriven input, so the output
   becomes a slew-limited triangle: its knee is at f ≈ `SR/(4·Vp,max)` and above it
   the curve falls as `SR/(4f)`. (`SR/(2π·Vp)` is the full-power bandwidth for an
   undistorted sine, about 0.64 times lower; do not compare it with this curve.)
   A follower pulse plot should show slopes of about `SR·RL/(RL+ROUT)`.
3. `ICCQ` is per amplifier.
4. `VHD + VLD` < V_CC − V_EE, and `ICMHI + ICMLO` < V_CC − V_EE.
5. `CMRR`, `PSRRP`, `PSRRN` are ratios (> 1), not dB.
6. `IB` sign matches the input type.
7. Noise: `ENOISE` in V/√Hz (e.g. `9n`, not `9`), `INOISE` in A/√Hz.
8. For each value converted from a plot, give the reading uncertainty (e.g. ±10 %).
9. Consistency: every parameter has the same value in the instance line, the table
   and the notes. If a note recommends a different value, put that value in the
   instance line and the table, or explain why not.
10. Redo each unit conversion once more against the copied datasheet row.
11. Compare each extracted value with the plausibility range of the part's class;
    re-check any value far outside it.

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
| FP2 | 3Meg | — | — | default | — |

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
