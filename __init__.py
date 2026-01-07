"""
Python client for etcd server version 2.3.x and later.

See: https://github.com/coreos/etcd
"""

from importlib.metadata import version

__version__ = version("k3etcd")
__name__ = "k3etcd"

from .client import (
    EtcdException,
    EtcdInternalError,
    NoMoreMachineError,
    EtcdReadTimeoutError,
    EtcdRequestError,
    EtcdResponseError,
    EtcdIncompleteRead,
    EtcdSSLError,
    EtcdWatchError,
    EtcdKeyError,
    EtcdValueError,
    EcodeKeyNotFound,
    EcodeTestFailed,
    EcodeNotFile,
    EcodeNotDir,
    EcodeNodeExist,
    EcodeRootROnly,
    EcodeDirNotEmpty,
    EcodePrevValueRequired,
    EcodeTTLNaN,
    EcodeIndexNaN,
    EcodeInvalidField,
    EcodeInvalidForm,
    EcodeInscientPermissions,
    EtcdKeysResult,
    Response,
    EtcdError,
    Client,
)

__all__ = [
    "EtcdException",
    "EtcdInternalError",
    "NoMoreMachineError",
    "EtcdReadTimeoutError",
    "EtcdRequestError",
    "EtcdResponseError",
    "EtcdIncompleteRead",
    "EtcdSSLError",
    "EtcdWatchError",
    "EtcdKeyError",
    "EtcdValueError",
    "EcodeKeyNotFound",
    "EcodeTestFailed",
    "EcodeNotFile",
    "EcodeNotDir",
    "EcodeNodeExist",
    "EcodeRootROnly",
    "EcodeDirNotEmpty",
    "EcodePrevValueRequired",
    "EcodeTTLNaN",
    "EcodeIndexNaN",
    "EcodeInvalidField",
    "EcodeInvalidForm",
    "EcodeInscientPermissions",
    "EtcdKeysResult",
    "Response",
    "EtcdError",
    "Client",
]
