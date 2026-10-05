"""
Python client for the etcd v2 API. It works with etcd server 2.3.x to 3.5.x.

etcd 3.4 and 3.5 serve the v2 API when started with `--enable-v2`.
etcd 3.6 removed the v2 API.

Use `protocol="https"` with `basic_auth_account`, so that the account is
encrypted on the network.

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
