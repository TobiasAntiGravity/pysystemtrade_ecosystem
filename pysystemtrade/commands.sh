#!/bin/bash

# send email test
python /opt/projects/pysystemtrade/private/mail_credentials_test.py

# keep the container running after test of mail is done
tail -f /dev/null
