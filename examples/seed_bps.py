# # ./manage.py create_test_user_json --username nicholas.long@nrel.gov --file ../py-seed/seed-config.json --pyseed

from datetime import date
from pathlib import Path

from pyseed.seed_client import SeedClient

# Location to SEED BPS Data -- this will be a checkout of the SEED repo and point to the {seed_repo}/seed/data/bps directory.

seed_config = Path('seed-config-local.json')
org_name = 'Program Tracking 1'
# path to seed repo checkout at the same level as pyseed-examples
data_dir = Path(__file__).parent.parent.parent.absolute() / 'seed' / 'seed' / 'tests' / 'data' / 'bps'
# path to where the mapping files exist
mappings_dir = Path(__file__).parent.absolute() / 'data' / 'bps'

client = SeedClient(
    None,
    connection_config_filepath=seed_config,
)

# let the user verify that this is the right place to
# perform the actions.
client_info = client.instance_information()
print("You are connecting to the following instance:")
print(f"\tHost: {client_info['host']}")
print(f"\tVersion: {client_info['version']}")
print(f"\tSHA: {client_info['sha']}")
print(f"\tUsername: {client_info['username']}")
print()
print("If this is not the correct instance, then verify the seed config file.")
cont_resp = input("Continue [y/n]: ")
if cont_resp.lower() == 'y':
    print("Continuing...")
else:
    print("Exiting...")
    exit()

# verify if they have the correct organization
orgs = client.get_organizations()
if org_name not in [org['name'] for org in orgs]:
    print(f"Organization '{org_name}' not found. Please create the organization and try again. You belong to the following organizations:")
    for org in orgs:
        print(f"\t{org['name']}")
    exit()

# You will need to make sure that the org name is already created on SEED.
client.get_org_by_name(org_name, set_org_id=True)

# upload mapping profile for the ESPM webservice
client.create_or_update_column_mapping_profile_from_file('ESPM Webservice', mappings_dir / 'espm-webservice-mappings.csv')

# for cycle_year in range(2019, 2024):
for cycle_year in range(2019, 2020):
    cycle = client.get_or_create_cycle(f"{str(cycle_year)}", date(cycle_year, 1, 1), date(cycle_year, 12, 31), set_cycle_id=True)

    # upload CBL data
    upload_file_name = f'CBL-building-performance-standards-sample-{cycle_year}.xlsx'
    if (data_dir / upload_file_name).exists():
        print(f'uploading {upload_file_name}')
        client.upload_and_match_datafile(
            'cbl-data',
            str(data_dir / upload_file_name),
            'cbl mappings',
            str(mappings_dir / 'cbl-mappings.csv'),
            import_meters_if_exist=False,
        )
    else:
        print(f'Could not find {data_dir / upload_file_name}, exiting...')
        exit()

    # upload targets
    upload_file_name = f'BPS-sample-Targets-{cycle_year}.xlsx'
    if (data_dir / upload_file_name).exists():
        print(f'uploading {upload_file_name}')
        client.upload_and_match_datafile(
            'bps-target-data',
            str(data_dir / upload_file_name),
            'bps target mappings',
            str(mappings_dir / 'bps-targets-mappings.csv'),
            import_meters_if_exist=False,
        )
    else:
        print(f'Could not find {data_dir / upload_file_name}, exiting...')
        exit()

    # upload performance data
    # upload_file_name = f'BPS-sample-Targets-{cycle_year}.xlsx'
    # if (data_dir / upload_file_name).exists():
    #     print(f'uploading {upload_file_name}')
    #     client.upload_and_match_datafile(
    #         f'bps-target-data',
    #         str(data_dir / upload_file_name),
    #         'bps target mappings',
    #         str(mappings_dir / 'bps-targets-mappings.csv'),
    #         import_meters_if_exist=False,
    #     )
    # else:
    #     print(f'Could not find {data_dir / upload_file_name}, exiting...')
    #     exit()
