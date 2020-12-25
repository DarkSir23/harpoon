import queue
from .common import currentTime
from harpoon import logger, hconfig
import os

DATADIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

CONF_LOCATION = os.path.join(DATADIR, 'conf', 'harpoon.conf')

config = hconfig.config(CONF_LOCATION)

class hQueue:

    def __init__(self):
        self.SNQUEUE = queue.Queue()

        # secondary queue to keep track of what's not been done, scheduled to be done, and completed.
        # 4 stages = to-do, current, reload, completed.
        self.CKQUEUE = {}

    def empty(self):
        return self.SNQUEUE.empty()

    def qsize(self):
        return self.SNQUEUE.qsize()

    def put(self, item):
        return self.SNQUEUE.put(item)

    def get(self, block):
        return self.SNQUEUE.get(block=block)

    def queuelist(self):
        return list(self.SNQUEUE.queue)

    def remove(self, hash, removefile=False):
        qsize = self.qsize()
        logger.debug('[QUEUE] Removal started (Queue Size: %s)' % qsize)
        msg = ''
        if qsize:
            for x in range(0, qsize):
                item = self.SNQUEUE.get(block=True)
                if not item['item'] == hash:
                    logger.debug('[QUEUE] Nope')
                    self.SNQUEUE.put(item)
                else:
                    logger.debug('[QUEUE] Found it')
                    if hash in list(self.CKQUEUE.keys()):
                        msg += "Item '%s' removed from queue.\n" % self.CKQUEUE[hash]['name']
                        logger.debug('[QUEUE] %s' % msg)
                        self.ckupdate(hash, {'stage': 'failed', 'status': 'Removed from Queue'})
                        if removefile:
                            try:
                                # filename = os.path.join(str(config.GENERAL['torrentfile_dir']), str(item['label']), str(item['item']) + '.' + str(item['mode']))
                                filename = self.ckqueue()[hash]['hashfilename']
                                os.remove(filename)
                                msg += "File '%s' removed." % filename
                                logger.info('[USER] File %s removed' % filename)
                            except Exception as e:
                                logger.info('[USER] File could not be removed: %s' % e)
                                msg += "File '%s' could not be removed.  Reason: %s" % (filename, e)
            return msg


    ### CKQUEUE ###

    def ckupdate(self, key, item):
        if key in list(self.CKQUEUE.keys()):
            for itemkey in list(item.keys()):
                self.CKQUEUE[key][itemkey] = item[itemkey]
            self.CKQUEUE[key]['timestamp'] = currentTime()
        else:
            self.CKQUEUE[key] = item
            self.CKQUEUE[key]['timestamp'] = currentTime()

    def ckremove(self, key, removefile=False):
        msg = ''
        if key in list(self.CKQUEUE.keys()):
            if removefile:
                try:
                    filename = self.CKQUEUE[key]['hashfilename']
                    os.remove(filename)
                    msg += "File '%s' removed." % filename
                    logger.info('[USER] File %s removed' % filename)
                except Exception as e:
                    logger.info('[USER] File could not be removed: %s' % e)
                    msg += "File '%s' could not be removed.  Reason: %s" % (filename, e)
            del self.CKQUEUE[key]
        return msg


    def ckappend(self, item):
        return self.CKQUEUE.append(item)

    def ckqueue(self):
        return self.CKQUEUE

