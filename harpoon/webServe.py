import datetime
import hashlib
import os
import random
import re
import threading
import time
import urllib
import calendar
from shutil import copyfile, rmtree
import json

import cherrypy
import harpoon
from harpoon import logger
from cherrypy.lib.static import serve_file
from mako import exceptions
from mako.lookup import TemplateLookup
import hashfile


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


    @cherrypy.expose
    def index(self):
        logger.debug("Serving index")
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def home(self, msg=None):
        logger.debug("Serving home")
        return serve_template(templatename='index.html', title="Queue Status", msg=msg)

    @cherrypy.expose
    def hashfile(self, hash=None):
        if hash:
            queuehash = harpoon.HQUEUE.ckqueue()[hash]
            logger.debug(queuehash)
            if 'label' in queuehash.keys():
                hashinfo = hashfile.info(hash=hash, label=queuehash['label'])
            else:
                hashinfo = {}
        else:
            hashinfo = {}
        return serve_template(templatename="hashfile.html", title="Hashfile Viewer", hashinfo=hashinfo)

    @cherrypy.expose
    def confirm(self, action=None, data=None):
        if action:
            return serve_template(templatename="confirm.html", title="Confirmation", action=action, data=data)
        else:
            return self.home

    @cherrypy.expose
    def removeItems(self, type=None, item=None):
        removeditems = 0
        if type == 'failed':
            for key in harpoon.HQUEUE.ckqueue().keys():
                if harpoon.HQUEUE.ckqueue()[key]['stage'] == 'failed':
                    harpoon.HQUEUE.ckremove(key=key)
                    removeditems += 1
        elif type == 'completed':
            for key in harpoon.HQUEUE.ckqueue().keys():
                if harpoon.HQUEUE.ckqueue()[key]['stage'] == 'completed':
                    harpoon.HQUEUE.ckremove(key=key)
                    removeditems += 1
        elif type == 'single' and item:
            if item in harpoon.HQUEUE.ckqueue().keys():
                if harpoon.HQUEUE.ckqueue()[item]['stage'] in ['failed', 'completed']:
                    harpoon.HQUEUE.ckremove(key=item)
                    removeditems += 1
                else:
                    pass
        if removeditems == 1:
            msg = '1 item removed.'
        else:
            msg = '%s items removed.' % removeditems
        return self.home(msg=msg)