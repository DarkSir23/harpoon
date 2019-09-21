import pysftp
from pysftp.helpers import reparent, WTCallbacks, path_advance
import os
from harpoon import logger
from paramiko import SFTPClient


class SFTP():
    def __init__(self, env, mirror=False):
        self.mirror = mirror
        self.env = env
        self.stats = {
            'trans': 0,
            'total': 0,
            'currentfile': '',
            'percent': 0
        }
        self.isopen = False
        self.exitlevel = 0
        opts = pysftp.CnOpts()
        opts.hostkeys = None
        opts.compression = True
        keyfile = self.env['harpoon_pp_keyfile'] if self.env['harpoon_pp_keyfile'] else None
        password = self.env['harpoon_pp_passwd'] if self.env['harpoon_pp_passwd'] else None
        logger.debug('SFTP: Opening connection.')
        if keyfile:
            self.connection = CustomConnection(self.env['harpoon_pp_host'], port=int(self.env['harpoon_pp_sshport']), username=self.env['harpoon_pp_user'], private_key=keyfile, cnopts=opts)
        else:
            self.connection = CustomConnection(self.env['harpoon_pp_host'], port=int(self.env['harpoon_pp_sshport']),
                                           username=self.env['harpoon_pp_user'], private_key=keyfile, password=password, cnopts=opts)

    def get(self, remoteloc, localloc):
        self.isopen = True
        try:
            if self.mirror:
                logger.debug('SFTP: Getting mirror: %s' % remoteloc)
                folder = os.path.basename(remoteloc)
                basefolder = os.path.dirname(remoteloc)
                logger.debug('SFTP: Moving to folder: %s' % basefolder)
                logger.debug('SFTP: Current Local Loc: %s' % localloc)
                # local = os.path.join(localloc, folder)
                # logger.debug('SFTP: Setting local location to: %s' % local)
                with self.connection.cd(basefolder):
                    logger.debug('SFTP: Mirroring: %s' % folder)
                    self.connection.get_r(folder, localdir=localloc, callback=self.receivestatus, statsdict=self.stats)
            else:
                logger.debug('SFTP: Getting local: %s' % remoteloc)
                self.stats['currentfile'] = os.path.basename(remoteloc)
                self.connection.get('%s' % remoteloc, localpath=localloc, callback=self.receivestatus)
        except UnicodeEncodeError as e:
            logger.exception('Error: %s' % e)
            pass
        except Exception as e:
            logger.debug('SFTP: Error: %s' % e)
            self.exitlevel = 1
            logger.debug('SFTP: Closing connection')
            self.connection.close()
            self.isopen = False
            raise e
        logger.debug('SFTP: Closing connection')
        self.connection.close()
        self.isopen = False

    def receivestatus(self, btrans, btotal):
        self.stats['trans'] = float(btrans)
        self.stats['total'] = float(btotal)
        if self.stats['trans'] and self.stats['total']:
            self.stats['percent'] = (self.stats['trans'] / self.stats['total']) * 100

    def get_stats(self):
        return self.stats

    def abort_download(self):
        self.isopen = False
        self.exitstatus = 1
        try:
            self.connection.close()
        except Exception as e:
            pass
        return 'Download stopped'

class CustomConnection(pysftp.Connection):

    def get_r(self, remotedir, localdir, preserve_mtime=False, callback=None, statsdict=None):
        """recursively copy remotedir structure to localdir

        :param str remotedir: the remote directory to copy from
        :param str localdir: the local directory to copy to
        :param bool preserve_mtime: *Default: False* -
            preserve modification time on files

        :returns: None

        :raises:

        """
        self._sftp_connect()
        wtcb = WTCallbacks()
        self.walktree(remotedir, wtcb.file_cb, wtcb.dir_cb, wtcb.unk_cb)
        # handle directories we recursed through
        for dname in wtcb.dlist:
            for subdir in path_advance(dname):
                try:
                    os.mkdir(reparent(localdir, subdir))
                    # force result to a list for setter,
                    wtcb.dlist = wtcb.dlist + [subdir, ]
                except OSError:     # dir exists
                    pass

        for fname in wtcb.flist:
            # they may have told us to start down farther, so we may not have
            # recursed through some, ensure local dir structure matches
            head, _ = os.path.split(fname)
            if head not in wtcb.dlist:
                for subdir in path_advance(head):
                    if subdir not in wtcb.dlist and subdir != '.':
                        try:
                            os.mkdir(reparent(localdir, subdir))
                            wtcb.dlist = wtcb.dlist + [subdir, ]
                        except OSError:
                            pass
            if statsdict:
                statsdict['currentfile'] = fname
            self.get(fname, reparent(localdir, fname), preserve_mtime=preserve_mtime, callback=callback)

    def _sftp_connect(self):
        """Establish the SFTP connection."""
        if not self._sftp_live:
            self._sftp = CustomSFTPClient.from_transport(self._transport)
            if self._default_path is not None:
                # print("_default_path: [%s]" % self._default_path)
                self._sftp.chdir(self._default_path)
            self._sftp_live = True


class CustomSFTPClient(SFTPClient):

    def get(self, remotepath, localpath, callback=None):
        """
        Copy a remote file (``remotepath``) from the SFTP server to the local
        host as ``localpath``.  Any exception raised by operations will be
        passed through.  This method is primarily provided as a convenience.

        :param str remotepath: the remote file to copy
        :param str localpath: the destination path on the local host
        :param callable callback:
            optional callback function (form: ``func(int, int)``) that accepts
            the bytes transferred so far and the total bytes to be transferred

        .. versionadded:: 1.4
        .. versionchanged:: 1.7.4
            Added the ``callback`` param
        """
        with open(localpath.encode('utf-8'), "wb") as fl:
            size = self.getfo(remotepath, fl, callback)
        s = os.stat(localpath.encode('utf-8'))
        if s.st_size != size:
            raise IOError(
                "size mismatch in get!  {} != {}".format(s.st_size, size)
            )
