import SocketServer
import json
import select
import threading

from harpoon import logger, SOCKET_API
from harpoon import HQUEUE as HQUEUE

class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        d = self.request.recv(1024)
        dt = d.split("\n")[1]
        data = json.loads(dt)
        #logger.info(type(data))
        if data['apikey'] == SOCKET_API:
            if data['mode'] == 'add':
                logger.info('[API-AWARE] Request received via API for item [%s] to be remotely added to queue:' % data['hash'])
                addq = self.add_queue(data)
                queue_position = self.IndexableQueue(data['hash'])
                if addq is True:
                    self.send({'Status': True, 'Message': 'Successful authentication', 'Added': True, 'QueuePosition': queue_position})
                else:
                    self.send({'Status': True, 'Message': 'Successful authentication', 'Added': False})
            elif data['mode'] == 'queue':
                logger.info('[API-AWARE] Request received via API for listing of current queue')
                currentqueue = None
                if HQUEUE.qsize() != 0:
                    for x in HQUEUE.ckqueue().keys():
                        if HQUEUE.ckqueue()[x]['stage'] == 'current':
                            currentqueue = x
                            logger.info('currentqueue: %s' % currentqueue)
                            break
                self.send({'Status': True, 'QueueSize': HQUEUE.qsize(), 'CurrentlyInProgress': currentqueue, 'QueueContent': HQUEUE.queuelist()})
        else:
            self.send({'Status': False, 'Message': 'Invalid APIKEY', 'Added': False})
            return

    def recv(self):
        return self._recv(self.request)

    def send(self, data):
        self._send(self.request, data)
        return self

    def _send(self, socket, data):
        try:
            serialized = json.dumps(data)
        except (TypeError, ValueError), e:
            raise Exception('You can only send JSON-serializable data')
        # send the length of the serialized data first
        socket.send('%d\n' % len(serialized))
        # send the serialized data
        socket.sendall(serialized)

    def _recv(self, socket):
        # read the length of the data, letter by letter until we reach EOL
        length_str = ''
        char = socket.recv(1)
        while char != '\n':
            length_str += char
            char = socket.recv(1)
        total = int(length_str)
        # use a memoryview to receive the data chunk by chunk efficiently
        view = memoryview(bytearray(total))
        next_offset = 0
        while total - next_offset > 0:
            recv_size = socket.recv_into(view[next_offset:], total - next_offset)
            next_offset += recv_size
        try:
            deserialized = json.loads(view.tobytes())
        except (TypeError, ValueError), e:
            raise Exception('Data received was not in JSON format')
        return deserialized

    def add_queue(self, data):
        try:
            item = data['file']
            mode = 'file'
        except:
            item = data['hash']
            mode = 'hash'
        try:
            if mode == 'file':
                logger.info('[API-AWARE] Adding file to queue via FILE %s [label:%s]' % (data['file'], data['label']))
                HQUEUE.put({'mode':  'file-add',
                            'item':  data['file'],
                            'label': data['label']})

            elif mode == 'hash':
                logger.info('[API-AWARE] Adding file to queue via HASH %s [label:%s]' % (data['hash'], data['label']))
                HQUEUE.put({'mode':  'hash-add',
                            'item':  data['hash'],
                            'label': data['label']})
            else:
                logger.info('[API-AWARE] Unsupported mode or error in parsing. Ignoring request [%s]' % data)
                return False
        except:
            logger.info('[API-AWARE] Unsupported mode or error in parsing. Ignoring request [%s]' % data)
            return False
        else:
            logger.warn('[API-AWARE] Successfully added to queue - Prepare for GLORIOUS retrieval')
            return True

    def IndexableQueue(self, item):
        import collections
        d = HQUEUE.listqueue
        queue_position = [i for i,t in enumerate(d) if t['item'] == item]
        queue_pos = '%s/%s' % (''.join(str(e) for e in queue_position), HQUEUE.qsize())
        logger.info('queue position of %s' % queue_pos)
        return queue_pos


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer, object):
    def __init__(self, server_address, RequestHandlerClass):
        super(ThreadedTCPServer, self).__init__(server_address, RequestHandlerClass)
        self.server_address = server_address
        self.RequestHandlerClass = RequestHandlerClass
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False

    def serve_forever(self, poll_interval=0.5):
        logger.debug('Step A')
        self.__is_shut_down.clear()
        logger.debug('Step B')
        try:
            logger.debug('Step C')
            while not self.__shutdown_request:
                # XXX: Consider using another file descriptor or
                # connecting to the socket to wake this up instead of
                # polling. Polling reduces our responsiveness to a
                # shutdown request and wastes cpu at all other times.
                r, w, e = _eintr_retry(select.select, [self], [], [],
                                       poll_interval)
                if self in r:
                    self._handle_request_noblock()
        finally:
            self.__shutdown_request = False
            self.__is_shut_down.set()
        logger.debug('Step D')
