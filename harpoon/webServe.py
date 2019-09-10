import datetime
import hashlib
import os
import random
import re
import threading
import time
import urllib.request, urllib.parse, urllib.error
import calendar
from shutil import copyfile, rmtree
import json

import cherrypy
import harpoon
from harpoon import logger
from cherrypy.lib.static import serve_file
from mako import exceptions
from mako.lookup import TemplateLookup
from . import hashfile


def serve_template(templatename, **kwargs):
    interface_dir = os.path.join(str(harpoon.DATADIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), 'bootstrap')

    _hplookup = TemplateLookup(directories=[template_dir])

    try:
        template = _hplookup.get_template(templatename)
        return template.render(http_root=harpoon.HTTP_ROOT, **kwargs)
    except Exception:
        return exceptions.html_error_template().render()

class WebInterface(object):

    def __init__(self, parent):
        self.parent = parent

    @cherrypy.expose
    def index(self):
        logger.debug("Serving index")
        # raise cherrypy.HTTPRedirect("home")
        return self.home()

    @cherrypy.expose
    def home(self, msg=None):
        logger.debug("Serving home")
        return serve_template(templatename='index.html', title="Queue Status", msg=msg)

    @cherrypy.expose
    def hashfile(self, hash=None):
        if hash:
            queuehash = harpoon.HQUEUE.ckqueue()[hash]
            logger.debug(queuehash)
            if 'label' in list(queuehash.keys()):
                hashinfo = hashfile.info(hash=hash, label=queuehash['label'])
            else:
                hashinfo = {}
        else:
            hashinfo = {}
        return serve_template(templatename="hashfile.html", title="Hashfile Viewer", hashinfo=hashinfo)

    @cherrypy.expose
    def confirm(self, action=None, data=None, type=None):
        if action:
            return serve_template(templatename="confirm.html", title="Confirmation", action=action, data=data, type=type)
        else:
            return self.home

    @cherrypy.expose
    def removeItems(self, type=None, item=None):
        removeditems = 0
        msg = ''
        if type == 'failed':
            for key in list(harpoon.HQUEUE.ckqueue().keys()):
                if harpoon.HQUEUE.ckqueue()[key]['stage'] == 'failed':
                    harpoon.HQUEUE.ckremove(key=key)
                    removeditems += 1
        elif type == 'completed':
            for key in list(harpoon.HQUEUE.ckqueue().keys()):
                if harpoon.HQUEUE.ckqueue()[key]['stage'] == 'completed':
                    harpoon.HQUEUE.ckremove(key=key)
                    removeditems += 1
        elif type == 'single' and item:
            if item in list(harpoon.HQUEUE.ckqueue().keys()):
                if harpoon.HQUEUE.ckqueue()[item]['stage'] in ['failed', 'completed']:
                    harpoon.HQUEUE.ckremove(key=item)
                    removeditems += 1
                else:
                    pass
        elif type == 'singleactive' and item:
            if item in list(harpoon.HQUEUE.ckqueue().keys()):
                msg = harpoon.HQUEUE.remove(item, removefile=False)
        elif type == 'singleactivewithfile' and item:
            if item in list(harpoon.HQUEUE.ckqueue().keys()):
                msg = harpoon.HQUEUE.remove(item, removefile=True)
        elif type == 'activedownload':
            if harpoon.CURRENT_DOWNLOAD and harpoon.CURRENT_DOWNLOAD.isopen:
                msg = harpoon.CURRENT_DOWNLOAD.abort_download()
        if len(msg) == 0:
            if removeditems == 1:
                msg = '1 item removed.'
            else:
                msg = '%s items removed.' % removeditems
        return self.home(msg=msg)

    @cherrypy.expose
    def restart(self):
        self.parent.restart = True
        msg = "Restarting harpoon.  Refresh in 20 seconds."
        return self.home(msg=msg)




