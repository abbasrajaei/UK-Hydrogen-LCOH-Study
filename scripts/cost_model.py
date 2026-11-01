"""A simple hydrogen cost model with constant yearly inputs.

Costs use the same money basis as the input data. The source price year is open.
The model does not include taxes, subsidies, extra compression or transport.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Inputs:
    investment_per_kw_e: float
    electricity_kwh_per_kg: float
    electricity_price_per_kwh: float
    capacity_factor: float
    fixed_cost_per_kw_e_year: float
    variable_cost_per_kg: float
    discount_rate: float
    years: int

    def check(self):
        numbers=[self.investment_per_kw_e,self.electricity_kwh_per_kg,
                 self.electricity_price_per_kwh,self.capacity_factor,
                 self.fixed_cost_per_kw_e_year,self.variable_cost_per_kg,
                 self.discount_rate]
        if not all(math.isfinite(x) for x in numbers):
            raise ValueError('All inputs must be finite numbers.')
        if not isinstance(self.years,int) or isinstance(self.years,bool) or self.years<=0:
            raise ValueError('Plant life must be a positive whole number.')
        if not 0<self.capacity_factor<=1:
            raise ValueError('Capacity factor must be above zero and at most one.')
        if self.electricity_kwh_per_kg<=0:
            raise ValueError('Electricity use must be above zero.')
        if min(self.investment_per_kw_e,self.electricity_price_per_kwh,
               self.fixed_cost_per_kw_e_year,self.variable_cost_per_kg,self.discount_rate)<0:
            raise ValueError('Costs and the finance rate must not be negative.')

def annual_investment_factor(rate,years):
    """Turn an up-front investment into equal yearly cost payments."""
    if years<=0 or rate<0:
        raise ValueError('Use a positive life and a nonnegative rate.')
    if rate==0:
        return 1/years
    return rate/(1-(1+rate)**-years)

def calculate(x):
    x.check()
    electricity=8760*x.capacity_factor # kWh/year for each kW of input capacity
    hydrogen=electricity/x.electricity_kwh_per_kg
    factor=annual_investment_factor(x.discount_rate,x.years)
    capital=x.investment_per_kw_e*factor/hydrogen
    power=x.electricity_price_per_kwh*x.electricity_kwh_per_kg
    fixed=x.fixed_cost_per_kw_e_year/hydrogen
    variable=x.variable_cost_per_kg
    return {
        'annual_electricity_kWh_per_kWe':electricity,
        'annual_hydrogen_kg_per_kWe':hydrogen,
        'annual_investment_factor':factor,
        'annual_equipment_cost_GBP_per_kWe':x.investment_per_kw_e*factor,
        'equipment_GBP_per_kg':capital,
        'electricity_GBP_per_kg':power,
        'fixed_running_cost_GBP_per_kg':fixed,
        'other_running_cost_GBP_per_kg':variable,
        'total_GBP_per_kg':capital+power+fixed+variable,
    }

def yearly_cash_flows(x):
    """A separate year-by-year calculation for checking the short formula."""
    x.check()
    rows=[]
    for year in range(x.years+1):
        discount=1/(1+x.discount_rate)**year
        if year==0:
            equipment=x.investment_per_kw_e
            hydrogen=power=fixed=other=0.
        else:
            equipment=0.
            # Work through yearly quantities, rather than calling calculate().
            hydrogen=8760*x.capacity_factor/x.electricity_kwh_per_kg
            power=8760*x.capacity_factor*x.electricity_price_per_kwh
            fixed=x.fixed_cost_per_kw_e_year
            other=hydrogen*x.variable_cost_per_kg
        cost=equipment+power+fixed+other
        rows.append({
            'year':year,'equipment_GBP_per_kWe':equipment,
            'electricity_GBP_per_kWe':power,'fixed_running_GBP_per_kWe':fixed,
            'other_running_GBP_per_kWe':other,'total_cost_GBP_per_kWe':cost,
            'hydrogen_kg_per_kWe':hydrogen,'discount_multiplier':discount,
            'discounted_cost_GBP_per_kWe':cost*discount,
            'discounted_hydrogen_kg_per_kWe':hydrogen*discount,
        })
    return rows

def discounted_cost(x):
    rows=yearly_cash_flows(x)
    return (sum(r['discounted_cost_GBP_per_kWe'] for r in rows)
            /sum(r['discounted_hydrogen_kg_per_kWe'] for r in rows))

def from_source(row,price_per_mwh,capacity_factor,rate,hhv_kwh_per_kg):
    """Use the source's hydrogen-output CAPEX column for source checks."""
    efficiency=row['efficiency_HHV_fraction']
    return Inputs(
        investment_per_kw_e=row['installed_CAPEX_reported_GBP_per_kW_H2_HHV']*efficiency,
        electricity_kwh_per_kg=hhv_kwh_per_kg/efficiency,
        electricity_price_per_kwh=price_per_mwh/1000,
        capacity_factor=capacity_factor,
        fixed_cost_per_kw_e_year=row['fixed_OPEX_GBP_per_kW_H2_HHV_year']*efficiency,
        variable_cost_per_kg=row['variable_OPEX_GBP_per_kWh_H2_HHV']*hhv_kwh_per_kg,
        discount_rate=rate,years=int(row['plant_life_years']),
    )
