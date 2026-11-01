"""Find the price limit for an efficiency improvement, under stated cost rules."""
import csv
import json
import math
from pathlib import Path
from cost_model import Inputs,calculate,discounted_cost,annual_investment_factor

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
case=json.loads((DATA/'starting_case.json').read_bytes())
previous=json.loads((DATA/'equipment_efficiency_study_checks.json').read_bytes())
frame=next(r for r in case['technology_inputs'] if r['technology']=='PEM')
base_cost=1500.;base_e=53.;better_e=48.
fixed_fraction=frame['annual_fixed_OPEX_fraction']
other=frame['variable_OPEX_GBP_per_kg']
alpha=(annual_investment_factor(case['discount_rate'],case['plant_life_years'])+fixed_fraction)/(8760*case['capacity_factor'])
cost_lo,cost_hi=previous['cost_range_GBP_per_kWe']

def model(k,e,p):
    return Inputs(k,e,p/1000,case['capacity_factor'],k*fixed_fraction,other,
                  case['discount_rate'],case['plant_life_years'])

rows=[]
for power_price in range(0,151,5):
    price=power_price/1000
    reference=calculate(model(base_cost,base_e,power_price))
    # Equate e*(p+K*alpha)+v for the two examples, with the same v.
    ceiling=(base_e*(price+base_cost*alpha)/better_e-price)/alpha
    exact=calculate(model(ceiling,better_e,power_price))
    assert abs(exact['total_GBP_per_kg']-reference['total_GBP_per_kg'])<1e-10
    assert abs(discounted_cost(model(ceiling,better_e,power_price))-reference['total_GBP_per_kg'])<1e-9
    assert calculate(model(ceiling-1,better_e,power_price))['total_GBP_per_kg']<reference['total_GBP_per_kg']
    assert calculate(model(ceiling+1,better_e,power_price))['total_GBP_per_kg']>reference['total_GBP_per_kg']
    rows.append({
        'electricity_price_GBP_per_MWh':power_price,
        'electricity_price_pence_per_kWh':power_price/10,
        'reference_equipment_cost_GBP_per_kWe':base_cost,
        'reference_electricity_kWh_per_kg':base_e,
        'improved_electricity_kWh_per_kg':better_e,
        'equal_cost_equipment_price_GBP_per_kWe':ceiling,
        'maximum_extra_equipment_price_GBP_per_kWe':ceiling-base_cost,
        'equal_cost_total_GBP_per_kg':exact['total_GBP_per_kg'],
        'calculated_price_limit_inside_source_cost_range':cost_lo<=ceiling<=cost_hi,
        'capacity_factor':case['capacity_factor'],'discount_rate':case['discount_rate'],
        'plant_life_years':case['plant_life_years'],
        'fixed_running_cost_fraction_of_investment':fixed_fraction,
        'other_running_cost_GBP_per_kg':other,
        'result_type':'Calculated cost limit; not a supplier price or cost forecast',
        'money_basis':'Source GBP; price year not confirmed',
    })
assert len(rows)==31
for a,b in zip(rows,rows[1:]):
    assert b['equal_cost_equipment_price_GBP_per_kWe']>a['equal_cost_equipment_price_GBP_per_kWe']

# Check that the new calculation gives the crossover found in Step 7.
old_cross=previous['example_crossover_electricity_price_GBP_per_MWh']
p=old_cross/1000
ceiling_at_old=(base_e*(p+base_cost*alpha)/better_e-p)/alpha
assert math.isclose(ceiling_at_old,2000,abs_tol=1e-9)

# Extra running-cost room for a new, explicitly hypothetical 1750 GBP/kW example.
# The allowance is calculated, not an estimate of actual repair costs.
new_cost=1750.
assert cost_lo<=new_cost<=cost_hi
example_a=calculate(model(new_cost,better_e,50))
example_b=calculate(model(base_cost,base_e,50))
room=example_b['total_GBP_per_kg']-example_a['total_GBP_per_kg']
annual_room=room*example_a['annual_hydrogen_kg_per_kWe']
assert room>0
adjusted=Inputs(new_cost,better_e,.05,.5,new_cost*fixed_fraction+annual_room,other,.08,25)
assert abs(calculate(adjusted)['total_GBP_per_kg']-example_b['total_GBP_per_kg'])<1e-10

with (DATA/'efficiency_value_limits.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(DATA/'efficiency_value_limits.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
summary={
    'question':'How much extra equipment cost can the efficiency improvement justify?',
    'rows':len(rows),'reference_example':{'equipment_GBP_per_kWe':base_cost,'electricity_kWh_per_kg':base_e},
    'improved_example_electricity_kWh_per_kg':better_e,
    'fixed_settings':{'capacity_factor':.5,'discount_rate':.08,'years':25,
                     'fixed_running_cost_fraction':fixed_fraction,'other_cost_GBP_per_kg':other},
    'source_cost_range_GBP_per_kWe':[cost_lo,cost_hi],
    'limits_outside_source_cost_range':sum(not r['calculated_price_limit_inside_source_cost_range'] for r in rows),
    'extra_running_cost_example':{
        'improved_equipment_GBP_per_kWe':new_cost,'electricity_price_GBP_per_MWh':50,
        'improved_total_GBP_per_kg':example_a['total_GBP_per_kg'],
        'reference_total_GBP_per_kg':example_b['total_GBP_per_kg'],
        'maximum_extra_running_cost_GBP_per_kg':room,
        'equivalent_extra_annual_cost_GBP_per_kWe_year':annual_room,
        'for_100_kWe_teaching_example_GBP_per_year':annual_room*100,
        'meaning':'Extra costs above included allowances, with output unchanged; not observed repair spending',
    },
    'checks':['Equal costs at all 31 calculated limits','Prices just below the limit reduce total cost',
              'Prices just above the limit raise total cost','Yearly cash-flow check at all limits',
              'Agrees with the previous 2000 GBP/kW crossover','Extra yearly cost uses up the calculated cost room'],
    'limits':['Real products may not follow these cost rules','Maintenance follows equipment price at 2.75% per year',
              'Same other per-kg cost for both examples','Source price year is open',
              'Some calculated limits lie above the source equipment-cost range; flagged, not product evidence',
              'No measured complexity, reliability or repair data','No hourly supply or ageing model'],
}
(DATA/'efficiency_value_study_checks.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
reg=json.loads((DATA/'source_register.json').read_bytes())
reg['stage']='Step 8: value of an efficiency improvement calculated'
done=reg.setdefault('completed_studies',[])
name='Efficiency improvement: equipment price limit and extra running-cost room'
if name not in done:done.append(name)
reg['next_priority']='Resolve the money basis and the remaining evidence gaps before a final GBP 1/kg claim'
(DATA/'source_register.json').write_text(json.dumps(reg,indent=2),encoding='utf-8')
for r in rows:
    if r['electricity_price_GBP_per_MWh'] in [0,10,50,90,150]:
        print(r['electricity_price_pence_per_kWh'],round(r['equal_cost_equipment_price_GBP_per_kWe'],2),round(r['maximum_extra_equipment_price_GBP_per_kWe'],2),r['calculated_price_limit_inside_source_cost_range'])
print(json.dumps(summary['extra_running_cost_example'],indent=2))
