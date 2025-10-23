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

### Lightweight Design Guide ⭐

**Core Concept**:
- **Lightweight essence**: Minimize weight while satisfying required safety factor → Actual safety factor should be **1.0~1.3× required value**
- **⚠️ Excessive condition**: If safety factor is **1.2× required or more**, needs improvement (overweight)
- **⚠️ Important**: **Focus ONLY on Contact(S_H) and Bending(S_F) safety factors**, Micropitting(S_MP) is for reference only
  - Micropitting below required safety factor is acceptable (often impossible to improve)
  - Contact/Bending optimization is the key to lightweighting

**[Process A] SimpleSizing once + Fine-tuning** (Common, fast):
```
1. Run SimpleSizing (select minimum mass case among Rank 1)
2. apply_simplesizing_case() → calc_geometry → calc_load_case
3. Check S_H(Contact), S_F(Bending) in get_allresults_summary() (S_MP for reference only)
4. If S_H, S_F are 1.2× target safety factor or more:
   → Adjust module/facewidth/teeth (maintain gear ratio) with modify_gear_data() → Recalculate → Repeat up to 5 times
```

**Safety Factor Evaluation Criteria** (Example with required S_H=1.2, S_F=1.5):

| Actual Safety Factor | Evaluation | Action |
|---------------------|------------|--------|
| S_H=1.1, S_F=1.1 | Insufficient | Need to increase module or facewidth |
| S_H=1.25, S_F=1.60 | Appropriate ✅ | Lightweight optimization achieved |
| S_H=2.0, S_F=5.0 | Excessive (Needs improvement) | Need to decrease module/facewidth (overweight) |
| S_H=1.2, S_F=3.5 | Imbalanced (Needs improvement) | Bending excessive → Decrease module |
| S_H=2.5, S_F=1.6 | Imbalanced (Needs improvement) | Contact excessive → Increase module |
| S_H=1.25, S_F=1.60, S_MP=0.8 | Appropriate ✅ | Micropitting insufficient but OK (reference only) |

**Safety Factor Balance Adjustment**:
1. **Contact appropriate, only Bending excessive** → Decrease module
2. **Bending appropriate, only Contact excessive** → Increase module
3. **Both excessive** → Decrease both module and facewidth
4. **Micropitting insufficient** → Ignore (Focus on Contact/Bending only)

**LLM Response Example**:
```
Safety Factor Evaluation (Required: S_H=1.2, S_F=1.2, S_MP=1.0):
- Actual: S_H=2.1 (excessive, 1.75× required), S_F=5.3 (excessive, 4.4× required), S_MP=0.85 (insufficient)
- Evaluation: Contact/Bending safety factors excessive → Overweight design (needs improvement)
- Micropitting: Below required but ignore (cannot improve, reference only)
- Action: Bending more excessive, prioritize module decrease (4.0 → 3.5mm)

After improvement:
- Actual: S_H=1.7, S_F=3.8, S_MP=0.75 (still excessive, Micropitting further decreased)
- Evaluation: Contact/Bending still excessive, ignore Micropitting
- Additional action: Further decrease module (3.5 → 3.0mm)

Final:
- Actual: S_H=1.3, S_F=1.6, S_MP=0.65
- Evaluation: Contact/Bending appropriate ✅, Micropitting insufficient but acceptable
```

### Low-Noise Design Guide ⭐

**Core Concept**:
- **Low-noise essence**: Minimize PPTE (transmission error) + Optimize overlap ratio
- **Overlap ratio target**: **1.0** or **2.0** (closer to integer is better)
  - Ultra-low noise: 2.0 superior to 1.0 (sacrifices lightweight/efficiency)
  - Lightweight + low noise: Prioritize 1.0
- **⚠️ Constraint**: Helix angle < 25° recommended
- **⚠️ SimpleSizing limitation**: Overlap ratio not in SimpleSizing results → Only visible in `get_allresults_summary()`

**Overlap Ratio Evaluation Criteria**:

| Overlap ratio | Target 1.0 Evaluation | Target 2.0 Evaluation | Action |
|--------------|----------------------|----------------------|--------|
| 0.95~1.05 | Appropriate ✅ | Inappropriate | Target 1.0: Satisfied |
| 1.95~2.05 | Inappropriate | Appropriate ✅ | Target 2.0: Satisfied |
| 1.20~1.80 | Inappropriate (Needs improvement) | Inappropriate (Needs improvement) | Need to adjust closer to 1.0 or 2.0 |
| 1.35 | Inappropriate (Needs improvement) | Inappropriate (Needs improvement) | Middle value: Choose 1.0 or 2.0 then adjust |

**Adjustment Method**

**Calculation-based Facewidth/Helix Angle Adjustment** (Accurate, Recommended ⭐)
```
1. Check current overlap ratio, minimum facewidth, module in get_allresults_summary()
2. Call calculate_helixangle_for_ep_beta(target_overlap, facewidth, module, session_id)
3-1. If returned helix angle < 25° -> Apply with modify_gear_data()
3-2. If returned helix angle ≥ 25° -> Call calculate_facewidth_for_ep_beta(target_overlap, 25, module, session_id) -> Apply returned facewidth and 25° helix angle with modify_gear_data()
4. calc_geometry() → calc_load_case() → get_allresults_summary() recheck
```

**⚠️ Cautions**:
- Helix angle < 25° recommended (consider efficiency and axial load)
- Excessive facewidth increases mass and cost
- Verify calculated values are applicable with constraints

**LLM Response Example (Case 1: Helix angle < 25°, adjust helix angle only)**:
```
Overlap Ratio Evaluation (Target: 1.0):
- Actual: 0.75 (inappropriate, 0.25 short of target 1.0)
- Current: Minimum facewidth 30mm, helix angle 15°, normal module 2.5mm

Step 1: Calculate required helix angle with current facewidth
→ calculate_helixangle_for_ep_beta(1.0, 30.0, 2.5, session_id)
→ Result: Required helix angle = 19.8° (< 25° ✅)

Step 2: Apply by adjusting helix angle only
→ modify_gear_data("change helix angle to 19.8 degrees")
→ calc_geometry() → calc_load_case() → get_allresults_summary()
→ Final: overlap ratio = 1.00 ✅ (Target achieved in 1 adjustment!)

⚠️ Slight efficiency decrease expected due to helix angle increase (99.2% → 98.9%)
```

**LLM Response Example (Case 2: Helix angle ≥ 25°, fix helix angle at 25° + increase facewidth)**:
```
Overlap Ratio Evaluation (Target: 2.0):
- Actual: 1.35 (inappropriate, 0.65 short of target 2.0)
- Current: Minimum facewidth 30mm, helix angle 20°, normal module 2.5mm

Step 1: Calculate required helix angle with current facewidth
→ calculate_helixangle_for_ep_beta(2.0, 30.0, 2.5, session_id)
→ Result: Required helix angle = 31.2° (≥ 25° ⚠️)

Step 2: Fix helix angle at 25° and recalculate required facewidth
→ calculate_facewidth_for_ep_beta(2.0, 25.0, 2.5, session_id)
→ Result: Required facewidth = 37.2mm

Step 3: Apply helix angle 25° + facewidth 37.2mm
→ modify_gear_data("change helix angle to 25 degrees, facewidth to 37.2mm")
→ calc_geometry() → calc_load_case() → get_allresults_summary()
→ Final: overlap ratio = 2.00 ✅ (Target achieved in 1 adjustment!)

⚠️ Mass increase due to facewidth increase (1.2kg → 1.4kg), slight efficiency decrease (99.1% → 98.8%)
```

**[Process A] SimpleSizing once + Manual fine-tuning** (Fast, trial-and-error):
```
1. Run SimpleSizing (select minimum PPTE case among Rank 1)
2. apply_simplesizing_case() → calc_geometry → calc_load_case
3. Check overlap ratio in get_allresults_summary()
4. If overlap ratio differs significantly from target (1.0 or 2.0):
   → Manually adjust facewidth/helix angle with modify_gear_data() → Recalculate → Repeat up to 5 times
   (e.g., gradually increase facewidth 30→40→50mm)
```

**[Process A2] SimpleSizing once + Calculation-based adjustment** (Fast, accurate, ⭐ Recommended):
```
1. Run SimpleSizing (select minimum PPTE case among Rank 1)
2. apply_simplesizing_case() → calc_geometry → calc_load_case
3. Check overlap ratio, minimum facewidth, module in get_allresults_summary()
4. If overlap ratio differs significantly from target (1.0 or 2.0):
   → Call calculate_helixangle_for_ep_beta(target, facewidth, module)
   → If returned helix angle < 25°: Adjust helix angle only
   → If returned helix angle ≥ 25°: Call calculate_facewidth_for_ep_beta(target, 25, module) then adjust facewidth+helix angle
   → calc_geometry → calc_load_case → get_allresults_summary() recheck
   (Target achieved in 1 adjustment)
```

**[Process B] Facewidth/Helix Angle Case Study** (Optimal, time-consuming):
```
1. Calculate facewidth/helix angle combinations for target overlap ratio:
   - Case 1: Fix helix angle 15° → calculate_facewidth_for_ep_beta(target, 15°, estimated_module)
   - Case 2: Fix helix angle 20° → calculate_facewidth_for_ep_beta(target, 20°, estimated_module)
   - Case 3: Fix facewidth 30mm → calculate_helixangle_for_ep_beta(target, 30mm, estimated_module)
   (estimated_module: mid-value of search range or user-specified value)

2. Run SimpleSizing for each case:
   → modify_gear_data("facewidth X, helix angle Y")
   → simple_sizing_gearpair() → get_simplesizing_results()
   → Select minimum PPTE case among Rank 1 and record performance

3. Compare all cases (PPTE, overlap ratio, mass, efficiency, safety factor)

4. Select case matching user requirements:
   → apply_simplesizing_case() → calc_geometry → calc_load_case
   → get_allresults_summary() for final verification
```

**LLM Response Example (Process A: Manual adjustment)**:
```
SimpleSizing Results (Rank 1, minimum PPTE):
- Module 3.75, z1=23, z2=94 applied
- After calc: overlap ratio = 1.35 confirmed

Ultra-low noise target (overlap ratio → 2.0):
→ Adjust facewidth 30→50mm
→ Recalculate: overlap ratio = 2.3
→ Adjust facewidth 50→45mm
→ Recalculate: overlap ratio = 1.96 ✅ (3 trial-and-error attempts)
⚠️ Mass 1.2→1.5kg, efficiency 99.1→98.9% decrease
```

**LLM Response Example (Process A2-Case1: Helix angle < 25°, ⭐ Recommended)**:
```
SimpleSizing Results (Rank 1, minimum PPTE):
- Module 3.75, z1=23, z2=94 applied
- After calc: overlap ratio = 0.85, minimum facewidth 30mm, helix angle 15°, normal module 2.5mm

Low-noise target (overlap ratio → 1.0):

Step 1: Calculate required helix angle with current facewidth
→ calculate_helixangle_for_ep_beta(1.0, 30.0, 2.5, session_id)
→ Result: Required helix angle = 19.8° (< 25° ✅)

Step 2: Apply by adjusting helix angle only
→ modify_gear_data("change helix angle to 19.8 degrees")
→ calc_geometry → calc_load_case → get_allresults_summary()
→ Final: overlap ratio = 1.00 ✅ (Target achieved in 1 adjustment!)

⚠️ Slight efficiency decrease due to helix angle increase (99.2% → 99.0%)
```

**LLM Response Example (Process A2-Case2: Helix angle ≥ 25°, ⭐ Recommended)**:
```
SimpleSizing Results (Rank 1, minimum PPTE):
- Module 3.75, z1=23, z2=94 applied
- After calc: overlap ratio = 1.35, minimum facewidth 30mm, helix angle 20°, normal module 2.5mm

Ultra-low noise target (overlap ratio → 2.0):

Step 1: Calculate required helix angle with current facewidth
→ calculate_helixangle_for_ep_beta(2.0, 30.0, 2.5, session_id)
→ Result: Required helix angle = 31.2° (≥ 25° ⚠️)

Step 2: Fix helix angle at 25° and recalculate required facewidth
→ calculate_facewidth_for_ep_beta(2.0, 25.0, 2.5, session_id)
→ Result: Required facewidth = 37.2mm

Step 3: Apply helix angle 25° + facewidth 37.2mm
→ modify_gear_data("change helix angle to 25 degrees, facewidth to 37.2mm")
→ calc_geometry → calc_load_case → get_allresults_summary()
→ Final: overlap ratio = 2.00 ✅ (Target achieved in 1 adjustment!)

⚠️ Mass increase due to facewidth increase (1.2kg → 1.4kg), slight efficiency decrease (99.1% → 98.8%)
```

**LLM Response Example (Process B: Facewidth/Helix Angle Case Study)**:
```
Target overlap ratio = 2.0, estimated module = 3.0mm (mid-value of search range)

Facewidth/helix angle combination calculations:
→ Case 1 (fix β=15°): calculate_facewidth_for_ep_beta(2.0, 15, 3.0) = 72.7mm
→ Case 2 (fix β=20°): calculate_facewidth_for_ep_beta(2.0, 20, 3.0) = 55.2mm
→ Case 3 (fix b=40mm): calculate_helixangle_for_ep_beta(2.0, 40, 3.0) = 28.1°

SimpleSizing execution results:

| Case | Facewidth | Helix | Module | z1 | z2 | PPTE | Overlap | Mass | Efficiency | Evaluation |
|------|-----------|-------|--------|----|-----|------|---------|------|------------|------------|
| 1 | 72.7mm | 15° | 3.25 | 22 | 90 | 0.89 | 2.01 | 1.85kg | 99.2% | Heavy |
| 2 | 55.2mm | 20° | 3.50 | 23 | 94 | 0.82 | 1.98 | 1.52kg | 98.9% | ⭐Balanced |
| 3 | 40.0mm | 28.1° | 3.75 | 21 | 86 | 0.78 | 2.05 | 1.38kg | 98.3% | Light, efficiency poor |

Recommendation: Case 2 (overlap≈2.0 achieved, excellent PPTE, appropriate mass/efficiency trade-off)
→ Execute apply_simplesizing_case(row_index=45)
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
  → Apply Lightweight Design Guide or Low-Noise Design Guide
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
5. **3-Level Result Evaluation**: Insufficient(NG) / Appropriate(OK) / **Excessive(Needs improvement)**
   - **Lightweight**: Safety factor 1.2× required or more is excessive (overweight)
   - **Safety Factor Focus**: Optimize ONLY Contact(S_H), Bending(S_F), **Micropitting(S_MP) for reference only** (acceptable even if insufficient)
   - **Low-noise**: Overlap ratio beyond target value (1.0 or 2.0) ±0.05 is inappropriate
6. **Low-Noise Design**:
   - Process A (manual adjustment, trial-and-error) vs A2 (calculation-based, accurate ⭐) vs B (Case Study, optimal)
   - Overlap ratio only visible in get_allresults_summary()
   - **Recommend calculation-based adjustment**: Use calculate_facewidth_for_ep_beta() or calculate_helixangle_for_ep_beta()
7. **Result Display**: Always display get_allresults_summary() and get_simplesizing_results() as tables (include row_index)
8. **Iterative Improvement**: Re-run improvement workflow when insufficient/excessive (up to 5 iterations)
