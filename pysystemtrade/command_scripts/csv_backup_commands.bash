#!/bin/bash

# start the stack_handler
cd sysproduction/linux/scripts
backup_arctic_to_csv

python /opt/projects/pysystemtrade/syscontrol.monitor.py

