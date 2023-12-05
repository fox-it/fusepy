import ctypes
from platform import machine, system

from fuse3.util import libfuse

_system = system()
_machine = machine()

c_byte_p = ctypes.POINTER(ctypes.c_byte)


if _system == "Windows":
    # NOTE:
    #
    # sizeof(long)==4 on Windows 32-bit and 64-bit
    # sizeof(long)==4 on Cygwin 32-bit and ==8 on Cygwin 64-bit
    #
    # We have to fix up c_long and c_ulong so that it matches the
    # Cygwin (and UNIX) sizes when run on Windows.
    import sys

    if sys.maxsize > 0xFFFFFFFF:
        c_win_long = ctypes.c_int64
        c_win_ulong = ctypes.c_uint64
    else:
        c_win_long = ctypes.c_int32
        c_win_ulong = ctypes.c_uint32

if _system == "Windows" or _system.startswith("CYGWIN"):

    class c_timespec(ctypes.Structure):
        _fields_ = [("tv_sec", c_win_long), ("tv_nsec", c_win_long)]

else:

    class c_timespec(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]


class c_utimbuf(ctypes.Structure):
    _fields_ = [("actime", c_timespec), ("modtime", c_timespec)]


class c_stat(ctypes.Structure):
    pass  # Platform dependent


if _system == "Darwin" and hasattr(libfuse, "macfuse_version"):
    _system = "Darwin-MacFuse"


if _system in ("Darwin", "Darwin-MacFuse", "FreeBSD"):
    ENOTSUP = 45

    c_dev_t = ctypes.c_int32
    c_fsblkcnt_t = ctypes.c_ulong
    c_fsfilcnt_t = ctypes.c_ulong
    c_gid_t = ctypes.c_uint32
    c_mode_t = ctypes.c_uint16
    c_off_t = ctypes.c_int64
    c_pid_t = ctypes.c_int32
    c_uid_t = ctypes.c_uint32
    setxattr_t = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_char_p,
        c_byte_p,
        ctypes.c_size_t,
        ctypes.c_int,
        ctypes.c_uint32,
    )
    getxattr_t = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_char_p,
        c_byte_p,
        ctypes.c_size_t,
        ctypes.c_uint32,
    )
    if _system == "Darwin":
        c_stat._fields_ = [
            ("st_dev", c_dev_t),
            ("st_mode", c_mode_t),
            ("st_nlink", ctypes.c_uint16),
            ("st_ino", ctypes.c_uint64),
            ("st_uid", c_uid_t),
            ("st_gid", c_gid_t),
            ("st_rdev", c_dev_t),
            ("st_atimespec", c_timespec),
            ("st_mtimespec", c_timespec),
            ("st_ctimespec", c_timespec),
            ("st_birthtimespec", c_timespec),
            ("st_size", c_off_t),
            ("st_blocks", ctypes.c_int64),
            ("st_blksize", ctypes.c_int32),
            ("st_flags", ctypes.c_int32),
            ("st_gen", ctypes.c_int32),
            ("st_lspare", ctypes.c_int32),
            ("st_qspare", ctypes.c_int64),
        ]
    else:
        c_stat._fields_ = [
            ("st_dev", c_dev_t),
            ("st_ino", ctypes.c_uint32),
            ("st_mode", c_mode_t),
            ("st_nlink", ctypes.c_uint16),
            ("st_uid", c_uid_t),
            ("st_gid", c_gid_t),
            ("st_rdev", c_dev_t),
            ("st_atimespec", c_timespec),
            ("st_mtimespec", c_timespec),
            ("st_ctimespec", c_timespec),
            ("st_size", c_off_t),
            ("st_blocks", ctypes.c_int64),
            ("st_blksize", ctypes.c_int32),
        ]
elif _system == "Linux":
    ENOTSUP = 95

    c_dev_t = ctypes.c_ulonglong
    c_fsblkcnt_t = ctypes.c_ulonglong
    c_fsfilcnt_t = ctypes.c_ulonglong
    c_gid_t = ctypes.c_uint
    c_mode_t = ctypes.c_uint
    c_off_t = ctypes.c_longlong
    c_pid_t = ctypes.c_int
    c_uid_t = ctypes.c_uint
    setxattr_t = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_char_p,
        c_byte_p,
        ctypes.c_size_t,
        ctypes.c_int,
    )

    getxattr_t = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_char_p,
        c_byte_p,
        ctypes.c_size_t,
    )

    if _machine == "x86_64":
        c_stat._fields_ = [
            ("st_dev", c_dev_t),
            ("st_ino", ctypes.c_ulong),
            ("st_nlink", ctypes.c_ulong),
            ("st_mode", c_mode_t),
            ("st_uid", c_uid_t),
            ("st_gid", c_gid_t),
            ("__pad0", ctypes.c_int),
            ("st_rdev", c_dev_t),
            ("st_size", c_off_t),
            ("st_blksize", ctypes.c_long),
            ("st_blocks", ctypes.c_long),
            ("st_atimespec", c_timespec),
            ("st_mtimespec", c_timespec),
            ("st_ctimespec", c_timespec),
        ]
    elif _machine == "mips":
        c_stat._fields_ = [
            ("st_dev", c_dev_t),
            ("__pad1_1", ctypes.c_ulong),
            ("__pad1_2", ctypes.c_ulong),
            ("__pad1_3", ctypes.c_ulong),
            ("st_ino", ctypes.c_ulong),
            ("st_mode", c_mode_t),
            ("st_nlink", ctypes.c_ulong),
            ("st_uid", c_uid_t),
            ("st_gid", c_gid_t),
            ("st_rdev", c_dev_t),
            ("__pad2_1", ctypes.c_ulong),
            ("__pad2_2", ctypes.c_ulong),
            ("st_size", c_off_t),
            ("__pad3", ctypes.c_ulong),
            ("st_atimespec", c_timespec),
            ("__pad4", ctypes.c_ulong),
            ("st_mtimespec", c_timespec),
            ("__pad5", ctypes.c_ulong),
            ("st_ctimespec", c_timespec),
            ("__pad6", ctypes.c_ulong),
            ("st_blksize", ctypes.c_long),
            ("st_blocks", ctypes.c_long),
            ("__pad7_1", ctypes.c_ulong),
            ("__pad7_2", ctypes.c_ulong),
            ("__pad7_3", ctypes.c_ulong),
            ("__pad7_4", ctypes.c_ulong),
            ("__pad7_5", ctypes.c_ulong),
            ("__pad7_6", ctypes.c_ulong),
            ("__pad7_7", ctypes.c_ulong),
            ("__pad7_8", ctypes.c_ulong),
            ("__pad7_9", ctypes.c_ulong),
            ("__pad7_10", ctypes.c_ulong),
            ("__pad7_11", ctypes.c_ulong),
            ("__pad7_12", ctypes.c_ulong),
            ("__pad7_13", ctypes.c_ulong),
            ("__pad7_14", ctypes.c_ulong),
        ]
    elif _machine == "ppc":
        c_stat._fields_ = [
            ("st_dev", c_dev_t),
            ("st_ino", ctypes.c_ulonglong),
            ("st_mode", c_mode_t),
            ("st_nlink", ctypes.c_uint),
            ("st_uid", c_uid_t),
            ("st_gid", c_gid_t),
            ("st_rdev", c_dev_t),
            ("__pad2", ctypes.c_ushort),
            ("st_size", c_off_t),
            ("st_blksize", ctypes.c_long),
            ("st_blocks", ctypes.c_longlong),
            ("st_atimespec", c_timespec),
            ("st_mtimespec", c_timespec),
            ("st_ctimespec", c_timespec),
        ]
    elif _machine == "ppc64" or _machine == "ppc64le":
        c_stat._fields_ = [
            ("st_dev", c_dev_t),
            ("st_ino", ctypes.c_ulong),
            ("st_nlink", ctypes.c_ulong),
            ("st_mode", c_mode_t),
            ("st_uid", c_uid_t),
            ("st_gid", c_gid_t),
            ("__pad", ctypes.c_uint),
            ("st_rdev", c_dev_t),
            ("st_size", c_off_t),
            ("st_blksize", ctypes.c_long),
            ("st_blocks", ctypes.c_long),
            ("st_atimespec", c_timespec),
            ("st_mtimespec", c_timespec),
            ("st_ctimespec", c_timespec),
        ]
    elif _machine == "aarch64":
        c_stat._fields_ = [
            ("st_dev", c_dev_t),
            ("st_ino", ctypes.c_ulong),
            ("st_mode", c_mode_t),
            ("st_nlink", ctypes.c_uint),
            ("st_uid", c_uid_t),
            ("st_gid", c_gid_t),
            ("st_rdev", c_dev_t),
            ("__pad1", ctypes.c_ulong),
            ("st_size", c_off_t),
            ("st_blksize", ctypes.c_int),
            ("__pad2", ctypes.c_int),
            ("st_blocks", ctypes.c_long),
            ("st_atimespec", c_timespec),
            ("st_mtimespec", c_timespec),
            ("st_ctimespec", c_timespec),
        ]
    else:
        # i686, use as fallback for everything else
        c_stat._fields_ = [
            ("st_dev", c_dev_t),
            ("__pad1", ctypes.c_ushort),
            ("__st_ino", ctypes.c_ulong),
            ("st_mode", c_mode_t),
            ("st_nlink", ctypes.c_uint),
            ("st_uid", c_uid_t),
            ("st_gid", c_gid_t),
            ("st_rdev", c_dev_t),
            ("__pad2", ctypes.c_ushort),
            ("st_size", c_off_t),
            ("st_blksize", ctypes.c_long),
            ("st_blocks", ctypes.c_longlong),
            ("st_atimespec", c_timespec),
            ("st_mtimespec", c_timespec),
            ("st_ctimespec", c_timespec),
            ("st_ino", ctypes.c_ulonglong),
        ]
elif _system == "Windows" or _system.startswith("CYGWIN"):
    ENOTSUP = 129 if _system == "Windows" else 134
    c_dev_t = ctypes.c_uint
    c_fsblkcnt_t = c_win_ulong
    c_fsfilcnt_t = c_win_ulong
    c_gid_t = ctypes.c_uint
    c_mode_t = ctypes.c_uint
    c_off_t = ctypes.c_longlong
    c_pid_t = ctypes.c_int
    c_uid_t = ctypes.c_uint
    setxattr_t = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_char_p,
        c_byte_p,
        ctypes.c_size_t,
        ctypes.c_int,
    )
    getxattr_t = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_char_p,
        c_byte_p,
        ctypes.c_size_t,
    )
    c_stat._fields_ = [
        ("st_dev", c_dev_t),
        ("st_ino", ctypes.c_ulonglong),
        ("st_mode", c_mode_t),
        ("st_nlink", ctypes.c_ushort),
        ("st_uid", c_uid_t),
        ("st_gid", c_gid_t),
        ("st_rdev", c_dev_t),
        ("st_size", c_off_t),
        ("st_atimespec", c_timespec),
        ("st_mtimespec", c_timespec),
        ("st_ctimespec", c_timespec),
        ("st_blksize", ctypes.c_int),
        ("st_blocks", ctypes.c_longlong),
        ("st_birthtimespec", c_timespec),
    ]
else:
    raise NotImplementedError("%s is not supported." % _system)


c_stat_p = ctypes.POINTER(c_stat)


if _system == "FreeBSD":
    c_fsblkcnt_t = ctypes.c_uint64
    c_fsfilcnt_t = ctypes.c_uint64
    setxattr_t = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_char_p,
        c_byte_p,
        ctypes.c_size_t,
        ctypes.c_int,
    )

    getxattr_t = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_char_p,
        c_byte_p,
        ctypes.c_size_t,
    )

    class c_statvfs(ctypes.Structure):
        _fields_ = [
            ("f_bavail", c_fsblkcnt_t),
            ("f_bfree", c_fsblkcnt_t),
            ("f_blocks", c_fsblkcnt_t),
            ("f_favail", c_fsfilcnt_t),
            ("f_ffree", c_fsfilcnt_t),
            ("f_files", c_fsfilcnt_t),
            ("f_bsize", ctypes.c_ulong),
            ("f_flag", ctypes.c_ulong),
            ("f_frsize", ctypes.c_ulong),
        ]

elif _system == "Windows" or _system.startswith("CYGWIN"):

    class c_statvfs(ctypes.Structure):
        _fields_ = [
            ("f_bsize", c_win_ulong),
            ("f_frsize", c_win_ulong),
            ("f_blocks", c_fsblkcnt_t),
            ("f_bfree", c_fsblkcnt_t),
            ("f_bavail", c_fsblkcnt_t),
            ("f_files", c_fsfilcnt_t),
            ("f_ffree", c_fsfilcnt_t),
            ("f_favail", c_fsfilcnt_t),
            ("f_fsid", c_win_ulong),
            ("f_flag", c_win_ulong),
            ("f_namemax", c_win_ulong),
        ]

else:

    class c_statvfs(ctypes.Structure):
        _fields_ = [
            ("f_bsize", ctypes.c_ulong),
            ("f_frsize", ctypes.c_ulong),
            ("f_blocks", c_fsblkcnt_t),
            ("f_bfree", c_fsblkcnt_t),
            ("f_bavail", c_fsblkcnt_t),
            ("f_files", c_fsfilcnt_t),
            ("f_ffree", c_fsfilcnt_t),
            ("f_favail", c_fsfilcnt_t),
            ("f_fsid", ctypes.c_ulong),
            ("f_flag", ctypes.c_ulong),
            ("f_namemax", ctypes.c_ulong),
        ]


c_statvfs_p = ctypes.POINTER(c_statvfs)


class fuse_file_info(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_int),
        ("writepage", ctypes.c_int, 1),
        ("direct_io", ctypes.c_uint, 1),
        ("keep_cache", ctypes.c_uint, 1),
        ("parallel_direct_writes", ctypes.c_uint, 1),
        ("flush", ctypes.c_uint, 1),
        ("nonseekable", ctypes.c_uint, 1),
        ("flock_release", ctypes.c_uint, 1),
        ("cache_readdir", ctypes.c_uint, 1),
        ("noflush", ctypes.c_uint, 1),
        ("padding", ctypes.c_uint, 23),
        ("padding2", ctypes.c_uint, 32),
        ("fh", ctypes.c_uint64),
        ("lock_owner", ctypes.c_uint64),
        ("poll_events", ctypes.c_uint32),
    ]


fuse_file_info_p = ctypes.POINTER(fuse_file_info)


class fuse_context(ctypes.Structure):
    _fields_ = [
        ("fuse", ctypes.c_void_p),
        ("uid", c_uid_t),
        ("gid", c_gid_t),
        ("pid", c_pid_t),
        ("private_data", ctypes.c_void_p),
        ("umask", c_mode_t),
    ]


libfuse.fuse_get_context.restype = ctypes.POINTER(fuse_context)


class fuse_buf(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_size_t),
        ("flags", ctypes.c_uint),
        ("mem", ctypes.c_void_p),
        ("fd", ctypes.c_int),
        ("pos", c_off_t),
    ]


class fuse_bufvec(ctypes.Structure):
    _fields_ = [
        ("count", ctypes.c_size_t),
        ("idx", ctypes.c_size_t),
        ("off", ctypes.c_size_t),
        ("buf", ctypes.ARRAY(fuse_buf, 1)),
    ]


fuse_bufvec_p = ctypes.POINTER(fuse_bufvec)
fuse_bufvec_pp = ctypes.POINTER(fuse_bufvec_p)


class fuse_conn_info(ctypes.Structure):
    """
    Documentation of structure:
        https://github.com/libfuse/libfuse/blob/2c736f516f28dfb5c58aff345c668a5ea6386295/include/fuse_common.h#L474 # noqa
    """

    _fields_ = [
        ("proto_major", ctypes.c_uint),
        ("proto_minor", ctypes.c_uint),
        ("max_write", ctypes.c_uint),
        ("max_read", ctypes.c_uint),
        ("max_readahead", ctypes.c_uint),
        ("capable", ctypes.c_uint),
        ("want", ctypes.c_uint),
        ("max_background", ctypes.c_uint),
        ("congestion_threshold", ctypes.c_uint),
        ("time_gran", ctypes.c_uint),
        ("reserved", ctypes.ARRAY(ctypes.c_uint, 22)),
    ]


fuse_conn_info_p = ctypes.POINTER(fuse_conn_info)


class fuse_config(ctypes.Structure):
    """
    Documentation of structure:
        https://github.com/libfuse/libfuse/blob/2c736f516f28dfb5c58aff345c668a5ea6386295/include/fuse.h#L96
    """

    _fields_ = [
        ("set_gid", ctypes.c_int),
        ("gid", ctypes.c_uint),
        ("set_uid", ctypes.c_int),
        ("uid", ctypes.c_uint),
        ("set_mode", ctypes.c_int),
        ("umask", ctypes.c_uint),
        ("entry_timeout", ctypes.c_double),
        ("negative_timeout", ctypes.c_double),
        ("attr_timeout", ctypes.c_double),
        ("intr", ctypes.c_int),
        ("intr_signal", ctypes.c_int),
        ("remember", ctypes.c_int),
        ("hard_remove", ctypes.c_int),
        ("use_ino", ctypes.c_int),
        ("readdir_ino", ctypes.c_int),
        ("direct_io", ctypes.c_int),
        ("kernel_cache", ctypes.c_int),
        ("auto_cache", ctypes.c_int),
        ("no_rofd_flush", ctypes.c_int),
        ("ac_attr_timeout_set", ctypes.c_int),
        ("ac_attr_timeout", ctypes.c_double),
        ("nullpath_ok", ctypes.c_int),
        ("parallel_direct_writes", ctypes.c_int),
        ("show_help", ctypes.c_int),
        ("modules", ctypes.c_char_p),
        ("debug", ctypes.c_int),
    ]


fuse_config_p = ctypes.POINTER(fuse_config)


class fuse_operations(ctypes.Structure):
    _fields_ = [
        (
            "getattr",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_stat_p,
                fuse_file_info_p,
            ),
        ),
        (
            "readlink",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_byte_p,
                ctypes.c_size_t,
            ),
        ),
        (
            "mknod",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_mode_t,
                c_dev_t,
            ),
        ),
        (
            "mkdir",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_mode_t,
            ),
        ),
        (
            "unlink",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
            ),
        ),
        (
            "rmdir",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
            ),
        ),
        (
            "symlink",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_char_p,
            ),
        ),
        (
            "rename",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_char_p,
            ),
        ),
        (
            "link",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_char_p,
            ),
        ),
        (
            "chmod",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_mode_t,
                fuse_file_info_p,
            ),
        ),
        (
            "chown",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_uid_t,
                c_gid_t,
                fuse_file_info_p,
            ),
        ),
        (
            "truncate",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_off_t,
                fuse_file_info_p,
            ),
        ),
        (
            "open",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                fuse_file_info_p,
            ),
        ),
        (
            "read",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_byte_p,
                ctypes.c_size_t,
                c_off_t,
                fuse_file_info_p,
            ),
        ),
        (
            "write",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_byte_p,
                ctypes.c_size_t,
                c_off_t,
                fuse_file_info_p,
            ),
        ),
        (
            "statfs",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_statvfs_p,
            ),
        ),
        (
            "flush",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                fuse_file_info_p,
            ),
        ),
        (
            "release",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                fuse_file_info_p,
            ),
        ),
        (
            "fsync",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                fuse_file_info_p,
            ),
        ),
        ("setxattr", setxattr_t),
        ("getxattr", getxattr_t),
        (
            "listxattr",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_byte_p,
                ctypes.c_size_t,
            ),
        ),
        (
            "removexattr",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_char_p,
            ),
        ),
        (
            "opendir",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                fuse_file_info_p,
            ),
        ),
        (
            "readdir",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_void_p,
                ctypes.CFUNCTYPE(
                    ctypes.c_int,
                    ctypes.c_void_p,
                    ctypes.c_char_p,
                    c_stat_p,
                    c_off_t,
                    ctypes.c_uint,
                ),
                c_off_t,
                fuse_file_info_p,
                ctypes.c_uint,
            ),
        ),
        (
            "releasedir",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                fuse_file_info_p,
            ),
        ),
        (
            "fsyncdir",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                fuse_file_info_p,
            ),
        ),
        (
            "init",
            ctypes.CFUNCTYPE(
                ctypes.c_void_p,
                fuse_conn_info_p,
                fuse_config_p,
            ),
        ),
        (
            "destroy",
            ctypes.CFUNCTYPE(
                ctypes.c_void_p,
                ctypes.c_void_p,
            ),
        ),
        (
            "access",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
            ),
        ),
        (
            "create",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_mode_t,
                fuse_file_info_p,
            ),
        ),
        (
            "ftruncate",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_off_t,
                fuse_file_info_p,
            ),
        ),
        (
            "fgetattr",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_stat_p,
                fuse_file_info_p,
            ),
        ),
        (
            "lock",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                fuse_file_info_p,
                ctypes.c_int,
                ctypes.c_void_p,
            ),
        ),
        (
            "utimens",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                c_utimbuf,
                fuse_file_info_p,
            ),
        ),
        (
            "bmap",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_ulonglong),
            ),
        ),
        (
            "ioctl",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_void_p,
                fuse_file_info_p,
                ctypes.c_uint,
                ctypes.c_void_p,
            ),
        ),
        (
            "poll",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                fuse_file_info_p,
                ctypes.c_void_p,
                ctypes.c_int,
            ),
        ),
        (
            "write_buf",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                fuse_bufvec_p,
                c_off_t,
                fuse_file_info_p,
            ),
        ),
        (
            "read_buf",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                fuse_bufvec_pp,
                ctypes.c_size_t,
                c_off_t,
                fuse_file_info_p,
            ),
        ),
        (
            "flock",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                fuse_file_info_p,
                ctypes.c_int,
            ),
        ),
        (
            "fallocate",
            ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                c_off_t,
                c_off_t,
                fuse_file_info_p,
            ),
        ),
        (
            "copy_file_range",
            ctypes.CFUNCTYPE(
                ctypes.c_ssize_t,
                ctypes.c_char_p,
                fuse_file_info_p,
                c_off_t,
                ctypes.c_char_p,
                fuse_file_info_p,
                c_off_t,
                ctypes.c_size_t,
                ctypes.c_int,
            ),
        ),
        (
            "lseek",
            ctypes.CFUNCTYPE(
                c_off_t,
                ctypes.c_char_p,
                c_off_t,
                ctypes.c_int,
                fuse_file_info_p,
            ),
        ),
    ]


def fuse_get_context():
    "Returns a (uid, gid, pid) tuple"

    ctxp = libfuse.fuse_get_context()
    ctx = ctxp.contents
    return ctx.uid, ctx.gid, ctx.pid


def get_fuse_context():
    return libfuse.fuse_get_context()


def fuse_exit():
    """
    This will shutdown the FUSE mount and cause the call to FUSE(...) to
    return, similar to sending SIGINT to the process.

    Flags the native FUSE session as terminated and will cause any running FUSE
    event loops to exit on the next opportunity. (see fuse.c::fuse_exit)
    """
    fuse_ptr = ctypes.c_void_p(libfuse.fuse_get_context().contents.fuse)
    libfuse.fuse_exit(fuse_ptr)
