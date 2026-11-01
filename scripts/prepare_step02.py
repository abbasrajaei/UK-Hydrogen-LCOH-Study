"""Check the source data and save a clear starting case."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
RAW = DATA / 'raw'
def read(path):
    return json.loads(path.read_bytes())
def save(name, value):
    (DATA/name).write_text(json.dumps(value,indent=2,ensure_ascii=True),encoding='utf-8')
def csv_save(name, rows):
    with (DATA/name).open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)

source=read(RAW/'neso_inputs.json')
assert source['success']
inputs=source['result']['records']
assert len(inputs)==source['result']['total']==36
keys=[(r['Tech'],r['Scenario'],r['Build Year']) for r in inputs]
expected=set(itertools.product(['PEM','Alkaline'],['Central','Low','High'],[2025,2030,2035,2040,2045,2050]))
assert len(keys)==len(set(keys)) and set(keys)==expected
for r in inputs:
    assert all(v is not None for v in r.values())
    assert 0<r['Efficiency']<1 and r['Plant Lifetime']==25
    assert r['Capex_GBP_per_kWe']>0 and r['Capex_GBP_per_kW_H2_HHV']>0
    assert 0<r['Fixed_Opex_Percent_of_Capex']<1
    assert r['Variable Opex']>=0
    for v in r.values():
        if isinstance(v,(int,float)):assert math.isfinite(v)
    assert abs(r['Fixed Opex']-r['Capex_GBP_per_kW_H2_HHV']*r['Fixed_Opex_Percent_of_Capex'])<1e-6

hhv=1000/25.4
checked=[]
flags=[]
for r in inputs:
    k_effective=r['Capex_GBP_per_kW_H2_HHV']*r['Efficiency']
    difference=(r['Capex_GBP_per_kWe']/k_effective-1)*100
    row={
        'source_row_id':r['_id'],'technology':r['Tech'],'source_scenario':r['Scenario'],
        'build_year':r['Build Year'],
        'installed_CAPEX_reported_GBP_per_kWe':r['Capex_GBP_per_kWe'],
        'installed_CAPEX_reported_GBP_per_kW_H2_HHV':r['Capex_GBP_per_kW_H2_HHV'],
        'efficiency_HHV_fraction':r['Efficiency'],
        'electricity_consumption_kWh_per_kg':hhv/r['Efficiency'],
        'installed_CAPEX_derived_GBP_per_kWe':k_effective,
        'CAPEX_column_difference_percent':difference,
        'annual_fixed_OPEX_fraction':r['Fixed_Opex_Percent_of_Capex'],
        'fixed_OPEX_GBP_per_kW_H2_HHV_year':r['Fixed Opex'],
        'variable_OPEX_GBP_per_kWh_H2_HHV':r['Variable Opex'],
        'variable_OPEX_GBP_per_kg':r['Variable Opex']*hhv,
        'plant_life_years':r['Plant Lifetime'],
        'data_type':'published_model_assumption',
        'currency_price_year':'not_confirmed',
    }
    checked.append(row)
    if abs(difference)>.001:
        flags.append({k:row[k] for k in ['source_row_id','technology','source_scenario','build_year','CAPEX_column_difference_percent']})
csv_save('neso_inputs_checked.csv',checked)

raw_refs=read(RAW/'neso_reference_cases.json')
assert raw_refs['success']
refs=[]
numeric=['Capacity Factor','Electricity Price','Discount Factor','LCOH','LCOH Capex',
         'LCOH Electricity Cost','LCOH Fixed Opex','LCOH Variable Opex']
for rr in raw_refs['result']['records']:
    r={k:v for k,v in rr.items() if k!='_full_text'}
    for k in numeric:r[k]=float(r[k])
    r['Build Year']=int(r['Build Year'])
    assert r['Units']=='£/kg H2'
    r['Units']='GBP/kg H2'
    assert 0<r['Capacity Factor']<=1 and r['Electricity Price']>=0
    assert math.isclose(r['LCOH'],sum(r[k] for k in ['LCOH Capex','LCOH Electricity Cost','LCOH Fixed Opex','LCOH Variable Opex']),abs_tol=1e-9)
    refs.append(r)
assert len(refs)==54
ref_keys={(r['Tech'],r['Capacity Factor'],r['Electricity Price'],r['Discount Factor']) for r in refs}
assert ref_keys==set(itertools.product(['PEM','Alkaline'],[.05,.5,.95],[0.,50.,150.],[.06,.08,.15]))
csv_save('neso_reference_cases_checked.csv',refs)

# This checks the source arithmetic. It does not prove that its assumptions
# match a real plant. No taxes or site-specific costs are added here.
max_gap=0.
for r in refs:
    i=next(x for x in inputs if (x['Tech'],x['Scenario'],x['Build Year'])==(r['Tech'],r['Scenario'],r['Build Year']))
    rate=r['Discount Factor'];n=i['Plant Lifetime']
    annual_payment_fraction=rate/(1-(1+rate)**-n)
    kg_per_output_kW=8760*r['Capacity Factor']/hhv
    calculated=(i['Capex_GBP_per_kW_H2_HHV']*annual_payment_fraction/kg_per_output_kW
                +i['Fixed Opex']/kg_per_output_kW
                +i['Variable Opex']*hhv
                +(r['Electricity Price']/1000)*hhv/i['Efficiency'])
    max_gap=max(max_gap,abs(calculated-r['LCOH']))
    assert abs(calculated-r['LCOH'])<1e-8

starting={
    'name':'2025 Central source-reproduction case',
    'status':'Inputs fixed for source reproduction; real-world price and performance claims remain provisional',
    'source_scenario':'Central','source_build_year':2025,
    'electricity_price_GBP_per_MWh':50,
    'electricity_price_GBP_per_kWh':.05,
    'capacity_factor':.5,'discount_rate':.08,'plant_life_years':25,
    'HHV_kWh_per_kg_source_convention':hhv,
    'normalizing_electrical_capacity_kW':1,
    'scale_note':'1 kW is a calculation unit, not a claim about a real 1 kW plant or economies of scale.',
    'setting_sources':{
        'electricity_price':'Study choice from the published reference grid; not a site price',
        'capacity_factor':'Study choice from the published reference grid; not measured operation',
        'discount_rate':'Study choice from the published reference grid; not a project finance quote',
        'life_and_technology_values':'NESO source inputs',
    },
    'cost_column_rule':'For source reproduction use reported GBP/kW_H2_HHV CAPEX. Preserve reported GBP/kWe; do not overwrite it.',
    'cash_flow_rule':'Source arithmetic matches an initial investment followed by 25 annual operating periods. Do not add another construction-year factor without a separate case.',
    'water_and_replacements':'Included in source variable OPEX; do not add twice',
    'exclusions':['Additional compression','Hydrogen storage','Transport','Fuel synthesis','Taxes','Subsidies'],
    'open_items':['Currency price year','Real or nominal price basis','Hydrogen outlet pressure and purity','Applicable plant scale','Reason for six source CAPEX conversion mismatches'],
    'technology_inputs':[r for r in checked if r['source_scenario']=='Central' and r['build_year']==2025],
}
save('starting_case.json',starting)
manifest=read(RAW/'download_manifest.json')
for entry in manifest:
    assert hashlib.sha256((RAW/entry['file']).read_bytes()).hexdigest()==entry['sha256']
report={
    'checked_on':'2026-11-01',
    'input_rows_checked':36,'input_key_duplicates':0,'missing_input_values':0,
    'expected_technology_scenario_year_combinations_present':True,
    'reference_rows_checked':54,
    'reference_scope':'2025 Central only; two technologies and selected CF, power-price and discount-rate combinations',
    'source_reported_total_output_rows':424080,
    'all_output_rows_downloaded':False,
    'download_hashes_checked':len(manifest),
    'source_CAPEX_conversion_flags':flags,
    'maximum_reference_arithmetic_difference_GBP_per_kg':max_gap,
    'interpretation':'Arithmetic agreement only. No independent real-plant validation.',
    'unresolved':starting['open_items'],
}
save('step02_data_checks.json',report)

reg=read(DATA/'source_register.json')
reg['stage']='Step 2: source files acquired; starting source-reproduction case selected'
reg['baseline_frozen']=False
reg['source_reproduction_inputs_fixed']=True
reg['production_cost_model_validated']=False
reg['communication_style']='Simple words, short sentences, explained terms and worked examples.'
for s in reg['sources']:
    if s['id']=='NESO_INPUTS':
        s['coverage_verified']='All 36 input rows downloaded and checked; raw JSON and download hashes saved'
        s['gaps']=['Currency price year and real/nominal basis unconfirmed','Outlet conditions and applicable plant scale unconfirmed','Six 2025 CAPEX conversion mismatches; reason not established']
    if s['id']=='NESO_OUTPUTS':
        s['coverage_verified']='54 selected 2025 Central cases downloaded and checked; first-five sample also saved; full output dataset not downloaded'
        s['gaps']=['Full output dataset not audited','Currency price year and real/nominal basis unconfirmed']
        s['reproduction_check']='Annuity arithmetic agrees within 1e-8 GBP/kg in all 54 selected cases using source output-capacity CAPEX'
reg['decisions']['currency']='GBP in the source monetary basis; price year remains unconfirmed'
for group in reg['input_groups']:
    if group['group']=='Installed CAPEX and efficiency':group['status']='All 36 rows checked; six conversion differences flagged'
    if group['group']=='OPEX, water and replacement':group['status']='Aggregate source treatment retained; no extra replacement charge'
    if group['group']=='Electricity price and utilization':group['status']='Starting study choice: GBP 50/MWh and CF 0.5; not a site claim'
    if group['group']=='Financing and lifetime':group['status']='Starting study choice: 8% rate and source 25-year life; price basis still open'
save('source_register.json',reg)

print(json.dumps({'input_rows':36,'reference_rows':54,'cost_column_flags':len(flags),'maximum_arithmetic_gap_GBP_per_kg':max_gap},indent=2))
for r in starting['technology_inputs']:
    print(r['technology'],'electricity kWh/kg',round(r['electricity_consumption_kWh_per_kg'],4),
          'reported CAPEX GBP/kWe',r['installed_CAPEX_reported_GBP_per_kWe'])
