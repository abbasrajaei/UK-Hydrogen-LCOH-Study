# Reproduce the Design-Expert charts

## What is supplied

- `NESO_three_factor_surface.xlsx`: the 125 calculated cases and their assumptions.
- `NESO_three_factor_cost_model.dxpx`: the native Design-Expert 13 project.
- `three_factor_data.tsv`: the same full-precision model results in plain text.
- The report figures are in `../figures/`, with names beginning `dx_`.

The native project was created and analysed in Design-Expert 13.0.5.0. Its factor units and explanatory note were set in the saved XML, then the project was closed and reopened in Design-Expert. Numeric records and fitted coefficients were preserved. The PNG figures were exported from the reopened application. They were not redrawn to resemble Design-Expert output.

## Inputs

| Code | Factor | Unit | Range |
|---|---|---|---|
| A | Installed CAPEX | GBP/kW electrical input | 670 to 2,008.485247 |
| B | Electricity consumption | kWh/kg hydrogen | 47.476506 to 53.478509 |
| C | Electricity price | GBP/MWh | 0 to 150 |
| Response | LCOH | GBP/kg hydrogen | Calculated from the cost model |

Each factor has five equally spaced levels. All combinations are used. This is a full grid of deterministic model cases. It is not a randomized laboratory experiment. The source ranges include future NESO assumptions. Crossed designs are hypothetical.

Fixed settings: yearly use 50%, finance rate 8%, plant life 25 years. Fixed OPEX equals 2.75% of installed CAPEX per year. The common water/replacement allowance is GBP 0.12261507874015748/kg. All money remains on the undated NESO source scale.

## Import the Excel data

1. Open the workbook in Excel. Select `Surface data!A1:D126` and copy.
2. In Design-Expert 13, choose **Import Data Set**. Choose **Paste from Clipboard**.
3. Select only the first row. Use **Use Row as Names** from its right-click menu.
4. Set the first three columns to **Numeric Factor**. Set LCOH to **Response**.
5. Choose **Finish**. Confirm 125 runs and the factor ranges above.
6. Enter the units. Commit each property edit with Enter and verify that it is saved.

The supplied project imported Excel's displayed values at six decimal places. Its data differ from the full-precision calculation by less than 0.000001 in each numeric field. The original full-precision CSV and TSV remain available.

## Fit the known model

Select LCOH, choose **No Transform** and start the analysis. Choose a two-factor interaction model. Retain these six terms:

    Intercept, A, B, C, AB, BC

Put AC in the error pool. Do not add squared or cubic terms to make the output look more complex. The retained terms follow the known equation:

    LCOH = e*p/1000 + e*K*(CRF+0.0275)/(8760*u) + v

Here K is CAPEX, e is electricity consumption, p is GBP/MWh, u is yearly-use fraction, and v is the common allowance per kg. CRF is the annual finance recovery factor.

Do not interpret tiny p-values or nearly perfect R-squared as evidence of real equipment certainty. The response is computed, not measured. Independent holdout points test representation of this equation only.

## Saved chart settings

| Figure | Type | Axes or lines | Fixed factor |
|---|---|---|---|
| `dx_contour_capex_energy_white.png` | Contour | A and B | C = 50 GBP/MWh |
| `dx_surface_capex_energy.png` | 3D surface | A and B | C = 50 GBP/MWh |
| `dx_interaction_energy_price.png` | Interaction | B with C at 0 and 150 GBP/MWh | A = 2,000 GBP/kWe |

Use **Model Graphs** to select each type. The Factors Tool sets the displayed factors and the fixed factor value. Press Enter after entering a fixed value.

Show units. Use an opaque export background so labels stay readable in dark viewers. Export each graph to a PNG file using its graph menu. The global colour and response-axis ranges cover all 125 cases. A single price slice therefore uses only part of the range.

The project may open on the design table. Select the analysed LCOH response, then **Model Graphs**. Switch graph type and factor settings using the table above.

## Check the native fit

Run:

    python scripts/validate_design_expert.py

The script reads the native project. It verifies all 125 imported cases and all factor units. It then compares the saved Design-Expert equation with 200 separate full-precision cost-model points. The saved maximum error is about GBP 0.000000101/kg. See `data/design_expert_validation.json`.

The native file uses Design-Expert's internal `Randomized` study subtype. This software label does not make these calculated cases randomized experiments.

Stat-Ease references: [Design-Expert 13 data import](https://shop.statease.com/blog/cutting-edge-tools-design-expert-version-13/), [graph export](https://shop.statease.com/docs/v22.0/hints-and-faqs/putting-data-in/) and [graph export background settings](https://www.statease.com/docs/se360/getting-started/all-graphs/). Menu details may differ in later versions.
