from __future__ import with_statement

import ConfigParser
import threading
import cherrypy
import subprocess
import sys
import os
import platform
import time
import json

FULL_PATH = None
PROG_DIR = None
DAEMON = False
SIGNAL = None
PIDFILE = ''
DATADIR = ''
CACHEDIR = ''
SESSIONDIR = ''
CONFIGFILE = ''
LOGLEVEL = 1
CONFIG = {}
CFG = ''
COMMIT_LIST =None
SYS_ENCODING = 'utf-8'
UPDATE_MSG = ''
HTTP_ROOT = ''
CURRENT_TAB = '1'
BOOTSTRAP_THEMELIST = []

