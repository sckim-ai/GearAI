# GearDesign IPC MCP Server Usage Guide

## Overview
Communicates with the gear design system via IPC to perform tooth geometry calculations, load analysis, sizing, and report generation.
**Important**: All operations are session-based and must start with `initialize()`.

---

## Workflow Selection (Decision Tree)

```
Analyze User Request
    ↓
[Performance Criteria Requested?] ("low noise", "lightweight", "high efficiency", etc.)
    ├─ YES → SimpleSizing Workflow
    └─ NO
        ↓
    [Specific Values for Module/Teeth?]
        ├─ NO → SimpleSizing Workflow
        └─ YES
            ↓
        [Abstract Expression?] ("appropriate", "good", etc.)
            ├─ YES → SimpleSizing Workflow
            └─ NO → Basic Workflow
    ↓
Execute Workflow → Evaluate Results
    ↓
[Results Satisfactory?]
    ├─ YES → End (Generate Outputs)
    └─ NO (Improvement Needed)
        ↓
    [Select Improvement Method]
        ├─ Fine-tuning (facewidth/helix angle, etc.) → Re-run Basic Workflow
        └─ Re-explore Module/Teeth → Re-run SimpleSizing Workflow
    ↓
(Up to 5 iterations allowed)
```

### 1️⃣ Basic Workflow (When Specific Specifications Provided)

**Condition**: Module, teeth count, etc. - **all provided as specific values**
**Example**: "Module 3, teeth 20-60, helix angle 15 degrees"

**Execution Sequence**:
```
initialize() → modify_gear_data() → calc_geometry() → calc_load_case()
→ get_allresults_summary() (MUST display as table)
→ [Result Evaluation]
   ├─ Satisfactory → get_2D_image/get_gear_report/get_3d_image/get_3d_modeling → End
   └─ Needs Improvement → modify_gear_data() → calc_geometry() → calc_load_case() (Repeat)
```

### 2️⃣ SimpleSizing Workflow (Rough Conditions/Performance Criteria)

**Condition**: **Any one** of the following applies
- Module/teeth as range or unspecified (e.g., "module 2~4", "only gear ratio provided")
- Performance criteria requested (e.g., "low noise", "lightweight", "high efficiency")
- Abstract expression (e.g., "appropriate", "find for me")

**Execution Sequence**:
```
initialize() → modify_gear_data(default settings) → simple_sizing_gearpair()
→ get_simplesizing_results() (rank-based analysis + MUST display as table)
→ User selection → apply_simplesizing_case(row_index)
→ calc_geometry() → calc_load_case() → get_allresults_summary()
→ [Result Evaluation]
   ├─ Satisfactory → get_2D_image/get_gear_report/get_3d_image/get_3d_modeling → End
   └─ Needs Improvement
      ├─ Fine-tuning (facewidth/helix angle) → modify_gear_data() → calc_geometry() → calc_load_case() (Repeat)
      └─ Re-explore Module/Teeth → simple_sizing_gearpair() → get_simplesizing_results() (Repeat)
```

### 3️⃣ Result Evaluation and Improvement Guide

**3-Level Evaluation Criteria** (⚠️ Excessive is also improvement needed!):

| Item | Insufficient (NG) | Appropriate (OK) | Excessive (Needs Improvement) |
|------|-------------------|------------------|-------------------------------|
| **Safety Factor** | Below required | 1.0~1.3× required | 1.5× required or more |
| **Overlap ratio** | - | Within target ±0.15 | Beyond target ±0.15 |
| **Constraints** | Out of range | Within range | - |

**Safety Factor Evaluation Example**:
- When required safety factor is 1.2:
  - Insufficient: Actual 1.1 (NG, unstable)
  - Appropriate: Actual 1.25 (OK, lightweight optimal)
  - Excessive: Actual 2.0 (Needs improvement, overweight)

**Overlap Ratio Evaluation Example**:
- When target is 1.0:
  - Appropriate: 0.95~1.15 (OK)
  - Excessive: 1.35 (Needs improvement, should target 1.0 or 2.0)
- When target is 2.0:
  - Appropriate: 1.85~2.15 (OK)
  - Excessive: 1.35 (Needs improvement, too far from target)

**Improvement Method Selection**:

| Evaluation Result | Issue | Recommended Workflow | Notes |
|-------------------|-------|---------------------|-------|
| Insufficient | Safety factor lacking | Basic | Increase module or facewidth |
| Excessive | Safety factor excessive (lightweight goal) | Basic | Decrease module or facewidth |
| Excessive | Only Contact excessive | Basic | Decrease module |
| Excessive | Only Bending excessive | Basic | Increase module |
| Excessive | Overlap ratio inappropriate | Basic | Adjust facewidth/helix angle |
| Insufficient | Need to re-explore module/teeth | SimpleSizing | Adjust search range and re-run |

**Iteration Limit**: Up to 5 iterations, propose constraint relaxation to user if more needed

---

## Core Tools

### Session Management
- **`initialize()`**: Create session and start IPC → Returns `session_id` (required for all functions)
- **`delete_session(session_id)`**: Delete session and files

### Data Input/Modification
- **`modify_gear_data(user_message, session_id)`**: Modify gear data with natural language
  - Automatically calculates teeth ratio when gear ratio requested
  - For operating condition changes, derive user_message to precisely match user requirements
  - Depending on gear type, torque/speed conditions must follow these rules:

   1) CASE1: Gear Pair - Must include ALL of:
    - 1 of Gear1/Gear2 speed (NOT recommended to provide both speeds as it conflicts with gear ratio)
    - 1 of Gear1/Gear2 power OR 1 of Gear1/Gear2 torque (power and torque are interconvertible; NOT recommended to provide both)
    - Gear1/Gear2 may be called input/output gears or Pinion/Wheel depending on user terminology
    - Example1: Input speed 1000 rpm, Output torque 50Nm → OK
    - Example2: Input speed 1000 rpm, Output speed 500 rpm, Output torque 50Nm → NG (both speeds provided)
    - Example3: Input speed 1000 rpm, Input power 100W, Output torque 50Nm → NG (both power and torque provided)

   2) CASE2: Three Gear
    - 1 of Gear1/Gear2/Gear3 speed (NOT recommended to provide both input/output speeds as it conflicts with gear ratio)
    - 2 of Gear1/Gear2/Gear3 power OR 2 of torque (power and torque are interconvertible; NOT recommended to provide both)
    - Gear1/Gear2/Gear3 may be called input/idler/output gears or Pinion/Idler/Wheel depending on user terminology
    - Example1: Gear1 speed 1000 rpm, Gear2 power 100W, Gear3 torque 50Nm → OK
    - Example2: Gear1 speed 1000 rpm, Gear2 speed 500 rpm, Gear3 torque 50Nm → NG (both speeds provided)
    - Example3: Gear1 speed 1000 rpm, Gear2 power 100W, Gear3 power 50W → NG (both power and torque provided)

   3) CASE3: Simple Planetary, Double Pinion Planetary
    - 2 of Sun/Carrier/Ring speeds (planetary gear speed is determined by 2 of 3 inputs, so 2 inputs required)
    - 1 of Sun/Carrier/Ring power OR 1 of torque (planetary gear power or torque calculates all others from 1 input and input speeds)

    #### Input/Output Operating Condition Units (When user doesn't specify units, assume these)
    - Time unit: "hr" (e.g., "100 hr", "5000 hours")
    - Speed unit: "rpm" (e.g., "1000rpm", "3600rpm")
    - Power unit: "kW" (e.g., "100 kW", "5kW")
    - Torque unit: "Nm" (e.g., "50Nm", "200Nm")
  - For macro specification changes, CDMethod=1 automatically set
- **`load_GearDesign_data(file_path, session_id)`**: Load JSON/GD1 file
- **`save_GearDesignData(session_id)`**: Save current data as JSON

### Calculation Execution
- **`calc_geometry(session_id)`**: Geometric calculation (required before calc_load_case)
- **`calc_load_case(session_id)`**: Load calculation (returns messages)

### Result Query
- **`get_allresults_summary(session_id)`**: Result summary → **MUST display ALL results in summary as table with same format**
  - Prerequisite: calc_geometry + calc_load_case completed
- **`get_messages(session_id)`**: Query calculation warnings/error messages

### Output Generation
- **`get_2D_image(session_id)`**: 2D mesh image (PNG)
- **`get_3d_image(session_id, width, height)`**: 3D image (PNG)
- **`get_3d_modeling(session_id)`**: 3D model (STEP)
- **`get_gear_report(session_id)`**: Design report (PDF)

### Low-Noise Design Optimization Tools
- **`calculate_facewidth_for_ep_beta(target_overlap_ratio, helix_angle_deg, normal_module, session_id)`**:
  - Calculate facewidth (b) to achieve target overlap ratio (εβ). Cannot be used when helix angle is 0!
  - Formula: b = (εβ × π × mn) / sin(β)
  - Example: εβ=1.3, β=25°, mn=2.5 → b ≈ 24.2mm
- **`calculate_helixangle_for_ep_beta(target_overlap_ratio, face_width, normal_module, session_id)`**:
  - Calculate helix angle (β) to achieve target overlap ratio (εβ). Increase facewidth if helix angle ≥ 25°
  - Formula: β = arcsin((εβ × π × mn) / b)
  - Example: εβ=1.3, b=25mm, mn=2.5 → β ≈ 23.5°

### SimpleSizing
- **`simple_sizing_gearpair(user_message, session_id)`**: Calculate various combinations
- **`get_simplesizing_results(session_id, return_all=False, top_n=100)`**: Query results
  - Return structure: Each result includes `index` (original row_index)
- **`apply_simplesizing_case(row_index, session_id)`**: Apply selected case
  - **row_index is the original DataFrame index** (`index` field value)
  - After application, MUST run calc_geometry → calc_load_case for final validation

---

## SimpleSizing Detailed Guide

### Parameter Search Range

**Parameters SimpleSizing Explores** (generates combinations within min/max range):
- **Module (m_n)**: Min ~ Max range
- **Teeth count (z_pinion)**: Min ~ Max range

**Parameters Fixed in SimpleSizing** (uses input values as-is):
- **Facewidth**: Single fixed value
- **Pressure angle (α_n)**: Single fixed value
- **Helix angle (β)**: Single fixed value

**⚠️ Important**: SimpleSizing does NOT explore by varying facewidth/pressure angle/helix angle!

**When Facewidth/Helix Angle Case Study Needed**:
```
[Case 1: Facewidth 30mm, Helix angle 15°]
→ modify_gear_data("facewidth 30mm, helix angle 15 degrees")
→ simple_sizing_gearpair() → get_simplesizing_results()
→ Select optimal case and record performance

[Case 2: Facewidth 40mm, Helix angle 20°]
→ modify_gear_data("facewidth 40mm, helix angle 20 degrees")
→ simple_sizing_gearpair() → get_simplesizing_results()
→ Select optimal case and record performance

→ Compare all cases and make final selection
```

### Performance Criteria Analysis

**Main DataFrame Columns**:
- **`rank`**: Pareto rank (lower is better, Rank 1 = Pareto front)
- **`PPTE`**: Transmission error (lower is better)
- **`total mass`**: Total mass (lower is better)
- **`efficiency`**: Efficiency (higher is better)
- Others: `module`, `z1`, `z2`, `CenterDistance`, `SF_bending`, `SF_contact`

**Analysis Principles (Absolute Rules!)**:
1. **Always use `rank` as primary sort criterion** in all analyses
2. **Among Rank 1 solutions**, apply secondary sort by requested performance metric
3. **Never recommend Rank 2+** (unless special reason)

**Sorting Method by Performance Criteria**:

| Performance Criteria | Primary Sort | Secondary Sort | Additional Considerations |
|---------------------|--------------|----------------|---------------------------|
| **Low Noise** | rank ↑ | PPTE ↑ | Overlap ratio ≈ 1 or 2 |
| **Lightweight** | rank ↑ | total mass ↑ | MUST verify safety factor |
| **High Efficiency** | rank ↑ | efficiency ↓ | - |
| **Compact** | rank ↑ | CenterDistance ↑ | - |
| **High Strength** | rank ↑ | min(SF_bending, SF_contact) ↓ | - |
| **Multiple Criteria** | Filter rank=1 | Explain trade-offs | Compare metrics within Rank 1 |

(↑: ascending, ↓: descending)

### row_index vs display_order

**Key Point**: Sorting SimpleSizing results by rank/metrics makes **display order differ from original index**!

**LLM Response Template**:
```
SimpleSizing Results (sorted by rank + PPTE):

| Display | row_index | Module | z1 | z2 | Rank | PPTE | S_H | S_F | Evaluation |
|---------|-----------|--------|----|-----|------|------|-----|-----|------------|
| 1 | 45 | 3.75 | 23 | 94 | 1 | 0.82 | 1.74 | 5.73 | ⭐ Recommended |
| 2 | 5 | 4.0 | 21 | 86 | 1 | 0.95 | 1.61 | 5.48 | - |
| 3 | 102 | 3.5 | 24 | 101 | 1 | 1.12 | 1.68 | 5.92 | - |

**Recommendation**: Display 1 case (row_index=45)
  - Module 3.75mm, z1=23, z2=94
  - Minimum PPTE (0.82), good safety factors

→ Will execute apply_simplesizing_case(row_index=45, session_id)
```

**Important Notes**:
- **Display**: Table order (1, 2, 3, ...) → For user communication
- **row_index**: Original index (`index` field) → **REQUIRED for apply_simplesizing_case()**
- **Never pass Display number to apply_simplesizing_case()!**

### Optimal Gear Design Guide ⭐

**Core Concept**:
- **Optimal gear**: Simultaneously achieving Lightweight + High Efficiency + Low Noise
- **3-stage process**: 1) Lightweight design first → 2) Low-noise design → 3) High efficiency verification
- **⚠️ Trade-off management**: Minimize impact on other performance indicators at each stage

**Overall Process Flow**:
```
[Stage 1] Lightweight Design (Safety Factor Optimization)
  → Adjust Contact/Bending safety factors to 1.0~1.3× required values
  → Micropitting is for reference only (insufficient allowed)

[Stage 2] Low-Noise Design (Overlap Ratio Optimization)
  → Achieve target overlap ratio (1.0 or 2.0)
  → Adjust helix angle/facewidth (minimize efficiency impact)

[Stage 3] High Efficiency Verification
  → Check efficiency and judge trade-offs
  → Consider readjustment if efficiency decrease > 5%
```

---

#### Stage 1: Lightweight Design (Safety Factor Optimization)

**Objective**: Optimize Contact(S_H), Bending(S_F) safety factors to **1.0~1.3× required values**

**Core Principles**:
- **⚠️ Important**: **Focus ONLY on Contact(S_H) and Bending(S_F)**, Micropitting(S_MP) is for reference only
- Micropitting below required safety factor is acceptable (often impossible to improve)
- If safety factors are **1.2× required or more**, excessive (needs improvement)

**SimpleSizing-based Process**:
```
1. Run SimpleSizing (select minimum PPTE or minimum mass case among Rank 1)
2. apply_simplesizing_case() → calc_geometry → calc_load_case
3. Check S_H(Contact), S_F(Bending) in get_allresults_summary() (S_MP for reference only)
4. Evaluate and adjust safety factors (repeat up to 5 times):
   - If S_H, S_F are 1.2× required or more → Decrease module/facewidth
   - If S_H, S_F are below required → Increase module/facewidth
   - If imbalanced → Adjust module + teeth (maintain gear ratio/center distance)
```

**Safety Factor Evaluation Criteria** (Example with required S_H=1.2, S_F=1.5):

| Actual Safety Factor | Evaluation | Action |
|---------------------|------------|--------|
| S_H=1.1, S_F=1.1 | Insufficient | Increase module or facewidth |
| S_H=1.25, S_F=1.60 | Appropriate ✅ | Stage 1 complete → Proceed to Stage 2 |
| S_H=2.0, S_F=5.0 | Excessive (Needs improvement) | Decrease module/facewidth (overweight) |
| S_H=1.2, S_F=3.5 | Imbalanced (Needs improvement) | Bending excessive → Decrease module |
| S_H=2.5, S_F=1.6 | Imbalanced (Needs improvement) | Contact excessive → Increase module |
| S_H=1.25, S_F=1.60, S_MP=0.8 | Appropriate ✅ | Micropitting insufficient but OK |

**Safety Factor Balance Adjustment**:
1. **Contact appropriate, Bending excessive** → Decrease module
2. **Bending appropriate, Contact excessive** → Increase module
3. **Both excessive** → Reduced center distance and tooth width through tooth number adjustment
4. **Micropitting insufficient** → Ignore (Focus on Contact/Bending only)

---

#### Stage 2: Low-Noise Design (PPTE Optimization)

**Objective**: PPTE(peak-to-peak transmission error) minimizate by adjust overlap ratio close to **1.0** or **2.0** (maintain lightweight/efficiency)

**Core Principles**:
- **Lightweight + low-noise**: Prioritize overlap ratio 1.0
- **Ultra-low noise**: Target overlap ratio 2.0 (sacrifices some lightweight/efficiency)
- **⚠️ Constraint**: Helix angle < 25° recommended (consider efficiency and axial load)

**Overlap Ratio Evaluation Criteria**:

| Overlap ratio | Target 1.0 Evaluation | Target 2.0 Evaluation | Action |
|--------------|----------------------|----------------------|--------|
| 0.95~1.05 | Appropriate ✅ | Inappropriate | Target 1.0: Stage 2 complete → Proceed to Stage 3 |
| 1.95~2.05 | Inappropriate | Appropriate ✅ | Target 2.0: Stage 2 complete → Proceed to Stage 3 |
| 1.20~1.80 | Inappropriate (Needs improvement) | Inappropriate (Needs improvement) | Choose 1.0 or 2.0 then adjust |

**Calculation-based Adjustment Method** (Accurate, Recommended ⭐):
```
1. Check current overlap ratio, minimum facewidth, module in get_allresults_summary()
2. Call calculate_helixangle_for_ep_beta(target_overlap, facewidth, module, session_id)
3-1. If returned helix angle < 25° → Adjust helix angle only with modify_gear_data()
3-2. If returned helix angle ≥ 25° → calculate_facewidth_for_ep_beta(target_overlap, 25, module)
     → Adjust with modify_gear_data() using helix angle 25° + calculated facewidth
4. calc_geometry() → calc_load_case() → get_allresults_summary() recheck
5. Re-verify safety factors: Check if S_H, S_F are still within appropriate range
   - If safety factor insufficient → Return to Stage 1 (readjust module)
```

**⚠️ Cautions**:
- Helix angle increase decreases efficiency (typically 1~3%)
- Facewidth increase increases mass and cost
- **Safety factor re-verification required**: Facewidth/helix angle changes may affect safety factors

---

#### Stage 3: High Efficiency Verification and Trade-off Judgment

**Objective**: Check efficiency and evaluate balance with lightweight/low-noise

**Efficiency Evaluation Criteria**:
```
1. Check Efficiency in get_allresults_summary()
2. Calculate change rate vs baseline efficiency:
   - Efficiency decrease < 2%: Acceptable ✅ (Optimal gear achieved)
   - Efficiency decrease 2~5%: Caution (explain trade-off to user)
   - Efficiency decrease > 5%: Readjustment recommended (review helix angle/facewidth)
```

**Trade-off Judgment Criteria**:

| Efficiency Decrease | Lightweight Achieved | Low-noise Achieved | Recommended Action |
|-------------------|---------------------|-------------------|-------------------|
| < 2% | ✅ | ✅ | Optimal gear achieved ✅ (Design complete) |
| 2~5% | ✅ | ✅ | User confirmation needed (explain trade-off) |
| > 5% | ✅ | ✅ | Readjustment recommended (consider changing overlap ratio to 1.0) |
| > 5% | ✅ | ❌ | Consider relaxing low-noise target |

**LLM Response Example (Efficiency decrease > 5%)**:
```
Efficiency Evaluation:
- Efficiency after Stage 1: 99.2%
- Efficiency after Stage 2: 93.5% (5.7% decrease ⚠️)
- Cause: Applied helix angle 25° + facewidth 50mm to achieve overlap ratio 2.0

Trade-off Analysis:
- Lightweight: S_H=1.25, S_F=1.60 (Appropriate ✅)
- Low-noise: Overlap ratio = 2.02 (Appropriate ✅)
- Efficiency: 93.5% (5.7% decrease ⚠️, readjustment recommended)

Readjustment Proposal:
1. Change overlap ratio target from 2.0 → 1.0
2. Recalculate helix angle/facewidth → Efficiency improvement expected
3. User confirmation: Choose between ultra-low noise (overlap 2.0) vs high efficiency (overlap 1.0)
```

---

#### Complete LLM Response Example for Optimal Gear Design

```
Request: "Lightweight + low-noise gear, gear ratio 3, overlap ratio 1.0 design"

=== Stage 1: Lightweight Design (Safety Factor Optimization) ===

SimpleSizing Results (Rank 1, minimum PPTE):
- Module 3.75, z1=23, z2=94 applied

Safety Factor Evaluation (Required: S_H=1.2, S_F=1.2):
- Actual: S_H=2.1, S_F=5.3, S_MP=0.85
- Evaluation: Contact/Bending excessive (needs improvement), Micropitting insufficient but ignore

Adjustment 1: Decrease module (3.75 → 2.5mm)
→ Result: S_H=0.9, S_F=3.0 (S_H insufficient)

Adjustment 2: Module 2.0mm + increase teeth (z1=29, z2=117)
→ Result: S_H=1.2, S_F=1.7 (Appropriate ✅)
→ Efficiency: 99.2%, Mass: 1.2kg

Stage 1 complete ✅ → Proceed to Stage 2

=== Stage 2: Low-Noise Design (Overlap Ratio Optimization) ===

Overlap Ratio Evaluation (Target: 1.0):
- Actual: 0.75 (inappropriate)
- Current: Minimum facewidth 30mm, helix angle 15°, normal module 2.0mm

Calculation-based Adjustment:
→ calculate_helixangle_for_ep_beta(1.0, 30.0, 2.0, session_id)
→ Required helix angle = 19.5° (< 25° ✅)
→ modify_gear_data("change helix angle to 19.5 degrees")
→ Recalculation result: Overlap ratio = 1.00 ✅

Safety Factor Re-verification:
- S_H=1.18, S_F=1.65 (Still appropriate ✅)
- Efficiency: 98.9% (0.3% decrease)

Stage 2 complete ✅ → Proceed to Stage 3

=== Stage 3: High Efficiency Verification and Trade-off Judgment ===

Efficiency Evaluation:
- Efficiency after Stage 1: 99.2%
- Efficiency after Stage 2: 98.9%
- Efficiency decrease: 0.3% (< 2%, acceptable ✅)

Final Result:
┌─────────────────────────────────────────┐
│ Optimal Gear Design Complete ✅          │
├─────────────────────────────────────────┤
│ Lightweight: S_H=1.18, S_F=1.65 (OK)    │
│ Low-noise: Overlap ratio = 1.00 (OK)    │
│ High Efficiency: 98.9% (0.3% drop, OK)  │
│ Mass: 1.2kg                             │
│ Module: 2.0mm, z1=29, z2=117            │
│ Facewidth: 30mm, Helix angle: 19.5°    │
└─────────────────────────────────────────┘

→ Output generation: get_2D_image, get_gear_report available
```

### When SimpleSizing Results Insufficient

When SimpleSizing results are 0 or very few, relax conditions:

1. **Expand module range**: Decrease minimum or increase maximum (e.g., 2~4 → 1.5~5)
2. **Expand teeth range**: Decrease minimum or increase maximum (e.g., z_min=15 → 12)
3. **Adjust facewidth**: Increase facewidth or change to range (e.g., 30mm → 30~50mm)
4. **Increase max calculation count**: Explore more combinations
5. **Relax safety factor criteria**: Lower minimum safety factor requirements

**LLM Response Example**:
```
SimpleSizing results: 0 cases. Current conditions (module 2~2.5, z_min=20) are too strict.
Please adjust one of the following:
1. Expand module range (e.g., 1.5~3.0)
2. Decrease minimum teeth (e.g., z_min=15)
3. Increase facewidth or specify range (e.g., 30~50mm)
```

---

## Gear Design Main Scenarios

### 1. Specific Specifications Provided (Basic Workflow)
```
Request: "Module 3, teeth 20-60, helix angle 15 degrees design"
→ initialize → modify_gear_data → calc_geometry → calc_load_case
  → get_allresults_summary (display as table) → get_gear_report
```

### 2. Rough Conditions (SimpleSizing Workflow)
```
Request: "Gear ratio 3, find module between 2~4"
→ initialize → modify_gear_data → simple_sizing_gearpair
  → get_simplesizing_results (display as table sorted by rank+metric)
  → Recommend to user (Display 1, row_index=45)
  → apply_simplesizing_case(row_index=45)
  → Apply Optimal Gear Design Guide (3 stages: Lightweight → Low-noise → Efficiency)
  → calc_geometry → calc_load_case → get_allresults_summary
```

---

## Important Notes

### Required Execution Order
- Before calc_geometry(): modify_gear_data() or load_GearDesign_data()
- Before calc_load_case(): calc_geometry() required
- Before get_gear_report(): calc_load_case() required

### Gear Ratio Settings
- Gear pair: z2/z1
- Three gear: z3/z1
- Planetary: z3/z1 (ring gear/sun gear)
- Double pinion planetary: z3/z1

### Session Management
- Session timeout: 1 hour automatic deletion
- Output directory: `outputs/{session_id}/`

### Error Handling
- All functions indicate success/failure with `success` field
- Verify changes with `change_summary`
- When path mismatch, check LLM's JSON keys

---

## Summary: 8 Most Important Points

1. **Workflow Selection**: Performance criteria/range/abstract expression → SimpleSizing, specific specifications → Basic
2. **SimpleSizing Parameters**: Only explores module/teeth, facewidth/pressure angle/helix angle are fixed
3. **Performance Analysis**: Always primary sort by rank → Select based on requested metric among Rank 1
4. **row_index**: Pass `index` field value (NOT Display number) to apply_simplesizing_case()
5. **Optimal Gear Design 3-Stage Process**:
   - **Stage 1 (Lightweight)**: Optimize safety factors to 1.0~1.3× required (Contact/Bending only, ignore Micropitting)
   - **Stage 2 (Low-noise)**: Adjust overlap ratio to 1.0 or 2.0 (calculation-based method recommended ⭐)
   - **Stage 3 (Efficiency)**: Verify efficiency decrease and judge trade-offs (< 2%: ignore, 2~5%: consider adjustment, > 5%: redesign)
6. **Safety Factor Evaluation**:
   - Contact(S_H), Bending(S_F) are optimization targets
   - **Micropitting(S_MP) for reference only** (acceptable even if insufficient)
   - 3-level result evaluation: Insufficient(NG) / Appropriate(OK, 1.0~1.3×) / Excessive(Needs improvement, > 1.3×)
7. **Low-Noise Design Tools**:
   - **Recommend calculation-based adjustment**: calculate_helixangle_for_ep_beta() → branch at 25° → calculate_facewidth_for_ep_beta()
   - Overlap ratio only visible in get_allresults_summary()
8. **Result Display and Iteration**: Always display get_allresults_summary() and get_simplesizing_results() as tables, iterate up to 5 times when insufficient/excessive
