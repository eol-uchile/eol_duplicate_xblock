#!/bin/bash

set -e

pip install --src /openedx/venv/src -e /openedx/requirements/app
pip install pytest-cov genbadge[coverage]

cd /openedx/requirements/app
cp /openedx/edx-platform/setup.cfg .
sed -i '/--json-report/c addopts = --nomigrations --reuse-db --durations=20 --json-report --json-report-omit keywords streams collectors log traceback tests --json-report-file=none --cov=eol_duplicate_xblock/ --cov-report term-missing --cov-report xml:reports/coverage/coverage.xml --cov-fail-under 70' setup.cfg

mkdir test_root
cd test_root/
ln -s /openedx/staticfiles .

cd /openedx/requirements/app

SERVICE_VARIANT=cms DJANGO_SETTINGS_MODULE=cms.envs.test EDXAPP_TEST_MONGO_HOST=mongodb pytest eol_duplicate_xblock/tests.py 

rm -r test_root

echo "[run]\nomit = eol_duplicate_xblock/migrations/*" > .coverage
genbadge coverage
