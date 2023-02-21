#!/bin/bash

cd sysproduction/linux/scripts
. run_daily_fx_and_contract_updates
. run_daily_price_updates
. run_systems
. run_strategy_order_generator
. run_cleaners
. run_reports
