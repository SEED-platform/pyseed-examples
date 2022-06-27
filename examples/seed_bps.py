# Example to read and sync seed properties with salesforce

# # ./manage.py create_test_user_json --username nicholas.long@nrel.gov --file ../py-seed/seed-config.json --pyseed

from datetime import date
from pathlib import Path

from pyseed.seed_client import SeedClient

seed_config = Path('seed-config-dev.json')
data_dir = Path(__file__).parent.absolute() / 'data' / 'bps'

client = SeedClient(
    None,
    connection_config_filepath=seed_config,
)
# You will need to make sure that the org name is already
# created on SEED.
client.get_org_by_name('NREL BPS', set_org_id=True)

cycle_2023 = client.get_or_create_cycle('2023', date(2023, 1, 1), date(2023, 12, 31))
cycle_2024 = client.get_or_create_cycle('2024', date(2024, 1, 1), date(2024, 12, 31))
cycle_2025 = client.get_or_create_cycle('2025', date(2024, 1, 1), date(2025, 12, 31))

# set the active cycle and upload to that cycle
client.cycle_id = cycle_2023['id']
client.upload_and_match_datafile(
    'bps-data',
    str(data_dir / 'building-performance-standards-sample-2023.xlsx'),
    'bps mappings',
    str(data_dir / 'bps-mappings.csv')
)

client.cycle_id = cycle_2024['id']
client.upload_and_match_datafile(
    'bps-data',
    str(data_dir / 'building-performance-standards-sample-2024.xlsx'),
    'bps mappings',
    str(data_dir / 'bps-mappings.csv')
)
