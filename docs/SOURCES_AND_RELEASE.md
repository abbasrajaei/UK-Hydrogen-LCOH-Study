# Sources, snapshot and release notes

## Main source

The release uses the saved NESO input snapshot and 54 selected source output cases. The original downloads and hashes are in `data/raw/download_manifest.json`. The input table has 36 rows. It covers two technologies, three cost scenarios and six build years.

These are costs on the **NESO source-money scale**.

The project converts the source's hydrogen-output cost units to electrical-input units for source reproduction. Small disagreements with the separately reported electrical-input CAPEX column are retained and explained.

## Other source work

The separate UK government comparison uses the supplied 2021 annex's central free-electricity cases. The original public source URLs and SHA256 values are in `data/raw/uk_source_downloads.json`. Its extracted input/output tables and numerical check are included. The public report and annex can be reacquired with `scripts/fetch_uk_reference.py`.

## What was added in the final stage

1. A seven-input local sensitivity screen.
2. A joint electricity-price and yearly-use grid for PEM and alkaline.
3. A 54-case equipment-saving calculation to offset an efficiency loss.
4. A 125-case three-factor Excel table and a native Design-Expert 13 model.
5. Three figures exported from Design-Expert and 200 native-fit holdout checks.
6. One consistent report, a reproduction command, source credits and a focused release archive.

All scenario outputs are calculated from the documented inputs and assumptions.

## Completion boundary

The scenario study and its portfolio package are complete. Site-specific supply, real equipment quotations, hourly operation and delivered-hydrogen engineering remain possible future projects. They are not missing tasks concealed inside the present scope.

All seven report charts are native Excel or Design-Expert charts.

## Code, data and licensing

NESO data retain their original licence. Supported by National Energy SO Open Data. Other source terms are not replaced by this project. No licence for the original code has yet been selected.

Public repository: [uk-hydrogen-lcoh-study](https://github.com/abbasrajaei/uk-hydrogen-lcoh-study).
