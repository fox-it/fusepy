# Copyright (c) 2012 Terence Honles <terence@honles.com> (maintainer)
# Copyright (c) 2008 Giorgos Verigakis <verigak@gmail.com> (author)
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import absolute_import, division, print_function

import ctypes
import errno
import logging
import os
import warnings
from functools import partial
from signal import SIG_DFL, SIGINT, signal
from stat import S_IFDIR

from fuse3.c_fuse import (
    ENOTSUP,
    c_gid_t,
    c_stat,
    c_uid_t,
    fuse_exit,
    fuse_file_info_p,
    fuse_operations,
    get_fuse_context,
)
from fuse3.util import libfuse

log = logging.getLogger("fuse")


def time_of_timespec(ts, use_ns=False):
    if use_ns:
        return ts.tv_sec * 10**9 + ts.tv_nsec
    else:
        return ts.tv_sec + ts.tv_nsec / 1e9


def set_st_attrs(st, attrs, use_ns=False):
    for key, val in attrs.items():
        if key in ("st_atime", "st_mtime", "st_ctime", "st_birthtime"):
            timespec = getattr(st, key + "spec", None)
            if timespec is None:
                continue

            if use_ns:
                timespec.tv_sec, timespec.tv_nsec = divmod(int(val), 10**9)
            else:
                timespec.tv_sec = int(val)
                timespec.tv_nsec = int((val - timespec.tv_sec) * 1e9)
        elif hasattr(st, key):
            setattr(st, key, val)


class FuseOSError(OSError):
    def __init__(self, errno):
        super(FuseOSError, self).__init__(errno, os.strerror(errno))


class FUSE3:
    """
    This class is the lower level interface and should not be subclassed under
    normal use. Its methods are called by fuse.

    Assumes API version 3+ or later.
    """

    OPTIONS = (
        ("foreground", "-f"),
        ("debug", "-d"),
        ("nothreads", "-s"),
    )

    def __init__(self, operations, mountpoint, raw_fi=False, encoding="utf-8", **kwargs):
        """
        Setting raw_fi to True will cause FUSE to pass the fuse_file_info
        class as is to Operations, instead of just the fh field.

        This gives you access to direct_io, keep_cache, etc.
        """

        self.operations = operations
        self.raw_fi = raw_fi
        self.encoding = encoding
        self.__critical_exception = None

        self.use_ns = getattr(operations, "use_ns", False)
        if not self.use_ns:
            warnings.warn(
                "Time as floating point seconds for utimens is deprecated!\n"
                'To enable time as nanoseconds set the property "use_ns" to '
                "True in your operations class or set your fusepy "
                "requirements to <4.",
                DeprecationWarning,
            )

        args = ["fuse3"]

        args.extend(flag for arg, flag in self.OPTIONS if kwargs.pop(arg, False))

        kwargs.setdefault("fsname", operations.__class__.__name__)
        args.append("-o")
        args.append(",".join(self._normalize_fuse_options(**kwargs)))
        args.append(mountpoint)

        args = [arg.encode(encoding) for arg in args]
        argv = (ctypes.c_char_p * len(args))(*args)

        fuse_ops = fuse_operations()
        for ent in fuse_operations._fields_:
            name, prototype = ent[:2]

            check_name = name

            # ftruncate()/fgetattr() are implemented in terms of their
            # non-f-prefixed versions in the operations object
            if check_name in ["ftruncate", "fgetattr"]:
                check_name = check_name[1:]

            val = getattr(operations, check_name, None)
            if val is None:
                continue

            # Function pointer members are tested for using the
            # getattr(operations, name) above but are dynamically
            # invoked using self.operations(name)
            if hasattr(prototype, "argtypes"):
                val = prototype(partial(self._wrapper, getattr(self, name)))

            setattr(fuse_ops, name, val)

        try:
            old_handler = signal(SIGINT, SIG_DFL)
        except ValueError:
            old_handler = SIG_DFL

        err = libfuse.fuse_main_real(len(args), argv, ctypes.pointer(fuse_ops), ctypes.sizeof(fuse_ops), None)

        try:
            signal(SIGINT, old_handler)
        except ValueError:
            pass

        del self.operations  # Invoke the destructor
        if self.__critical_exception:
            raise self.__critical_exception
        if err:
            raise RuntimeError(err)

    @staticmethod
    def _normalize_fuse_options(**kargs):
        for key, value in kargs.items():
            if isinstance(value, bool):
                if value is True:
                    yield key
            else:
                yield "%s=%s" % (key, value)

    @staticmethod
    def _wrapper(func, *args, **kwargs):
        "Decorator for the methods that follow"

        try:
            if func.__name__ == "init":
                # init may not fail, as its return code is just stored as
                # private_data field of struct fuse_context
                return func(*args, **kwargs) or 0

            else:
                try:
                    return func(*args, **kwargs) or 0

                except OSError as e:
                    if e.errno > 0:
                        log.debug(
                            "FUSE operation %s raised a %s, returning errno %s.",
                            func.__name__,
                            type(e),
                            e.errno,
                            exc_info=True,
                        )
                        return -e.errno
                    else:
                        log.error(
                            "FUSE operation %s raised an OSError with negative " "errno %s, returning errno.EINVAL.",
                            func.__name__,
                            e.errno,
                            exc_info=True,
                        )
                        return -errno.EINVAL

                except Exception:
                    log.error(
                        "Uncaught exception from FUSE operation %s, returning errno.EINVAL.",
                        func.__name__,
                        exc_info=True,
                    )
                    return -errno.EINVAL

        except BaseException:
            log.critical(
                "Uncaught critical exception from FUSE operation %s, aborting.",
                func.__name__,
                exc_info=True,
            )
            # the raised exception (even SystemExit) will be caught by FUSE
            # potentially causing SIGSEGV, so tell system to stop/interrupt FUSE
            fuse_exit()
            return -errno.EFAULT

    def _decode_optional_path(self, path):
        # NB: this method is intended for fuse operations that
        #     allow the path argument to be NULL,
        #     *not* as a generic path decoding method
        if path is None:
            return None
        return path.decode(self.encoding)

    def getattr(self, path, buf, fip):
        fh = self._get_fileheader(fip)
        return self.fgetattr(path, buf, fh)

    def readlink(self, path, buf, bufsize):
        ret = self.operations("readlink", path.decode(self.encoding)).encode(self.encoding)

        # copies a string into the given buffer
        # (null terminated and truncated if necessary)
        data = ctypes.create_string_buffer(ret[: bufsize - 1])
        ctypes.memmove(buf, data, len(data))
        return 0

    def mknod(self, path, mode, dev):
        return self.operations("mknod", path.decode(self.encoding), mode, dev)

    def mkdir(self, path, mode):
        return self.operations("mkdir", path.decode(self.encoding), mode)

    def unlink(self, path):
        return self.operations("unlink", path.decode(self.encoding))

    def rmdir(self, path):
        return self.operations("rmdir", path.decode(self.encoding))

    def symlink(self, source, target):
        "creates a symlink `target -> source` (e.g. ln -s source target)"

        return self.operations("symlink", target.decode(self.encoding), source.decode(self.encoding))

    def rename(self, old, new, flags):
        return self.operations("rename", old.decode(self.encoding), new.decode(self.encoding), flags)

    def link(self, source, target):
        "creates a hard link `target -> source` (e.g. ln source target)"

        return self.operations("link", target.decode(self.encoding), source.decode(self.encoding))

    def chmod(self, path, mode, fip):
        fh = self._get_fileheader(fip)

        return self.operations("chmod", path.decode(self.encoding), mode, fh)

    def chown(self, path, uid, gid, fip):
        # Check if any of the arguments is a -1 that has overflowed
        if c_uid_t(uid + 1).value == 0:
            uid = -1
        if c_gid_t(gid + 1).value == 0:
            gid = -1

        fh = self._get_fileheader(fip)
        return self.operations("chown", path.decode(self.encoding), uid, gid, fh)

    def truncate(self, path, length, fip):
        return self.operations("truncate", path.decode(self.encoding), length, fip)

    def open(self, path, fip):
        fi = fip.contents
        if self.raw_fi:
            return self.operations("open", path.decode(self.encoding), fi)
        else:
            fi.fh = self.operations("open", path.decode(self.encoding), fi.flags)

            return 0

    def read(self, path, buf, size, offset, fip):
        fh = self._get_fileheader(fip)

        ret = self.operations("read", self._decode_optional_path(path), size, offset, fh)

        if not ret:
            return 0

        retsize = len(ret)
        assert retsize <= size, "actual amount read %d greater than expected %d" % (
            retsize,
            size,
        )

        ctypes.memmove(buf, ret, retsize)
        return retsize

    def write(self, path, buf, size, offset, fip):
        data = ctypes.string_at(buf, size)

        fh = self._get_fileheader(fip)

        return self.operations("write", self._decode_optional_path(path), data, offset, fh)

    def statfs(self, path, buf):
        stv = buf.contents
        attrs = self.operations("statfs", path.decode(self.encoding))
        for key, val in attrs.items():
            if hasattr(stv, key):
                setattr(stv, key, val)

        return 0

    def flush(self, path, fip):
        fh = self._get_fileheader(fip)
        return self.operations("flush", self._decode_optional_path(path), fh)

    def release(self, path, fip):
        fh = self._get_fileheader(fip)
        return self.operations("release", self._decode_optional_path(path), fh)

    def fsync(self, path, datasync, fip):
        fh = self._get_fileheader(fip)
        return self.operations("fsync", self._decode_optional_path(path), datasync, fh)

    def setxattr(self, path, name, value, size, options, *args):
        return self.operations(
            "setxattr",
            path.decode(self.encoding),
            name.decode(self.encoding),
            ctypes.string_at(value, size),
            options,
            *args,
        )

    def getxattr(self, path, name, value, size, *args):
        ret = self.operations("getxattr", path.decode(self.encoding), name.decode(self.encoding), *args)

        retsize = len(ret)
        # allow size queries
        if not value:
            return retsize

        # do not truncate
        if retsize > size:
            return -errno.ERANGE

        # Does not add trailing 0
        buf = ctypes.create_string_buffer(ret, retsize)
        ctypes.memmove(value, buf, retsize)

        return retsize

    def listxattr(self, path, namebuf, size):
        attrs = self.operations("listxattr", path.decode(self.encoding)) or ""
        ret = "\x00".join(attrs).encode(self.encoding)
        if len(ret) > 0:
            ret += "\x00".encode(self.encoding)

        retsize = len(ret)
        # allow size queries
        if not namebuf:
            return retsize

        # do not truncate
        if retsize > size:
            return -errno.ERANGE

        buf = ctypes.create_string_buffer(ret, retsize)
        ctypes.memmove(namebuf, buf, retsize)

        return retsize

    def removexattr(self, path, name):
        return self.operations("removexattr", path.decode(self.encoding), name.decode(self.encoding))

    def opendir(self, path, fip):
        # Ignore raw_fi
        fip.contents.fh = self.operations("opendir", path.decode(self.encoding))

        return 0

    def readdir(self, path, buf, filler, offset, fip, flags):
        # Ignore raw_fi
        for item in self.operations("readdir", self._decode_optional_path(path), fip.contents.fh, flags):
            if isinstance(item, str):
                name, st, offset = item, None, 0
            else:
                name, attrs, offset = item
                if attrs:
                    st = c_stat()
                    set_st_attrs(st, attrs, use_ns=self.use_ns)
                else:
                    st = None
            if filler(buf, name.encode(self.encoding), st, offset, 0) != 0:
                break

        return 0

    def releasedir(self, path, fip):
        # Ignore raw_fi
        return self.operations("releasedir", self._decode_optional_path(path), fip.contents.fh)

    def fsyncdir(self, path, datasync, fip):
        # Ignore raw_fi
        return self.operations("fsyncdir", self._decode_optional_path(path), datasync, fip.contents.fh)

    def init(self, conn=None, cfg=None):
        self.operations("init", "/", conn, cfg)
        # This is because I saw a lot of examples returning the private_data field.
        return get_fuse_context().contents.private_data

    def destroy(self, private_data):
        return self.operations("destroy", "/")

    def access(self, path, amode):
        return self.operations("access", path.decode(self.encoding), amode)

    def create(self, path, mode, fip):
        fi = fip.contents
        path = path.decode(self.encoding)

        if self.raw_fi:
            return self.operations("create", path, mode, fi)
        else:
            fi.fh = self.operations("create", path, mode)
            return 0

    def ftruncate(self, path, length, fip):
        # couldn't use fip at this moment in time, setting it to None for operations.
        return self.operations("truncate", self._decode_optional_path(path), length, None)

    def fgetattr(self, path, buf, fip):
        ctypes.memset(buf, 0, ctypes.sizeof(c_stat))

        st = buf.contents
        fh = self._get_fileheader(fip)

        attrs = self.operations("getattr", self._decode_optional_path(path), fh)
        set_st_attrs(st, attrs, use_ns=self.use_ns)
        return 0

    def lock(self, path, fip, cmd, lock):
        fh = self._get_fileheader(fip)

        return self.operations("lock", self._decode_optional_path(path), fh, cmd, lock)

    def utimens(self, path, timespec, fip):
        if timespec:
            atime = time_of_timespec(timespec.actime, use_ns=self.use_ns)
            mtime = time_of_timespec(timespec.modtime, use_ns=self.use_ns)
            times = (atime, mtime)
        else:
            times = None

        # Ignore fip for now
        # it seems to crash once an attempt is made to open it.

        return self.operations("utimens", path.decode(self.encoding), times, None)

    def bmap(self, path, blocksize, idx):
        return self.operations("bmap", path.decode(self.encoding), blocksize, idx)

    def ioctl(self, path, cmd, arg, fip, flags, data):
        fh = self._get_fileheader(fip)

        return self.operations("ioctl", path.decode(self.encoding), cmd, arg, fh, flags, data)

    def poll(self, path, fip, ph, reventsp):
        fh = self._get_fileheader(fip)

        return self.operations("poll", path.decode(self.encoding), fh, ph, reventsp)

    def write_buf(self, path, buf, off, fip):
        fh = self._get_fileheader(fip)

        return self.operations("write_buf", path.decode(self.encoding), buf, off, fh)

    def read_buf(self, path, bufp, size, off, fip) -> int:
        fh = self._get_fileheader(fip)

        return self.operations("read_buf", path.decode(self.encoding), bufp, size, off, fh)

    def flock(self, path, fip, op):
        fh = self._get_fileheader(fip)
        return self.operations("flock", path.decode(self.encoding), fh, op)

    def fallocate(self, path, mode, offset, length, fip):
        fh = self._get_fileheader(fip)
        return self.operations("fallocate", path.decode(self.encoding), mode, offset, length, fh)

    def copy_file_range(self, path_in, fip_in, off_in, path_out, fip_out, off_out, size, flags):
        fh_1 = self._get_fileheader(fip_in)
        fh_2 = self._get_fileheader(fip_out)
        return self.operations(
            "copy_file_range",
            path_in.decode(self.encoding),
            fh_1,
            off_in,
            path_out.decode(self.encoding),
            fh_2,
            off_out,
            size,
            flags,
        )

    def lseek(self, path, off, whence, fip):
        fh = self._get_fileheader(fip)
        return self.operations("lseek", path.decode(self.encoding), off, whence, fh)

    def _get_fileheader(self, fip: fuse_file_info_p):
        if not fip:
            return None

        if isinstance(fip, int):
            return fip

        fh = fip.contents
        if not self.raw_fi:
            fh = fh.fh

        return fh


class Operations:
    """
    This class should be subclassed and passed as an argument to FUSE on
    initialization. All operations should raise a FuseOSError exception on
    error.

    When in doubt of what an operation should do, check the FUSE header file
    or the corresponding system call man page.
    """

    def __call__(self, op, *args):
        if not hasattr(self, op):
            raise FuseOSError(errno.EFAULT)
        return getattr(self, op)(*args)

    def getattr(self, path, fh=None):
        """
        Returns a dictionary with keys identical to the stat C structure of
        stat(2).

        st_atime, st_mtime and st_ctime should be floats.

        NOTE: There is an incompatibility between Linux and Mac OS X
        concerning st_nlink of directories. Mac OS X counts all files inside
        the directory, while Linux counts only the subdirectories.
        """

        if path != "/":
            raise FuseOSError(errno.ENOENT)
        return dict(st_mode=(S_IFDIR | 0o755), st_nlink=2)

    def readlink(self, path):
        raise FuseOSError(errno.ENOENT)

    def mknod(self, path, mode, dev):
        raise FuseOSError(errno.EROFS)

    def mkdir(self, path, mode):
        raise FuseOSError(errno.EROFS)

    def unlink(self, path):
        raise FuseOSError(errno.EROFS)

    def rmdir(self, path):
        raise FuseOSError(errno.EROFS)

    def symlink(self, target, source):
        "creates a symlink `target -> source` (e.g. ln -s source target)"

        raise FuseOSError(errno.EROFS)

    def rename(self, old, new, flags):
        raise FuseOSError(errno.EROFS)

    def link(self, target, source):
        "creates a hard link `target -> source` (e.g. ln source target)"

        raise FuseOSError(errno.EROFS)

    def chmod(self, path, mode):
        raise FuseOSError(errno.EROFS)

    def chown(self, path, uid, gid):
        raise FuseOSError(errno.EROFS)

    truncate = None
    """Change the size of a file.

    Used for both ftruncate and truncate

    signature: truncate(self, path: str, length: int, fd: int)

    man page: `$ man ftruncate`

    Args:
        path: The file name
        length: the bytes to truncate
        fd: the file descriptor (only used in ftruncate)
    """

    def open(self, path, flags):
        """
        When raw_fi is False (default case), open should return a numerical
        file handle.

        When raw_fi is True the signature of open becomes:
            open(self, path, fi)

        and the file handle should be set directly.
        """

        return 0

    def read(self, path, size, offset, fh) -> str:
        "Returns a string containing the data requested."

        raise FuseOSError(errno.EIO)

    def write(self, path, data, offset, fh):
        raise FuseOSError(errno.EROFS)

    def statfs(self, path):
        """
        Returns a dictionary with keys identical to the statvfs C structure of
        statvfs(3).

        On Mac OS X f_bsize and f_frsize must be a power of 2
        (minimum 512).
        """

        return {}

    def flush(self, path: str, fh):
        return 0

    def release(self, path: str, fh):
        return 0

    def fsync(self, path: str, datasync, fh):
        return 0

    def setxattr(self, path: str, name, value, options, position=0):
        raise FuseOSError(ENOTSUP)

    def getxattr(self, path: str, name, position=0):
        raise FuseOSError(ENOTSUP)

    def listxattr(self, path: str):
        return []

    def removexattr(self, path: str, name: str):
        raise FuseOSError(ENOTSUP)

    def opendir(self, path: str):
        "Returns a numerical file handle."

        return 0

    def readdir(self, path: str, fh: int, flags: int):
        """
        Can return either a list of names, or a list of (name, attrs, offset)
        tuples. attrs is a dict as in getattr.
        """

        return [".", ".."]

    def releasedir(self, path: str, fh):
        return 0

    def fsyncdir(self, path: str, datasync, fh):
        return 0

    def init(self, path: str, conn=None, cfg=None):
        """
        Called on filesystem initialization. (Path is always /)

        Use it instead of __init__ if you start threads on initialization.
        """

        pass

    def destroy(self, path: str):
        "Called on filesystem destruction. Path is always /"

        pass

    def access(self, path: str, amode):
        return 0

    def create(self, path: str, mode, fi=None):
        """
        When raw_fi is False (default case), fi is None and create should
        return a numerical file handle.

        When raw_fi is True the file handle should be set directly by create
        and return 0.
        """

        raise FuseOSError(errno.EROFS)

    lock = None

    def utimens(self, path: str, times=None, fi=None):
        "Times is a (atime, mtime) tuple. If None use current time."

        return 0

    bmap = None
    """Map block index within file to block index within device.

    signature: bmap(self, path: int, block: int, idx)

    Args:
        path: The path to the block device.
        blocksize: The block size of the device.
        idx: Pointer to the indexes to map.
    """

    ioctl = None
    """Manipulates underlying devuce parameters of special files.

    signature: ioctl(
        self,
        path: str,
        cmd: int,
        arg: int,
        fd: int,
        flags: int,
        data: int
    )

    man page: `$ man ioctl`

    Args:
        path: The file name.
        cmd: The type of operation to perform.
        arg: Arguments to the ioctl device as a memory address.
        fd: File descriptor.
        flags:
        data:
    """

    poll = None
    """Poll for IO readiness events.

    signature: poll(self, path: str, fd: int, ph: int, reventsp: int)

    man page: `$ man poll`

    Args:
        path: The file name.
        fd: The file descriptor.
        ph: A memory address to polhandles.
        reventsp: A memory address to ....?
    """

    write_buf = None
    """Write contents of buffer to an open file.

    signature: write_buf(self, path: str, buf: bytes, off: int, fd: int)

    Args:
        path: The file name.
        buf: The data to write.
        off: The position in file name to start writing.
        fd: The file descriptor.
    """

    read_buf = None
    """Store data from an open file in a buffer.

    signature: read_buf(self, path: str, size: int, off: int, fd: int)

    Args:
        path: The file name.
        size: The number of bytes to read.
        off: The offset from where to read.
        fd: The file descriptor.
    """

    flock = None
    """Perform BSD file locking operation.

    signature: flock(self, path: str, fd: int, operation: int)

    man page: `$ man flock\\(2\\)`

    Args:
        path: The file name.
        fd: The file descriptor.
        operation: The type of lock to place.
    """

    fallocate = None
    """Allocates space for an open file.

    signature: fallocate(self, path: str, mode: int, offset: int, length: int, fd: int)
    man page: `$ man fallocate\\(2\\)`

    Args:
        path: The file name.
        mode: How it should allocate.
        offset: Where to start allocating.
        length: The number of bytes to allocate.
        fd: The file descriptor.
    """

    copy_file_range = None
    """Copy a range of data from one file to another.

    Overwrites any data inside that range.

    man page: `$ man copy_file_range`


    signature: copy_file_range(
        self,
        path_in: str,
        fh_in: Optional[int],
        off_in: int,
        path_out: str,
        fh_out: Optional[int],
        off_out: int,
        size: int,
        flags: int
    )

    Args:
        path_in: The file name to read from.
        fip_in: The file descriptor of the input file.
        off_in: The offset where to start from.
        path_out: The file name to write to.
        fh_out: The file descriptor of the output file.
        off_out: Where to start writing.
        size: the bytes to write.
        flags: Currently 0, used in the future

    """

    lseek = None
    """Find the next data or hole after the specified offset.

    signature: lseek(self, path: str, off: int, whence: int, fd: Optional[int])

    man page: `$ man lseek`

    Args:
        path: The filepath.
        off: The offset into the file.
        whence: Where it should start looking.
        fd: The file descriptor.
    """


class LoggingMixIn:
    log = logging.getLogger("fuse.log-mixin")

    def __call__(self, op, path, *args):
        self.log.debug("-> %s %s %s", op, path, repr(args))
        ret = "[Unhandled Exception]"
        try:
            ret = getattr(self, op)(path, *args)
            return ret
        except OSError as e:
            ret = str(e)
            raise
        finally:
            self.log.debug("<- %s %s", op, repr(ret))
