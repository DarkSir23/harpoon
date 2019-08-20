import pysftp
from pysftp.helpers import reparent, WTCallbacks, path_advance
import os
from harpoon import logger


class SFTP():
    def __init__(self, env, mirror=False):
        self.mirror = mirror
        self.env = env
        self.btrans = 0
        self.btotal = 0
        self.isopen = False
        opts = pysftp.CnOpts()
        opts.hostkeys = None
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
        if self.mirror:
            logger.debug('SFTP: Getting mirror: %s' % remoteloc)
            folder = os.path.basename(remoteloc)
            basefolder = os.path.dirname(remoteloc)
            logger.debug('SFTP: Moving to folder: %s' % basefolder)
            # local = os.path.join(localloc, folder)
            # logger.debug('SFTP: Setting local location to: %s' % local)
            with self.connection.cd(basefolder):
                logger.debug('SFTP: Mirroring: %s' % folder)
                self.connection.get_r(folder, localdir=localloc, callback=self.receivestatus)
        else:
            logger.debug('SFTP: Getting local: %s' % remoteloc)
            self.connection.get('%s' % remoteloc, localpath=localloc, callback=self.receivestatus)
        logger.debug('SFTP: Closing connection')
        self.connection.close()
        self.isopen = False

    def receivestatus(self, btrans, btotal):
        self.btrans = float(btrans)
        self.btotal = float(btotal)
        if self.btrans and self.btotal:
            logger.debug((self.btrans / self.btotal) * 100)

    def get_status(self):
        if self.btotal:
            percentstring = '{0: .2f}%'.format((self.btrans / self.btotal) * 100)
            return percentstring
        else:
            return 100

class CustomConnection(pysftp.Connection):

    def get_r(self, remotedir, localdir, preserve_mtime=False, callback=None):
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
                        os.mkdir(reparent(localdir, subdir))
                        wtcb.dlist = wtcb.dlist + [subdir, ]

            self.get(fname,
                     reparent(localdir, fname),
                     preserve_mtime=preserve_mtime, callback=callback)
