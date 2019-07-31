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
import requests
from harpoon import logger, config

class Sickrage(object):

    def __init__(self, sickrage_info):
       logger.info(sickrage_info)
       self.sickrage_url = config.SICKRAGE['sickrage_url']
       self.sickrage_apikey = config.SICKRAGE['sickrage_apikey']
       self.sickrage_forcereplace = config.SICKRAGE['sickrage_forcereplace']
       self.sickrage_forcenext = config.SICKRAGE['sickrage_forcenext']
       self.sickrage_process_method = config.SICKRAGE['sickrage_process_method']
       self.sickrage_is_priority = config.SICKRAGE['sickrage_is_priority']
       self.sickrage_failed = config.SICKRAGE['sickrage_failed']
       self.sickrage_delete = config.SICKRAGE['sickrage_delete']
       self.sickrage_type = config.SICKRAGE['sickrage_type']
       self.sickrage_headers = config.SICKRAGE['sickrage_headers']
       self.applylabel = config.GENERAL['applylabel']
       self.defaultdir = config.GENERAL['defaultdir']
       self.snstat = sickrage_info['snstat']

    def post_process(self):
        url = self.sickrage_url + '/api/' + self.sickrage_apikey
        if self.applylabel is True:
            if self.snstat['label'] == 'None':
                newpath = os.path.join(self.defaultdir, self.snstat['name'])
            else:
                newpath = os.path.join(self.defaultdir, self.snstat['label'], self.snstat['name'])
        else:
            newpath = os.path.join(self.defaultdir, self.snstat['name'])

        payload = {'cmd':  'postprocess',
                   'path': newpath,
                   'delete': bool(self.sickrage_delete),
                   'force_next': 0,
                   'force_replace': bool(self.sickrage_forcereplace),
                   'is_priority': bool(self.sickrage_is_priority),
                   'process_method':  self.sickrage_process_method,
                   'return_data': 1,
                   'failed': bool(self.sickrage_failed),
                   'type': self.sickrage_type}

        logger.info('[SICKRAGE] Posting url: %s' % url)
        logger.info('[SICKRAGE] Posting to completed download handling now: %s' % payload)

        r = requests.post(url, json=payload, headers=self.sickrage_headers)
        data = r.json()
        logger.info('content: %s' % data)
        logger.info('[SICKRAGE] Successfully post-processed : ' + self.snstat['name'])
        return True
