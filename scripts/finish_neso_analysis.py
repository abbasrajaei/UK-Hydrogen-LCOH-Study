"""Final source-bounded Design-Expert sample and efficiency-loss compensation."""
import csv
import json
import math
from pathlib import Path
import random
import numpy as np
from cost_model import Inputs,calculate,discounted_cost,annual_investment_factor

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
DX=ROOT/'design_expert'


def save(name,rows):
    with (DATA/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    DX.mkdir(exist_ok=True)
    case=json.loads((DATA/'starting_case.json').read_bytes())
    bounds=json.loads((DATA/'equipment_efficiency_study_checks.json').read_bytes())
    pem=next(r for r in case['technology_inputs'] if r['technology']=='PEM')
    fraction=pem['annual_fixed_OPEX_fraction'];v=pem['variable_OPEX_GBP_per_kg']
    rate=case['discount_rate'];life=case['plant_life_years']
    def model(k,e,p,u=.5):return Inputs(k,e,p/1000,u,k*fraction,v,rate,life)
    k0,k1=bounds['cost_range_GBP_per_kWe'];e0,e1=bounds['electricity_range_kWh_per_kg']
    rows=[]
    for k in np.linspace(k0,k1,5):
        for e in np.linspace(e0,e1,5):
            for p in np.linspace(0,150,5):
                x=model(float(k),float(e),float(p));result=calculate(x)
                assert math.isclose(result['total_GBP_per_kg'],discounted_cost(x),abs_tol=1e-9)
                rows.append(dict(CAPEX_GBP_kWe=float(k),Electricity_kWh_kg=float(e),
                                 Power_price_GBP_MWh=float(p),LCOH_GBP_kg=result['total_GBP_per_kg']))
    save('neso_design_expert_three_factors.csv',rows)
    # The known cost expression is exactly bilinear in K*e and p*e.
    def basis(r):
        k=(r['CAPEX_GBP_kWe']-(k0+k1)/2)/((k1-k0)/2)
        e=(r['Electricity_kWh_kg']-(e0+e1)/2)/((e1-e0)/2)
        p=(r['Power_price_GBP_MWh']-75)/75
        return [1,k,e,p,k*e,e*p]
    coefficients=np.linalg.lstsq(np.array([basis(r) for r in rows]),
                                 np.array([r['LCOH_GBP_kg'] for r in rows]),rcond=None)[0]
    rng=random.Random(20261101);held=[]
    for _ in range(200):
        k=rng.uniform(k0,k1);e=rng.uniform(e0,e1);p=rng.uniform(0,150)
        r=dict(CAPEX_GBP_kWe=k,Electricity_kWh_kg=e,Power_price_GBP_MWh=p)
        exact=calculate(model(k,e,p))['total_GBP_per_kg'];pred=float(np.dot(basis(r),coefficients))
        held.append({**r,'model_LCOH_GBP_kg':exact,'bilinear_fit_LCOH_GBP_kg':pred,'error_GBP_kg':pred-exact})
    assert max(abs(r['error_GBP_kg']) for r in held)<1e-10
    save('neso_surface_holdout_checks.csv',held)
    compensation=[]
    for use in (.25,.5,.75):
        alpha=(annual_investment_factor(rate,life)+fraction)/(8760*use)
        for price in (10,50,150):
            base=calculate(model(2000,48,price,use))['total_GBP_per_kg']
            for energy in range(48,54):
                limit=(48*(price/1000+2000*alpha)/energy-price/1000)/alpha
                total=calculate(model(limit,energy,price,use))['total_GBP_per_kg']
                assert math.isclose(total,base,abs_tol=1e-10)
                compensation.append(dict(Yearly_use_percent=use*100,Power_price_GBP_MWh=price,
                    Reference_CAPEX_GBP_kWe=2000,Reference_energy_kWh_kg=48,
                    Higher_energy_kWh_kg=energy,Maximum_CAPEX_for_equal_cost_GBP_kWe=limit,
                    Required_CAPEX_reduction_GBP_kWe=2000-limit,
                    Required_CAPEX_reduction_percent=(2000-limit)/2000*100,
                    Equal_LCOH_GBP_kg=total,Within_source_CAPEX_bounds=k0<=limit<=k1))
    save('neso_efficiency_loss_compensation.csv',compensation)
    out=dict(design_expert_sample_rows=125,efficiency_loss_rows=54,
             model_form='LCOH=e*p/1000+e*K*(CRF+0.0275)/(8760*u)+v',
             bounds_CAPEX_GBP_kWe=[k0,k1],bounds_energy_kWh_kg=[e0,e1],bounds_power_GBP_MWh=[0,150],
             source_range_meaning='Bounds span 36 NESO assumptions including 2025-2050 projections; no current market range claim',
             fixed_rules=dict(use_fraction=.5,finance_rate=rate,life_years=life,
                              fixed_OPEX_fraction=fraction,variable_OPEX_GBP_kg=v),
             analytical_terms=['Intercept','CAPEX','Electricity consumption','Power price',
                               'CAPEX x electricity consumption','Power price x electricity consumption'],
             coded_coefficients=coefficients.tolist(),
             independent_holdout_points=len(held),maximum_holdout_error_GBP_kg=max(abs(r['error_GBP_kg']) for r in held),
             seed=20261101,
             inference='Deterministic cost model; regression verifies representation, not real-world accuracy or statistical significance')
    (DATA/'neso_final_analysis_checks.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    # Plain tab-separated data for transfer through Excel's normal UI.
    with (DX/'three_factor_data.tsv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
    print(json.dumps(dict(checks=out,loss_53=[r for r in compensation if r['Higher_energy_kWh_kg']==53]),indent=2))


if __name__=='__main__':main()
