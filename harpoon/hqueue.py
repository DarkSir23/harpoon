import Queue
from common import currentTime

class hQueue:

    def __init__(self):
        self.SNQUEUE = Queue.Queue()

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



    ### CKQUEUE ###

    def ckupdate(self, key, item):
        if key in self.CKQUEUE.keys():
            for itemkey in item.keys():
                self.CKQUEUE[key][itemkey] = item[itemkey]
            self.CKQUEUE[key]['timestamp'] = currentTime()
        else:
            self.CKQUEUE[key] = item
            self.CKQUEUE[key]['timestamp'] = currentTime()

    def ckremove(self, key):
        if key in self.CKQUEUE.keys():
            del self.CKQUEUE[key]

    def ckappend(self, item):
        return self.CKQUEUE.append(item)

    def ckqueue(self):
        return self.CKQUEUE

