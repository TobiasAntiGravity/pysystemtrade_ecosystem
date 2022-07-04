#!/bin/bash

# start the stack_handler
cd sysproduction/linux/scripts
run_daily_price_updates

python /opt/projects/pysystemtrade/syscontrol.monitor.py