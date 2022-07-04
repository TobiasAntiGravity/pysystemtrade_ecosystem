#!/bin/bash

# start the stack_handler
cd sysproduction/linux/scripts
run_daily_price_updates
run_systems
run_strategy_order_generator
run_cleaners
run_reports

python /opt/projects/pysystemtrade/syscontrol.monitor.py
