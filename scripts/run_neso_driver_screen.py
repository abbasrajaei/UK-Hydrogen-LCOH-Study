"""One-input-at-a-time, +/-10% screening around the saved NESO case."""
import csv
from dataclasses import replace
import json
import math
from pathlib import Path
from cost_model import calculate, discounted_cost, from_source

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


def main():
    case = json.loads((DATA / 'starting_case.json').read_bytes())
    drivers = [
        ('electricity_price_per_kwh', 'Electricity price', .9),
        ('capacity_factor', 'Yearly plant use', 1.1),
        ('investment_per_kw_e', 'Equipment cost', .9),
        ('electricity_kwh_per_kg', 'Electricity needed per kg', .9),
        ('discount_rate', 'Finance rate', .9),
        ('fixed_cost_per_kw_e_year', 'Fixed running cost', .9),
        ('variable_cost_per_kg', 'Water and replacement allowance', .9),
    ]
    results = []
    for source in case['technology_inputs']:
        base = from_source(source, case['electricity_price_GBP_per_MWh'],
                           case['capacity_factor'], case['discount_rate'],
                           case['HHV_kWh_per_kg_source_convention'])
        baseline = calculate(base)['total_GBP_per_kg']
        for field, label, favourable in drivers:
            for multiplier in (.9, 1.1):
                altered = replace(base, **{field: getattr(base, field) * multiplier})
                total = calculate(altered)['total_GBP_per_kg']
                assert math.isclose(total, discounted_cost(altered), abs_tol=1e-9)
                assert (total < baseline) == (multiplier == favourable)
                results.append(dict(technology=source['technology'], driver=label,
                                    input_field=field, baseline_input=getattr(base, field),
                                    scenario_input=getattr(altered, field),
                                    input_change_percent=round((multiplier - 1) * 100),
                                    favourable_change=multiplier == favourable,
                                    baseline_GBP_per_kg=baseline, scenario_GBP_per_kg=total,
                                    saving_GBP_per_kg=baseline-total,
                                    saving_percent=(baseline-total)/baseline*100,
                                    money_basis='NESO source GBP; price year unconfirmed',
                                    case_type='Our hypothetical one-input change; not an observed plant'))
    assert len(results) == 28
    with (DATA / 'neso_driver_screen.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    checks = dict(cases=28, source='Saved NESO starting_case.json; 2025 Central PEM and alkaline',
                  baseline=dict(power_price_GBP_per_MWh=50, capacity_factor=.5,
                                finance_rate=.08, plant_life_years=25),
                  perturbation='Each input separately increased and decreased by 10% relative to its baseline',
                  checks=['All 28 results match independent discounted yearly flows',
                          'All cost changes follow the expected direction'],
                  coupling_rules=[
                      'Equipment-only perturbation holds annual fixed OPEX constant to isolate its direct effect',
                      'Electricity-use perturbation holds investment and fixed cost per electrical input kW constant',
                      'Water and stack replacement allowance per kg stays fixed in all other perturbations',
                      'Joint CAPEX/fixed-OPEX and efficiency/CAPEX changes require separate interaction studies'],
                  limits=['Equal relative changes do not represent equal engineering difficulty or uncertainty',
                          'Ranking is local to this baseline; it can change elsewhere',
                          'Power price and available operating hours may be linked in a real supply',
                          'Source money year is unconfirmed; no dated GBP1/kg or current-price claim',
                          'No new evidence for hourly operation, plant ageing or scale effects'])
    (DATA / 'neso_driver_screen_checks.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
    preferred = sorted([r for r in results if r['technology'] == 'PEM' and r['favourable_change']],
                       key=lambda r: -r['saving_GBP_per_kg'])
    print(json.dumps(preferred, indent=2))


if __name__ == '__main__':
    main()
