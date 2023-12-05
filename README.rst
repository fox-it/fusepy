fusepy3
=======

``fusepy3`` is a Python module that provides a simple interface to FUSE_. It's a port of the `fusepy`_ module for compatibility with libfuse3.

``fusepy3`` is written in 3x syntax.

examples
--------
See some examples of how you can use fusepy:

:memory_: A simple memory filesystem
:loopback_: A loopback filesystem
:context_: Sample usage of fuse_get_context()
:sftp_: A simple SFTP filesystem (requires paramiko)

To get started download_ fusepy or just browse the source_.

fusepy requires FUSE 3 (or later) and runs on:

- Linux (i386, x86_64, PPC, arm64, MIPS)
- Mac OS X (Intel, PowerPC)
- FreeBSD (i386, amd64)


.. _fusepy: https://github.com/fusepy/fusepy
.. _FUSE: http://fuse.sourceforge.net/

.. _officially hosted on GitHub: source_
.. _download: https://github.com/fox-it/fusepy3/zipball/master
.. _source: https://github.com/fox-it/fusepy3

.. examples
.. _memory: https://github.com/fox-it/fusepy3/blob/master/legacy/examples/memory.py
.. _loopback: https://github.com/fox-it/fusepy3/blob/master/legacy/examples/loopback.py
.. _context: https://github.com/fox-it/fusepy3/blob/master/legacy/examples/context.py
.. _sftp: https://github.com/fox-it/fusepy3/blob/master/legacy/examples/sftp.py
