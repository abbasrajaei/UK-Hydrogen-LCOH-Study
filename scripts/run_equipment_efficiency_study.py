"""Test equipment cost and electricity use inside the source's numeric ranges.

The new combinations are examples. They are not products or source forecasts.
"""
import csv
import json
import math
from pathlib import Path
from cost_model import Inputs,calculate,discounted_cost,annual_investment_factor

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
case=json.loads((DATA/'starting_case.json').read_bytes())
with (DATA/'neso_inputs_checked.csv').open(encoding='utf-8-sig',newline='') as f:
    source=list(csv.DictReader(f))
cost_range=[min(float(r['installed_CAPEX_derived_GBP_per_kWe']) for r in source),
            max(float(r['installed_CAPEX_derived_GBP_per_kWe']) for r in source)]
energy_range=[min(float(r['electricity_consumption_kWh_per_kg']) for r in source),
              max(float(r['electricity_consumption_kWh_per_kg']) for r in source)]
pem=next(r for r in case['technology_inputs'] if r['technology']=='PEM')
fixed_fraction=pem['annual_fixed_OPEX_fraction']
variable=pem['variable_OPEX_GBP_per_kg']
def model(k,e,p):
    return Inputs(k,e,p/1000,case['capacity_factor'],k*fixed_fraction,variable,
                  case['discount_rate'],case['plant_life_years'])
def row(k,e,p,name):
    got=calculate(model(k,e,p))
    return {
        'example':name,'installed_equipment_cost_GBP_per_kWe':k,
        'electricity_use_kWh_per_kg':e,
        'efficiency_HHV_fraction':case['HHV_kWh_per_kg_source_convention']/e,
        'electricity_price_GBP_per_MWh':p,
        'capacity_factor':case['capacity_factor'],'discount_rate':case['discount_rate'],
        'plant_life_years':case['plant_life_years'],
        'fixed_running_cost_fraction_of_investment':fixed_fraction,
        'other_running_cost_GBP_per_kg_assumed':variable,
        **{key:got[key] for key in ['equipment_GBP_per_kg','electricity_GBP_per_kg',
              'fixed_running_cost_GBP_per_kg','other_running_cost_GBP_per_kg','total_GBP_per_kg']},
        'case_type':'Hypothetical combination inside source numeric ranges; not a real product',
        'range_source':'All NESO technology, cost-case and build-year assumptions, 2025-2050',
        'money_basis':'Source GBP; price year not confirmed',
    }

def write(name,rows):
    with (DATA/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

# 61 points per axis. The count sets drawing detail; it is not source sampling.
costs=[cost_range[0]+i*(cost_range[1]-cost_range[0])/60 for i in range(61)]
energies=[energy_range[0]+i*(energy_range[1]-energy_range[0])/60 for i in range(61)]
grid=[row(k,e,p,'Range test') for p in [10,50,150] for e in energies for k in costs]
assert len(grid)==11163
assert len({(r['installed_equipment_cost_GBP_per_kWe'],r['electricity_use_kWh_per_kg'],r['electricity_price_GBP_per_MWh']) for r in grid})==11163
write('equipment_efficiency_grid.csv',grid)

examples=[('A: higher cost, less electricity',2000.,48.),
          ('B: lower cost, more electricity',1500.,53.)]
pair=[]
for name,k,e in examples:
    assert cost_range[0]<=k<=cost_range[1] and energy_range[0]<=e<=energy_range[1]
    for price in range(0,151,5):
        r=row(k,e,price,name)
        assert abs(discounted_cost(model(k,e,price))-r['total_GBP_per_kg'])<1e-9
        pair.append(r)
write('equipment_examples_by_power_price.csv',pair)
(DATA/'equipment_examples_by_power_price.json').write_text(json.dumps(pair,indent=2),encoding='utf-8')

alpha=(annual_investment_factor(case['discount_rate'],case['plant_life_years'])+fixed_fraction)/(8760*case['capacity_factor'])
# The common per-kg allowance cancels in this two-example comparison.
break_price=1000*alpha*(2000*48-1500*53)/(53-48)
at_break=[calculate(model(k,e,break_price))['total_GBP_per_kg'] for _,k,e in examples]
assert math.isclose(at_break[0],at_break[1],abs_tol=1e-12)
assert calculate(model(1500,53,50))['total_GBP_per_kg']<calculate(model(2000,48,50))['total_GBP_per_kg']
assert calculate(model(1500,53,150))['total_GBP_per_kg']>calculate(model(2000,48,150))['total_GBP_per_kg']
# Efficiency improvements must lower cost when equipment and other rules stay fixed.
for k in [cost_range[0],1500,cost_range[1]]:
    for price in [10,50,150]:
        assert calculate(model(k,energy_range[0],price))['total_GBP_per_kg']<calculate(model(k,energy_range[1],price))['total_GBP_per_kg']
        expected_delta=(energy_range[1]-energy_range[0])*(price/1000+k*alpha)
        actual_delta=calculate(model(k,energy_range[1],price))['total_GBP_per_kg']-calculate(model(k,energy_range[0],price))['total_GBP_per_kg']
        assert math.isclose(expected_delta,actual_delta,abs_tol=1e-12)

# At fixed efficiency and price, more expensive equipment must increase cost.
for e in [energy_range[0],53,energy_range[1]]:
    for price in [10,50,150]:
        assert calculate(model(cost_range[0],e,price))['total_GBP_per_kg']<calculate(model(cost_range[1],e,price))['total_GBP_per_kg']

summary={
    'grid_rows':len(grid),'paired_example_rows':len(pair),
    'cost_range_GBP_per_kWe':cost_range,'electricity_range_kWh_per_kg':energy_range,
    'range_rule':'Use the minimum and maximum across source scenarios from 2025 to 2050; not a current market range',
    'grid_sampling_rule':'61 equally spaced model points per axis; assumed sampling, not recovered observations',
    'grid_power_prices_GBP_per_MWh':[10,50,150],
    'fixed_settings':{'capacity_factor':.5,'discount_rate':.08,'plant_life_years':25,
                     'fixed_running_cost_fraction':fixed_fraction,'other_running_cost_GBP_per_kg':variable},
    'examples':[{'name':name,'installed_cost_GBP_per_kWe':k,'electricity_kWh_per_kg':e} for name,k,e in examples],
    'example_crossover_electricity_price_GBP_per_MWh':break_price,
    'crossover_cost_GBP_per_kg':at_break[0],
    'checks':['Grid has 11163 unique points','Both examples are inside source ranges',
              'Year-by-year results match the short formula for all 62 paired cases',
              'At the crossover price the examples have equal cost',
              'Greater efficiency helps at the same equipment cost',
              'Lower equipment cost helps at the same efficiency'],
    'limits':['No evidence that all combinations can be built or bought',
              'Ranges include future source scenarios; they are not current product data',
              'The source does not establish a physical cost-efficiency trade-off law',
              'Fixed running costs follow equipment cost at the chosen 2.75% yearly rate',
              'Both examples use the same per-kg water and replacement allowance; this is an assumption',
              'Source price year is open; no current-money claim',
              'No hourly supply, ageing, start-stop or detailed process model'],
}
(DATA/'equipment_efficiency_study_checks.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
reg=json.loads((DATA/'source_register.json').read_bytes())
reg['stage']='Step 7: equipment cost and efficiency scenario test completed'
done=reg.setdefault('completed_studies',[])
if 'Equipment cost and efficiency; 11163 grid cases and 62 paired cases' not in done:
    done.append('Equipment cost and efficiency; 11163 grid cases and 62 paired cases')
reg['open_studies']=['Defined money-year threshold','Joint power-price and plant-use cases with supply evidence']
(DATA/'source_register.json').write_text(json.dumps(reg,indent=2),encoding='utf-8')
print('Crossover power price, GBP/MWh:',break_price)
for r in pair:
    if r['electricity_price_GBP_per_MWh'] in [10,50,150]:
        print(r['example'],r['electricity_price_GBP_per_MWh'],round(r['total_GBP_per_kg'],6))
print('Grid rows:',len(grid),'Paired rows:',len(pair))
