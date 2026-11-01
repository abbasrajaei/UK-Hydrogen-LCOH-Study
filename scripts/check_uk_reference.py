"""Rebuild the 14 government zero-electricity-price central cases.

This uses a separate year-by-year calculation. It does not edit the workbook.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
def read_csv(name):
    with (DATA/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))
def write_csv(name,rows):
    with (DATA/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def cash_flow(k,fixed,variable,ratio,phases,years,rate,cf=.25,power_price=0):
    """Costs and hydrogen per 1 kW of hydrogen-output capacity (HHV)."""
    if k<=0 or fixed<0 or variable<0 or ratio<=0 or not 0<cf<=1 or rate<0:
        raise ValueError('Check the physical and cost inputs.')
    if years<=0 or len(phases)!=3 or abs(sum(phases)-1)>1e-12:
        raise ValueError('Check life and construction spending shares.')
    annual_energy=8760*cf # kWh H2 HHV per kW H2 HHV per year
    flows=[]
    for year in range(len(phases)+years):
        operating=year>=len(phases)
        investment=k*phases[year] if year<len(phases) else 0.
        energy=annual_energy if operating else 0.
        kg=energy/1000*25.4
        power=energy*ratio*power_price
        running=fixed if operating else 0.
        other=energy*variable
        discount=(1+rate)**-year
        flows.append({
            'year':year,'phase':'Operation' if operating else 'Construction',
            'investment_GBP2020_per_kW_H2_HHV':investment,
            'electricity_GBP2020_per_kW_H2_HHV':power,
            'fixed_running_GBP2020_per_kW_H2_HHV':running,
            'stack_allowance_GBP2020_per_kW_H2_HHV':other,
            'hydrogen_kg_per_kW_H2_HHV':kg,'discount_multiplier':discount,
        })
    output_pv=sum(r['hydrogen_kg_per_kW_H2_HHV']*r['discount_multiplier'] for r in flows)
    parts={}
    for name,key in [('equipment','investment_GBP2020_per_kW_H2_HHV'),
                     ('electricity','electricity_GBP2020_per_kW_H2_HHV'),
                     ('fixed_running','fixed_running_GBP2020_per_kW_H2_HHV'),
                     ('stack_allowance','stack_allowance_GBP2020_per_kW_H2_HHV')]:
        parts[name]=sum(r[key]*r['discount_multiplier'] for r in flows)/output_pv
    parts['total']=sum(parts.values())
    return parts,flows

inputs=read_csv('uk_reference_inputs_2020gbp.csv')
outputs=read_csv('uk_reference_outputs_2020gbp.csv')
results=[];all_flows=[]
for source in inputs:
    tech=source['technology'];year=int(source['commissioning_year'])
    target=next(r for r in outputs if r['technology']==tech and int(r['commissioning_year'])==year and r['source_scenario']=='Curtailed electricity')
    assert float(target['electricity_GBP2020_per_MWh_H2_HHV'])==0
    k=float(source['CAPEX_GBP2020_per_kW_H2_HHV'])
    fixed=float(source['fixed_OPEX_GBP2020_per_kW_H2_HHV_year'])
    variable=float(source['variable_OPEX_GBP2020_per_kWh_H2_HHV'])
    ratio=float(source['electric_input_kWh_per_kWh_H2_HHV'])
    phases=[float(source[f'construction_spend_fraction_year_{j}']) for j in [1,2,3]]
    years=int(source['plant_life_years']);rate=float(source['hurdle_rate_fraction'])
    got,flows=cash_flow(k,fixed,variable,ratio,phases,years,rate)
    # Separate short-form check, including spending spread over construction.
    annual_output_MWh=8760*.25/1000
    recovery=1/years if rate==0 else rate/(1-(1+rate)**-years)
    build_factor=sum(share*(1+rate)**(len(phases)-1-j) for j,share in enumerate(phases))
    short=(k*recovery*build_factor+fixed)/annual_output_MWh+variable*1000
    assert math.isclose(short/25.4,got['total'],abs_tol=1e-10)

    # These are explicit rounding assumptions, not a statistical interval.
    # Source numerical inputs have 0.01 GBP cost steps and 0.0001 variable steps.
    # They can differ from the full-precision source outputs.
    bound_parts={
        'equipment':.005*recovery*build_factor/annual_output_MWh/25.4,
        'electricity':0.,
        'fixed_running':.005/annual_output_MWh/25.4,
        'stack_allowance':.00005*1000/25.4,
    }
    mapping={'equipment':'equipment_GBP2020_per_MWh_H2_HHV',
             'electricity':'electricity_GBP2020_per_MWh_H2_HHV',
             'fixed_running':'fixed_OPEX_GBP2020_per_MWh_H2_HHV',
             'stack_allowance':'variable_OPEX_GBP2020_per_MWh_H2_HHV',
             'total':'total_GBP2020_per_MWh_H2_HHV'}
    reference={key:float(target[column])/25.4 for key,column in mapping.items()}
    for key in bound_parts:
        assert abs(got[key]-reference[key])<=bound_parts[key]+1e-9,(tech,year,key)
    rounding_bound=sum(bound_parts.values())
    gap=got['total']-reference['total']
    assert abs(gap)<=rounding_bound+1e-9
    results.append({
        'technology':tech,'commissioning_year':year,'source_case':'Curtailed electricity; central inputs',
        'money_basis':'Real 2020 GBP','electricity_price_GBP2020_per_kWh':0,
        'capacity_factor':.25,'plant_life_years':years,'finance_rate':rate,'construction_years':len(phases),
        **{f'calculated_{key}_GBP2020_per_kg':value for key,value in got.items()},
        **{f'published_{key}_GBP2020_per_kg':value for key,value in reference.items()},
        'difference_GBP2020_per_kg':gap,'difference_pence2020_per_kg':gap*100,
        'assumed_rounding_bound_GBP2020_per_kg':rounding_bound,
        'inside_assumed_rounding_bound':True,
        'source_input_sheet':source['source_sheet'],'source_input_year_cell':source['source_year_cell'],
        'source_output_sheet':target['source_sheet'],'source_total_cell':target['source_total_cell'],
    })
    all_flows.extend({'technology':tech,'commissioning_year':year,**r} for r in flows)
assert len(results)==14
assert len(all_flows)==14*33
write_csv('uk_reference_reproduction.csv',results)
write_csv('uk_reference_yearly_flows.csv',all_flows)
(DATA/'uk_reference_reproduction.json').write_text(json.dumps(results,indent=2),encoding='utf-8')

review={
    'checked_date':'2026-11-01','case_count':len(results),
    'scope':'PEM and alkaline; seven build years; central curtailed-electricity case only',
    'price_basis':'Real 2020 GBP','source_case_settings':{'power_price_GBP_per_kWh':0,'capacity_factor':.25,
                 'finance_rate':.10,'plant_life_years':30,'construction_years':3},
    'timing':'One third of equipment spending in each of years 0, 1 and 2. Operation in years 3 to 32.',
    'units':'1 kW hydrogen-output HHV capacity; 1 MWh hydrogen HHV = 25.4 kg',
    'maximum_absolute_difference_GBP2020_per_kg':max(abs(r['difference_GBP2020_per_kg']) for r in results),
    'maximum_absolute_difference_pence2020_per_kg':max(abs(r['difference_pence2020_per_kg']) for r in results),
    'all_components_inside_assumed_rounding_bounds':True,
    'rounding_assumptions':{'CAPEX_GBP_per_kW_output_half_step':.005,
                          'fixed_OPEX_GBP_per_kW_output_year_half_step':.005,
                          'variable_OPEX_GBP_per_kWh_output_half_step':.00005},
    'rounding_meaning':'Bounds reflect stated possible rounding of the supplied input numbers. They are not confidence intervals. They do not prove the cause of every source difference.',
    'checks':['Four cost parts sum to the full total','Direct yearly costs match a separate short formula',
              'Published totals and components agree within assumed input-rounding bounds',
              'Source blank cases were not treated as zero'],
    'limits':['The source scenario is simplified; it is not a real free-electricity supply offer',
              'This checks cost arithmetic and construction timing; not plant performance',
              'The dated source electricity-price paths for grid and wind cases have not been reproduced',
              'Electrolysis variable OPEX is a stack-replacement allowance in this source; a separate water bill is not identified',
              'The source assumes outlet pressure around 3 MPa, or 30 bar; extra compression is outside the cost',
              'The report was published in 2021 and contains historical projections, not current supplier quotes'],
    'report_evidence':{'money_year':'Printed page 27','hydrogen_units':'Printed page 8, Table 1.1',
                       'stack_cost_and_outlet_pressure':'Printed page 19','free-electricity_case':'Printed page 23'},
}
(DATA/'uk_reference_reproduction_checks.json').write_text(json.dumps(review,indent=2),encoding='utf-8')
reg=json.loads((DATA/'source_register.json').read_bytes())
reg['stage']='Step 10: 14 dated UK reference cases reproduced within stated rounding bounds'
reg['dated_reference_model_reproduced']=False
reg['dated_reference_reproduction_status']='14 central curtailed-electricity cases reproduced; grid and wind price paths not yet reproduced'
reg['independent_cost_arithmetic_check']={'source':'UK government 2021 annex','cases':14,
                                       'scope':'Free-electricity cases only; within stated rounding bounds'}
reg['next_priority']='Use the dated model to calculate target conditions; show the limits of constant-price cases'
(DATA/'source_register.json').write_text(json.dumps(reg,indent=2),encoding='utf-8')
print(json.dumps({'cases':len(results),'maximum_gap_GBP_per_kg':review['maximum_absolute_difference_GBP2020_per_kg'],
                  'maximum_gap_pence_per_kg':review['maximum_absolute_difference_pence2020_per_kg']},indent=2))
for r in results:
    if r['commissioning_year']==2025:
        print(r['technology'],'source',r['published_total_GBP2020_per_kg'],'calculated',r['calculated_total_GBP2020_per_kg'])
