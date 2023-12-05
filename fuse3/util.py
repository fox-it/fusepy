import ctypes
import os
import sys
from ctypes.util import find_library
from platform import system

_system = system()


def load_libfuse():
    _libfuse_path = os.environ.get("FUSE_LIBRARY_PATH")
    if not _libfuse_path:
        _libfuse_path = _find_libfuse()

    if not _libfuse_path:
        raise EnvironmentError("Unable to find libfuse3")
    else:
        _libfuse = ctypes.CDLL(_libfuse_path)

    return _libfuse


def _find_libfuse() -> str:
    _libfuse_path = None
    if _system == "Darwin":
        # libfuse dependency
        ctypes.CDLL(find_library("iconv"), ctypes.RTLD_GLOBAL)

        _libfuse_path = find_library("fuse4x") or find_library("osxfuse") or find_library("fuse3")
    elif _system == "Windows":
        import winreg as reg

        def Reg32GetValue(rootkey, keyname, valname):
            key, val = None, None
            try:
                key = reg.OpenKey(rootkey, keyname, 0, reg.KEY_READ | reg.KEY_WOW64_32KEY)
                val = str(reg.QueryValueEx(key, valname)[0])
            except OSError:
                pass
            finally:
                if key is not None:
                    reg.CloseKey(key)
            return val

        _libfuse_path = Reg32GetValue(reg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WinFsp", r"InstallDir")
        if _libfuse_path:
            _libfuse_path += r"bin\winfsp-%s.dll" % ("x64" if sys.maxsize > 0xFFFFFFFF else "x86")
    else:
        _libfuse_path = find_library("fuse3")

    return _libfuse_path


libfuse = load_libfuse()
