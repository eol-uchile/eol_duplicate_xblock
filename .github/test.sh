#!/bin/dash

pip install -e /openedx/requirements/eol_duplicate_xblock

cd /openedx/requirements/eol_duplicate_xblock
cp /openedx/edx-platform/setup.cfg .

cd /openedx/edx-platform
mkdir test_root
cd test_root/
ln -s /openedx/staticfiles .
cd ..
#openedx-assets collect --settings=prod.assets
EDXAPP_TEST_MONGO_HOST=mongodb python -Wd -m pytest --ds=cms.envs.test --junitxml=/openedx/edx-platform/reports/cms/nosetests.xml /openedx/requirements/eol_duplicate_xblock/eol_duplicate_xblock/tests.py