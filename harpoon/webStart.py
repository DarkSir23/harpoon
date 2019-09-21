import os
import sys

import cherrypy
import harpoon
from harpoon import logger
from harpoon.webServe import WebInterface
import portend

def initialize(options=None, basepath=None, parent=None):

    if options is None:
        options = {}
    https_enabled = options['https_enabled']
    https_cert = options['https_cert']
    https_key = options['https_key']
    logger.debug("Web Initializing: %s" % options)
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
        'tools.sessions.storage_path': os.path.join(basepath, "sessions"),
        'tools.sessions.timeout': 120,
        'tools.sessions.clean_freq': 240,
        # 'engine.timeout_monitor.on': False,
    }
    if https_enabled:
        options_dict['server.ssl_certificate'] = https_cert
        options_dict['server.ssl_private_key'] = https_key
        protocol = "https"
    else:
        protocol = "http"
    logger.debug("Options: %s" % options_dict)
    logger.info("Starting harpoon web server on %s://%s:%d/" % (protocol, options['http_host'], options['http_port']))
    cherrypy.config.update(options_dict)
    cherrypy.log.access_log.propagate = False
    logger.debug('DataDir: %s' % basepath)
    conf = {
        '/': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(basepath, 'data'),
            'tools.proxy.on': options['http_proxy'],
            'tools.auth.on': False,
            'tools.sessions.on': True
        },
        '/interfaces': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(basepath, 'data', 'interfaces'),
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/images': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(basepath, 'data', 'images'),
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/css': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(basepath, 'data', 'css'),
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/js': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(basepath, 'data', 'js'),
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(basepath, 'data', 'images', 'favicon.ico'),
            'tools.auth.on': False,
            'tools.sessions.on': False
        }
    }

    if options['http_pass'] != "":
        logger.info("Web server authentication is enabled, username is '%s'" %options['http_user'])
        conf['/'].update({
            'tools.auth.on': True,
            'tools.sessions.on': True,
            'tools.auth_basic.on': True,
            'tools.auth_basic.realm': 'harpoon',
            'tools.auth_basic.checkpassword': cherrypy.lib.auth_basic.checkpassword_dict({ options['http_user']: options['http_pass']})
        })
        conf['/api'] = {'tools.auth_basic.on': False}
    logger.debug('config: %s' % conf)
    # Prevent time-outs
    try:
        # cherrypy.engine.timeout_monitor.unsubscribe()
        cherrypy.tree.mount(WebInterface(parent=parent), str(options['http_root']), config=conf)
        cherrypy.engine.autoreload.subscribe()
        portend.Checker().assert_free(str(options['http_host']), options['http_port'])
        cherrypy.server.start()

    except IOError:
        print('Failed to start on port: %i. is something else running?' % (options['http_port']))
        sys.exit(1)
    except Exception as e:
        print('Error: %s' % e)
        sys.exit(1)
    cherrypy.server.wait()


