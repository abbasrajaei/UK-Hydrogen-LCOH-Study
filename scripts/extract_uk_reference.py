"""Read the public UK annex. Do not modify it. Needs openpyxl."""
import csv
import hashlib
import json
from pathlib import Path
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data';RAW=DATA/'raw'
path=RAW/'uk_hydrogen_costs_2021_annex.xlsx'
w=load_workbook(path,data_only=True,read_only=True)
home=w['Home'];table=w['Technical and cost assumptions']
money_cells=[]
for row in home.iter_rows(min_row=18,max_row=21):
    for cell in row:
        if isinstance(cell.value,str) and 'All costs are in real 2020 GBP' in cell.value:
            money_cells.append({'sheet':'Home','cell':cell.coordinate,'text':cell.value})
assert len(money_cells)==1
assert '2020 real prices' in table['A1'].value

inputs=[]
for tech,first in [('Alkaline',4),('PEM',11)]:
    for col in range(first,first+7):
        year=int(table.cell(3,col).value)
        cell=lambda row:table.cell(row,col)
        assert year in [2020,2025,2030,2035,2040,2045,2050]
        ratio=float(cell(11).value)
        assert ratio>1
        inputs.append({
            'technology':tech,'commissioning_year':year,'case':'Medium source assumptions',
            'money_unit':'GBP','price_year':2020,'inflation_basis':'real',
            'reference_size_MW_H2_HHV':cell(4).value,
            'maximum_load_fraction':cell(5).value,
            'electric_input_kWh_per_kWh_H2_HHV':ratio,
            'HHV_efficiency_fraction_derived':1/ratio,
            'electricity_kWh_per_kg_using_source_25_4kg_per_MWh':ratio*1000/25.4,
            'plant_life_years':cell(13).value,
            'CAPEX_GBP2020_per_kW_H2_HHV':cell(15).value,
            'construction_years':cell(17).value,
            'construction_spend_fraction_year_1':cell(18).value,
            'construction_spend_fraction_year_2':cell(19).value,
            'construction_spend_fraction_year_3':cell(20).value,
            'fixed_OPEX_GBP2020_per_kW_H2_HHV_year':cell(22).value,
            'variable_OPEX_GBP2020_per_kWh_H2_HHV':cell(25).value,
            'hurdle_rate_fraction':cell(27).value,
            'source_sheet':table.title,'source_year_cell':cell(3).coordinate,
            'source_electricity_cell':cell(11).coordinate,
            'source_CAPEX_cell':cell(15).coordinate,
            'data_type':'Published 2021 model assumptions; not observed later market prices',
        })
assert len(inputs)==14
assert len({(r['technology'],r['commissioning_year']) for r in inputs})==14
for r in inputs:
    assert r['plant_life_years']==30 and r['hurdle_rate_fraction']==.1
    assert abs(sum(r[k] for k in ['construction_spend_fraction_year_1','construction_spend_fraction_year_2','construction_spend_fraction_year_3'])-1)<1e-12

outputs=[];not_available=[]
# Only the central blocks for PEM and alkaline; no SOE or sensitivity blocks.
for year in [2020,2025,2030,2035,2040,2045,2050]:
    sheet=w[f'{year}_E']
    for scenario,col0 in [('Grid retail',2),('Grid LRVC',5),('Dedicated offshore wind',8),('Curtailed electricity',11)]:
        for offset,tech in [(0,'Alkaline'),(1,'PEM')]:
            col=col0+offset
            if sheet.cell(12,col).value is None:
                assert all(sheet.cell(row,col).value is None for row in [4,5,6,7,8,9,10,11])
                not_available.append({'technology':tech,'year':year,'scenario':scenario,'reason':'Blank source result; not converted to zero'})
                continue
            parts={
                'equipment_GBP2020_per_MWh_H2_HHV':float(sheet.cell(4,col).value),
                'fixed_OPEX_GBP2020_per_MWh_H2_HHV':float(sheet.cell(5,col).value),
                'variable_OPEX_GBP2020_per_MWh_H2_HHV':float(sheet.cell(6,col).value),
                'electricity_GBP2020_per_MWh_H2_HHV':float(sheet.cell(7,col).value),
            }
            total=float(sheet.cell(12,col).value)
            assert all(float(sheet.cell(row,col).value)==0 for row in [8,9,10,11])
            assert abs(sum(parts.values())-total)<1e-8
            outputs.append({'technology':tech,'commissioning_year':year,'source_scenario':scenario,
                            **parts,'total_GBP2020_per_MWh_H2_HHV':total,
                            'source_sheet':sheet.title,'source_total_cell':sheet.cell(12,col).coordinate,
                            'money_basis':'Real 2020 GBP','data_type':'Published 2021 model output'})
assert len(outputs)+len(not_available)==56
for name,rows in [('uk_reference_inputs_2020gbp.csv',inputs),('uk_reference_outputs_2020gbp.csv',outputs)]:
    with (DATA/name).open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

review={
    'review_date':'2026-11-01',
    'NESO':{
        'status':'Price year still not confirmed',
        'checked':['Dataset page','Input definitions','Downloaded package metadata','All three public dashboard pages'],
        'dashboard_limits':'Two visuals showed field errors. Readable notes did not state a price year.',
        'decision':'Keep earlier results in the source GBP basis; do not relabel them as 2020 or current pounds',
    },
    'UK_2021_annex':{
        'publication_year':2021,'money_unit':'GBP','price_year':2020,'inflation_basis':'real',
        'evidence_cells':money_cells+[{'sheet':table.title,'cell':'A1','text':table['A1'].value}],
        'report_evidence':'PDF printed page 27: reported results use 2020 real prices',
        'unit_evidence':'PDF printed page 8, Table 1.1: capacity is hydrogen output MW HHV; 1 MWh HHV equals 25.4 kg',
        'inputs_extracted':14,'outputs_extracted':len(outputs),'blank_source_cases':not_available,
        'scope':'PEM and alkaline; central assumptions and four central supply cases; 2020-2050',
        'inputs_checked':'Unique technology/year keys, positive electricity ratios, stated life/rate, construction shares sum to one',
        'outputs_checked':'Each saved total agrees with its four nonzero cost parts',
        'read_method':'Read saved workbook values; no workbook edits or formula recalculation',
        'annex_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'source_page':'https://www.gov.uk/government/publications/hydrogen-production-costs-2021',
        'source_annex':'https://assets.publishing.service.gov.uk/media/611a706ed3bf7f63a7b29216/Hydrogen_Production_Cost_2021_Annex.xlsx',
    },
    'study_decision':{
        'dated_threshold_case':'Define a separate study question: GBP 1/kg in real 2020 GBP',
        'reason':'The separate official reference has an explicit and checked money basis',
        'not_claimed':['That this is the Rivan blog target year','That NESO costs are in 2020 GBP','That the 2021 report gives current supplier quotes'],
        'existing_NESO_studies':'Retained separately with their original open money-year note',
        'new_reference_model':'Inputs acquired; numerical reproduction not yet completed',
    },
    'remaining_work':['Check the new reference construction and operating-cost timing',
                      'Keep time-varying electricity-price assumptions separate from constant-price tests',
                      'Confirm all boundaries before a like-for-like benchmark',
                      'Use a sourced inflation index only if a later-money target is needed'],
}
(DATA/'money_basis_review.json').write_text(json.dumps(review,indent=2),encoding='utf-8')
reg=json.loads((DATA/'source_register.json').read_bytes())
reg['stage']='Step 9: dated money basis established for a separate UK reference'
reg['money_basis_review_file']='money_basis_review.json'
reg['NESO_price_year_confirmed']=False
reg['dated_reference_price_year']=2020
reg['dated_reference_currency']='GBP'
reg['dated_reference_model_reproduced']=False
reg['threshold_definition']='Separate case: GBP 1/kg in real 2020 GBP; not a statement of the blog target year'
if not any(s['id']=='UK_BEIS_2021' for s in reg['sources']):
    reg['sources'].append({'id':'UK_BEIS_2021','url':review['UK_2021_annex']['source_page'],
                          'price_year':2020,'currency':'GBP','inflation_basis':'real',
                          'coverage_verified':f'Report and annex acquired; 14 input and {len(outputs)} central output cases extracted and checked; blank source cases retained as unavailable',
                          'status':'Separate historical model reference; full reproduction pending'})
reg['next_priority']='Reproduce the dated UK reference before a price-year-defined threshold study'
(DATA/'source_register.json').write_text(json.dumps(reg,indent=2),encoding='utf-8')
old=json.loads((DATA/'external_reference_review.json').read_bytes())
old['additional_candidate']['status']='Report and annex acquired; explicit money basis checked; inputs and central results extracted'
(DATA/'external_reference_review.json').write_text(json.dumps(old,indent=2),encoding='utf-8')
w.close()
print('Money statement:',money_cells)
print('Saved input cases:',len(inputs),'Saved output cases:',len(outputs))
print('This does not establish NESO money year or complete model reproduction.')
