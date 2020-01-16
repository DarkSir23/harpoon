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

import os
import time
import shutil
import requests
import json
from harpoon import logger, config, common

class LazyLibrarian(object):

    def __init__(self, ll_info):
        logger.info(ll_info)
        self.lazylibrarian_url = config.LAZYLIBRARIAN['lazylibrarian_url']
        self.lazylibrarian_label = config.LAZYLIBRARIAN['lazylibrarian_label']
        self.lazylibrarian_headers = config.LAZYLIBRARIAN['lazylibrarian_headers']
        self.lazylibrarian_apikey = config.LAZYLIBRARIAN['lazylibrarian_apikey']
        self.lazylibrarian_filedata = ll_info['filedata']
        self.applylabel = config.GENERAL['applylabel']
        self.defaultdir = config.GENERAL['defaultdir']
        self.snstat = ll_info['snstat']
        self.ll_type = ll_info['ll_type']
        logger.debug("---")

    def post_process(self):
        logger.debug('[LAZYLIBRARIAN] Type: %s' % self.ll_type)
        url = self.lazylibrarian_url + '/api'
        if 'extendedname' in list(self.snstat.keys()):
            nzbname = self.snstat['extendedname']
        else:
            nzbname = self.snstat['name']
        if self.applylabel is True:
            if self.snstat['label'] == 'None':
                filepath = os.path.join(self.defaultdir, nzbname)
            else:
                filepath = os.path.join(self.defaultdir, self.snstat['label'], nzbname)
        else:
            filepath = os.path.join(self.defaultdir, nzbname)
        filebase = os.path.basename(filepath)
        logger.debug('[LAZYLIBRARIAN] Path: %s' % filepath)
        midpath = os.path.abspath(os.path.join(filepath, os.pardir))
        midbase = os.path.basename(midpath)
        defaultbase = os.path.basename(self.defaultdir)
        downloadid = ''
        if 'DownloadID' in self.lazylibrarian_filedata.keys():
            downloadid = self.lazylibrarian_filedata['DownloadID']
        movefile = False
        if self.lazylibrarian_filedata and 'BookID' in list(self.lazylibrarian_filedata.keys()):
            process_suffix = ' LL.(%s)' % self.lazylibrarian_filedata['BookID']
        else:
            process_suffix = ' PROCESS'
        logger.info('[LAZYLIBRARIAN] Process Suffix: %s' % process_suffix)
        if midbase == defaultbase or midbase == self.snstat['label']:
            # name is 1 deep - if file, move it.  if folder, check for LL
            filepath = filepath.encode('utf-8')
            if os.path.isfile(filepath):
                logger.info('[LAZYLIBRARIAN] Prepping file to move')
                process_path = filepath + process_suffix.encode('utf-8')
                movefile = True
            elif os.path.isdir(filepath):
                logger.info('[LAZYLIBRARIAN] Path is a folder')
                if str(filepath).endswith(process_suffix):
                    logger.info('[LAZYLIBRARIAN] Folder is already properly named')
                    movefile = False
                    process_path = filepath
                else:
                    logger.info('[LAZYLIBRARIAN] Renaming folder')
                    movefile = False
                    process_path = filepath + process_suffix.encode('utf-8')
                    if os.path.exists(process_path):
                        logger.info('[LAZYLIBRARIAN] Path Exists.  Removing.')
                        shutil.rmtree(process_path)
                    os.rename(filepath, process_path)
            else:
                logger.debug('[LAZYLIBRARIAN] File not found')
                return False
        elif midbase.endswith(process_suffix):
            logger.debug('[LAZYLIBRARIAN] Setting working folder to %s' % midpath)
            process_path = midpath
            movefile = False
        else:
            logger.debug('[LAZYLIBRARIAN] Setting working folder to %s and renaming' % midpath)
            process_path = midpath + process_suffix
            os.rename(midpath, process_path)
            movefile = False
        if movefile:
            logger.debug("[LAZYLIBRARIAN] Moving %s to %s" % (filepath, os.path.join(process_path, filebase.encode('utf-8'))))
            if not os.path.exists(process_path):
                os.mkdir(process_path)
            shutil.move(filepath, os.path.join(process_path, filebase.encode('utf-8')))

        # if self.lazylibrarian_filedata and 'BookID' in self.lazylibrarian_filedata.keys():
        #     movefile = True
        #     midpath = os.path.basename(os.path.abspath(os.path.join(newpath,os.path.pardir)))
        #     if midpath.endswith('LL.(%s)' % self.lazylibrarian_filedata['BookID']):
        #         logger.debug("Option 1")
        #         brandnewpath = os.path.abspath(os.path.join(newpath,os.path.pardir))
        #         movefile = False
        #     elif not newpath.endswith('LL.(%s)' % self.lazylibrarian_filedata['BookID']):
        #         logger.debug("Option 2")
        #         brandnewpath = newpath + ' LL.(%s)' % self.lazylibrarian_filedata['BookID']
        #     else:
        #         logger.debug("Option 3")
        #         brandnewpath = newpath
        #         movefile = False
        #     logger.debug('[LAZYLIBRARIAN] New Path: %s' % brandnewpath)
        #     if os.path.isdir(newpath) and newpath != brandnewpath:
        #         logger.debug('[LAZYLIBRARIAN] Renaming Folder')
        #         os.rename(newpath, brandnewpath)
        #         logger.debug('Path Renamed')
        #     elif os.path.isfile(newpath) and movefile:
        #         logger.debug('[LAZYLIBRARIAN] Moving file (%s) into folder (%s)' % (newpath, brandnewpath))
        #         newfile = os.path.join(brandnewpath, self.snstat['name'])
        #         os.mkdir(brandnewpath)
        #         logger.debug('NewFile: %s' % newfile)
        #         shutil.move(newpath, newfile)
        #     elif os.path.isdir(brandnewpath):
        #         logger.debug('[LAZYLIBRARIAN] Processing folder already exists.')
        #     else:
        #         logger.debug('[LAZYLIBRARIAN] File not found.')
        #         return False
        # else:
        #     if os.path.isfile(newpath):
        #         brandnewpath = newpath + ' PROCESS'
        #         logger.debug('[LAZYLIBRARIAN] Moving file (%s) into folder (%s)' % (newpath, brandnewpath))
        #         newfile = os.path.join(brandnewpath, self.snstat['name'])
        #         os.mkdir(brandnewpath)
        #         logger.debug('NewFile: %s' % newfile)
        #         shutil.move(newpath, newfile)
        #     else:
        #         brandnewpath = newpath

        logger.info('[LAZYLIBRARIAN] Path: %s' % process_path)

        if self.ll_type == 'Magazine':
            payload = {'cmd': 'forceProcess',
                       'dir': process_path,
                       'apikey': self.lazylibrarian_apikey,
                       'ignoreclient': 'True',
                       'wait': 'True',
                       'downloadid': downloadid,
                       }
        else:
            payload = {'cmd':  'importAlternate',
                       'dir': process_path,
                       'apikey': self.lazylibrarian_apikey,
                       'library': self.ll_type,
                       'wait': 'True',
                       'ignoreclient': 'True',}

        logger.info('[LAZYLIBRARIAN] Posting url: %s' % url)
        logger.info('[LAZYLIBRARIAN] Posting to completed download handling now: %s' % payload)
        processing = True
        while processing:
            r = requests.post(url, data=payload, headers=self.lazylibrarian_headers)
            try:
                data = json.loads(r.text)
            except:
                data = None
            logger.debug('Response: %s - type: %s' % (data, type(data)))
            if self.ll_type == 'Magazine' and data and 'status' in data.keys():
                if data['status'] =='success':
                    processing = False
                    logger.info('[LAZYLIBRARIAN] Successfully post-processed : ' + self.snstat['name'])
                    return True
                elif data['status'] == 'failed':
                    processing = False
                    logger.info('[LAZYLIBRARIAN] Failed post-processing : ' + self.snstat['name'])
                    return False
                else:
                    logger.debug('[LAZYLIBRARIAN] Processing is already running.  Trying again in 10 seconds.')
                    time.sleep(10)
            elif data == True:
                logger.info('[LAZYLIBRARIAN] Successfully post=processed : ' + self.snstat['name'])
                return True
            elif data == False:
                logger.info('[LAZYLIBRARIAN[ Failed post-processing : ' + self.snstat['name'])
                return False
            else:
                processing = False
                logger.info('[LAZYLIBRARIAN] No status returned.  Assuming failure.')
                logger.info('content: %s' % data)
                return False

        logger.info('[LAZYLIBRARIAN] Successfully post-processed : ' + self.snstat['name'])
        return True
