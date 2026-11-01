"""Build Step 3 results from the saved starting case. No internet needed."""
import csv
import json
from pathlib import Path
from cost_model import calculate,discounted_cost,from_source,yearly_cash_flows

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'

def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)

if __name__=='__main__':
    case=json.loads((DATA/'starting_case.json').read_bytes())
    results=[];cash=[]
    for row in case['technology_inputs']:
        x=from_source(row,case['electricity_price_GBP_per_MWh'],case['capacity_factor'],
                      case['discount_rate'],case['HHV_kWh_per_kg_source_convention'])
        values=calculate(x)
        check=discounted_cost(x)
        assert abs(values['total_GBP_per_kg']-check)<1e-9
        results.append({
            'technology':row['technology'],'source_build_year':case['source_build_year'],
            'electricity_price_GBP_per_kWh':x.electricity_price_per_kwh,
            'capacity_factor':x.capacity_factor,'discount_rate':x.discount_rate,
            'plant_life_years':x.years,
            'source_consistent_investment_GBP_per_kWe':x.investment_per_kw_e,
            'fixed_running_GBP_per_kWe_year':x.fixed_cost_per_kw_e_year,
            **values,'year_by_year_check_GBP_per_kg':check,
            'money_basis':'Source GBP; price year not confirmed',
            'result_type':'Reproduction of source model; not a measured site cost',
        })
        cash.extend({'technology':row['technology'],**r} for r in yearly_cash_flows(x))
    write_csv(DATA/'baseline_costs.csv',results)
    write_csv(DATA/'baseline_yearly_costs.csv',cash)
    (DATA/'baseline_costs.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    register=json.loads((DATA/'source_register.json').read_bytes())
    register['stage']='Step 3: cost model built; starting-case costs and yearly flows saved'
    register['core_model_implemented']=True
    register['independent_reference_check_complete']=False
    register['model_limits']=['Source price year is open','No explicit equipment ageing or hourly operation',
                              'Source running-cost allowance covers water and replacements',
                              'Results reproduce a source model; they are not measured site costs']
    (DATA/'source_register.json').write_text(json.dumps(register,indent=2),encoding='utf-8')
    for r in results:
        print(r['technology'],{k:round(r[k],6) for k in ['equipment_GBP_per_kg','electricity_GBP_per_kg','fixed_running_cost_GBP_per_kg','other_running_cost_GBP_per_kg','total_GBP_per_kg']})
