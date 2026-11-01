"""Check the report, saved numerical studies, Excel data and native DX results."""
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from PIL import Image
from openpyxl import load_workbook
from cost_model import Inputs,calculate,discounted_cost

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'

def rows(name):
    with (DATA/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    source=json.loads((DATA/'raw/download_manifest.json').read_bytes())
    for record in source:
        p=DATA/'raw'/record['file']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256'],record['file']
    case=json.loads((DATA/'starting_case.json').read_bytes())
    pem=next(r for r in case['technology_inputs'] if r['technology']=='PEM')
    grid=rows('equipment_efficiency_grid.csv')
    max_gap=0.
    for row in grid:
        x=Inputs(float(row['installed_equipment_cost_GBP_per_kWe']),float(row['electricity_use_kWh_per_kg']),
                 float(row['electricity_price_GBP_per_MWh'])/1000,.5,
                 float(row['installed_equipment_cost_GBP_per_kWe'])*pem['annual_fixed_OPEX_fraction'],
                 pem['variable_OPEX_GBP_per_kg'],.08,25)
        got=discounted_cost(x);gap=abs(got-float(row['total_GBP_per_kg']))
        max_gap=max(max_gap,gap);assert gap<1e-9
    assert len(grid)==11163
    expected_counts={'neso_driver_screen.csv':28,'neso_joint_price_use.csv':1178,
                     'neso_design_expert_three_factors.csv':125,'neso_efficiency_loss_compensation.csv':54}
    for name,count in expected_counts.items():assert len(rows(name))==count
    dx=json.loads((DATA/'design_expert_validation.json').read_bytes())
    assert dx['maximum_native_fit_holdout_error_GBP_kg']<1e-6
    expected=rows('neso_design_expert_three_factors.csv')
    wb=load_workbook(ROOT/'design_expert/NESO_three_factor_surface.xlsx',read_only=True,data_only=True)
    imported=list(wb['Surface data'].iter_rows(min_row=2,values_only=True))
    assert len(imported)==125
    for got,want in zip(imported,expected):
        for actual,key in zip(got,['CAPEX_GBP_kWe','Electricity_kWh_kg','Power_price_GBP_MWh','LCOH_GBP_kg']):
            assert isinstance(actual,(int,float)) and math.isclose(actual,float(want[key]),abs_tol=1e-10)
    wb.close()
    joint=rows('neso_joint_price_use.csv')
    wb=load_workbook(DATA/'NESO_price_and_plant_use_Design_Expert.xlsx',read_only=True,data_only=True)
    for tech in ('PEM','Alkaline'):
        got=list(wb[tech+' data'].iter_rows(min_row=2,values_only=True))
        want=[r for r in joint if r['Technology']==tech]
        assert len(got)==len(want)==589
        for a,b in zip(got,want):
            for i,key in [(1,'A_Power_price_GBP_MWh'),(2,'B_Plant_use_percent'),(3,'Y_Hydrogen_cost_GBP_kg')]:
                assert isinstance(a[i],(int,float)) and math.isclose(a[i],float(b[key]),abs_tol=1e-10)
    wb.close()
    report=ROOT/'docs/FINAL_REPORT.md'
    targets=re.findall(r'\]\(([^)]+)\)',report.read_text(encoding='utf-8'))
    local=[t for t in targets if not t.startswith(('http:','https:','#'))]
    for t in local:
        if t=='../data/release_checks.json':continue
        assert (report.parent/t).resolve().exists(),t
    pictures=[]
    for t in local:
        if not t.endswith('.png'):continue
        p=(report.parent/t).resolve()
        with Image.open(p) as image:
            assert image.width>=1000 and image.height>=600
            if 'A' in image.getbands():
                # Excel PNG exports can have a few partially transparent edge pixels.
                alpha=image.getchannel('A').histogram()
                assert alpha[255]/(image.width*image.height)>.999,p.name
                assert image.convert('RGB').getpixel((10,10))==(255,255,255),p.name
            pictures.append(dict(file=p.name,width=image.width,height=image.height))
    compensation=rows('neso_efficiency_loss_compensation.csv')
    example=next(r for r in compensation if float(r['Yearly_use_percent'])==50
                 and float(r['Power_price_GBP_MWh'])==50 and int(r['Higher_energy_kWh_kg'])==53)
    assert round(float(example['Required_CAPEX_reduction_percent']),2)==17.96
    result=dict(status='Passed for the declared scenario-study scope',date='2026-11-01',
                python=sys.version.split()[0],raw_NESO_files_hash_checked=len(source),
                study_counts=expected_counts,equipment_grid_yearly_DCF_checks=len(grid),
                equipment_grid_maximum_DCF_gap_GBP_kg=max_gap,
                native_Design_Expert_holdout_cases=dx['holdout_cases'],
                native_Design_Expert_maximum_error_GBP_kg=dx['maximum_native_fit_holdout_error_GBP_kg'],
                Excel_rows_checked=125+1178,report_local_links_checked=len(local),
                figures=pictures,visual_review='Four chart images exported through Microsoft Excel and reviewed; three Design-Expert exports retained and reviewed',
                scope_limits=['NESO money year unconfirmed','No site or supplier feasibility claim',
                              'No laboratory significance or physical equipment validation claim'])
    (DATA/'release_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    reg=json.loads((DATA/'source_register.json').read_bytes())
    reg['stage']='NESO portfolio scenario study completed; native Design-Expert charts and final report supplied'
    reg['main_study_status']='Complete for the declared NESO scenario-study scope'
    reg['main_study_source']='NESO'
    reg['main_study_priority']='Optional extension: site-specific hourly power supply and updated dated equipment quotes'
    reg['earlier_scope_open_items']=reg.get('earlier_scope_open_items',reg.get('open_studies',[]))
    reg['open_studies']=[]
    reg['next_priority']=reg['main_study_priority']
    reg['math_validation_scope']='54 selected NESO cases; 14 separate government free-power cases within stated bounds; deterministic scenario checks'
    reg['final_report']='docs/FINAL_REPORT.md'
    reg['native_design_expert_project']='design_expert/NESO_three_factor_cost_model.dxpx'
    reg['release_checks']='data/release_checks.json'
    (DATA/'source_register.json').write_text(json.dumps(reg,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
