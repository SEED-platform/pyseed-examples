## SEED Examples

This repository contains example scripts to load datasets into SEED and test the overall functionality of the py-seed library (SEED Python API Client).

### Getting Started

To get started, you will need to checkout py-seed (with the branch `add-seed-helpers`) and place the project at the same level as this project. For example:

```
cd ..
git clone git@github.com:SEED-platform/py-seed.git
git checkout add-seed-helpers
```

Then install the poetry-based dependencies. Note that installing a package from GitHub through poetry can cause some issues with updating, therefore, it is easiest (for now) to clone the dependencies manually.

```
pip install poetry
poetry install
```

### Configuring

SEED needs to be configured for accessing its web application.

#### SEED

Copy `seed-config-example.json` to `seed-config-dev.json` and fill
in with the correct credentials. The format of the SEED configuration should contain the following:

```
{
    "name": "seed_api_test",
    "base_url": "https://dev1.seed-platform.org",
    "username": "user@company.com",
    "api_key": "secure-key",
    "port": 443,
    "use_ssl": true
}
```

### Running Examples

From the examples directory, run the `seed_*.py` files. The files may require some manual SEED configuration, e.g., creating an organization.

### TODO

- [ ] TBD
