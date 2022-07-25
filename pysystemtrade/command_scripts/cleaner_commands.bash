#!/bin/bash

python3 run_monitor_once.py

cd sysproduction/linux/scripts
echo startup >> /proc/1/fd/1

