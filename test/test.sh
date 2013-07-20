#!/bin/bash

# Python versions to test
declare -a pythons=('python2.6' 'python2.7')

for i in "${pythons[@]}"
do
    echo Setting up $i environment...
    deactivate
    rm -rf ve$i
    virtualenv -p /usr/bin/$i ve$i
    source ve$i/bin/activate 
    pushd ..
    python setup.py install
    popd 
    pip install -r requirements.txt
    echo  
    echo Starting tests in $i environment
    nosetests --verbose --with-coverage --cover-erase --cover-package=exoline
done

#deactivate
