from __future__ import with_statement

import hqueue
import threading
import cherrypy
import subprocess
import sys
import os
import platform
import time
import json
from harpoon import logger, hconfig





SYS_ENCODING = 'utf-8'
DATADIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
CONF_LOCATION = os.path.join(DATADIR, 'conf', 'harpoon.conf')
BOOTSTRAP_THEME = 'cerulean'

config = hconfig.config(CONF_LOCATION)
logpath = config.get('general', 'logpath', str, os.path.join(DATADIR, 'logs'))

if not os.path.isdir(logpath):
    os.mkdir(logpath)

logger.initLogger(logpath)

SOCKET_API = config.get('general', 'socket_api', str, None)
HTTP_ROOT = config.get('webserver', 'root', str, '/')
BOOTSTRAP_THEME = config.get('webserver', 'bootstrap_theme', str, 'cerulean')

HQUEUE = hqueue.hQueue()
MAINTHREAD = None

