#!/bin/bash

cd sysproduction/linux/scripts
#python /opt/projects/pysystemtrade/syscontrol/monitor.py &
run_daily_price_updates 
run_systems
run_strategy_order_generator
run_cleaners
run_reports


