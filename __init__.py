"""
#   Description

A python client for Etcd https://github.com/coreos/etcd

This module will only work correctly with the etcd server version 2.3.x or later.

"""

__version__ = "0.1.0"
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
