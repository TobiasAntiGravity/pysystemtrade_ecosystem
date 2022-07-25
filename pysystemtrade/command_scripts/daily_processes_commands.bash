#!/bin/bash

cd sysproduction/linux/scripts

echo run_daily_price_updates >> /proc/1/fd/1
echo run_systems >> /proc/1/fd/1
echo run_strategy_order_generator >> /proc/1/fd/1
echo run_cleaners >> /proc/1/fd/1
echo run_reports >> /proc/1/fd/1

