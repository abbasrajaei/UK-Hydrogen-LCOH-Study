"""NESO price/use scenario grid. All quantities are calculated, not measured."""
import csv
import json
import math
from pathlib import Path
from cost_model import calculate, discounted_cost, from_source

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'


def main():
    case=json.loads((DATA/'starting_case.json').read_bytes())
    rows=[]
    for source in case['technology_inputs']:
        run=0
        for price in range(0,151,5):
            for use in range(5,96,5):
                run+=1
                x=from_source(source,price,use/100,case['discount_rate'],
                              case['HHV_kWh_per_kg_source_convention'])
                result=calculate(x)
                assert math.isclose(result['total_GBP_per_kg'],discounted_cost(x),abs_tol=1e-9)
                rows.append(dict(Technology=source['technology'],Run_ID=run,
                    A_Power_price_GBP_MWh=price,B_Plant_use_percent=use,
                    Y_Hydrogen_cost_GBP_kg=result['total_GBP_per_kg'],
                    Equipment_GBP_kg=result['equipment_GBP_per_kg'],
                    Electricity_GBP_kg=result['electricity_GBP_per_kg'],
                    Fixed_running_GBP_kg=result['fixed_running_cost_GBP_per_kg'],
                    Water_replacement_GBP_kg=result['other_running_cost_GBP_per_kg'],
                    Hydrogen_kg_per_kWe_year=result['annual_hydrogen_kg_per_kWe'],
                    Equivalent_full_load_hours_year=8760*x.capacity_factor,
                    Inverse_use_fraction=1/x.capacity_factor))
    assert len(rows)==1178
    index={(r['Technology'],r['A_Power_price_GBP_MWh'],r['B_Plant_use_percent']):r for r in rows}
    assert len(index)==len(rows)
    for r in rows:
        tech,p,u=r['Technology'],r['A_Power_price_GBP_MWh'],r['B_Plant_use_percent']
        if p<150: assert index[tech,p+5,u]['Y_Hydrogen_cost_GBP_kg']>r['Y_Hydrogen_cost_GBP_kg']
        if u<95: assert index[tech,p,u+5]['Y_Hydrogen_cost_GBP_kg']<r['Y_Hydrogen_cost_GBP_kg']
    with (DATA/'neso_reference_cases_checked.csv').open(encoding='utf-8-sig',newline='') as f:
        refs=list(csv.DictReader(f))
    matches=0
    for ref in refs:
        if math.isclose(float(ref['Discount Factor']),case['discount_rate']):
            key=(ref['Tech'],round(float(ref['Electricity Price'])),round(float(ref['Capacity Factor'])*100))
            got=index[key]
            assert math.isclose(got['Y_Hydrogen_cost_GBP_kg'],float(ref['LCOH']),abs_tol=1e-8)
            matches+=1
    assert matches==18
    for filename,group in [('neso_joint_price_use.csv',rows)]+[
            (f'neso_joint_{tech.lower()}_design_expert.csv',[r for r in rows if r['Technology']==tech])
            for tech in ('PEM','Alkaline')]:
        with (DATA/filename).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(group[0]));w.writeheader();w.writerows(group)
    payload=dict(case=case,columns=list(rows[0]),rows=rows)
    (DATA/'neso_joint_price_use.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    examples=[index['PEM',10,25],index['PEM',50,50],index['PEM',50,75]]
    checks=dict(cases=len(rows),cases_per_technology=589,matched_NESO_reference_cases=matches,
        price_range_GBP_MWh=[0,150],price_step=5,use_percent_range=[5,95],use_step_percentage_points=5,
        source_basis='NESO 2025 Central; source GBP, money year unconfirmed',
        tests=['All 1178 points match independent yearly discounted flows',
               '18 matching saved NESO published totals agree',
               'All points are unique; cost increases with price and falls with use',
               'The price effect per kg is independent of use under this model'],
        interpretation='Joint trade-off study; no site power-price/availability relationship has been established',
        mathematics='LCOH = e*p + e*(K*CRF+F)/(8760*u) + V; p in GBP/kWh, u as a fraction',
        design_expert_status='Input tables prepared; no Design-Expert project or fitted chart created in this step',
        limits=['No empirical noise or replicated experiments; do not infer statistical significance',
                'CF dependence is reciprocal; a quadratic approximation must be checked against the model',
                'Technology cost differences do not demonstrate a universal real equipment ranking',
                'No hourly supply, degradation, added compression, storage, transport, tax or subsidy'])
    # Verify zero price-use cross-difference. This model is additive in p and 1/u.
    for tech in ('PEM','Alkaline'):
        delta=lambda u:index[tech,50,u]['Y_Hydrogen_cost_GBP_kg']-index[tech,10,u]['Y_Hydrogen_cost_GBP_kg']
        assert math.isclose(delta(25),delta(75),abs_tol=1e-12)
    (DATA/'neso_joint_study_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    reg=json.loads((DATA/'source_register.json').read_bytes())
    reg['main_study_status']='Joint electricity-price and plant-use study: 1178 NESO-based calculated scenarios'
    reg['main_study_priority']='Review joint study, then assess equipment-cost/efficiency trade-offs and Design-Expert fits'
    (DATA/'source_register.json').write_text(json.dumps(reg,indent=2),encoding='utf-8')
    print(json.dumps(dict(checks=checks,PEM_teaching_examples=examples),indent=2))


if __name__=='__main__': main()
