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
import json
import requests
from harpoon import logger

class Mylar(object):

    def __init__(self, mylar_info):
       self.mylar_url = mylar_info['mylar_url']
       self.mylar_apikey = mylar_info['mylar_apikey']
       self.mylar_label = mylar_info['mylar_label']
       self.mylar_headers = mylar_info['mylar_headers']
       self.applylabel = mylar_info['applylabel']
       self.torrentfile_dir = mylar_info['torrentfile_dir']
       self.defaultdir = mylar_info['defaultdir']
       self.snstat = mylar_info['snstat']

    def post_process(self):
       nzb_name = None
       try:
           logger.debug('attempting to open: %s' % os.path.join(self.torrentfile_dir, self.mylar_label, self.snstat['hash'] + '.hash'))
           with open(os.path.join(self.torrentfile_dir, self.mylar_label, self.snstat['hash'] + '.hash')) as dfile:
               data = json.load(dfile)
       except Exception as e:
           logger.error('[%s] not able to load .hash file.' % e)
           #for those that were done outside of Mylar or using the -s switch on the cli directly by hash
           nzb_name = 'Manual Run'
       else:
           logger.debug('loaded .hash successfully - extracting info.')
           try:
               nzb_name = data['mylar_release_name']
           except:
               #if mylar_release_name doesn't exist, fall back to the torrent_filename.
               #mylar retry issue will not have a release_name
               nzb_name = data['mylar_torrent_filename']

           if data['mylar_release_pack'] is False:
               issueid = data['mylar_issueid']
           else:
               issueid = None
           comicid = data['mylar_comicid']

       url = self.mylar_url + '/api'
       if self.applylabel == 'true':
           if self.snstat['label'] == 'None':
               newpath = os.path.join(self.defaultdir, self.snstat['name'])
           else:
               newpath = os.path.join(self.defaultdir, self.snstat['label'], self.snstat['name'])
       else:
           newpath = os.path.join(self.defaultdir, self.snstat['name'])

       payload = {'cmd':         'forceProcess',
                  'apikey':      self.mylar_apikey,
                  'nzb_name':    nzb_name,
                  'issueid':     issueid,
                  'comicid':     comicid,
                  'nzb_folder':  newpath}

       logger.info('[MYLAR] Posting url: %s' % url)
       logger.info('[MYLAR] Posting to completed download handling now: %s' % payload)

       r = requests.post(url, params=payload, headers=self.mylar_headers)
       response = r.json()
       logger.debug('content: %s' % response)

       logger.debug('[MYLAR] status_code: %s' % r.status_code)
       logger.info('[MYLAR] Successfully post-processed : ' + self.snstat['name'])

       return True
