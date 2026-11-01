"""Rebuild the main study from saved inputs and validate the saved native fit."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
steps=['run_baseline.py','test_cost_model.py','run_electricity_study.py',
       'run_plant_use_study.py','run_equipment_efficiency_study.py','run_efficiency_value_study.py',
       'run_neso_driver_screen.py','run_neso_joint_study.py','finish_neso_analysis.py',
       'validate_design_expert.py','check_uk_reference.py','verify_release.py']
for step in steps:
    print('Running',step,flush=True)
    subprocess.run([sys.executable,str(ROOT/'scripts'/step)],cwd=ROOT,check=True)
print('Main tables rebuilt and checked. Report charts remain the saved Excel and Design-Expert exports.')
