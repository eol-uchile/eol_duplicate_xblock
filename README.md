# EOL Duplicate Xblock

![https://github.com/eol-uchile/eol_duplicate_xblock/actions](https://github.com/eol-uchile/eol_duplicate_xblock/workflows/Python%20application/badge.svg)

Duplicate a block_id in any user course

# Install

    docker-compose exec cms pip install -e /openedx/requirements/eol_duplicate_xblock

## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run lms /openedx/requirements/eol_duplicate_xblock/.github/test.sh
