#!/bin/bash

cd sysproduction/linux/scripts

echo run_daily_price_updates >> /proc/1/fd/1
run_systems
run_strategy_order_generator
run_cleaners
run_reports
