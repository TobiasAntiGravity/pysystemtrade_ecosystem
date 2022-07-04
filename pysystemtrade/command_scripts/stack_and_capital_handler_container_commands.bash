#!/bin/bash

# start the stack_handler
cd sysproduction/linux/scripts
run_stack_handler
run_capital_update

python /opt/projects/pysystemtrade/syscontrol.monitor.py

