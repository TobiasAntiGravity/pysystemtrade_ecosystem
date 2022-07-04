#!/bin/bash

# start the stack_handler
cd sysproduction/linux/scripts
run_strategy_order_generator

python /opt/projects/pysystemtrade/syscontrol.monitor.py
