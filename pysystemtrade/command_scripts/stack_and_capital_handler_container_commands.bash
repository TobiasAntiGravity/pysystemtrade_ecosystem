#!/bin/bash

#python3 run_monitor_once.py

cd sysproduction/linux/scripts
startup

run_stack_handler &
run_capital_update &
python3 /opt/projects/pysystemtrade/syscontrol/monitor.py


