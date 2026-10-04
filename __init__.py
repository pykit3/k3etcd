"""
Python client for etcd server version 2.3.x and later.

See: https://github.com/coreos/etcd
"""

from importlib.metadata import version

__version__ = version("k3etcd")
__name__ = "k3etcd"

from .client import (
    Client,
    EcodeDirNotEmpty,
    EcodeIndexNaN,
    EcodeInscientPermissions,
    EcodeInvalidField,
    EcodeInvalidForm,
    EcodeKeyNotFound,
    EcodeNodeExist,
    EcodeNotDir,
    EcodeNotFile,
    EcodePrevValueRequired,
    EcodeRootROnly,
    EcodeTestFailed,
    EcodeTTLNaN,
    EtcdError,
    EtcdException,
    EtcdIncompleteRead,
    EtcdInternalError,
    EtcdKeyError,
    EtcdKeysResult,
    EtcdReadTimeoutError,
    EtcdRequestError,
    EtcdResponseError,
    EtcdSSLError,
    EtcdValueError,
    EtcdWatchError,
    NoMoreMachineError,
    Response,
)

__all__ = [
    "Client",
    "EcodeDirNotEmpty",
    "EcodeIndexNaN",
    "EcodeInscientPermissions",
    "EcodeInvalidField",
    "EcodeInvalidForm",
    "EcodeKeyNotFound",
    "EcodeNodeExist",
    "EcodeNotDir",
    "EcodeNotFile",
    "EcodePrevValueRequired",
    "EcodeRootROnly",
    "EcodeTTLNaN",
    "EcodeTestFailed",
    "EtcdError",
    "EtcdException",
    "EtcdIncompleteRead",
    "EtcdInternalError",
    "EtcdKeyError",
    "EtcdKeysResult",
    "EtcdReadTimeoutError",
    "EtcdRequestError",
    "EtcdResponseError",
    "EtcdSSLError",
    "EtcdValueError",
    "EtcdWatchError",
    "NoMoreMachineError",
    "Response",
]
