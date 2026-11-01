"""Change yearly plant use. Keep power price and other inputs fixed."""
import csv
import json
import math
from pathlib import Path
from cost_model import calculate,discounted_cost,from_source

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
case=json.loads((DATA/'starting_case.json').read_bytes())
rows=[]
for tech in case['technology_inputs']:
    for percent in range(5,96,5):
        x=from_source(tech,case['electricity_price_GBP_per_MWh'],percent/100,
                      case['discount_rate'],case['HHV_kWh_per_kg_source_convention'])
        got=calculate(x)
        assert abs(discounted_cost(x)-got['total_GBP_per_kg'])<1e-9
        rows.append({
            'technology':tech['technology'],'plant_use_percent':percent,
            'capacity_factor':x.capacity_factor,
            'equivalent_full_power_hours_per_year':8760*x.capacity_factor,
            'electricity_price_GBP_per_MWh':case['electricity_price_GBP_per_MWh'],
            'discount_rate':x.discount_rate,'plant_life_years':x.years,
            'source_build_year':case['source_build_year'],
            **got,
            'hydrogen_kg_year_for_100_kWe_example':got['annual_hydrogen_kg_per_kWe']*100,
            'annual_electricity_GBP_for_100_kWe_example':got['annual_electricity_kWh_per_kWe']*100*x.electricity_price_per_kwh,
            'case_type':'Plant-use-only model test; not a real operating schedule',
            'money_basis':'Source GBP; price year not confirmed',
            'scale_note':'100 kW is a teaching calculation; no real plant quote or scale claim',
        })
assert len(rows)==38
assert len({(r['technology'],r['plant_use_percent']) for r in rows})==38
base=json.loads((DATA/'baseline_costs.json').read_bytes())
for tech in ['PEM','Alkaline']:
    group=[r for r in rows if r['technology']==tech]
    original=next(r for r in base if r['technology']==tech)
    middle=next(r for r in group if r['plant_use_percent']==50)
    assert abs(middle['total_GBP_per_kg']-original['total_GBP_per_kg'])<1e-12
    for a,b in zip(group,group[1:]):
        assert b['total_GBP_per_kg']<a['total_GBP_per_kg']
        assert b['annual_hydrogen_kg_per_kWe']>a['annual_hydrogen_kg_per_kWe']
        for key in ['electricity_GBP_per_kg','other_running_cost_GBP_per_kg']:
            assert a[key]==b[key]
        assert a['annual_equipment_cost_GBP_per_kWe']==b['annual_equipment_cost_GBP_per_kWe']
    quarter=next(r for r in group if r['plant_use_percent']==25)
    for key in ['equipment_GBP_per_kg','fixed_running_cost_GBP_per_kg']:
        assert math.isclose(quarter[key],2*middle[key],abs_tol=1e-12)

with (DATA/'neso_reference_cases_checked.csv').open(encoding='utf-8-sig',newline='') as f:
    refs=list(csv.DictReader(f))
matched=0
for ref in refs:
    if float(ref['Electricity Price'])==50 and float(ref['Discount Factor'])==.08:
        local=next(r for r in rows if r['technology']==ref['Tech'] and math.isclose(r['capacity_factor'],float(ref['Capacity Factor'])))
        assert abs(local['total_GBP_per_kg']-float(ref['LCOH']))<1e-8
        matched+=1
assert matched==6
with (DATA/'plant_use_study.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(DATA/'plant_use_study.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
summary={
    'question':'How does yearly plant use change cost when all other inputs stay fixed?',
    'rows':38,'plant_use_percent_range':[5,95],'step_percentage_points':5,
    'fixed_settings':{'electricity_price_GBP_per_MWh':50,'discount_rate':.08,'plant_life_years':25,
                      'source_build_year':2025,'source_scenario':'Central'},
    'source_cases_matched':matched,
    'checks':['38 unique cases','50% use matches the starting case','Year-by-year costs match the short formula',
              'Halving use doubles equipment and fixed cost per kg','Electricity cost per kg stays fixed',
              'All six matching selected source cases agree'],
    'limits':['Source price year is open','Price is held fixed; real power offers may link price and available hours',
              'No hourly supply or demand model','No explicit ageing or start-stop costs',
              'Water and replacements use the source variable-cost allowance',
              'This test does not identify the best real operating schedule'],
}
(DATA/'plant_use_study_checks.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
register=json.loads((DATA/'source_register.json').read_bytes())
register['stage']='Step 6: yearly plant-use test completed'
done=register.setdefault('completed_studies',[])
if 'Yearly plant use only; 38 cases' not in done:done.append('Yearly plant use only; 38 cases')
register['open_studies']=['CAPEX-efficiency trade-offs','Defined money-year threshold']
(DATA/'source_register.json').write_text(json.dumps(register,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
print('Teaching values:')
for r in rows:
    if r['plant_use_percent'] in [25,50,75]:
        print(r['technology'],r['plant_use_percent'],round(r['hydrogen_kg_year_for_100_kWe_example'],2),round(r['total_GBP_per_kg'],6))
