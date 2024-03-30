#!/bin/bash

current_dir=$(pwd)

# Create a /tmp/random_dir and copy
tmp_dir=$(mktemp -d)
echo "$tmp_dir"
cp -r main.py payment.py num2persian.py configuration.py database.py requirements.txt "$tmp_dir"

cd "$tmp_dir"
python3.10 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
deactivate
cd venv/lib/python3.10/site-packages
zip -r ../../../../my_deployment_package.zip .
cd ../../../../
zip my_deployment_package.zip main.py payment.py num2persian.py configuration.py database.py

cp my_deployment_package.zip "$current_dir"
