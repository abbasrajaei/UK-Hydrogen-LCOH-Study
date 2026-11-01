"""Read native Design-Expert data and coefficients; compare with our cost model."""
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'


def main():
    path=ROOT/'design_expert/NESO_three_factor_cost_model.dxpx'
    root=ET.parse(path).getroot()
    factors=root.findall('./factorInfo/factor')
    assert [f.attrib['unit'] for f in factors]==['GBP/kWe','kWh/kg H2','GBP/MWh']
    assert root.find('./responseInfo/response').attrib['unit']=='GBP/kg H2'
    bounds={f.attrib['id']:(float(f.find('numeric').attrib['low']),float(f.find('numeric').attrib['high'])) for f in factors}
    model=root.find('./responseModel/compModel')
    coef={t.attrib['term']:float(t.attrib['coef']) for t in model.findall('equationTerm') if 'coef' in t.attrib}
    assert set(coef)=={'Intercept','A','B','C','AB','BC'}
    def predict(k,e,p):
        values={name:(2*value-lo-hi)/(hi-lo) for (name,(lo,hi)),value in zip(bounds.items(),(k,e,p))}
        return (coef['Intercept']+sum(coef[a]*values[a] for a in ('A','B','C'))
                +coef['AB']*values['A']*values['B']+coef['BC']*values['B']*values['C'])
    with (DATA/'neso_design_expert_three_factors.csv').open(encoding='utf-8-sig',newline='') as f: originals=list(csv.DictReader(f))
    runs=root.findall('./run');assert len(runs)==len(originals)==125
    maximum_input_gap=maximum_response_gap=0.
    for run,original in zip(runs,originals):
        values={f.attrib['id']:float(f.text) for f in run.findall('facActual')}
        for factor,key in [('A','CAPEX_GBP_kWe'),('B','Electricity_kWh_kg'),('C','Power_price_GBP_MWh')]:
            gap=abs(values[factor]-float(original[key]));maximum_input_gap=max(maximum_input_gap,gap)
            assert gap<1e-6
        gap=abs(float(run.find('resVal').text)-float(original['LCOH_GBP_kg']))
        maximum_response_gap=max(maximum_response_gap,gap);assert gap<1e-6
    with (DATA/'neso_surface_holdout_checks.csv').open(encoding='utf-8-sig',newline='') as f: holdouts=list(csv.DictReader(f))
    errors=[]
    for row in holdouts:
        k=float(row['CAPEX_GBP_kWe']);e=float(row['Electricity_kWh_kg']);p=float(row['Power_price_GBP_MWh'])
        got=predict(k,e,p);expected=float(row['model_LCOH_GBP_kg'])
        errors.append(dict(CAPEX_GBP_kWe=k,Electricity_kWh_kg=e,Power_price_GBP_MWh=p,
                           Direct_model_GBP_kg=expected,Design_Expert_GBP_kg=got,Error_GBP_kg=got-expected))
    worst=max(abs(r['Error_GBP_kg']) for r in errors)
    assert worst<1e-6
    with (DATA/'design_expert_holdout_checks.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(errors[0]));w.writeheader();w.writerows(errors)
    checks=dict(application=root.attrib['creator'],version=root.attrib['version'],
        native_project=path.name,imported_cases=len(runs),holdout_cases=len(errors),
        imported_data_maximum_input_rounding_gap=maximum_input_gap,
        imported_data_maximum_response_rounding_gap_GBP_kg=maximum_response_gap,
        maximum_native_fit_holdout_error_GBP_kg=worst,
        import_precision='Excel clipboard values displayed with six decimal places',
        fitted_coded_coefficients=coef,factor_bounds=bounds,
        units_checked=True,native_project_reopened_successfully=True,
        inference='Representation of a deterministic cost model; not experimental significance or real-plant validation')
    (DATA/'design_expert_validation.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':main()
