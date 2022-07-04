#!/bin/bash

# start the stack_handler
cd sysproduction/linux/scripts
run_reports

python /opt/projects/pysystemtrade/syscontrol.monitor.py
