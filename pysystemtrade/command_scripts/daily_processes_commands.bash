#!/bin/bash

cd sysproduction/linux/scripts
. run_daily_update_multiple_adjusted_prices
. run_systems
. run_strategy_order_generator
. run_cleaners
. run_reports
