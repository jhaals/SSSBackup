#!/usr/bin/python
# Copyright (c) 2009, Johan Haals <johan.haals@gmail.com>
# All rights reserved.
# SSBackup [Simple Secure System Backup] - Version 1.0

import commands, smtplib, time, sys, tarfile
from email.MIMEText import MIMEText
from optparse import OptionParser
from zlib import adler32
import socket
import os

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

# DO NOT CHANGE ANYTHING UNDER THIS LINE UNLESS YOU KNOW WHAT YOU'RE DOING.

BACKUP_MACHINE = socket.gethostname()
start_time = time.strftime('%Y-%m-%d %m:%M:%S')

# Arguments/options
usage = "usage: %prog [path] [temp store] [options]"
parser = OptionParser(usage, version="%prog 1.2")
parser.add_option("--email", "-e", help="Send email to administrator on success/fail", action="store_true")
parser.add_option("--name", help="Name for this backup, will be displayed in result email")
parser.add_option("--test-smtp", help="Will send a test mail to the administrator", action="store_true")
parser.add_option("--remove-temp", help="Removes temp dmg after successful backup", action="store_true")
parser.add_option("-v", "--verbose", help="Run backup in verbose mode(you see whats going on)", action="store_true")
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
        if (options.verbose):
            print 'sending success email'
    else:
        message = 'SSSBackup job "%s" on machine %s failed!\n Source Size: %s\n Target Size: %s' % (BACKUP_NAME, BACKUP_MACHINE, source_size.split()[0], target_size.split()[0])
        subject = 'SSSbackup job "%s" on machine "%s" failed!' % (BACKUP_NAME, BACKUP_MACHINE)
        if (options.verbose):
            print 'sending fail email'

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = USER_EMAIL
    msg['To'] = ADMIN_EMAIL

    SMTP_SERVER_CONNECT.sendmail(ADMIN_EMAIL, ADMIN_EMAIL, msg.as_string())
    SMTP_SERVER_CONNECT.quit()

# This function returns a checksum of the input file. Used to verify target and source file.
def CheckSum(file):
    CHUNK_SIZE = 1024
    try:
        f = open(file, 'rb')
    except IOError:
        if(options.email):
            Error = True
            SendMail(Error)
        sys.exit('Unable to open %s' % file)
    current = 0

    while True:
        buffer = f.read(CHUNK_SIZE)
        if not buffer:
            break

        current = adler32(buffer, current)
    f.close()
    return current
     
if options.verbose:
    print 'Starting backup %s. Doing remove on existing dmg and starting new.' % start_time

BACKUP_FILE = '%s%s.tar.bz2' % (BACKUP_TEMP_STORE, BACKUP_NAME)

try:
    os.remove(BACKUP_FILE)
except:
    pass

# Creates a tar.bz2 archive of selected path
if options.verbose:
    print 'Creating new archive'
try:
    archive = tarfile.open(BACKUP_FILE, mode = 'w:bz2')
    archive.add(BACKUP_PATH)
    archive.close()
except:
    sys.exit('Error when creating tar.bz2 archive')

source_size = commands.getoutput('du -sh %s' % BACKUP_FILE) # Checking size of source archive
if (options.verbose):
    print 'Source archive size: %s' % source_size.split()[0]


if (options.verbose):
    print 'Doing remove of old target archive before copy'
commands.getoutput('ssh %s@%s rm %s%s.tar.bz2' % (TARGET_USERNAME, TARGET_IP, TARGET_FOLDER, BACKUP_NAME)) 
if (options.verbose):
    print 'Doing copy of archive to remote host. This may take some time...'
commands.getoutput('scp %s %s@%s:%s' % (BACKUP_FILE, TARGET_USERNAME, TARGET_IP, TARGET_FOLDER))

if (options.verbose):
    print 'Checking size of remote archive'
target_size = commands.getoutput('ssh %s@%s du -sh %s%s.tar.bz2' % (TARGET_USERNAME, TARGET_IP, TARGET_FOLDER, BACKUP_NAME)) # Checking size of target archive
if (options.verbose):
    print 'Target archive size: %s' % target_size.split()[0]

if (options.verbose):
    print 'Doing verify of source/target files'
source_sum = CheckSum(BACKUP_FILE)
if (options.verbose):
    print 'Still working...'
target_sum = commands.getoutput('ssh %s@%s checksum %s%s.tar.bz2' % (TARGET_USERNAME, TARGET_IP, TARGET_FOLDER, BACKUP_NAME)) 
target_sum = int(target_sum)

end_time = time.strftime('%Y-%m-%d %m:%M:%S')

# if checksum of source == checksum of target
if source_sum == target_sum:
    if (options.verbose):
        print 'The checksum of source matches target, backup done!'
    if (options.email):
        Error = False
        SendMail(Error)
    if options.verbose:
        print 'Completed backup ' + end_time
    if options.remove_temp:
        os.remove(BACKUP_FILE)
else:
    if(options.verbose):
        print 'Error, the size of source does not match the target'
    if(options.verbose and options.email):
        print 'Doing logon to SMTP server' 
    if(options.email):
        Error = True
        SendMail(Error)
