import os
import sys

import cherrypy
import harpoon
from harpoon import logger, database
from harpoon.webServe import WebInterface

def initialize(options=None):

    if options is None:
        options = {}
    https_enabled = options['https_enabled']
    https_cert = options['https_cert']
    https_key = options['https_key']

    if https_enabled:
        if not (os.path.exists(https_cert) and os.path.exists(https_key)):
            logger.warn("Disabled HTTPS because of missing certificate and key.")
            https_enabled = False

    options_dict = {
        'log.screen': False,
        'server.thread_pool': 10,
        'server.socket_port': options['http_port'],
        'server.socket_host': options['http_host'],
        'engine.autoreload.on': False,
        'tools.encode.on': True,
        'tools.encode.encoding': 'utf-8',
        'tools.decode.on': True,
        'tools.sessions.on': True,
        'tools.sessions.storage_type': "File",
        'tools.sessions.storage_path': "sessions",
        'tools.sessions.timeout': 120,
    }

    if https_enabled:
        options_dict['server.ssl_certificate'] = https_cert
        options_dict['server.ssl_private_key'] = https_key
        protocol = "https"
    else:
        protocol = "http"

    logger.info("Starting schoolkeeper web server on %s://%s:%d/" % (protocol, options['http_host'], options['http_port']))
    cherrypy.config.update(options_dict)
    cherrypy.tools.auth = cherrypy.Tool('before_handler', webauth.check_auth)

    conf = {
        '/': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(schoolkeeper.PROG_DIR, 'data'),
            'tools.proxy.on': options['http_proxy'],
            'tools.auth.on': True,
            'tools.sessions.on': True
        },
        '/interfaces': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(schoolkeeper.PROG_DIR, 'data', 'interfaces'),
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/images': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(schoolkeeper.PROG_DIR, 'data', 'images'),
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/profileimages': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': schoolkeeper.CONFIG['IMAGEDIR'],
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/cache': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': schoolkeeper.CACHEDIR,
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/css': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(schoolkeeper.PROG_DIR, 'data', 'css'),
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/js': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(schoolkeeper.PROG_DIR, 'data', 'js'),
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(schoolkeeper.PROG_DIR, 'data', 'images', 'favicon.ico'),
            'tools.auth.on': False,
            'tools.sessions.on': False
        }
    }

    if options['http_pass'] != "":
        logger.info("Web server authentication is enabled, username is '%s'" %options['http_user'])
        conf['/'].update({
            'tools.auth.on': True,
            'tools.sessions.on': True,
            'tools.auth_basic.on': False,
            'tools.auth_basic.realm': 'schoolkeeper',
            'tools.auth_basic.checkpassword': cherrypy.lib.auth_basic.checkpassword_dict({ options['http_user']: options['http_pass']})
        })
        conf['/api'] = {'tools.auth_basic.on': False}

    # Prevent time-outs
    cherrypy.engine.timeout_monitor.unsubscribe()
    cherrypy.tree.mount(WebInterface(), str(options['http_root']), config=conf)

    cherrypy.engine.autoreload.subscribe()

    try:
        cherrypy.process.servers.check_port(str(options['http_host']), options['http_port'])
        cherrypy.server.start()
    except IOError:
        print 'Failed to start on port: %i. is something else running?' % (options['http_port'])
        sys.exit(1)

    cherrypy.server.wait()


