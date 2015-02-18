#!/bin/bash

sed -i "/Host ${1}/,/END ${1}/d" ${2}
