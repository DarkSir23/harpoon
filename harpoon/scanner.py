from harpoon import config, logger, rtorrent, sabnzbd
from harpoon import HQUEUE
from harpoon import hashfile as hf
import json, requests, re, bencode, hashlib

import os

class Scanner:

    def __init__(self, queue, working_hash):
        # if queue.empty():
        #    logger.info('Nothing to do')
        #    return
        self.queue = queue
        self.current_hash = working_hash

    def scan(self):
        logger.info('SCANNER: Running New File Scan')
        extensions = ['.file', '.hash', '.torrent', '.nzb']
        for (dirpath, dirnames, filenames) in os.walk(config.GENERAL['torrentfile_dir'], followlinks=True):
            for f in filenames:
                ll_type = ''
                if any([f.endswith(ext) for ext in extensions]):
                    client = None
                    if f.endswith('.file'):
                        # history only works with sonarr/radarr/lidarr...
                        # if any([f[-11:] == 'sonarr', f[-11:] == 'radarr']):
                        hash, client = self.history_poll(f[:-5])
                        logger.info('Client: %s' % client)
                        logger.info('hash:' + str(hash))
                        logger.info('working_hash:' + str(self.current_hash))
                        # dupchk = [x for x in self.queue.ckqueue() if x['hash'] == hash]
                        dupchk = hash in list(HQUEUE.ckqueue().keys())
                        if all([hash is not None, not dupchk]):
                            logger.info('Adding : ' + f + ' to queue.')

                            if 'sonarr' in f[-11:]:
                                label = config.SONARR['sonarr_label']
                            elif 'radarr' in f[-11:]:
                                label = config.RADARR['radarr_label']
                            elif 'mylar' in f[-10:]:
                                label = config.MYLAR['mylar_label']
                            elif 'sickrage' in f[-13:]:
                                label = config.SICKRAGE['sickrage_label']
                            elif 'lidarr' in f[-11:]:
                                label = config.LIDARR['lidarr_label']
                            else:
                                # label = os.path.basename(dirpath)
                                label = None
                            if client:
                                self.queue.put({'mode': 'hash',
                                                'item': hash,
                                                'label': label,
                                                'client': client})
                            else:
                                self.queue.put({'mode': 'hash',
                                                'item': hash,
                                                'label': label})
                            hashinfo = hf.info(filename=f, label=label)
                            self.queue.ckupdate(hash, {'hash': hash, 'name': hashinfo['name'],
                                                       'stage': 'to-do', 'status': 'Waiting', 'label': label})

                            if label is not None:
                                fpath = os.path.join(config.GENERAL['torrentfile_dir'], label, f)
                            else:
                                fpath = os.path.join(config.GENERAL['torrentfile_dir'], f)

                            try:
                                os.remove(fpath)
                                logger.info('Succesfully removed file : ' + fpath)
                            except:
                                logger.warn('Unable to remove file : ' + fpath)
                        else:
                            logger.warn(
                                'HASH is already present in queue - but has not been converted to hash for some reason. Ignoring at this time cause I dont know what to do.')
                            logger.warn(self.queue.ckqueue())

                    else:
                        # here we queue it up to send to the client and then monitor.
                        if f.endswith('.torrent'):
                            client = 'rtorrent'  # Assumes rtorrent, if we add more torrent clients, this needs to change.
                            subdir = os.path.basename(dirpath)
                            # torrents to snatch should be subfolders in order to apply labels if required.
                            fpath = os.path.join(config.GENERAL['torrentfile_dir'], subdir, f)
                            logger.info('label to be set to : ' + str(subdir))
                            logger.info('Filepath set to : ' + str(fpath))
                            tinfo = rtorrent.RTorrent(file=fpath, add=True, label=subdir)
                            if not tinfo:
                                logger.debug('Unable to load .torrent file')
                                return False
                            torrent_info = tinfo.main()
                            logger.info(torrent_info)
                            if torrent_info:
                                hashfile = str(torrent_info['hash']) + '.hash'
                                os.rename(fpath, os.path.join(config.GENERAL['torrentfile_dir'], subdir, hashfile))
                            else:
                                logger.warn('something went wrong. Skipping torrent file.')
                                continue
                            queuefile = hashfile[:-5]
                            hashfile = hashfile[:-5]
                            mode = 'hash'
                            label = torrent_info['label']
                        elif f.endswith('.nzb'):
                            client = 'sabnzbd'  # Assumes sab, if we add more nbz clients, this needs to change
                            subdir = os.path.basename(dirpath)
                            fpath = os.path.join(config.GENERAL['torrentfile_dir'], subdir, f)
                            logger.info('Label to be set to : ' + str(subdir))
                            logger.info('Filepath set to : ' + str(fpath))
                            sab_params = {}
                            sab_params['mode'] = 'addfile'
                            sab_params['cat'] = subdir
                            sab_params['apikey'] = config.SAB['sab_apikey']
                            nzb_connection = sabnzbd.SABnzbd(params=sab_params, saburl=config.SAB['sab_url'])
                            nzb_info = nzb_connection.sender(files={'name': open(fpath, 'rb')})
                            mode = 'hash'
                            label = str(subdir)
                            logger.debug('SAB Response: %s' % nzb_info)
                            if nzb_info:
                                hashfile = str(nzb_info['nzo_id']) + '.hash'
                                os.rename(fpath, os.path.join(config.GENERAL['torrentfile_dir'], subdir, hashfile))
                            else:
                                logger.warn('something went wrong')
                            queuefile = hashfile[:-5]
                            hashfile = hashfile[:-5]
                        else:
                            label = None
                            if 'mylar' in f[-10:]:
                                label = config.MYLAR['mylar_label']
                                hashfile = f[:-11]
                                queuefile = f[:-5]
                            elif 'sickrage' in f[-13:]:
                                label = config.SICKRAGE['sickrage_label']
                                hashfile = f[:-14]
                                queuefile = f[:-5]
                            elif 'lazylibrarian' in f[-18:]:
                                label = config.LAZYLIBRARIAN['lazylibrarian_label']
                                hashfile = f[:-19]
                                queuefile = f[:-5]
                            else:
                                hashfile = f[:-5]
                                queuefile = f[:-5]
                            dirp = os.path.basename(dirpath)
                            if label is None and os.path.basename(config.GENERAL['torrentfile_dir']) != dirp:
                                label = dirp
                            mode = f[-4:]
                            actualfile = os.path.join(dirpath, f)
                            try:
                                filecontent = json.load(open(actualfile))
                                if filecontent:
                                    if 'data' in list(filecontent.keys()):
                                        if 'downloadClient' in list(filecontent['data'].keys()):
                                            client = filecontent['data']['downloadClient'].lower()
                                    elif 'Source' in list(filecontent.keys()):
                                        client = filecontent['Source'].lower()
                                    elif 'mylar_client' in list(filecontent.keys()):
                                        client = filecontent['mylar_client'].lower()
                                    else:
                                        client = None
                                    if 'AuxInfo' in list(filecontent.keys()):
                                        ll_type = filecontent['AuxInfo'].lower()
                                        if ll_type == 'ebook':
                                            ll_type = 'eBook'
                                        elif ll_type == 'audiobook':
                                            ll_type = 'AudioBook'
                                        else:
                                            ll_type = "Magazine"
                                else:
                                    client = None
                            except Exception as e:
                                try:
                                    with open(actualfile) as unknown_file:
                                        c = unknown_file.read(1)
                                        if c == '<':
                                            client = 'sabnzbd'
                                        else:
                                            client = 'rtorrent'
                                except Exception as e:
                                    client = 'rtorrent'  # Couldn't read file, assume it's a torrent.

                        # test here to make sure the file isn't being worked on currently & doesnt exist in queue already
                        # dupchk = [x for x in HQUEUE.ckqueue() if x['hash'] == hashfile]
                        if hashfile in list(HQUEUE.ckqueue().keys()):
                            dupchk = HQUEUE.ckqueue()[hashfile]
                        else:
                            dupchk = None
                        duplist = []
                        if dupchk:
                            if dupchk['stage'] == 'completed':
                                try:
                                    logger.info('Status is now completed - forcing removal of HASH from queue.')
                                    # self.queue.pop(xc['hash']) -- This needs fixed.   Queue has no pop method
                                except Exception as e:
                                    logger.warn(
                                        'Unable to locate hash in queue. Was already removed most likely. This was the error returned: %s' % e)
                                    continue
                            else:
                                pass
                                # logger.info('HASH already exists in queue in a status of ' + xc['stage'] + ' - avoiding duplication: ' + hashfile)
                        else:
                            logger.info('HASH not in queue - adding : ' + hashfile)
                            logger.info('Client: %s' % client)
                            logger.info('Queuefile: %s' % queuefile)
                            logger.info('LL_Type: %s' % ll_type)
                            hashinfo = hf.info(queuefile, label=label, mode=mode)
                            self.queue.ckupdate(hashfile, {'hash': hashfile,
                                                           'stage': 'to-do',
                                                           'name': hashinfo['name'],
                                                           'status': 'Waiting',
                                                           'label': label,
                                                           'll_type': ll_type, })
                            if client:
                                self.queue.put({'mode': mode,
                                                'item': hashfile,
                                                'label': label,
                                                'client': client})
                            else:
                                self.queue.put({'mode': mode,
                                                'item': hashfile,
                                                'label': label})
                            hashfile = str(hashfile) + '.hash'
                            if label is not None:
                                fpath = os.path.join(config.GENERAL['torrentfile_dir'], label, f)
                                npath = os.path.join(config.GENERAL['torrentfile_dir'], label, hashfile)
                            else:
                                fpath = os.path.join(config.GENERAL['torrentfile_dir'], f)
                                npath = os.path.join(config.GENERAL['torrentfile_dir'], hashfile)

                            if mode != 'hash':
                                try:
                                    os.rename(fpath, npath)
                                    logger.info('Succesfully renamed file to ' + npath)
                                except Exception as e:
                                    logger.warn('[%s] Unable to rename file %s to %s' % (e, fpath, npath))
                                    continue


    def history_poll(self, torrentname):
        path = config.GENERAL['torrentfile_dir']
        if 'sonarr' in torrentname[-6:]:
            historyurl = config.SONARR['sonarr_url']
            headers = config.SONARR['sonarr_headers']
            label = config.SONARR['sonarr_label']
            url = historyurl + '/api/history'
            mode = 'sonarr'
        elif 'radarr' in torrentname[-6:]:
            historyurl = config.RADARR['radarr_url']
            headers = config.RADARR['radarr_headers']
            label = config.RADARR['radarr_label']
            url = historyurl + '/api/history'
            mode = 'radarr'
        elif 'lidarr' in torrentname[-6:]:
            historyurl = config.LIDARR['lidarr_url']
            headers = config.LIDARR['lidarr_headers']
            label = config.LIDARR['lidarr_label']
            url = historyurl + '/api/v1/history'

        torrentname = torrentname[:-7]
        payload = {'pageSize': 1000,
                   'page': 1,
                   'filterKey': 'eventType',
                   'filterValue': 1,
                   'sortKey': 'date',
                   'sortDir': 'desc'}

        logger.info('Quering against history now: %s' % payload)
        r = requests.get(url, params=payload, headers=headers)
        logger.info(r.status_code)
        result = r.json()
        hash = None
        client = None
        logger.info(torrentname)
        for x in result['records']:
            # logger.info(x)
            if self.filesafe(torrentname.lower()) == self.filesafe(x['sourceTitle'].lower()):
                hash = x['downloadId']
                client = x['data']['downloadClient'].lower()
                info = x
                logger.info('file located as HASH: %s' % hash)
                break

        if hash is not None:

            filepath = os.path.join(path, label, str(hash) + '.hash')

            # create empty file with the given filename and update the mtime
            with open(filepath, 'w') as outfile:
                json.dump(info, outfile)

            logger.info("wrote to snatch queue-directory %s" % filepath)
        #            try:
        #                os.remove(os.path.join(path, torrentname + '.' + mode + '.file'))
        #            except:
        #                logger.warn('file doesnt exist...ignoring deletion of .file remnant')

        else:
            logger.info('No hash discovered - this requires the torrent name, NOT the filename')

        return hash, client


    def get_the_hash(self, filepath):
        # Open torrent file
        torrent_file = open(filepath, "rb")
        metainfo = bencode.decode(torrent_file.read())
        info = metainfo['info']
        thehash = hashlib.sha1(bencode.encode(info)).hexdigest().upper()
        logger.info('Hash: ' + thehash)
        return thehash


    def get_free_space(self, folder, min_threshold=100000000):
        # threshold for minimum amount of freespace available (#100mb)
        st = os.statvfs(folder)
        dst_freesize = st.f_bavail * st.f_frsize
        logger.debug('[FREESPACE-CHECK] %s has %s free' % (folder, self.sizeof_fmt(dst_freesize)))
        if min_threshold > dst_freesize:
            logger.warn('[FREESPACE-CHECK] There is only %s space left on %s' % (dst_freesize, folder))
            return False
        else:
            return True


    def sizeof_fmt(self, num, suffix='B'):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)


    def filesafe(self, name):
        import unicodedata

        try:
            name = name.decode('utf-8')
        except:
            pass

        if '\u2014' in name:
            name = re.sub('\u2014', ' - ', name)
        try:
            u_name = str(unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').strip())
        except TypeError:
            u_name = str(name.encode('ASCII', 'ignore').strip())

        name_filesafe = re.sub('[\:\'\"\,\?\!\\\]', '', u_name)
        name_filesafe = re.sub('[\/\*]', '-', name_filesafe)

        return name_filesafe
