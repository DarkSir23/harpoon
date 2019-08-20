from harpoon import config, logger
import json
import torrent_parser
import os
import fnmatch



def info(hash=None, label=None, mode=None, filename=None):
    if all([filename, label]):
        hashfile = os.path.join(config.GENERAL['torrentfile_dir'], label, filename)
    elif all([hash, label, mode]):
        hashfile = os.path.join(config.GENERAL['torrentfile_dir'], label, hash + '.' + mode)
    elif all([hash, label]):
        searchfolder = os.path.join(config.GENERAL['torrentfile_dir'], label)
        logger.debug('sd: %s' % searchfolder)
        hashfile = None
        for fn in os.listdir(searchfolder):
            if fnmatch.fnmatch(fn, hash + '.*'):
                hashfile = os.path.join(searchfolder, fn)
                logger.debug('hf: %s' % hashfile)
    else:
        hashfile = None
    if hashfile and os.path.exists(hashfile):
        hashtype = 'hash'
        logger.debug("HashFile: %s" % hashfile)
        try:
            hashinfo = json.load(open(hashfile))
        except:
            hashtype = 'unknown'
        if hashtype == 'unknown':
            try:
                hashinfo = torrent_parser.parse_torrent_file(hashfile)
                hashinfo['name'] = hashinfo['info']['name']
            except:
                hashtype = 'nzb'
                hashinfo = {
                    'name': 'Manually Added NZB File'
                }
        if 'name' not in hashinfo.keys():
            if 'sourceTitle' in hashinfo.keys():
                hashinfo['name'] = hashinfo['sourceTitle']
            elif 'BookName' in hashinfo.keys():
                hashinfo['name'] = hashinfo['BookName']
            elif 'mylar_release_name' in hashinfo.keys():
                hashinfo['name'] = hashinfo['mylar_release_name']
            elif 'mylar_release_nzbname' in hashinfo.keys():
                hashinfo['name'] = hashinfo['mylar_release_nzbname']
            elif 'Title' in hashinfo.keys() and 'AuxInfo' in hashinfo.keys():
                hashinfo['name'] = '%s %s' % (hashinfo['Title'],hashinfo['AuxInfo'])
            elif 'lidarr_release_title' in hashinfo.keys():
                hashinfo['name'] = hashinfo['lidarr_release_title']
            elif 'radarr_release_title' in hashinfo.keys():
                hashinfo['name'] = hashinfo['radarr_release_title']
            elif 'sonarr_release_title' in hashinfo.keys():
                hashinfo['name'] = hashinfo['sonarr_release_title']
            else:
                hashinfo['name'] = 'Unknown'
        logger.debug("HashInfo: %s" % hashinfo)
        return hashinfo
    else:
        return {'name': 'Hash File Not Found: %s' % hashfile}

def remove(hash=None, label=None, mode=None, filename=None):
    if all([filename, label]):
        hashfile = os.path.join(config.GENERAL['torrentfile_dir'], label, filename)
    elif all([hash, label, mode]):
        hashfile = os.path.join(config.GENERAL['torrentfile_dir'], label, hash + '.' + mode)
    elif all([hash, label]):
        searchfolder = os.path.join(config.GENERAL['torrentfile_dir'], label)
        logger.debug('sd: %s' % searchfolder)
        hashfile = None
        for fn in os.listdir(searchfolder):
            if fnmatch.fnmatch(fn, hash + '.*'):
                hashfile = os.path.join(searchfolder, fn)
                logger.debug('hf: %s' % hashfile)
    else:
        hashfile = None
    if hashfile and os.path.exists(hashfile):
        os.remove(hashfile)
        return True
    else:
        return False
