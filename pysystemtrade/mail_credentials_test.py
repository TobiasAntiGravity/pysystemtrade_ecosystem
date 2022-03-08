from syslogdiag.emailing import send_mail_msg

try:
	send_mail_msg(body='This mail was sent to confirm that the mail credentials in private_config.yaml is correct. No worries - they were :)', 
				  subject='test of mail login credentials')

except:
	pass
    