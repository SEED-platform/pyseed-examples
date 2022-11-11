# Example to read and sync seed properties with salesforce

# ./manage.py create_test_user_json --username nicholas.long@nrel.gov --file ../py-seed/seed-config.json --pyseed
# Make sure that the host is localhost and not 127.0.0.1. For some reason the organization endpoints only work on
# localhost.

from datetime import date
from pathlib import Path

from pyseed.seed_client import SeedClient

seed_config = Path('seed-config-dev.json')
data_dir = Path(__file__).parent.absolute() / 'data' / 'better'

client = SeedClient(None, connection_config_filepath=seed_config)
client.get_org_by_name('better', set_org_id=True)

# get or create the cycle
cycle = client.get_or_create_cycle('BETTER Cycle', date(2020, 1, 1), date(2020, 12, 31), set_cycle_id=True)

# upload the data to seed
client.upload_and_match_datafile(
    'better-data',
    str(data_dir / 'better-test-data.xlsx'),
    'better mappings',
    str(data_dir / 'better-mappings.csv'),
    import_meters_if_exist=True,
)

