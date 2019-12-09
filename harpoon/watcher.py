import time
from lib.watchdog.observers import Observer
from lib.watchdog.events import PatternMatchingEventHandler
from harpoon import config, logger


class Watcher:
    def __init__(self, scanner):
        self.observer = Observer()
        self.scanner = scanner
        self.event_handler = PatternMatchingEventHandler(case_sensitive=False, patterns=["*.torrent", "*.nzb", "*.file"])
        self.event_handler.on_created = self.on_created
        self.observer.schedule(self.event_handler, config.GENERAL['torrentfile_dir'], recursive=True)
        logger.debug('SCANNER: Monitoring %s' % config.GENERAL['torrentfile_dir'])
        self.observer.start()

    def on_created(self, event):
        logger.debug('SCANNER: Event.')
        if event.is_directory:
            return None
        else:
            logger.debug('SCANNER: New file detected.  Running scanner.')
            self.scanner.scan()

    def stop(self):
        self.observer.stop()
        self.observer.join()