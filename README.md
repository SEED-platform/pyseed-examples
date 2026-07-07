## SEED Examples

This repository contains example scripts to load datasets into SEED and test the overall functionality of the py-seed library (SEED Python API Client).

### Getting Started

To get started, you will need to checkout py-seed or install py-seed. Installing pyseed is easier but limited the ability to update during development. If you checkout py-seed, then place the project at the same level as this project. For example:

```
cd ..
git clone git@github.com:SEED-platform/py-seed.git
git checkout develop
```

This repository uses uv for environment and dependency management.

Supported Python versions are 3.10 through 3.12.

```
uv sync --all-groups
```

### Configuring

SEED needs to be configured for accessing its web application.

#### SEED

Copy `seed-config-example.json` to `seed-config-dev.json` and fill
in with the correct credentials. The format of the SEED configuration should contain the following:

```json
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

There are two options for running the examples, either open the `ipynb` files or execute the scripts in the
examples directory. The `ipynb` files provide more flexibility to understand how the py-seed library works.

### TODO

- [ ] Import audit template files
