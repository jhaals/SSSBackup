#!/usr/bin/python
# Copyright (c) 2009, Johan Haals <johan.haals@gmail.com>
# All rights reserved.
# SSBackup [Simple Secure System Backup] - Version 1.2

import commands, smtplib, time, sys, tarfile, socket, os, logging, logging.handlers
from email.MIMEText import MIMEText
from optparse import OptionParser
from zlib import adler32

from checksum import checksum_of_file

# Please set the following parameters.

# TARGET
TARGET_IP = '' # Where to connect? Enter IP or DNS for the target
TARGET_FOLDER = '' # Target folder (where backup is stored) 
TARGET_USERNAME = '' # Username on remote server

# EMAIL settings
USER_EMAIL = '' # The email address for the user on the smtp server
ADMIN_EMAIL = '' # You're email address!
SMTP_SERVER = '' # mydomain.com:port
SMTP_SERVER_USER = '' # SMTP username
SMTP_SERVER_PASSWORD = '' # SMTP password

LOG_FILENAME = '/tmp/SSSBackup.log' # Where do you want the logfile?

# DO NOT CHANGE ANYTHING UNDER THIS LINE UNLESS YOU KNOW WHAT YOU'RE DOING.

BACKUP_MACHINE = socket.gethostname()
start_time = time.strftime('%Y-%m-%d %m:%M:%S')

# Log settings
SSSBackup_logger = logging.getLogger('SSSBackup')
SSSBackup_logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(
              LOG_FILENAME, maxBytes=1048576, backupCount=5) # 1mb max log size, 5 files will be saved.

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

SSSBackup_logger.addHandler(handler)

# Arguments/options
usage = "usage: %prog [path] [temp store] [options]"
parser = OptionParser(usage, version="%prog 1.2")
parser.add_option("--email", "-e", help="Send email to administrator on success/fail", action="store_true")
parser.add_option("--name", help="Name for this backup, will be displayed in result email")
parser.add_option("--test-smtp", help="Will send a test mail to the administrator", action="store_true")
parser.add_option("--remove-temp", help="Removes temp dmg after successful backup", action="store_true")
(options, args) = parser.parse_args()

# Testing the SMTP if argument --test-smtp is used. 
if options.test_smtp:
    print 'Testing SMTP configuration. If you dont recive any email from SSSBackup, please verify SMTP configuration'
    SMTP_SERVER_CONNECT = smtplib.SMTP(SMTP_SERVER) # Connect to smtp
    try:
        SMTP_SERVER_CONNECT.login(SMTP_SERVER_USER, SMTP_SERVER_PASSWORD) # Auth to smtp
    except smtplib.SMTPHeloError:
        sys.exit('The server didnt reply properly to the HELO greeting.')
    except smtplib.SMTPAuthenticationError:
        sys.exit('The SMTP server didnt accept the username/password combination.')
    message = 'SSSBackup can send messages with this configuration!'
    msg = MIMEText(message)
    msg['Subject'] = 'Hello from SSSbackup!'
    msg['From'] = USER_EMAIL
    msg['To'] = ADMIN_EMAIL
    SMTP_SERVER_CONNECT.sendmail(ADMIN_EMAIL, ADMIN_EMAIL, msg.as_string())
    SMTP_SERVER_CONNECT.quit()
    sys.exit('Test done')

if (options.name):
    BACKUP_NAME = options.name
else:
    BACKUP_NAME = BACKUP_MACHINE
 
if len(args) != 2:
    parser.error("incorrect number of arguments")
if len(args) == 2:
    BACKUP_PATH = args[0]
    BACKUP_TEMP_STORE = args[1]
# EOF Arguments/options


# Connects to the SMTP server and send success/error email.
def SendMail(error):
    SMTP_SERVER_CONNECT = smtplib.SMTP(SMTP_SERVER) # Connect to smtp
    SMTP_SERVER_CONNECT.login(SMTP_SERVER_USER, SMTP_SERVER_PASSWORD) # Auth to smtp

    if not error:
        message = 'SSSBackup job "%s" on machine %s completed!\n Source Size: %s\n Target Size: %s\n Backup Started: %s\n Backup Ended: %s' % (BACKUP_NAME, BACKUP_MACHINE, source_size.split()[0], target_size.split()[0], start_time, end_time)
        subject = 'SSSbackup job "%s" on machine "%s" completed!' % (BACKUP_NAME, BACKUP_MACHINE)
        SSSBackup_logger.info('sending success email to %s' % ADMIN_EMAIL)
    else:
        message = 'SSSBackup job "%s" on machine %s failed!\n Source Size: %s\n Target Size: %s' % (BACKUP_NAME, BACKUP_MACHINE, source_size.split()[0], target_size.split()[0])
        subject = 'SSSbackup job "%s" on machine "%s" failed!' % (BACKUP_NAME, BACKUP_MACHINE)
        SSSBackup_logger.info('sending fail email to %s' % ADMIN_EMAIL)

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = USER_EMAIL
    msg['To'] = ADMIN_EMAIL

    SMTP_SERVER_CONNECT.sendmail(ADMIN_EMAIL, ADMIN_EMAIL, msg.as_string())
    SMTP_SERVER_CONNECT.quit()

SSSBackup_logger.info('---- SSSBACKUP Started ----')
SSSBackup_logger.info('Backup path: %s' % BACKUP_PATH)
SSSBackup_logger.info('Backup temp storage: %s' % BACKUP_TEMP_STORE)
    
SSSBackup_logger.info('Doing remove on any existing old archive') 

BACKUP_FILE = '%s%s.tar.bz2' % (BACKUP_TEMP_STORE, BACKUP_NAME)

try:
    os.remove(BACKUP_FILE)
except:
    pass

SSSBackup_logger.info('Creating %s' % BACKUP_FILE)
try:
    archive = tarfile.open(BACKUP_FILE, mode = 'w:bz2')
    archive.add(BACKUP_PATH)
    archive.close()
except:
    SSSBackup_logger.critical('Could not create tar.bz2 archive.')    
    SSSBackup_logger.critical('---- SSSBackup failed, unable to create archive ----\n\n')
    sys.exit('Error when creating tar.bz2 archive')

source_size = commands.getoutput('du -sh %s' % BACKUP_FILE) # Checking size of source archive
SSSBackup_logger.info('Source archive size: %s' % source_size.split()[0])

SSSBackup_logger.info('Doing remove of old target archive before copy to remote host')
commands.getoutput('ssh %s@%s rm %s%s.tar.bz2' % (TARGET_USERNAME, TARGET_IP, TARGET_FOLDER, BACKUP_NAME)) 

SSSBackup_logger.info('Doing copy of archive to remote host...')
commands.getoutput('scp %s %s@%s:%s' % (BACKUP_FILE, TARGET_USERNAME, TARGET_IP, TARGET_FOLDER))

SSSBackup_logger.info('Asking remote machine for the archive size')
target_size = commands.getoutput('ssh %s@%s du -sh %s%s.tar.bz2' % (TARGET_USERNAME, TARGET_IP, TARGET_FOLDER, BACKUP_NAME)) # Checking size of target archive

SSSBackup_logger.info('Target archive size: %s' % target_size.split()[0])

SSSBackup_logger.info('Doing checksum compare of source/target')

try:
    source_sum = checksum_of_file(BACKUP_FILE)
except IOError:
    # Couldn't open the specified file
    SendMail(error=True)
    SSSBackup_logger.critical('Unable to open %s I/O error' % BACKUP_FILE)
    sys.exit('Unable to open "%s"!' % BACKUP_FILE)

SSSBackup_logger.info('Requesting checksum from remote machine')
target_sum = commands.getoutput('ssh %s@%s checksum %s%s.tar.bz2' % (TARGET_USERNAME, TARGET_IP, TARGET_FOLDER, BACKUP_NAME)) 

if target_sum[0:6] == 'Error:':
    SSSBackup_logger.error('Error in return from remote machine:%s. Backup aborted.' % target_sum[6:])
    sys.exit('Backup aborted due errors, please read logfile')
target_sum = int(target_sum)

end_time = time.strftime('%Y-%m-%d %m:%M:%S')

# if checksum of source == checksum of target
if source_sum == target_sum:
    if options.email:
        SendMail(error=False)
    if options.remove_temp:
        os.remove(BACKUP_FILE)
        SSSBackup_logger.info('Removing source backup file')
    SSSBackup_logger.info('---- source/target checksum matched Backup done! ----\n\n')
    
else:
    SSSBackup_logger.error('Error, the checksum of source does mot match target!\n\n')
    if options.email:
        SendMail(error=True)
