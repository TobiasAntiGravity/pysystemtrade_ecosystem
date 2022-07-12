#!/bin/bash

python3 run_monitor_once.py

cd sysproduction/linux/scripts
run_stack_handler &
run_capital_update


