"""Checks of units, cost behaviour and selected published results."""
import csv
from dataclasses import replace
import json
import unittest
from pathlib import Path
from cost_model import Inputs,calculate,discounted_cost,from_source

DATA=Path(__file__).resolve().parents[1]/'data'

class CostChecks(unittest.TestCase):
    def setUp(self):
        self.x=Inputs(1000,50,.04,.5,20,.1,.08,20)

    def test_zero_finance_rate_hand_calculation(self):
        x=replace(self.x,discount_rate=0)
        # 4380/50 = 87.6 kg/year. Capital costs 1000/20 = 50/year.
        expected=(50+20)/87.6+2+.1
        self.assertAlmostEqual(calculate(x)['total_GBP_per_kg'],expected,places=12)
        self.assertAlmostEqual(discounted_cost(x),expected,places=12)

    def test_yearly_cash_flow_matches_short_formula(self):
        for rate in [0,.06,.08,.15]:
            for cf in [.05,.5,.95]:
                x=replace(self.x,discount_rate=rate,capacity_factor=cf)
                self.assertAlmostEqual(calculate(x)['total_GBP_per_kg'],discounted_cost(x),places=10)

    def test_half_use_doubles_time_based_cost_per_kg(self):
        full=calculate(self.x)
        half=calculate(replace(self.x,capacity_factor=self.x.capacity_factor/2))
        self.assertAlmostEqual(half['annual_hydrogen_kg_per_kWe'],full['annual_hydrogen_kg_per_kWe']/2)
        for k in ['equipment_GBP_per_kg','fixed_running_cost_GBP_per_kg']:
            self.assertAlmostEqual(half[k],2*full[k])
        for k in ['electricity_GBP_per_kg','other_running_cost_GBP_per_kg']:
            self.assertAlmostEqual(half[k],full[k])

    def test_zero_electricity_price_keeps_other_costs(self):
        r=calculate(replace(self.x,electricity_price_per_kwh=0))
        self.assertEqual(r['electricity_GBP_per_kg'],0)
        self.assertGreater(r['total_GBP_per_kg'],0)

    def test_bad_inputs_rejected(self):
        for changes in [{'capacity_factor':0},{'capacity_factor':1.1},
                        {'electricity_kwh_per_kg':0},{'years':0},
                        {'electricity_price_per_kwh':-1},{'investment_per_kw_e':float('nan')}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                calculate(replace(self.x,**changes))

    def test_selected_source_components_and_totals(self):
        case=json.loads((DATA/'starting_case.json').read_bytes())
        with (DATA/'neso_reference_cases_checked.csv').open(encoding='utf-8-sig',newline='') as f:
            refs=list(csv.DictReader(f))
        self.assertEqual(len(refs),54)
        mapping={'equipment_GBP_per_kg':'LCOH Capex','electricity_GBP_per_kg':'LCOH Electricity Cost',
                 'fixed_running_cost_GBP_per_kg':'LCOH Fixed Opex',
                 'other_running_cost_GBP_per_kg':'LCOH Variable Opex','total_GBP_per_kg':'LCOH'}
        for ref in refs:
            row=next(r for r in case['technology_inputs'] if r['technology']==ref['Tech'])
            x=from_source(row,float(ref['Electricity Price']),float(ref['Capacity Factor']),
                          float(ref['Discount Factor']),case['HHV_kWh_per_kg_source_convention'])
            got=calculate(x)
            for local,source in mapping.items():
                with self.subTest(case=ref['_id'],component=local):
                    self.assertAlmostEqual(got[local],float(ref[source]),places=8)
            self.assertAlmostEqual(discounted_cost(x),float(ref['LCOH']),places=8)

if __name__=='__main__':
    unittest.main(verbosity=2)
