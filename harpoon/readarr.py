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

from harpoon import logger, config

class Readarr(object):

    def __init__(self, readarr_info):
        self.readarr_url = config.READARR['readarr_url']
        self.readarr_label = config.READARR['readarr_label']
        self.readarr_headers = config.READARR['readarr_headers']
        self.applylabel = config.GENERAL['applylabel']
        self.defaultdir = config.GENERAL['defaultdir']
        self.torrentfile_dir = config.GENERAL['torrentfile_dir']
        self.snstat = readarr_info['snstat']


    def post_process(self):
        url = self.readarr_url + '/api/v1/command'
        if self.applylabel is True:
            if self.snstat['label'] == 'None':
                newpath = os.path.join(self.defaultdir, self.snstat['name'])
            else:
                newpath = os.path.join(self.defaultdir, self.snstat['label'], self.snstat['name'])
        else:
            newpath = os.path.join(self.defaultdir, self.snstat['name'])

        payload = {'name': 'DownloadedBooksScan',
                   'path': newpath,
                   'downloadClientID': self.snstat['hash'],
                   'importMode': 'Move'}

        logger.info('[READARR] Posting url: %s' % url)
        logger.info('[READARR] Posting to completed download handling now: %s' % payload)

        r = requests.post(url, json=payload, headers=self.readarr_headers)
        data = r.json()
        logger.info('content: %s' % data)

        check = True
        while check:
            url = self.readarr_url + '/api/v1/command/' + str(data['id'])
            logger.info('[READARR] command check url : %s' % url)
            try:
                r = requests.get(url, params=None, headers=self.readarr_headers)
                dt = r.json()
                logger.info('[READARR] Reponse: %s' % dt)
            except:
                logger.warn('error returned from readarr call. Aborting.')
                return False
            else:
                if dt['status'] == 'completed':
                    logger.info('[READARR] Successfully post-processed : ' + self.snstat['name'])
                    check = False
                elif any([dt['status'] == 'failed', dt['status'] == 'aborted', dt['status'] == 'cancelled']):
                    logger.info('[READARR] FAiled to post-process : ' + self.snstat['name'])
                    check = False
                else:
                    time.sleep(10)

        if check is False:
            # we need to get the root path here in order to make sure we call the correct plex update ...
            # hash is know @ self.snstat['hash'], file will exist in snatch queue dir as hashvalue.hash
            # file contains complete snatch record - retrieve the 'path' value to get the series directory.
            return True
        else:
            return False
