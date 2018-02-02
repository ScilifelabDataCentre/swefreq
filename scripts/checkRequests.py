from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import peewee
import smtplib

import db
import secrets

def send_email():
    msg             = MIMEMultipart()
    msg['to']       = secrets.admin_address
    msg['from']     = secrets.from_address
    msg['subject']  = 'Pending SweFreq requests'
    msg['reply-to'] = secrets.reply_to_address
    body            = "There are pending requests for SweFreq accounts, please visit http://swefreq.nbis.se"
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(secrets.mail_server)
    server.sendmail(msg['from'], [msg['to']], msg.as_string())

if __name__ == '__main__':
    requests = db.get_outstanding_requests(1)
    try:
        requests.get() # There's at least one request
        send_email()
    except peewee.DoesNotExist:
        # No new users so we don't send any emails.
        pass
    except smtplib.SMTPException as e:
        logging.warning("Can't send email. Got this exception: {}".format(e))
