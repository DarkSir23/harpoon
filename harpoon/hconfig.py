import configparser
import os, sys
from harpoon import common

defaults = {
    'general':
        [
            {'option': 'applylabel', 'category': 'general', 'type': bool, 'desc': 'Use Label Directories', 'default': 'true'},
            {'option': 'defaultdir', 'category': 'general', 'type': str, 'desc': 'Local Download Location'},
            {'option': 'torrentfile_dir', 'category': 'general', 'type': str, 'desc': 'Local Torrent, NZB and Hashfile Location'},
            {'option': 'torrentclient', 'category': 'general', 'type': str, 'desc': 'Torrent Client', 'default': 'rtorrent'}
       ]
}

class config:


    def __init__(self, location):
        self.conf = configparser.SafeConfigParser()
        if not os.path.exists(location):
            self.createConfig()
        self.conf.read(location)
        self.GENERAL = {}
        self.SAB = {}
        self.PP = {}
        self.SICKRAGE = {}
        self.SONARR = {}
        self.WEB = {}
        self.RADARR = {}
        self.LIDARR = {}
        self.READARR = {}
        self.MYLAR = {}
        self.LAZYLIBRARIAN = {}
        self.PLEX = {}
        self.GENERAL['applylabel'] = self.get('general', 'applylabel', bool)
        self.GENERAL['defaultdir'] = self.get('general', 'defaultdir', str)
        self.GENERAL['torrentfile_dir'] = self.get('general', 'torrentfile_dir', str)
        self.GENERAL['torrentclient'] = self.get('general', 'torrentclient', str)
        self.GENERAL['lcmdparallel'] = self.get('general', 'lcmd_parallel', int, 2)
        self.GENERAL['lcmdsegments'] = self.get('general', 'lcmd_segments', int, 6)
        #defaultdir is the default download directory on your rtorrent client. This is used to determine if the download
        #should initiate a mirror vs a get (multiple file vs single vs directories)
        self.GENERAL['tvdir'] = self.get('label_directories', 'tvdir', str)
        self.GENERAL['moviedir'] = self.get('label_directories', 'moviedir', str)
        self.GENERAL['musicdir'] = self.get('label_directories', 'musicdir', str)
        self.GENERAL['xxxdir'] = self.get('label_directories', 'xxxdir', str)
        self.GENERAL['comicsdir'] = self.get('label_directories', 'comicsdir', str)
        self.GENERAL['bookdir'] = self.get('label_directories', 'bookdir', str)
        self.GENERAL['newextensions'] = self.get('general', 'extensions', str)

        #sabnzbd
        #sab_enable is only used for harpoonshot so it doesn't create extra sab entries ...
        self.SAB['sab_enable'] = self.get('sabnzbd', 'sab_enable', bool)
        self.SAB['sab_cleanup'] = self.get('sabnzbd', 'sab_cleanup', bool)
        self.SAB['sab_url'] = self.get('sabnzbd', 'sab_url', str)
        self.SAB['sab_apikey'] = self.get('sabnzbd', 'sab_apikey', str)

        #lftp/transfer
        self.PP['pp_host'] = self.get('post-processing', 'pp_host', str)
        self.PP['pp_sshport'] = self.get('post-processing', 'pp_sshport', int, 22)
        self.PP['pp_user'] = self.get('post-processing', 'pp_user', str)
        self.PP['pp_passwd'] = self.get('post-processing', 'pp_passwd', str)
        self.PP['pp_keyfile'] = self.get('post-processing', 'pp_keyfile', str)
        self.PP['pp_host2'] = self.get('post-processing2', 'pp_host2', str)
        self.PP['pp_sshport2'] = self.get('post-processing2', 'pp_sshport2', int, 22)
        self.PP['pp_user2'] = self.get('post-processing2', 'pp_user2', str)
        self.PP['pp_passwd2'] = self.get('post-processing2', 'pp_passwd2', str)
        self.PP['pp_keyfile2'] = self.get('post-processing2', 'pp_keyfile2', str)

        #sickrage
        self.SICKRAGE = {'sickrage_headers': {'Accept': 'application/json'},
                  'sickrage_url':   self.get('sickrage', 'url', str),
                  'sickrage_label': self.get('sickrage', 'sickrage_label', str),
                  'sickrage_delete': self.get('sickrage', 'delete', bool),
                  'sickrage_failed': self.get('sickrage', 'failed', bool),
                  'sickrage_force_next': self.get('sickrage', 'force_next', bool),
                  'sickrage_force_replace': self.get('sickrage', 'force_replace', bool),
                  'sickrage_is_priority': self.get('sickrage', 'is_priority', bool),
                  'sickrage_process_method': self.get('sickrage', 'process_method', str),
                  'sickrage_type': self.get('sickrage', 'type', str)}

        #sonarr
        self.SONARR['sonarr_headers'] = {'X-Api-Key': self.get('sonarr', 'apikey', str),
                               'Accept': 'application/json'}
        self.SONARR['sonarr_url'] = self.get('sonarr', 'url', str)
        self.SONARR['sonarr_label'] = self.get('sonarr', 'sonarr_label', str)

        if self.SONARR['sonarr_url'] is not None:
            self.GENERAL['tv_choice'] = 'sonarr'
        elif self.SICKRAGE['sickrage_url'] is not None:
            self.GENERAL['tv_choice'] = 'sickrage'
        else:
            self.GENERAL['tv_choice'] = None

        self.READARR['readarr_headers'] = {'X-Api-Key': self.get('readarr', 'apikey', str),
                               'Accept': 'application/json'}
        self.READARR['readarr_url'] = self.get('readarr', 'url', str)
        self.READARR['readarr_label'] = self.get('readarr', 'readarr_label', str)

        #webserver
        self.WEB = {
            'http_enable': self.get('webserver', 'enable', bool),
            'http_port': self.get('webserver', 'port', int),
            'http_host': self.get('webserver', 'host', str),
            'http_root': self.get('webserver', 'root', str),
            'http_user': self.get('webserver', 'user', str),
            'http_pass': self.get('webserver', 'pass', str),
            'http_proxy': self.get('webserver', 'proxy', str),
            'https_enabled': self.get('webserver', 'https_enabled', bool),
            'https_cert': self.get('webserver', 'https_cert', str),
            'https_key': self.get('webserver', 'https_key', str),
        }

        #radarr
        self.RADARR['radarr_headers'] = {'X-Api-Key': self.get('radarr', 'apikey', str),
                               'Accept': 'application/json'}
        self.RADARR['radarr_url'] = self.get('radarr', 'url', str)
        self.RADARR['radarr_label'] = self.get('radarr', 'radarr_label', str)
        self.RADARR['radarr_rootdir'] = self.get('radarr', 'radarr_rootdir', str)
        self.RADARR['radarr_keep_original_foldernames'] = self.get('radarr', 'keep_original_foldernames', bool)
        self.RADARR['dir_hd_movies'] = self.get('radarr', 'radarr_dir_hd_movies', str)
        self.RADARR['dir_sd_movies'] = self.get('radarr', 'radarr_dir_sd_movies', str)
        self.RADARR['dir_web_movies'] = self.get('radarr', 'radarr_dir_web_movies', str)
        self.RADARR['hd_movies_defs'] = ('720p', '1080p', '4k', '2160p', 'bluray', 'remux')
        self.RADARR['sd_movies_defs'] = ('screener', 'r5', 'dvdrip', 'xvid', 'dvd-rip', 'dvdscr', 'dvdscreener', 'ac3', 'webrip', 'bdrip')
        self.RADARR['web_movies_defs'] = ('web-dl', 'webdl', 'hdrip', 'webrip')

        #lidarr
        self.LIDARR['lidarr_headers'] = {'X-Api-Key': self.get('lidarr', 'apikey', str),
                               'Accept': 'application/json'}
        self.LIDARR['lidarr_url'] = self.get('lidarr', 'url', str)
        self.LIDARR['lidarr_label'] = self.get('lidarr', 'lidarr_label', str)


        #mylar
        self.MYLAR['mylar_headers'] = {'X-Api-Key': 'None', #config.self.get('mylar', 'apikey'),
                              'Accept': 'application/json'}
        self.MYLAR['mylar_apikey'] = self.get('mylar', 'apikey', str)
        self.MYLAR['mylar_url'] = self.get('mylar', 'url', str)
        self.MYLAR['mylar_label'] = self.get('mylar', 'mylar_label', str)

        #lazylibrarian
        self.LAZYLIBRARIAN['lazylibrarian_headers'] = {'Accept': 'application/json'}
        self.LAZYLIBRARIAN['lazylibrarian_apikey'] = self.get('lazylibrarian', 'apikey', str)
        self.LAZYLIBRARIAN['lazylibrarian_url'] = self.get('lazylibrarian', 'url', str)
        self.LAZYLIBRARIAN['lazylibrarian_label'] = self.get('lazylibrarian', 'lazylibrarian_label', str)

        #plex
        self.PLEX['plex_update'] = self.get('plex', 'plex_update', bool)
        self.PLEX['plex_host_ip'] = self.get('plex', 'plex_host_ip', str)
        self.PLEX['plex_host_port'] = self.get('plex', 'plex_host_port', int, 32400)
        self.PLEX['plex_login'] = self.get('plex', 'plex_login', str)
        self.PLEX['plex_password'] = self.get('plex', 'plex_password', str)
        self.PLEX['plex_token'] = self.get('plex', 'plex_token', str)


    def get(self, section, id, type=str, default=None):
        if self.conf.has_option(section, id):
            try:
                if type == bool:
                    return self.conf.getboolean(section, id)
                elif type == int:
                    return self.conf.getint(section, id)
                elif type == str:
                    return self.conf.get(section, id)
            except ValueError:
                # will be raised if option is left blank in conf, so set it to default value.
                if default:
                    return default
        if type == bool:
            return False
        elif type == int:
            return 0
        elif type == str:
            return None

    def write(self):
        pass

    def createConfig(self):
        sys.stdout.write("It looks like this is your first time running Harpoon.  We need to create a configuration file.\nPlease answering the following questions.\n")
