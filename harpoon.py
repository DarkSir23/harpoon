#!/usr/bin/python
#  This file is part of Harpoon.
#
#  Harpoon is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Harpoon is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Harpoon.  If not, see <http://www.gnu.org/licenses/>.

import sys, os
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'lib'))

import optparse
import re
import time
import json
import requests
import socket as checksocket
from contextlib import closing
import hashlib
import bencode
import threading
import traceback

import harpoon
from harpoon import rtorrent, sabnzbd, unrar, logger, sonarr, radarr, plex, sickrage, mylar, lazylibrarian, lidarr, webStart, sftp
from harpoon import HQUEUE as HQUEUE
from harpoon import config, watcher
from harpoon.scanner import Scanner

from harpoon import CURRENT_DOWNFOLDER, CURRENT_DOWNLOAD
from harpoon.threadedtcp import ThreadedTCPRequestHandler, ThreadedTCPServer


from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers import interval
#global variables
#this is required here to get the log path below


class QueueR(object):


    def __init__(self):

        #accept parser options for cli usage
        description = ("Harpoon. "
                       "A python-based CLI daemon application that will monitor a remote location "
                       "(ie.seedbox) & then download from the remote location to the local "
                       "destination which is running an automation client. "
                       "Unrar, cleanup and client-side post-processing as required. "
                       "Also supports direct dropping of .torrent files into a watch directory. "
                       "Supported client-side applications: "
                       "Sonarr, Radarr, Lidarr, Mylar, LazyLibrarian, SickRage")
        self.server = None
        self.server_thread = None
        self.ARGS = sys.argv[:]
        self.FULL_PATH = os.path.abspath(sys.executable)
        parser = optparse.OptionParser(description=description)
        parser.add_option('-a', '--add', dest='add', help='Specify a filename to snatch from specified torrent client when monitor is running already.')
        parser.add_option('-s', '--hash', dest='hash', help='Specify a HASH to snatch from specified torrent client.')
        parser.add_option('-l', '--label', dest='label', help='For use ONLY with -t, specify a label that the HASH has that harpoon can check against when querying the torrent client.')
        parser.add_option('-t', '--exists', dest='exists', action='store_true', help='In combination with -s (Specify a HASH) & -l (Specify a label) with this enabled and it will not download the torrent (it must exist in the designated location already')
        parser.add_option('-f', '--file', dest='file', help='Specify an exact filename to snatch from specified torrent client. (Will do recursive if more than one file)')
        parser.add_option('-i', '--issueid', dest='issueid', help='In conjunction with -s,-l allows you to specify an exact issueid post-process against (MYLAR ONLY).')
        parser.add_option('-b', '--partial', dest='partial', action='store_true', help='Grab the torrent regardless of completion status (for cherrypicked torrents)')
        parser.add_option('-m', '--monitor', dest='monitor', action='store_true', help='Monitor a designated file location for new files to harpoon.')
        parser.add_option('-d', '--daemon', dest='daemon', action='store_true', help='Daemonize the complete program so it runs in the background.')
        parser.add_option('-p', '--pidfile', dest='pidfile', help='specify a pidfile location to store pidfile for daemon usage.')
        (options, args) = parser.parse_args()

        self.restart = False

        if options.daemon:
            if sys.platform == 'win32':
                print("Daemonize not supported under Windows, starting normally")
                self.daemon = False
            else:
                self.daemon = True
                options.monitor = True
        else:
            self.daemon = False
        if options.monitor:
            self.monitor = True
        else:
            self.monitor = False

        if options.exists:
            self.exists = True
        else:
            self.exists = False

        if options.issueid:
            self.issueid = options.issueid
        else:
            self.issueid = None

        if options.partial:
            self.partial = True
        else:
            self.partial = False

        if options.pidfile:
            self.pidfile = str(options.pidfile)

            # If the pidfile already exists, harpoon may still be running, so exit
            if os.path.exists(self.pidfile):
                sys.exit("PID file '" + self.pidfile + "' already exists. Exiting.")

            # The pidfile is only useful in daemon mode, make sure we can write the file properly
            if self.daemon:
                self.createpid = True
                try:
                    open(self.pidfile, 'w').write("pid\n")
                except IOError as e:
                    raise SystemExit("Unable to write PID file: %s [%d]" % (e.strerror, e.errno))
            else:
                self.createpid = False
                logger.warn("Not running in daemon mode. PID file creation disabled.")

        else:
            self.pidfile = None
            self.createpid = False

        self.file = options.file
        self.hash = options.hash

        self.working_hash = None
        self.hash_reload = False
        self.not_loaded = 0

        self.CURRENT_DOWNFOLDER = CURRENT_DOWNFOLDER


        self.extensions = ['mkv', 'avi', 'mp4', 'mpg', 'mov', 'cbr', 'cbz', 'flac', 'mp3', 'alac', 'epub', 'mobi', 'pdf', 'azw3', '4a', 'm4b', 'm4a', 'lit']
        if config.GENERAL['newextensions'] is not None:
            for x in newextensions.split(","):
                if x != "":
                    self.extensions.append(x)

        if options.daemon:
            self.daemonize()

        logger.info("Initializing background worker thread for queue manipulation.")

        #for multiprocessing (would cause some problems)
        #self.SNQUEUE = Queue()
        #harpoon.SNPOOL = Process(target=self.worker_main, args=(self.SNQUEUE,))
        #harpoon.SNPOOL.daemon = True
        #harpoon.SNPOOL.start()






        if self.daemon is True:
            #if it's daemonized, fire up the soccket listener to listen for add requests.
            logger.info('[HARPOON] Initializing the API-AWARE portion of Harpoon.')
            #socketlisten.listentome(self.SNQUEUE,)
            #sockme = threading.Thread(target=socketlisten.listentome, args=(self.SNQUEUE,))
            #sockme.setdaemon = True
            #sockme.start()
            HOST, PORT = "localhost", 50007
            port_open = True
            while port_open:
                with closing(checksocket.socket(checksocket.AF_INET, checksocket.SOCK_STREAM)) as sock:
                    res = sock.connect_ex((HOST, PORT))
                    if res == 0:
                        pass
                    else:
                        logger.debug('[API] Socket available.  Continuing.')
                        port_open = False
                time.sleep(2)
            self.server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
            logger.debug('Class Server: %s' % self.server)
            server_thread = threading.Thread(target=self.server.serve_forever)
            logger.debug('Server Thread: %s' % server_thread)
            server_thread.daemon = True
            server_thread.start()
            logger.info('Started...')

        self.HQUEUE = HQUEUE

        logger.info('Web: %s' % config.WEB)
        if config.WEB['http_enable']:
            logger.debug("Starting web server")
            webStart.initialize(options=config.WEB, basepath=harpoon.DATADIR, parent=self)

        #for threading
        self.SNPOOL = threading.Thread(target=self.worker_main, args=(self.HQUEUE,))
        self.SNPOOL.setdaemon = True
        self.SNPOOL.start()
        harpoon.MAINTHREAD = threading.current_thread()
        logger.debug("Threads: %s" % threading.enumerate())

        logger.info('TV-Client set to : %s' % config.GENERAL['tv_choice'])


        if self.monitor:
            # self.SCHED = BackgroundScheduler()
            # logger.info('Setting directory scanner to monitor %s every 2 minutes for new files to harpoon' % config.GENERAL['torrentfile_dir'])
            # self.scansched = Scanner(self.HQUEUE, self.working_hash)
            # job = self.SCHED.add_job(func=self.scansched.scan, trigger=interval.IntervalTrigger(minutes=2))
            # # start the scheduler now
            # self.SCHED.start()
            # #run the scanner immediately on startup.
            # self.scansched.scan()
            self.scanner = Scanner(self.HQUEUE, self.working_hash)
            self.watcher = watcher.Watcher(self.scanner)
            # Run for the first time
            self.scanner.scan()

        elif self.file is not None:
            logger.info('Adding file to queue via FILE %s [label:%s]' % (self.file, options.label))
            self.HQUEUE.put({'mode':  'file-add',
                             'item':  self.file,
                             'label': options.label})
        elif self.hash is not None:
            logger.info('Adding file to queue via HASH %s [label:%s]' % (self.hash, options.label))
            self.HQUEUE.put({'mode':  'hash-add',
                             'item':  self.hash,
                             'label': options.label})
        else:
            logger.info('Not enough information given - specify hash / filename')
            return



        if options.add:
            logger.info('Adding file to queue %s' % options.add)
            self.HQUEUE.put(options.add)
            return



        while True:
            if self.restart:
                logger.info('Restarting')
                try:
                    # popen_list = [self.FULL_PATH]
                    # popen_list += self.ARGS
                    # logger.debug("Args: %s" % (popen_list))
                    # if self.server:
                    #     self.server.shutdown()
                    #     self.server.server_close()
                    #     while not self.server.is_shut_down():
                    #         logger.debug("Running? %s" % self.server.is_running())
                    #         time.sleep(1)
                    # os.remove(self.pidfile)
                    # po = subprocess.Popen(popen_list, cwd=os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    # logger.debug("Process: %s" % po.poll())
                    # os._exit(0)
                    os.execl(sys.executable, sys.executable, *sys.argv)
                except Exception as e:
                    logger.debug("Failed to restart: %s" % e)
            else:
                self.worker_main(self.HQUEUE)

    def worker_main(self, queue):

        while True:
            if self.monitor:
                # if not len(self.SCHED.get_jobs()):
                #     logger.debug('Restarting Scanner Job')
                #     job = self.SCHED.add_interval_job(func=self.scansched.scan, minutes=2)
                #     self.SCHED.start()
                if not self.watcher.observer.isAlive():
                    self.watcher.observer.join()
            if self.hash_reload is False:
                if queue.empty():
                    #do a time.sleep here so we don't use 100% cpu
                    time.sleep(5)
                    return #continue
                item = queue.get(True)
                if item['mode'] == 'exit':
                    logger.info('Cleaning up workers for shutdown')
                    return self.shutdown()

                if item['item'] == self.working_hash and item['mode'] == 'current':
                    #file is currently being processed...ignore.
                    logger.warn('hash item from queue ' + item['item'] + ' is already being processed as [' + str(self.working_hash) + ']')
                    return #continue
                else:
                    logger.info('_hash to [' + item['item'] + ']')
                    queue.ckupdate(item['item'], {'stage': 'current'})

                    # ck = [x for x in queue.ckqueue() if x['hash'] == item['item']]
                    # if not ck:
                    #     queue.ckappend({'hash':   item['item'],
                    #                     'stage':  'current'})
                    self.working_hash = item['item']

                logger.info('[' + item['mode'] +'] Now loading from queue: %s (%s items remaining in queue)' % (item['item'], queue.qsize()))
            else:
                self.hash_reload = False

            # Check for client type.  If no client set, assume rtorrent.

            if 'client' not in list(item.keys()):
                item['client'] = 'rtorrent'

            #Sonarr stores torrent names without the extension which throws things off.
            #use the below code to reference Sonarr to poll the history and get the hash from the given torrentid
            if item['client'] == 'sabnzbd':
                sa_params = {}
                sa_params['nzo_id'] = item['item']
                sa_params['apikey'] = config.SAB['sab_apikey']
                try:
                    sab = sabnzbd.SABnzbd(params=sa_params, saburl=config.SAB['sab_url'])
                    snstat = sab.query()

                except Exception as e:
                    logger.info('ERROR 307 - %s' %e)
                    snstat = None
            else:
                try:
                    if any([item['mode'] == 'file', item['mode'] == 'file-add']):
                        logger.info('sending to rtorrent as file...')
                        rt = rtorrent.RTorrent(file=item['item'], label=item['label'], partial=self.partial)
                    else:
                        logger.info('checking rtorrent...')
                        rt = rtorrent.RTorrent(hash=item['item'], label=item['label'])
                    snstat = rt.main()
                except Exception as e:
                    logger.info('ERROR 319 - %s' % e)
                    logger.debug('Traceback: %s' % traceback.format_exc())
                    snstat = None

                #import torrent.clients.deluge as delu
                #dp = delu.TorrentClient()
                #if not dp.connect():
                #    logger.warn('Not connected to Deluge!')
                #snstat = dp.get_torrent(torrent_hash)


            logger.info('---')
            logger.info(snstat)
            logger.info('---')

            if (snstat is None or not snstat['completed']) and self.partial is False:
                if snstat is None:
                    ckqueue_entry = queue.ckqueue()[item['item']]
                    if 'retry_count' in list(ckqueue_entry.keys()):
                        retry_count = ckqueue_entry['retry_count'] + 1
                    else:
                        retry_count = 1
                    logger.warn('[Current attempt: ' + str(retry_count) + '] Cannot locate torrent on client. Ignoring this result for up to 5 retries / 2 minutes')
                    if retry_count > 5:
                        logger.warn('Unable to locate torrent on client. Removing item from queue.')
                        try:
                            os.remove(os.path.join(config.GENERAL['torrentfile_dir'], item['label'],
                                                   item['item'] + '.' + item['mode']))
                            logger.info('[HARPOON] File removed')
                        except:
                            logger.warn(
                                '[HARPOON] Unable to remove file from snatch queue directory [' + item['item'] + '.' +
                                item['mode'] + ']. You should delete it manually to avoid re-downloading')
                        queue.ckupdate(item['item'], {'stage': 'failed', 'status': 'Failed (Could not find on client)'})
                        self.not_loaded = 0
                        continue
                    else:
                        queue.put({'mode': item['mode'],
                                   'item': item['item'],
                                   'label': item['label'],
                                   'client': item['client']})
                        queue.ckupdate(item['item'],{'stage': 'to-do', 'status': 'Not found in client. Attempt %s' % retry_count, 'retry_count': retry_count})
                else:
                    #we already popped the item out of the queue earlier, now we need to add it back in.
                    queue.put({'mode':  item['mode'],
                               'item':  item['item'],
                               'label': item['label'],
                               'client': item['client']})
                    queue.ckupdate(item['item'],{'stage': 'to-do', 'status': 'Still downloading in client'})
                    if queue.qsize() > 4:
                        delay = 5
                    elif queue.qsize() > 2:
                        delay = 15
                    else:
                        delay = 30
                    logger.info('Still downloading in client....let\'s try again in %s seconds.' % delay)
                    time.sleep(delay)
            elif snstat and 'failed' in list(snstat.keys()) and snstat['failed']:
                logger.info('Torrent or NZB returned status of "failed".  Removing queue item.')
                if item['client'] == 'sabnzbd' and config.SAB['sab_cleanup']:
                    sa_params = {}
                    sa_params['nzo_id'] = item['item']
                    sa_params['apikey'] = config.SAB['sab_apikey']
                    try:
                        sab = sabnzbd.SABnzbd(params=sa_params, saburl=config.SAB['sab_url'])
                        snstat = sab.cleanup()
                    except Exception as e:
                        logger.info('ERROR 379 - %s' % e)
                        snstat = None
                # try:
                #     os.remove(os.path.join(config.GENERAL['torrentfile_dir'], item['label'],
                #                            item['item'] + '.' + item['mode']))
                #     logger.info('[HARPOON] File removed')
                # except:
                #     logger.warn(
                #         '[HARPOON] Unable to remove file from snatch queue directory [' + item['item'] + '.' + item[
                #             'mode'] + ']. You should delete it manually to avoid re-downloading')
                queue.ckupdate(item['item'], {'stage': 'failed', 'status': 'Failed (%s returned a failure)' % item['client']})
            else:
                if self.exists is False:
                    import shlex, subprocess
                    logger.info('Torrent is completed and status is currently Snatched. Attempting to auto-retrieve.')
                    tmp_script = os.path.join(harpoon.DATADIR, 'snatcher', 'getlftp.sh')
                    with open(tmp_script, 'r') as f:
                        first_line = f.readline()

                    if tmp_script.endswith('.sh'):
                        shell_cmd = re.sub('#!', '', first_line)
                        if shell_cmd == '' or shell_cmd is None:
                            shell_cmd = '/bin/bash'
                    else:
                        shell_cmd = sys.executable

                    curScriptName = shell_cmd + ' ' + tmp_script
                    # curScriptName = shell_cmd + ' ' + tmp_script.decode("string_escape")
                    if snstat['mirror'] is True:
                        downlocation = snstat['folder']
                        # logger.info('trying to convert : %s' % snstat['folder'])
                        # try:
                        #     downlocation = snstat['folder'].decode('utf-8')
                        #     logger.info('[HARPOON] downlocation: %s' % downlocation)
                        # except Exception as e:
                        #     logger.info('utf-8 error: %s' % e)
                    else:
                        try:
                            tmpfolder = snstat['folder']
                            tmpname = snstat['name']
                            # tmpfolder = snstat['folder'].encode('utf-8')
                            # tmpname = snstat['name'].encode('utf-8')
                            # logger.info('[UTF-8 SAFETY] tmpfolder, tmpname: %s' % os.path.join(tmpfolder, tmpname))
                        except:
                            pass

                        logger.info('snstat[files]: %s' % snstat['files'][0])
                        #if it's one file in a sub-directory vs one-file in the root...
                        #if os.path.join(snstat['folder'], snstat['name']) != snstat['files'][0]:
                        if os.path.join(tmpfolder, tmpname) != snstat['files'][0]:
                            # downlocation = snstat['files'][0].decode('utf-8')
                            downlocation = snstat['files'][0]
                        else:
                            #downlocation = os.path.join(snstat['folder'], snstat['files'][0])
                            downlocation = os.path.join(tmpfolder, snstat['files'][0])
                            # downlocation = os.path.join(tmpfolder, snstat['files'][0].decode('utf-8'))
                            # downlocation = re.sub(",", "\\,", downlocation)

                    labelit = None
                    if config.GENERAL['applylabel'] is True:
                        if any([snstat['label'] != 'None', snstat['label'] is not None]):
                            labelit = snstat['label']

                    if snstat['multiple'] is None:
                        multiplebox = '0'
                    else:
                        multiplebox = snstat['multiple']

                    harpoon_env = os.environ.copy()

                    harpoon_env['conf_location'] = harpoon.CONF_LOCATION
                    harpoon_env['harpoon_location'] = re.sub("'", "\\'", downlocation)
                    harpoon_env['harpoon_location'] = re.sub("!", "\\!", downlocation)
                    harpoon_env['harpoon_label'] = labelit
                    harpoon_env['harpoon_applylabel'] = str(config.GENERAL['applylabel']).lower()
                    harpoon_env['harpoon_defaultdir'] = config.GENERAL['defaultdir']
                    harpoon_env['harpoon_multiplebox'] = multiplebox
                    harpoon_env['download_total'] = snstat['total_filesize']

                    if config.GENERAL['applylabel'] is True:
                        self.CURRENT_DOWNFOLDER = os.path.join(config.GENERAL['defaultdir'], labelit)
                    else:
                        self.CURRENT_DOWNFOLDER = config.GENERAL['defaultdir']

                    # if any([downlocation.endswith(ext) for ext in self.extensions]) or snstat['mirror'] is False:
                    logger.debug('[HARPOON] Ext: %s' % os.path.splitext(downlocation)[1])
                    if any([os.path.splitext(downlocation)[1].endswith(ext) for ext in self.extensions]) or snstat['mirror'] is False:
                        combined_lcmd = 'pget -c -n %s \"%s\"' % (config.GENERAL['lcmdsegments'], downlocation)
                        logger.debug('[HARPOON] file lcmd: %s' % combined_lcmd)
                        self.CURRENT_DOWNFOLDER = os.path.join(self.CURRENT_DOWNFOLDER, os.path.basename(downlocation))
                        self.mirror = False
                    else:
                        combined_lcmd = 'mirror -c -P %s --use-pget-n=%s \"%s\"' % (config.GENERAL['lcmdparallel'],config.GENERAL['lcmdsegments'], downlocation)
                        logger.debug('[HARPOON] folder   lcmd: %s' % combined_lcmd)
                        self.mirror=True

                    harpoon_env['harpoon_lcmd'] = combined_lcmd

                    if any([multiplebox == '1', multiplebox == '0']):
                        harpoon_env['harpoon_pp_host'] = config.PP['pp_host']
                        harpoon_env['harpoon_pp_sshport'] = str(config.PP['pp_sshport'])
                        harpoon_env['harpoon_pp_user'] = config.PP['pp_user']
                        if config.PP['pp_keyfile'] is not None:
                            harpoon_env['harpoon_pp_keyfile'] = config.PP['pp_keyfile']
                        else:
                            harpoon_env['harpoon_pp_keyfile'] = ''
                        if config.PP['pp_passwd'] is not None:
                            harpoon_env['harpoon_pp_passwd'] = config.PP['pp_passwd']
                        else:
                            harpoon_env['harpoon_pp_passwd'] = ''
                    else:
                        harpoon_env['harpoon_pp_host'] = config.PP['pp_host2']
                        harpoon_env['harpoon_pp_sshport'] = config.PP['pp_sshport2']
                        harpoon_env['harpoon_pp_user'] = config.PP['pp_user2']
                        if config.PP['pp_keyfile2'] is not None:
                            harpoon_env['harpoon_pp_keyfile'] = config.PP['pp_keyfile2']
                        else:
                            harpoon_env['harpoon_pp_keyfile'] = ''
                        if config.PP['pp_passwd2'] is not None:
                            harpoon_env['harpoon_pp_passwd'] = config.PP['pp_passwd2']
                        else:
                            harpoon_env['harpoon_pp_passwd'] = ''

                    logger.info('Downlocation: %s' % re.sub("'", "\\'", downlocation))
                    logger.info('Label: %s' % labelit)
                    logger.info('Multiple Seedbox: %s' % multiplebox)

                    script_cmd = shlex.split(curScriptName)# + [downlocation, labelit, multiplebox]
                    # logger.info("Executing command " + str(script_cmd))

                    try:
                        queue.ckupdate(item['item'], {'status': 'Fetching', 'stage': 'current'})
                        harpoon.CURRENT_DOWNLOAD = sftp.SFTP(env=harpoon_env, mirror=self.mirror)
                        harpoon.CURRENT_DOWNLOAD.get(remoteloc = downlocation, localloc = self.CURRENT_DOWNFOLDER)
                        while harpoon.CURRENT_DOWNLOAD.isopen:
                            time.sleep(1)
                        # p = subprocess.Popen(script_cmd, env=dict(harpoon_env), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        # output, error = p.communicate()
                        # if error:
                        #     logger.warn('[ERROR] %s' % error)
                        # if output:
                        #    logger.info('[OUTPUT] %s'% output)
                    except Exception as e:
                        if harpoon.CURRENT_DOWNLOAD.exitlevel == 1:
                            queue.ckupdate(item['item'], {'stage': 'failed', 'status': 'Failed (Could not fetch from host)'})
                        logger.warn('Exception occured: %s' % e)
                        continue
                    else:
                        snatch_status = 'COMPLETED'

                if all([snstat['label'] == config.SONARR['sonarr_label'], config.GENERAL['tv_choice'] == 'sonarr']):  #probably should be sonarr_label instead of 'tv'
                    check_unrar = True
                    label_name='Sonarr'
                    label = config.SONARR['sonarr_label']
                    pp_obj = sonarr.Sonarr
                    info = {'snstat': snstat}
                    plex_pp = True
                elif all([snstat['label'] == config.SICKRAGE['sickrage_label'], config.GENERAL['tv_choice'] == 'sickrage']):
                    check_unrar = True
                    label_name = 'Sickrage'
                    label = config.SICKRAGE['sickrage_label']
                    pp_obj = sickrage.Sickrage
                    info = {'snstat': snstat}
                    plex_pp = True
                elif snstat['label'] == config.RADARR['radarr_label']:
                    check_unrar = True
                    label_name = 'Radarr'
                    label=config.RADARR['radarr_label']
                    pp_obj = radarr.Radarr
                    info = {'radarr_id': None, 'radarr_movie': None, 'snstat': snstat}
                    plex_pp = True
                elif snstat['label'] == config.LIDARR['lidarr_label']:
                    check_unrar = True
                    label_name = 'Lidarr'
                    label = config.LIDARR['lidarr_label']
                    pp_obj = lidarr.Lidarr
                    info = {'snstat': snstat}
                    plex_pp = True
                elif snstat['label'] == config.LAZYLIBRARIAN['lazylibrarian_label']:
                    check_unrar = True
                    label_name = 'LazyLibrarian'
                    label = config.LAZYLIBRARIAN['lazylibrarian_label']
                    pp_obj = lazylibrarian.LazyLibrarian
                    ll_file = os.path.join(config.GENERAL['torrentfile_dir'], config.LAZYLIBRARIAN['lazylibrarian_label'], item['item'] + '.' + item['mode'])
                    ll_type = queue.ckqueue()[snstat['hash']]['ll_type']
                    if os.path.isfile(ll_file):
                        try:
                            ll_filedata = json.load(open(ll_file))
                            logger.info('[LAZYLIBRARIAN] File data loaded.')
                        except:
                            ll_filedata = None
                            logger.info('[LAZYLIBRARIAN] File data NOT loaded.')
                    else:
                        ll_filedata = None
                        logger.info('[LAZYLIBRARIAN] File data NOT loaded.')
                    info = {'snstat':        snstat,
                            'filedata':      ll_filedata,
                            'll_type':  ll_type,}
                    plex_pp = False
                elif snstat['label'] == 'music':
                    check_unrar = True
                    label_name = 'Music'
                    label = 'music'
                    pp_obj = None
                    info = None
                    plex_pp = False
                elif snstat['label'] == 'xxx':
                    check_unrar = True
                    label = 'xxx'
                    label_name = 'XXX'
                    pp_obj = None
                    info = None
                    plex_pp = False
                elif snstat['label'] == config.MYLAR['mylar_label']:
                    check_unrar = False
                    label_name = 'Mylar'
                    label = config.MYLAR['mylar_label']
                    pp_obj = mylar.Mylar
                    info = {'issueid': self.issueid, 'snstat': snstat}
                    plex_pp = False
                else:
                    check_unrar = True
                    label = snstat['label']
                    label_name = snstat['label']
                    pp_obj = None
                    info = None
                    plex_pp = False
                log_label = label_name.upper()

                # Process
                logger.debug('[HARPOON] - %s detected' % label_name)
                if check_unrar:
                    # unrar it, delete the .rar's and post-process against the items remaining in the given directory.
                    queue.ckupdate(item['item'], {'status': 'Unpacking'})
                    cr = unrar.UnRAR(os.path.join(config.GENERAL['defaultdir'], label ,snstat['name']))
                    queue.ckupdate(item['item'], {'status': 'Processing'})
                    chkrelease = cr.main()
                    if all([len(chkrelease) == 0, len(snstat['files']) > 1, not os.path.isdir(os.path.join(config.GENERAL['defaultdir'], label, snstat['name']))]):
                        #if this hits, then the retrieval from the seedbox failed probably due to another script moving into a finished/completed directory (ie. race-condition)
                        logger.warn('[%s] Problem with snatched files - nothing seems to have downloaded. Retrying the snatch again in case the file was moved from a download location to a completed location on the client.' % log_label)
                        time.sleep(5)
                        self.hash_reload = True
                        continue
                if pp_obj:
                    logger.info('[%s] Placing call to update %s' % (log_label, label_name))
                    pp = pp_obj(info)
                    pp_process = pp.post_process()
                else:
                    pp_process = None

                if not any([item['mode'] == 'hash-add', item['mode'] == 'file-add']):
                    logger.info('[HARPOON] Removing completed file from queue directory.')
                    try:
                        #os.remove(os.path.join(config.GENERAL['torrentfile_dir'], label, item['item'] + '.' + item['mode']))
                        hashfilename = queue.ckqueue()[item['item']]['hashfilename']
                        os.remove(hashfilename)
                        logger.info('[HARPOON] File removed')
                    except:
                        logger.warn('[HARPOON] Unable to remove file from snatch queue directory [' + hashfilename + ']. You should delete it manually to avoid re-downloading')

                # Radarr Specific
                if label == 'radarr' and config.RADARR['radarr_keep_original_foldernames'] is True:
                    logger.info('[HARPOON] Keep Original FolderNames are enabled for Radarr. Altering paths ...')
                    radarr_info['radarr_id'] = radarr_process['radarr_id']
                    radarr_info['radarr_movie'] = radarr_process['radarr_movie']

                    rof = pp_obj(radarr_info)
                    radarr_keep_og = rof.og_folders()

                if pp_obj:
                    if pp_process == True:
                        logger.info('[%s] Successfully post-processed : %s' % (log_label, snstat['name']))
                        if config.SAB['sab_enable'] is True:
                            self.cleanup_check(item, script_cmd, downlocation, snstat)
                    else:
                        logger.info('[%s] Unable to confirm successful post-processing - this could be due to running out of hdd-space, an error, or something else occuring to halt post-processing of the episode.' % log_label)
                        logger.info('[%s] HASH: %s / label: %s' % (log_label, snstat['hash'], snstat['label']))

                queue.ckupdate(snstat['hash'], {'hash': snstat['hash'], 'stage': 'completed', 'status': 'Finished'})

                if all([plex_pp, config.PLEX['plex_update'] is True, pp_process is True]):

                    if pp_process and 'radarr_root' in pp_process.keys():
                        root_path = pp_process['radarr_root']
                    else:
                        root_path = None

                    logger.info('[PLEX-UPDATE] Now submitting update library request to plex')
                    plexit = plex.Plex({'plex_label': snstat['label'],
                                        'root_path': root_path, })

                    pl = plexit.connect()

                    if pl['status'] is True:
                        logger.info('[HARPOON-PLEX-UPDATE] Completed (library is currently being refreshed)')
                    else:
                        logger.warn('[HARPOON-PLEX-UPDATE] Failure - library could NOT be refreshed')

                if any([item['mode'] == 'hash-add', item['mode'] == 'file-add']) and self.daemon is False:
                    queue.put({'mode': 'exit',
                               'item': 'None'})

    def cleanup_check(self, item, script_cmd, downlocation, snstat):
        logger.info('[CLEANUP-CHECK] item: %s' % item)
        if 'client' in list(item.keys()) and config.SAB['sab_cleanup'] and item['client'] == 'sabnzbd':
            import subprocess
            logger.info('[HARPOON] Triggering cleanup')
            sa_params = {}
            sa_params['nzo_id'] = item['item']
            sa_params['apikey'] = config.SAB['sab_apikey']
            try:
                sab = sabnzbd.SABnzbd(params=sa_params, saburl=config.SAB['sab_url'])
                cleanup = sab.cleanup()
            except Exception as e:
                logger.info('ERROR 938 - %s' % e)
                cleanup = None

            labelit = None
            if config.GENERAL['applylabel'] is True:
                if any([snstat['label'] != 'None', snstat['label'] is not None]):
                    labelit = snstat['label']

            if snstat['multiple'] is None:
                multiplebox = '0'
            else:
                multiplebox = snstat['multiple']
            harpoon_env = os.environ.copy()

            harpoon_env['conf_location'] = harpoon.CONF_LOCATION
            harpoon_env['harpoon_location'] = re.sub("'", "\\'", downlocation)
            harpoon_env['harpoon_location'] = re.sub("!", "\\!", downlocation)
            harpoon_env['harpoon_label'] = labelit
            harpoon_env['harpoon_applylabel'] = str(config.GENERAL['applylabel']).lower()
            harpoon_env['harpoon_defaultdir'] = config.GENERAL['defaultdir']
            harpoon_env['harpoon_lcmd'] = 'rm -r \"%s\"' % downlocation

            if any([multiplebox == '1', multiplebox == '0']):
                harpoon_env['harpoon_pp_host'] = config.PP['pp_host']
                harpoon_env['harpoon_pp_sshport'] = str(config.PP['pp_sshport'])
                harpoon_env['harpoon_pp_user'] = config.PP['pp_user']
                if config.PP['pp_keyfile'] is not None:
                    harpoon_env['harpoon_pp_keyfile'] = config.PP['pp_keyfile']
                else:
                    harpoon_env['harpoon_pp_keyfile'] = ''
                if config.PP['pp_passwd'] is not None:
                    harpoon_env['harpoon_pp_passwd'] = config.PP['pp_passwd']
                else:
                    harpoon_env['harpoon_pp_passwd'] = ''
            else:
                harpoon_env['harpoon_pp_host'] = config.PP['pp_host2']
                harpoon_env['harpoon_pp_sshport'] = config.PP['pp_sshport2']
                harpoon_env['harpoon_pp_user'] = config.PP['pp_user2']
                if config.PP['pp_keyfile2'] is not None:
                    harpoon_env['harpoon_pp_keyfile'] = config.PP['pp_keyfile2']
                else:
                    harpoon_env['harpoon_pp_keyfile'] = ''
                if config.PP['pp_passwd2'] is not None:
                    harpoon_env['harpoon_pp_passwd'] = config.PP['pp_passwd2']
                else:
                    harpoon_env['harpoon_pp_passwd'] = ''

            # logger.debug('Params: %s' % harpoon_env)
            try:
                p = subprocess.Popen(script_cmd, env=dict(harpoon_env), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                output, error = p.communicate()
                if error:
                    logger.warn('[ERROR] %s' % error)
                if output:
                    logger.info('[OUTPUT] %s' % output)
            except Exception as e:
                logger.warn('Exception occured: %s' % e)

    def sizeof_fmt(self, num, suffix='B'):
        for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)


    def moviecheck(self, movieinfo):
        movie_type = None
        filename = movieinfo['movieFile']['relativePath']
        vsize = str(movieinfo['movieFile']['mediaInfo']['width'])
        for webdl in config.RADARR['web_movies_defs']:
            if webdl.lower() in filename.lower():
                logger.info('[RADARR] HD - WEB-DL Movie detected')
                movie_type = 'WEBDL' #movie_type = hd   - will store the hd def (ie. 720p, 1080p)
                break

        if movie_type is None or movie_type == 'HD':   #check the hd to get the match_type since we already know it's HD.
            for hd in config.RADARR['hd_movies_defs']:
                if hd.lower() in filename.lower():
                    logger.info('[MOVIE] HD - Movie detected')
                    movie_type = 'HD' #movie_type = hd   - will store the hd def (ie. 720p, 1080p)
                    break

        if movie_type is None:
            for sd in config.RADARR['sd_movies_defs']:
                if sd.lower() in filename.lower():
                    logger.info('[MOVIE] SD - Movie detected')
                    movie_type = 'SD' #movie_type = sd
                    break

        #not sure if right spot, we can determine movie_type (HD/SD) by checking video dimensions.
        #1920/1280 = HD
        #720/640 = SD
        SD_Dimensions = ('720', '640')
        if vsize.startswith(SD_Dimensions):
            logger.info('[MOVIE] SD Movie detected as Dimensions are : ' + str(vsize))
            movie_type = 'SD'
            match_type = 'dimensions'

        if movie_type == 'HD':
            dest = self.dir_hd_movies
        elif movie_type == 'WEBDL':
            dest = self.dir_web_movies
        else:
            dest = self.dir_sd_movies

        return dest

    def daemonize(self):

        if threading.activeCount() != 1:
            logger.warn('There are %r active threads. Daemonizing may cause \
                            strange behavior.' % threading.enumerate())

        sys.stdout.flush()
        sys.stderr.flush()

        # Do first fork
        try:
            pid = os.fork()
            if pid == 0:
                pass
            else:
                # Exit the parent process
                logger.debug('Forking once...')
                os._exit(0)
        except OSError as e:
            sys.exit("1st fork failed: %s [%d]" % (e.strerror, e.errno))

        os.setsid()

        # Make sure I can read my own files and shut out others
        prev = os.umask(0)  # @UndefinedVariable - only available in UNIX
        os.umask(prev and int('077', 8))

        # Do second fork
        try:
            pid = os.fork()
            if pid > 0:
                logger.debug('Forking twice...')
                os._exit(0) # Exit second parent process
        except OSError as e:
            sys.exit("2nd fork failed: %s [%d]" % (e.strerror, e.errno))

        # dev_null = open('/dev/null', 'r')
        # os.dup2(dev_null.fileno(), sys.stdin.fileno())
        #
        # si = open('/dev/null', "r")
        # so = open('/dev/null', "a+")
        # se = open('/dev/null', "a+")
        #
        # os.dup2(si.fileno(), sys.stdin.fileno())
        # os.dup2(so.fileno(), sys.stdout.fileno())
        # os.dup2(se.fileno(), sys.stderr.fileno())

        pid = os.getpid()
        logger.info('Daemonized to PID: %s' % pid)
        if self.createpid:
            logger.info("Writing PID %d to %s", pid, self.pidfile)
            with open(self.pidfile, 'w') as fp:
                fp.write("%s\n" % pid)

    def shutdown(self):
        logger.info('Now Shutting DOWN')
        try:
            self.SNPOOL.join(10)
            logger.info('Joined pool for termination - Successful')
        except KeyboardInterrupt:
            HQUEUE.put('exit')
            self.SNPOOL.join(5)
        except AssertionError:
            os._exit(0)

        if self.createpid:
            logger.info('Removing pidfile %s' % self.pidfile)
            os.remove(self.pidfile)

        os._exit(0)


if __name__ == '__main__':
    gf = QueueR()

