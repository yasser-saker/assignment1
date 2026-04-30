# Domain Context — Construction Takeoff

**Last Updated:** 2026-04-29  
**Purpose:** Provide AI agents with construction domain knowledge needed to understand and process project files accurately.

---

## What is a Construction Takeoff?

A **construction takeoff** (also called a "quantity takeoff" or "material takeoff") is the process of identifying and quantifying all materials, labor, and equipment needed for a construction project by analyzing drawings, specifications, and scope documents.

**Output:** An estimate with "line items" — each line item describes one type of work with a quantity and unit of measure.

---

## Project Types in This Dataset

### Commercial Tenant Improvement (TI) / Interior Fit-Out
- Renovating or building out interior space for a commercial tenant
- Examples: retail stores, medical clinics, office spaces
- Typical trades: demo, framing, drywall, ceilings, flooring, paint, millwork, electrical, plumbing, HVAC

### Retail Store Build-Outs
- Specific brand standards and fixtures
- Examples: Gap Kids, Jack & Jones, Walmart, Gucci
- May include: custom fixtures, signage, flooring patterns, specific paint colors

### Medical/Institutional
- Higher standards for infection control, accessibility, specialized equipment
- Examples: Maryland Vision Institute (eye clinic), Portland VA Surgical Center
- May include: medical gas, specialized electrical, casework, flooring with specific requirements

---

## Common Construction Trades

| Trade | Description | Common Units |
|-------|-------------|--------------|
| **Demolition** | Removing existing walls, fixtures, flooring, ceilings | SF, LF, EA, CY |
| **Framing** | Wood or metal studs for walls and ceilings | LF, EA |
| **Drywall** | Gypsum wallboard installation | SF |
| **Taping/Mudding** | Finishing drywall joints | SF |
| **Ceilings** | Acoustic tile, gypsum, or specialty ceiling systems | SF |
| **Flooring** | Carpet, tile, vinyl, hardwood, epoxy | SF |
| **Painting** | Primer, paint, stain, specialty coatings | SF |
| **Millwork** | Custom cabinets, countertops, trim, casework | LF, SF, EA |
| **Doors/Frames/Hardware** | Door installation, frames, closers, locks | EA |
| **Electrical** | Outlets, lighting, panels, conduit, wiring | EA, LF |
| **Plumbing** | Fixtures, piping, drains, water supply | EA, LF |
| **HVAC** | Ductwork, diffusers, units, controls | SF, LF, EA |
| **Fire Protection** | Sprinklers, alarms | EA, LF |
| **Glazing** | Windows, glass partitions, mirrors | SF |
| **Signage** | Interior and exterior signs | EA |
| **Security** | Cameras, access control, alarms | EA |

---

## Common Units of Measure (UOM)

| Unit | Meaning | Typical Use |
|------|---------|-------------|
| **SF** | Square Feet | Floors, walls, ceilings, paint areas |
| **LF** | Linear Feet | Baseboard, trim, framing, conduit, piping |
| **EA** | Each | Doors, fixtures, outlets, lights, equipment |
| **CY** | Cubic Yards | Concrete, demolition debris |
| **SY** | Square Yards | Carpet, some flooring |
| **LS** | Lump Sum | Complete systems or undefined scope |
| **HR** | Hours | Labor-only items |
| **TON** | Tons | HVAC equipment |
| **PAIR** | Pair | Door hardware sets |
| **SET** | Set | Matching items |

---

## Input File Types & What They Contain

### Construction Drawings (Architectural, Mechanical, Electrical, Plumbing)
- **Format:** Multi-page PDF, often scanned from paper
- **Content:** Floor plans, elevations, sections, details
- **Key Info:** Room dimensions, wall types, door/window locations, material callouts, finish schedules
- **Extraction Challenge:** May be scanned images requiring OCR; dimensions may need visual interpretation

### Specifications ("Specs")
- **Format:** Text-based PDF, often divided by CSI MasterFormat divisions
- **Content:** Material standards, installation requirements, quality standards
- **Key Info:** Specific products, grades, methods
- **Extraction Challenge:** Very text-dense; need to correlate with drawing quantities

### Scope of Work (SOW)
- **Format:** Text-based PDF or Word
- **Content:** Narrative description of contractor's responsibilities
- **Key Info:** What is included/excluded, specific tasks, coordination requirements
- **Extraction Challenge:** Narrative format; quantities often implicit or absent

### Addendums
- **Format:** Text-based PDF
- **Content:** Changes to original drawings/specs after bid issuance
- **Key Info:** Revised quantities, deleted items, added scope
- **Extraction Challenge:** Must be merged with base documents; may override original quantities

### Contractor Rules/Regulations
- **Format:** Text-based PDF
- **Content:** Standard requirements for all projects (safety, hours, access, protection)
- **Key Info:** May affect labor costs but usually not material quantities
- **Extraction Challenge:** Usually not directly relevant to quantity takeoff

### Breakout Drawings
- **Format:** PDF
- **Content:** Detailed views of specific areas or conditions
- **Key Info:** Dimensions, material details for complex areas
- **Extraction Challenge:** May duplicate information from main drawings

---

## How Quantities Are Derived

### From Drawings (Direct Measurement)
- **Area (SF):** Length × Width from dimensions
- **Length (LF):** Direct dimension or calculated from coordinates
- **Count (EA):** Direct counting of symbols (doors, lights, outlets)
- **Volume (CY):** Area × Thickness

### From Specs/SOW (Implicit Quantities)
- Specifications describe WHAT but not HOW MUCH
- Quantities must be derived by applying spec requirements to drawing measurements
- Example: Spec says "Paint: 2 coats, eggshell finish" → Quantity = wall area from drawings

### From Addendums (Revised Quantities)
- Addendums may add or delete scope
- Must adjust base quantities accordingly

---

## Key Challenges in Automated Takeoff

1. **Scanned Drawings:** Old projects use scanned paper drawings; text and dimensions are images, not selectable text
2. **Scale Detection:** Drawings have scale (e.g., 1/8" = 1'-0"); must detect scale to convert measured pixels/inches to real dimensions
3. **Dimension Interpretation:** Dimensions are leader lines with numbers; must associate dimension with correct wall/room/element
4. **Finish Schedules:** Room finish schedules (table format) list materials per room; must correlate with room areas on floor plans
5. **Overhead/Profit:** Takeoffs usually include overhead and profit percentages; these are markup, not physical quantities
6. **Waste Factors:** Material quantities often include waste factors (e.g., 10% extra for tile); these may or may not be in the estimate

---

## Data Discipline: What AI Should vs. Should NOT See

### AI-Visible Inputs (Safe to use during extraction)
- All files in `Project Files/` directory
- File names, metadata, page counts
- Extracted text, OCR results, images

### Evaluation-Only Reference (NEVER use during extraction)
- Files in `Expected Manual Output/` directory
- Human estimates (Excel files)
- Human markups (PDF annotations)
- Any known quantities or line items from expected outputs

### Why This Matters
Using expected outputs during extraction is "cheating" and invalidates the assessment. The system must generalize from project files alone, just as a human estimator would.

---

## Relevant Standards & Formats

### CSI MasterFormat
- Industry standard for organizing construction specifications
- Divisions 01–49 cover all construction trades
- Common divisions for TI work:
  - 02: Existing Conditions (Demolition)
  - 06: Wood, Plastics, Composites (Millwork)
  - 09: Finishes (Flooring, Painting, Ceilings)
  - 10: Specialties (Signage, Toilet Accessories)
  - 21: Fire Suppression
  - 22: Plumbing
  - 23: HVAC
  - 26: Electrical
  - 28: Electronic Safety and Security

### Uniformat
- Alternative classification by building element (foundation, shell, interiors, services)
- Less common for TI takeoffs but may appear in some estimates

---

## Glossary

| Term | Definition |
|------|------------|
| **Addendum** | Formal change to bid documents after issuance but before bid due date |
| **Allowance** | Budget placeholder for undefined work or materials |
| **As-Built** | Drawings showing actual constructed conditions (may differ from design) |
| **Bid** | Contractor's price proposal for a project |
| **BOMA** | Building Owners and Managers Association (standard for measuring rentable area) |
| **Change Order** | Formal modification to contract scope/price after award |
| **CSI** | Construction Specifications Institute |
| **General Contractor (GC)** | Primary contractor overseeing all trades |
| **Lump Sum** | Fixed price for complete scope, regardless of actual quantities |
| **RFI** | Request for Information (clarification on documents) |
| **Rough Opening** | Framed opening for doors/windows, larger than actual unit |
| **Subcontractor** | Specialty contractor working under GC (e.g., electrical, plumbing) |
| **Takeoff** | Process of measuring and quantifying work from drawings |
| **Tenant Improvement (TI)** | Work to prepare space for a specific tenant |
| **Unit Price** | Price per unit of measure (e.g., $5.50/SF for flooring) |
| **Value Engineering (VE)** | Reducing cost while maintaining function |
