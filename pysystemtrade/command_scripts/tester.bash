#!/bin/bash

# start the stack_handler
cd sysproduction/linux/scripts
cat update_sampled_contracts -> /home/echos/update_sampled_contracts.txt

python /opt/projects/pysystemtrade/syscontrol.monitor.py

