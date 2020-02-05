"""Definition and dynamic routing to Hangar backend implementations.

This module defines the available backends for a Hangar installation & provides
dynamic routing of method calls to the appropriate backend from a stored record
specification.

Identification
--------------

A two character ascii code identifies which backend/version some record belongs
to. Valid characters are the union of ``ascii_lowercase``, ``ascii_uppercase``,
and ``ascii_digits``:

.. centered:: ``abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789``

Though stored as bytes in the backend, we use human readable characters (and not
unprintable bytes) to aid in human tasks like developer database dumps and
debugging. The characters making up the two digit code have the following
symantic meanings:

   *  First Character (element 0) indicates the ``backend type`` used.

   *  Second character (element 1) indicates the ``version`` of the backend type
      which should be used to parse the specification & accesss data (more on
      this later)

The number of codes possible (a 2-choice permutation with repetition) is: 3844
which we anticipate to be more then sufficient long into the future. As a
convention, the range of values in which the first digit of the code falls into
can be used to identify the storage medium location:

   *  Lowercase ``ascii_letters`` & digits ``[0, 1, 2, 3, 4]`` -> reserved for
      backends handling data on the local disk.

   *  Uppercase ``ascii_letters`` & digits ``[5, 6, 7, 8, 9]`` -> reserved for
      backends referring to data residing on a remote server.

This is not a hard and fast rule though, and can be changed in the future if the
need arises.

Process & Guarantees
--------------------

In order to maintain backwards compatibility across versions of Hangar into the
future the following ruleset is specified and MUST BE HONORED:

*  When a new backend is proposed, the contributor(s) provide the class with a
   meaningful name (``HDF5``, ``NUMPY``, ``TILEDB``, etc) identifying the
   backend to Hangar developers. The review team will provide:

   -  ``backend type`` code
   -  ``version`` code

   which all records related to that implementation identify themselves with. In
   addition, Externally facing classes / methods go by a canonical name which is
   the concatenation of the ``meaningful name`` and assigned ``"format code"``
   ie. for ``backend name: 'NUMPY'`` assigned ``type code: '1'`` and ``version
   code: '0'`` must start external method/class names with: ``NUMPY_10_foo``

*  Once a new backend is accepted, the code assigned to it is PERMANENT &
   UNCHANGING. The same code cannot be used in the future for other backends.

*  Each backend independently determines the information it needs to log/store
   to uniquely identify and retrieve a sample stored by it. There is no standard
   format, each is free to define whatever fields they find most convenient.
   Unique encode/decode methods are defined in order to serialize this
   information to bytes and then reconstruct the information later. These bytes
   are what are passed in when a retrieval request is made, and returned when a
   storage request for some piece of data is performed.

*  Once accepted, The record format specified (ie. the byte representation
   described above) cannot be modified in any way. This must remain permanent!

*  Backend (internal) methods can be updated, optimized, and/or changed at any
   time so long as:

   *  No changes to the record format specification are introduced

   *  Data stored via any previous iteration of the backend's accessor methods
      can be retrieved bitwise exactly by the "updated" version.

Before proposing a new backend or making changes to this file, please consider
reaching out to the Hangar core development team so we can guide you through the
process.
"""
import string
from typing import Union, NamedTuple, Optional, Dict

import numpy as np

from .hdf5_00 import HDF5_00_FileHandles, HDF5_00_Options, HDF5_00_Capabilities
from .hdf5_01 import HDF5_01_FileHandles, HDF5_01_Options, HDF5_01_Capabilities
from .numpy_10 import NUMPY_10_FileHandles, NUMPY_10_Options, NUMPY_10_Capabilities
from .remote_50 import REMOTE_50_Handler, REMOTE_50_Options, REMOTE_50_Capabilities
from .lmdb_30 import LMDB_30_FileHandles, LMDB_30_Options, LMDB_30_Capabilities


# ------------------------ Accessor Types and Mapping -------------------------


_BeAccessors = Union[HDF5_00_FileHandles, HDF5_01_FileHandles,
                     NUMPY_10_FileHandles, LMDB_30_FileHandles,
                     REMOTE_50_Handler]
AccessorMapType = Dict[str, _BeAccessors]

# Reserved Backend Codes: ['20', '60'] for ['tiledb_20', 'url_60']
BACKEND_ACCESSOR_MAP = {
    # LOCALS -> [00:50] + ['aa':'zz']
    '00': HDF5_00_FileHandles,
    '01': HDF5_01_FileHandles,
    '10': NUMPY_10_FileHandles,
    '30': LMDB_30_FileHandles,
    # REMOTES -> [50:99] + ['AA':'ZZ']
    '50': REMOTE_50_Handler,
}

BACKEND_OPTIONS_MAP = {
    '00': HDF5_00_Options,
    '01': HDF5_01_Options,
    '10': NUMPY_10_Options,
    '30': LMDB_30_Options,
    '50': REMOTE_50_Options,
}

BACKEND_CAPABILITIES_MAP = {
    '00': HDF5_00_Capabilities,
    '01': HDF5_01_Capabilities,
    '10': NUMPY_10_Capabilities,
    '30': LMDB_30_Capabilities,
    '50': REMOTE_50_Capabilities,
}

_local_prefixes = string.digits[0:5] + string.ascii_lowercase
BACKEND_IS_LOCAL_MAP: Dict[str, bool] = {
    k: bool(k[0] in _local_prefixes) for k in BACKEND_ACCESSOR_MAP.keys()
}


# --------------------------- Backend Heuristics ------------------------------


BackendOpts = NamedTuple('BackendOpts', [('backend', str), ('opts', dict)])


def backend_from_heuristics(array: np.ndarray,
                            variable_shape: bool) -> str:
    """Given a prototype array, attempt to select the appropriate backend.

    Parameters
    ----------
    array : np.ndarray
        prototype array to determine the appropriate backend for.
    variable_shape : bool
        If this is a variable sized arrayset.

    Returns
    -------
    str
        Backend code specification for the selected backend.

    TODO
    ----
    Configuration of this entire module as the available backends fill out.
    """
    # uncompressed numpy memmap data is most appropriate for data whose shape is
    # likely small tabular row data (CSV or such...)
    if (array.ndim == 1) and (array.size < 400):
        backend = '10'
    # hdf5 is the default backend for larger array sizes.
    elif (array.ndim == 1) and (array.size <= 10_000_000):
        backend = '00'
    # on fixed arrays sized arrays apply optimizations.
    elif variable_shape is False:
        backend = '01'
    else:
        backend = '00'

    return backend


def backend_opts_from_heuristics(backend: str,
                                 array: np.ndarray,
                                 variable_shape: bool) -> dict:
    """Generate default backend opt args for a backend and array sample.

    Parameters
    ----------
    backend : str
        backend format code.
    array : np.ndarray
        sample (prototype) of the array data which the backend opts will be
        applied to
    variable_shape : bool
        If this is a variable sized arrayset.

    Returns
    -------
    dict
        backend opts determined appropriate for the system.

    Raises
    ------
    ValueError
        if the specified backend format code is invalid.

    TODO
    ----
    In the current implementation, the `array` parameter is unused. Either come
    up with a use or remove it from the parameter list.
    """
    if backend == '10':
        opts = {}
    elif backend == '00':
        import h5py
        stdopts = {
            'default': {
                'shuffle': None,
                'complib': 'blosc:zstd',
                'complevel': 3,
            },
            'backup': {
                'shuffle': 'byte',
                'complib': 'lzf',
                'complevel': None,
            },
        }
        hdf5BloscAvail = h5py.h5z.filter_avail(32001)
        opts = stdopts['default'] if hdf5BloscAvail else stdopts['backup']
        if opts['complib'].startswith('blosc:') and array.nbytes < 16:
            # cannot have compression buffer size < 16 bytes with blosc lib.
            opts = stdopts['backup']
    elif backend == '01':
        import h5py
        stdopts = {
            'default': {
                'complib': 'blosc:lz4hc',
                'complevel': 5,
                'shuffle': 'byte',
            },
            'backup': {
                'complib': 'lzf',
                'complevel': None,
                'shuffle': 'byte',
            },
        }
        hdf5BloscAvail = h5py.h5z.filter_avail(32001)
        opts = stdopts['default'] if hdf5BloscAvail else stdopts['backup']
        if opts['complib'].startswith('blosc:') and array.nbytes < 16:
            # cannot have compression buffer size < 16 bytes with blosc lib.
            opts = stdopts['backup']
    elif backend == '50':
        opts = {}
    else:
        raise ValueError('Should not have been able to not select backend')

    return opts


def parse_user_backend_opts(backend_opts: Optional[Union[str, dict]],
                            prototype: np.ndarray,
                            variable_shape: bool) -> BackendOpts:
    """Decide the backend and opts to apply given a users selection (or default `None` value)

    Parameters
    ----------
    backend_opts : Optional[Union[str, dict]]
        If str, backend format code to specify, opts are automatically
        inffered. If dict, key `backend` must have a valid backend format code
        value, and the rest of the items are assumed to be valid specs for that
        particular backend. If none, both backend and opts are inffered from
        the array prototype provided.
    prototype : np.ndarray
        Sample of the data array which will be save (same dtype and shape) to
        base the storage backend and opts on.
    variable_shape : bool
        If this is a variable sized arrayset.

    Returns
    -------
    BackendOpts : Optional[Union[str, dict]]
        NamedTuple containing fields `backend` and `opts`

    Raises
    ------
    ValueError
        If str type and backend format code invalid
    ValueError
        if dict type, and no `backend` field (or invalid value) is present
        identifying a backend format code
    ValueError
        If anything other than a str, dict, or `None` object was passed in from
        the user
    """
    if isinstance(backend_opts, str):
        if backend_opts not in BACKEND_ACCESSOR_MAP:
            raise ValueError(f'Backend specifier: {backend_opts} not known')
        else:
            backend = backend_opts
            opts = backend_opts_from_heuristics(backend=backend,
                                                array=prototype,
                                                variable_shape=variable_shape)
    elif isinstance(backend_opts, dict):
        if backend_opts['backend'] not in BACKEND_ACCESSOR_MAP:
            raise ValueError(f'Backend specifier: {backend_opts} not known')
        backend = backend_opts['backend']
        opts = {k: v for k, v in backend_opts.items() if k != 'backend'}
        if backend in ['00', '01'] and 'complib' in opts:
            if opts['complib'].startswith('blosc:') and prototype.nbytes < 16:
                # cannot have compression buffer size < 16 bytes with blosc lib.
                raise ValueError(
                    f'Blosc compression for backend {backend} is not supported for '
                    f'arrays less than 16 bytes in size. Schema with specified shape '
                    f'{prototype.shape} and dtype "{prototype.dtype}" '
                    f'(itemsize={prototype.itemsize}B) totals {prototype.nbytes}B. '
                    f'To resolve either modify schema shape / dtype, or select '
                    f'another complib / backend.'
                )
    elif backend_opts is None:
        backend = backend_from_heuristics(array=prototype,
                                          variable_shape=variable_shape)
        opts = backend_opts_from_heuristics(backend=backend,
                                            array=prototype,
                                            variable_shape=variable_shape)
    else:
        raise ValueError(f'Backend opts value: {backend_opts} is invalid')

    return BackendOpts(backend=backend, opts=opts)
