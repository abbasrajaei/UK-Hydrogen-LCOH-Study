"""Change only electricity price. Keep every other starting-case input fixed."""
import csv
import json
import math
from pathlib import Path
from cost_model import calculate,from_source

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
case=json.loads((DATA/'starting_case.json').read_bytes())
rows=[]
for technology in case['technology_inputs']:
    for price in range(0,151,5):
        x=from_source(technology,price,case['capacity_factor'],case['discount_rate'],
                      case['HHV_kWh_per_kg_source_convention'])
        result=calculate(x)
        rows.append({
            'technology':technology['technology'],
            'electricity_price_GBP_per_MWh':price,
            'electricity_price_GBP_per_kWh':price/1000,
            'source_build_year':2025,'capacity_factor':x.capacity_factor,
            'discount_rate':x.discount_rate,'plant_life_years':x.years,
            'electricity_use_kWh_per_kg':x.electricity_kwh_per_kg,
            **{k:result[k] for k in ['equipment_GBP_per_kg','electricity_GBP_per_kg',
               'fixed_running_cost_GBP_per_kg','other_running_cost_GBP_per_kg','total_GBP_per_kg']},
            'case_type':'One-price-at-a-time model test; not a real supply offer',
            'money_basis':'Source GBP; price year not confirmed',
        })

assert len(rows)==62
assert len({(r['technology'],r['electricity_price_GBP_per_MWh']) for r in rows})==62
baseline=json.loads((DATA/'baseline_costs.json').read_bytes())
for tech in ['PEM','Alkaline']:
    group=[r for r in rows if r['technology']==tech]
    zero=group[0]
    assert zero['electricity_GBP_per_kg']==0
    assert zero['total_GBP_per_kg']>1
    for a,b in zip(group,group[1:]):
        expected_increase=a['electricity_use_kWh_per_kg']*.005
        assert math.isclose(b['total_GBP_per_kg']-a['total_GBP_per_kg'],expected_increase,abs_tol=1e-12)
        for name in ['equipment_GBP_per_kg','fixed_running_cost_GBP_per_kg','other_running_cost_GBP_per_kg']:
            assert a[name]==b[name]
    got=next(r for r in group if r['electricity_price_GBP_per_MWh']==50)
    old=next(r for r in baseline if r['technology']==tech)
    assert math.isclose(got['total_GBP_per_kg'],old['total_GBP_per_kg'],abs_tol=1e-12)

with (DATA/'electricity_price_study.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(DATA/'electricity_price_study.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
summary={
    'question':'How does electricity price change cost if all other inputs stay fixed?',
    'rows':62,'price_range_GBP_per_MWh':[0,150],'price_step_GBP_per_MWh':5,
    'fixed_inputs':{'source_build_year':2025,'source_scenario':'Central','capacity_factor':.5,
                    'discount_rate':.08,'plant_life_years':25},
    'zero_price_cost_GBP_per_kg':{r['technology']:r['total_GBP_per_kg'] for r in rows if r['electricity_price_GBP_per_MWh']==0},
    'checks':['62 unique cases','50 GBP/MWh reproduces starting case','Price steps match energy-use calculation','Other cost parts do not change'],
    'limits':['Source price year is not confirmed','Price and plant use may be linked in real supply options',
              'No claim of a real zero-price offer','This does not test lower equipment cost or other plant-use levels',
              'Independent full-cost validation remains open'],
}
(DATA/'electricity_price_study_checks.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
register=json.loads((DATA/'source_register.json').read_bytes())
register['stage']='Step 5: first electricity-price test completed'
register['independent_reference_review_complete']=True
register['independent_reference_check_complete']=False
register['independent_reference_check_status']='Separate sources reviewed; exact full-cost validation remains open'
register['completed_studies']=['Starting-case cost breakdown','Electricity price only; 62 cases']
register['open_studies']=['Yearly plant use','CAPEX-efficiency trade-offs','Defined money-year threshold']
register['external_review_file']='external_reference_review.json'
(DATA/'source_register.json').write_text(json.dumps(register,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
