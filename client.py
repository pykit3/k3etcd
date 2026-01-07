#!/usr/bin/env python
# coding: utf-8

import http.client
import logging
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import base64
import k3http
import k3utfjson

logger = logging.getLogger(__name__)


class EtcdException(Exception):
    """
    The base class of the other exceptions in this module.
    It is a subclass of `Exception`.
    """

    pass


class EtcdInternalError(EtcdException):
    """
    A subclass of `etcd.EtcdException`.
    Raise if etcd server "Raft Internal Error" or "During Leader Election".
    """

    pass


class NoMoreMachineError(EtcdException):
    """
    A subclass of `etcd.EtcdException`.
    Raise if there are no machines left to try.
    """

    pass


class EtcdReadTimeoutError(EtcdException):
    """
    A subclass of `etcd.EtcdException`.
    Raise if timeout when watching a key.
    """

    pass


class EtcdRequestError(EtcdException):
    """
    A subclass of `etcd.EtcdException`.
    Raise if the http request is invalid.
    Such as invalid http request method or invalid headers.
    """

    pass


class EtcdResponseError(EtcdException):
    """
    A subclass of `etcd.EtcdException`.
    Raise if etcd server failed to process request.
    """

    pass


class EtcdIncompleteRead(EtcdResponseError):
    """
    A subclass of `etcd.EtcdException`.
    Raise if the encoding of response body is not json.
    """

    pass


class EtcdSSLError(EtcdException):
    """
    A subclass of `etcd.EtcdException`.
    Raise if the protocol is `https`.
    Right now, this module don't support `https`.
    """

    pass


class EtcdWatchError(EtcdException):
    """
    A subclass of `etcd.EtcdException`.
    Raise if "watcher is cleared due to etcd recovery"
    or "The event in requested index is outdated and cleared".
    """

    pass


class EtcdKeyError(EtcdException, KeyError):
    """
    A subclass of `etcd.EtcdException` and `KeyError`.
    The base class of `etcd.EcodeKeyNotFound`, `etcd.EcodeNotFile`,
    `etcd.EcodeNotDir` and `etcd.EcodeNodeExist` in this module.
    """

    pass


class EtcdValueError(EtcdException, ValueError):
    """
    A subclass of `etcd.EtcdException` and `ValueError`.
    The base class of `etcd.EcodeTestFailed`, `etcd.EcodeRootROnly`,
    `etcd.EcodeDirNotEmpty`, `etcd.EcodePrevValueRequired`,
    `etcd.EcodeTTLNaN`, `etcd.EcodeIndexNaN`, `etcd.EcodeInvalidField` and
    `etcd.EcodeInvalidForm` in this module.
    """

    pass


class EcodeKeyNotFound(EtcdKeyError):
    """
    A subclass of `etcd.EtcdKeyError`.
    Raise if key not found.
    """

    pass


class EcodeTestFailed(EtcdValueError):
    """
    A subclass of `etcd.EtcdValueError`.
    Raise if compare failed.
    Such as `prevValue=abc` compare failed in the cluster.
    """

    pass


class EcodeNotFile(EtcdKeyError):
    """
    A subclass of `etcd.EtcdKeyError`.
    Raise if the file operation to a dir.

    """

    pass


class EcodeNotDir(EtcdKeyError):
    """
    A subclass of `etcd.EtcdKeyError`.
    Raise if the dir operation to a file.
    """

    pass


class EcodeNodeExist(EtcdKeyError):
    """
    A subclass of `etcd.EtcdKeyError`.
    Raise if create a existed key with `prevExist=False`.
    """

    pass


class EcodeRootROnly(EtcdValueError):
    """
    A subclass of `etcd.EtcdValueError`.
    Raise if root is read only.
    """

    pass


class EcodeDirNotEmpty(EtcdValueError):
    """
    A subclass of `etcd.EtcdValueError`.
    Raise if delete a not empty dir with `recursive=false`.
    """

    pass


class EcodePrevValueRequired(EtcdValueError):
    """
    A subclass of `etcd.EtcdValueError`.
    Raise if not provide `prevValue` when it is required in post form.
    """

    pass


class EcodeTTLNaN(EtcdValueError):
    """
    A subclass of `etcd.EtcdValueError`.
    Raise if the given `TTL` in post form is not a number.
    """

    pass


class EcodeIndexNaN(EtcdValueError):
    """
    A subclass of `etcd.EtcdValueError`.
    Raise if the given `index` in post form is not a number.
    """

    pass


class EcodeInvalidField(EtcdValueError):
    """
    A subclass of `etcd.EtcdValueError`.
    Raise if the http header field is invalid.
    """

    pass


class EcodeInvalidForm(EtcdValueError):
    """
    A subclass of `etcd.EtcdValueError`.
    Raise if post form is invalid.
    """

    pass


class EcodeInscientPermissions(EtcdException):
    """
    A subclass of `etcd.EtcdException`.
    Raise if Unauthorized.
    """

    pass


def list_type(x):
    if isinstance(x, (list, tuple)):
        return True

    return False


class EtcdError(object):
    error_exceptions = {
        100: EcodeKeyNotFound,
        101: EcodeTestFailed,
        102: EcodeNotFile,
        103: EtcdException,
        104: EcodeNotDir,
        105: EcodeNodeExist,
        106: EtcdKeyError,
        107: EcodeRootROnly,
        108: EcodeDirNotEmpty,
        110: EcodeInscientPermissions,
        200: EtcdValueError,
        201: EcodePrevValueRequired,
        202: EcodeTTLNaN,
        203: EcodeIndexNaN,
        209: EcodeInvalidField,
        210: EcodeInvalidForm,
        300: EtcdInternalError,
        301: EtcdInternalError,
        400: EtcdWatchError,
        401: EtcdWatchError,
        500: EtcdInternalError,
    }

    @classmethod
    def handle(cls, response):
        body = response.data

        e = {}
        e["status"] = response.status
        e["headers"] = response.headers
        e["response"] = body

        try:
            r = k3utfjson.load(body)
        except ValueError:
            r = {"message": "response body is not json", "cause": str(body)}
        ecode = r.get("errorCode")
        default_exc = EtcdException
        if response.status == 404:
            ecode = 100
        elif response.status == 401:
            ecode = 110
        elif response.status >= 500:
            default_exc = EtcdResponseError

        exc = cls.error_exceptions.get(ecode, default_exc)
        if ecode in cls.error_exceptions:
            msg = "{msg} : {cause}".format(msg=r.get("message"), cause=r.get("cause"))
        else:
            msg = "Unable to decode server response"

        e["message"] = msg

        raise exc(e)


class EtcdKeysResult(object):
    """
    `etcd.EtcdKeysResult.expiration`

    Type is `str`, the current node expire time. Defaults to `None`.

    ##  etcd.EtcdKeysResult.ttl

    The left seconds of the current node.
    If `None`, it is a permanent node. Defaults to `None`.

    ##  etcd.EtcdKeysResult.modifiedIndex

    Type is `int`, modified index of the node returned from server.

    ##  etcd.EtcdKeysResult.createdIndex


    Type is `int`, created index of the node returned from server.

    ##  etcd.EtcdKeysResult.newKey


    Whether the node is created in this request.
    Type is `bool`, defaults to `False`.

    ##  etcd.EtcdKeysResult.dir

    Whether the node is a dir or not.
    Type is `bool`, defaults to `False`.

    ##  etcd.EtcdKeysResult.leaves

    The nodes which have value.
    It is an iterator. Each element is a `etcd.EtcdKeysResult` object.
    """

    _node_props = {
        "key": None,
        "value": None,
        "expiration": None,
        "ttl": None,
        "modifiedIndex": None,
        "createdIndex": None,
        "newKey": False,
        "dir": False,
    }

    def __init__(self, action=None, node=None, prevNode=None, **argkv):
        self.action = action
        for key, default in self._node_props.items():
            if node is not None and key in node:
                setattr(self, key, node[key])
            else:
                setattr(self, key, default)

        self._children = []
        if self.dir and "nodes" in node:
            self._children = node["nodes"]

        if prevNode:
            self._prev_node = EtcdKeysResult(None, node=prevNode)
            """
            #fix this bug
            r = c.write('/foo', None, dir=True, ttl=50)
            print(r.dir) #True
            r2 = c.write('/foo', None, dir=True, ttl=120, prevExist=True)
            print(r2.dir) #False
            """
            if self._prev_node.dir and not self.dir:
                self.dir = True

    def parse_response(self, response):
        if response.status == http.client.CREATED:
            self.newKey = True

        headers = response.headers
        self.etcd_index = int(headers.get("x-etcd-index", 1))
        self.raft_index = int(headers.get("x-raft-index", 1))
        self.raft_term = int(headers.get("x-raft-term", 0))

    def get_subtree(self, leaves_only=False):
        """
        Get all the subtree resulting from a `recursive=true` call to etcd.
        :param leaves_only: If `True`, only value nodes are returned,
        else return all the nodes.

        :return: It is an iterator. Each element is a `etcd.EtcdKeysResult` object.
        """
        if not self._children:
            yield self
            return

        if not leaves_only:
            yield self

        for n in self._children:
            node = EtcdKeysResult(None, n)
            for child in node.get_subtree(leaves_only=leaves_only):
                yield child

        return

    @property
    def leaves(self):
        return self.get_subtree(leaves_only=True)

    def __eq__(self, other):
        """
        Compare one with another,
        if they are same, return `True`, else return `False`
        :return:
        """
        if not isinstance(other, EtcdKeysResult):
            return False

        for k in list(self._node_props.keys()):
            try:
                a = getattr(self, k)
                b = getattr(other, k)
                if a != b:
                    return False
            except Exception:
                return False

        return True

    def __ne__(self, other):
        """
        Compare one with another,
        if they are same, return `False`, else return `True`
        """
        return not self.__eq__(other)

    def __repr__(self):
        """
        Convert the object to a string and return it.
        """
        return "%s(%r)" % (self.__class__, self.__dict__)


class Response(object):
    REDIRECT_STATUSES = (301, 302, 303, 307, 308)

    def __init__(self, conn=None, status=0, version=0, reason=None, headers=None, body=""):
        self._conn = conn
        self.status = status
        self.version = version
        self.reason = reason
        self.headers = headers
        self._body = body

    @property
    def data(self):
        if self._body:
            return self._body

        if hasattr(self._conn, "read"):
            self._body = self._conn.read()
            return self._body

        return ""

    def get_redirect_location(self):
        if self.status in self.REDIRECT_STATUSES:
            return self.headers.get("location")

        return None

    @classmethod
    def from_http(Cls, h, **argkv):
        return Cls(h, status=h.status, headers=h.headers, body=h.read_body(None), **argkv)


class Client(object):
    _MGET = "GET"
    _MPUT = "PUT"
    _MPOST = "POST"
    _MDELETE = "DELETE"

    _write_conditions = {"prevValue", "prevIndex", "prevExist"}
    _read_options = {"recursive", "wait", "waitIndex", "sorted", "quorum"}
    _del_conditions = {"prevValue", "prevIndex"}
    """
    ##  etcd.Client.base_uri
    
    Type is `str`, the default etcd server clienturl.
    
    ##  etcd.Client.host

    Type is `str`, the default etcd server ip.
    Defaults to `127.0.0.1`.
    
    ##  etcd.Client.port
    
    Type is `int`, the port used to connect to etcd server.
    Defaults to `2379`.
    
    ##  etcd.Client.protocol
    
    Type is `str`, protocol used to connect etcd server.
    Only support http, defaults to `http`.
    
    ##  etcd.Client.read_timeout
    
    Max seconds to wait for a request.
    Type is `int`, defaults to `10`.
    
    ##  etcd.Client.allow_redirect

    Type is `bool`, allow the client to connect other nodes.
    Defaults to `True`.
    
    ##  etcd.Client.machines
    
    Members of the cluster.
    Type is `list`, like `['http://127.0.0.1:4001', 'http://127.0.0.1:4002']`.
    
    ##  etcd.Client.members
    
    A more structured view of peers in the cluster.
    Type is `list`, like
    
    ```python
    [
        {
          "id": "291578612bc6deb",
          "name": "node_0",
          "peerURLs": [
            "http://192.168.52.30:3380"
          ],
          "clientURLs": [
            "http://192.168.52.30:3379"
          ]
        },
        {
          "id": "183ebbe2e22ee250",
          "name": "node_2",
          "peerURLs": [
            "http://192.168.52.32:3380"
          ],
          "clientURLs": [
            "http://192.168.52.32:3379"
          ]
        },
    ]
    ```
    
    ##  etcd.Client.leader
    
    **syntax**:
    `etcd.Client.leader`
    
    The leader of the cluster.
    Type is `dict`, like
    ```python
    {
        "id":"ce2a822cea30bfca",
        "name":"n",
        "peerURLs":["http://127.0.0.1:2380"],
        "clientURLs":["http://127.0.0.1:4001"]
    }
    ```
    
    ##  etcd.Client.version
    
    Version of etcd server.
    
    ##  etcd.Client.st_leader
    
    The stats of the leader.
    Type is `dict`.
    
    ##  etcd.Client.st_self
    
    The stats of the local server.
    Type is `dict`.
    
    ##  etcd.Client.st_store
    
    The stats of the kv store.
    Type is `dict`.
    
    ##  etcd.Client.names
    
    Name of members in the cluster.
    Type is `list`.
    
    ##  etcd.Client.ids
    
    Id of members in the cluster.
    Type is `list`.
    
    ##  etcd.Client.clienturls
    
    ClientUrls of members in the cluster.
    Type is `list`.
    
    ##  etcd.Client.peerurls
    
    PeerUrls of members in the cluster.
    Type is `list`.
    """

    def __init__(
        self,
        host="127.0.0.1",
        port=2379,
        version_prefix="/v2",
        read_timeout=10,
        allow_redirect=True,
        protocol="http",
        allow_reconnect=True,
        basic_auth_account=None,
    ):
        """
        Etcd client class.
        :param host: Mixed, if a `str`, it is the IP to connect to.
        If a `tuple` or `list`, like `((ip, port), (ip, port))`.
        Defaults to `127.0.0.1`.
        :param port: Type is `int`, the port used to connect to etcd server.
        Defaults to `2379`.
        :param version_prefix: Type is `str`, url or version prefix in etcd url. Defaults to `v2`.
        :param read_timeout: Type is `int`, max seconds to wait for a request. Defaults to `10`.
        :param allow_redirect: Type is `bool`, allow the client to connect other nodes. Defaults to `True`.
        :param protocol: Type is `str`, right now only support http. Defaults to `http`.
        :param allow_reconnect: Type is `bool`, allow the client to reconnect to another etcd server
        in the cluster in the case the default one does not respond. Defaults to `True`.
        :param basic_auth_account: Type is `str`, the authorization information. Defaults to `None`.
        """
        self._protocol = protocol
        if protocol == "https":
            raise EtcdSSLError("not supported https right now")

        self._machines_cache = []
        if not list_type(host):
            self._host = host
            self._port = int(port)
            self._base_uri = "%s://%s:%d" % (self._protocol, self._host, self._port)
        else:
            for h in host:
                if list_type(h):
                    _h, _p = (list(h) + [int(port)])[:2]
                else:
                    _h, _p = h, int(port)
                self._machines_cache.append("%s://%s:%d" % (self._protocol, _h, _p))

            self._base_uri = self._machines_cache.pop(0)
            _, self._host, self._port = self._extract_base_uri()

        self.version_prefix = version_prefix
        self._keys_path = self.version_prefix + "/keys"
        self._stats_path = self.version_prefix + "/stats"
        self._mem_path = self.version_prefix + "/members"
        self._user_path = self.version_prefix + "/auth/users"
        self._role_path = self.version_prefix + "/auth/roles"
        self._read_timeout = read_timeout
        self._allow_redirect = allow_redirect
        self._allow_reconnect = allow_reconnect
        self.basic_auth_account = basic_auth_account

        if self._allow_reconnect:
            if len(self._machines_cache) <= 0:
                self._machines_cache = self.machines
            if self._base_uri in self._machines_cache:
                self._machines_cache.remove(self._base_uri)
        else:
            self._machines_cache = []

    @property
    def base_uri(self):
        return self._base_uri

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def protocol(self):
        return self._protocol

    @property
    def read_timeout(self):
        return self._read_timeout

    @property
    def allow_redirect(self):
        return self._allow_redirect

    @property
    def machines(self):
        res = self.api_execute(self.version_prefix + "/machines", self._MGET, need_refresh_machines=False)

        nodes = res.data.split(",")

        return [n.strip() for n in nodes]

    @property
    def members(self):
        res = self.api_execute(self._mem_path, self._MGET)

        return k3utfjson.load(res.data)["members"]

    @property
    def leader(self):
        res = self.api_execute(self._stats_path + "/self", self._MGET)
        self_st = k3utfjson.load(res.data)

        leader_id = self_st.get("leaderInfo", {}).get("leader")
        if leader_id is None:
            return None

        mems = self.members
        for mem in mems:
            if mem["id"] != leader_id:
                continue

            return mem.copy()

    @property
    def version(self):
        res = self.api_execute("/version", self._MGET)

        return k3utfjson.load(res.data)

    @property
    def st_leader(self):
        leader = self.leader
        if leader is None:
            return None

        leaderhosts = []
        for url in leader["clientURLs"]:
            if not url.startswith(self._protocol):
                url = self._protocol + "://" + url
            p = urllib.parse.urlparse(url)
            if p.hostname == "127.0.0.1":
                continue

            port = p.port or self.port
            leaderhosts.append((p.hostname, port))

        return Client(host=leaderhosts)._st("/leader")

    @property
    def st_self(self):
        return self._st("/self")

    @property
    def st_store(self):
        return self._st("/store")

    @property
    def names(self):
        return [n["name"] for n in self.members]

    @property
    def ids(self):
        return [n["id"] for n in self.members]

    @property
    def clienturls(self):
        return sum([n["clientURLs"] for n in self.members], [])

    @property
    def peerurls(self):
        return sum([n["peerURLs"] for n in self.members], [])

    def __contains__(self, key):
        try:
            self.get(key)
            return True
        except EcodeKeyNotFound:
            return False

    def _sanitize_key(self, key):
        if not key.startswith("/"):
            key = "/{key}".format(key=key)
        return key

    def _extract_base_uri(self):
        p = urllib.parse.urlparse(self._base_uri)
        return p.scheme, p.hostname, p.port

    def _parse_url(self, url):
        p = urllib.parse.urlparse(url)

        if p.scheme == "https":
            raise EtcdSSLError("not supported https right now. " + url)
        elif p.scheme != "http":
            return None, None, url

        port = p.port or self.port

        return p.hostname, port, p.path

    def _generate_params(self, options, argkv):
        params = {}
        for k, v in list(argkv.items()):
            if k not in options:
                continue

            if isinstance(v, bool):
                params[k] = v and "true" or "false"
                continue

            params[k] = v

        return params

    def _st(self, st_path):
        st_path = self._sanitize_key(st_path)
        response = self.api_execute(self._stats_path + st_path, self._MGET)
        return self._to_dict(response)

    def _to_keysresult(self, response):
        try:
            res = k3utfjson.load(response.data)
            r = EtcdKeysResult(**res)
            r.parse_response(response)
            return r
        except ValueError as e:
            logger.error(repr(e) + " while decode {data}".format(data=response.data))
            raise EtcdIncompleteRead("failed to decode %s" % response.data)
        except Exception as e:
            logger.error(repr(e) + " while decode {data}".format(data=response.data))
            raise EtcdResponseError("failed to decode %s" % response.data)

    def _to_dict(self, response):
        try:
            return k3utfjson.load(response.data)
        except ValueError as e:
            logger.error(repr(e) + " while decode {data}".format(data=response.data))
            raise EtcdIncompleteRead("failed to decode %s" % response.data)
        except Exception as e:
            logger.error(repr(e) + " while decode {data}".format(data=response.data))
            raise EtcdResponseError("failed to decode %s" % response.data)

    def _handle_server_response(self, response):
        if response.status in (http.client.OK, http.client.CREATED, http.client.NO_CONTENT):
            return response

        logger.debug("invalid response status:{st} body:{body}".format(st=response.status, body=response.data))

        EtcdError.handle(response)

    def _request(self, url, method, params, timeout, bodyinjson):
        while True:
            host, port, path = self._parse_url(url)
            if host is None or port is None or path is None:
                raise EtcdException("url is invalid, {url}".format(url=url))

            qs = {}
            headers = {}
            body = ""

            if method in (self._MGET, self._MDELETE):
                qs.update(params or {})

                # use once, coz params is in location's query string
                params = None
                headers["Content-Length"] = 0

            elif method in (self._MPUT, self._MPOST):
                if bodyinjson:
                    if params is not None:
                        body = k3utfjson.dump(params)
                    headers.update({"Content-Type": "application/json", "Content-Length": len(body)})
                else:
                    body = urllib.parse.urlencode(params or {})
                    headers.update({"Content-Type": "application/x-www-form-urlencoded", "Content-Length": len(body)})
            else:
                raise EtcdRequestError("HTTP method {method} not supported".format(method=method))

            if len(qs) > 0:
                if "?" in path:
                    path = path + "&" + urllib.parse.urlencode(qs)
                else:
                    path = path + "?" + urllib.parse.urlencode(qs)

            if self.basic_auth_account is not None:
                auth = {
                    "Authorization": "Basic {ant}".format(
                        ant=base64.b64encode(self.basic_auth_account.encode()).strip().decode()
                    ),
                }
                headers.update(auth)

            logger.debug(
                "connect -> {mtd} {url}{path} {timeout}".format(
                    mtd=method, url=self._base_uri, path=path, timeout=timeout
                )
            )

            h = k3http.Client(host, port, timeout)
            h.send_request(path, method, headers)
            h.send_body(body)
            h.read_response()

            resp = Response.from_http(h)

            if not self.allow_redirect:
                return resp

            if resp.status not in Response.REDIRECT_STATUSES:
                return resp

            url = resp.get_redirect_location()
            if url is None:
                raise EtcdResponseError("location not found in {header}".format(header=resp.headers))

            logger.debug("redirect -> " + url)

    def _api_execute_with_retry(
        self, path, method, params=None, timeout=None, bodyinjson=False, raise_read_timeout=False, **request_kw
    ):
        # including _base_uri, there are len(_machines_cache) + 1 hosts to try
        # to connect to.
        for i in range(len(self._machines_cache) + 1):
            url = self._base_uri + path

            try:
                response = self._request(url, method, params, timeout, bodyinjson)
                break
            except (socket.error, k3http.HttpError) as e:
                if raise_read_timeout and isinstance(e, socket.timeout):
                    raise EtcdReadTimeoutError(e)

                if len(self._machines_cache) > 0:
                    self._machines_cache.append(self._base_uri)
                    self._base_uri = self._machines_cache.pop(0)
                    self._protocol, self._host, self._port = self._extract_base_uri()

                    logger.info(
                        "{err} while connect {cur}, try connect {nxt}".format(err=repr(e), cur=url, nxt=self._base_uri)
                    )

                else:
                    logger.info("no more host to retry")

            except Exception as e:
                logger.exception(repr(e) + " while send request to etcd")
                raise EtcdException(e)

        else:
            raise NoMoreMachineError("No more machines in the cluster")

        return self._handle_server_response(response)

    def api_execute(
        self,
        path,
        method,
        params=None,
        timeout=None,
        bodyinjson=False,
        raise_read_timeout=False,
        need_refresh_machines=True,
        **request_kw,
    ):
        if timeout is None:
            timeout = self.read_timeout
        if timeout == 0:
            timeout = None

        if not path.startswith("/"):
            raise ValueError("Path does not start with /")

        for i in range(0, 2):
            try:
                return self._api_execute_with_retry(
                    path,
                    method,
                    params=params,
                    timeout=timeout,
                    bodyinjson=bodyinjson,
                    raise_read_timeout=raise_read_timeout,
                    **request_kw,
                )

            except NoMoreMachineError as e:
                logger.info(repr(e) + " while send_request path:{path}, method:{mtd}".format(path=path, mtd=method))

                if i == 1 or not need_refresh_machines or not self._allow_reconnect:
                    raise

                new_machines = self.machines
                old_machines = self._machines_cache + [self._base_uri]

                if set(new_machines) == set(old_machines):
                    raise

                self._machines_cache = new_machines
                self._base_uri = self._machines_cache.pop(0)
                self._protocol, self._host, self._port = self._extract_base_uri()

    def read(self, key, **argkv):
        """
        Get the value with `key`
        :param key: The key which wil be accessed. `/XXX` is same as `XXX`.
        :param argkv: Other kv args.

        `recursive(bool)`:
        Fetch a dir recursively.

        `wait(bool)`:
        Wait and return next time the key is changed.

        `waitIndex(int)`:
        The index to fetch results from.

        `sorted(bool)`:
        Sort the output keys.

        `quorum(bool)`:
        If `True`, get value through raft.

        `timeout(int)`:
        Max seconds to wait for the request.
        :return: A `etcd.EtcdKeysResult` object.
        """
        key = self._sanitize_key(key)
        params = self._generate_params(self._read_options, argkv)
        timeout = argkv.get("timeout")
        response = self.api_execute(self._keys_path + key, self._MGET, params=params, timeout=timeout)

        return self._to_keysresult(response)

    get = read

    def write(self, key, value=None, ttl=None, dir=False, append=False, refresh=False, **argkv):
        """
        Writes the value for a key, possibly doing atomic Compare-and-Swap.
        Raise a `etcd.EtcdRequestError` when `value is not None` and `dir is True`.
        :param key: The key that will be writen.
        `/XXX` is same as `XXX`.
        :param value: Value to set. Defaults to `None`.
        :param ttl: Time in seconds of expiration (optional).
        Type is `int`. Defaults to `None`.
        :param dir: Set to `True` if we are writing a directory.
        Type is `bool`. Defaults to `False`.
        :param append: If `True`, it will post to append the new value to the dir, creating a sequential key.
        Defaults to false.
        :param refresh: If `True`, only update the ttl, prev key must existed(`prevExist=True`).
        :param argkv: Other kv args.
        `prevValue`: Compare with this value, and swap only if corresponding (optional).
        `prevIndex(int)`: Modify key only if actual modifiedIndex matches the provided one (optional).
        `prevExist(bool)`: If `False`, only create key; if `True`, only update key.
        :return: A `etcd.EtcdKeysResult` object.
        """
        key = self._sanitize_key(key)

        params = {}
        if ttl is not None:
            params["ttl"] = ttl

        if dir and value is not None:
            raise EtcdRequestError("Cannot create a directory with a value " + repr(value))
        elif value is not None:
            params["value"] = value
        elif dir:
            params["dir"] = "true"

        if refresh:
            params["refresh"] = "true"

        params.update(self._generate_params(self._write_conditions, argkv))

        method = append and self._MPOST or self._MPUT
        if "_endpoint" in argkv:
            path = argkv["_endpoint"] + key
        else:
            path = self._keys_path + key

        response = self.api_execute(path, method, params=params)

        return self._to_keysresult(response)

    def test_and_set(self, key, value, ttl=None, **argkv):
        """
        Set `value` with `key`.
        :param key: See `key` in `etcd.Client.write`.
        :param value: See `value` in `etcd.Client.write`.
        :param ttl: See `ttl` in `etcd.Client.write`.
        :param argkv: See other kv args in `etcd.Client.write`.
        :return: A `etcd.EtcdKeysResult` object.
        """
        return self.write(key, value=value, ttl=ttl, **argkv)

    def set(self, key, value, ttl=None):
        """
        Set `value` with `key`.
        :param key: See `key` in `etcd.Client.write`.
        :param value: See `value` in `etcd.Client.write`.
        :param ttl: See `ttl` in `etcd.Client.write`.
        :return: A `etcd.EtcdKeysResult` object.
        """
        return self.write(key, value=value, ttl=ttl)

    def update(self, res):
        """
        Updates the value for a key atomically.
        :param res: A `etcd.EtcdKeysResult` object.
        :return: A `etcd.EtcdKeysResult` object.
        """
        # c = etcd.Client(host=hosts)
        # res = c.read("/somekey")
        # res.value += 1
        # c.update(res)
        argkv = {
            "dir": res.dir,
            "ttl": res.ttl,
            "prevExist": True,
        }

        if not res.dir:
            # prevIndex on a dir causes a 'not a file' error. d'oh!
            argkv["prevIndex"] = res.modifiedIndex

        return self.write(res.key, value=res.value, **argkv)

    def delete(self, key, recursive=None, dir=None, **argkv):
        """
        Remove a key from etcd.
        :param key: The key which will be delete.
        :param recursive: If we want to recursively delete a directory, set it to `True`.
        Defaults to `None`.
        :param dir: If we want to delete a directory, set it to `True`.
        Defaults to `None`.
        :param argkv: Other kv args.
        `prevValue`:
        Compare with this value and delete only if corresponding (optional).
        `prevIndex(int)`:
        Delete only if actual modifiedIndex matches the provided one (optional).
        :return: A `etcd.EtcdKeysResult` object.
        """
        key = self._sanitize_key(key)

        params = {}
        if recursive is not None:
            params["recursive"] = recursive and "true" or "false"

        if dir is not None:
            params["dir"] = dir and "true" or "false"

        params.update(self._generate_params(self._del_conditions, argkv))

        response = self.api_execute(self._keys_path + key, self._MDELETE, params=params)

        return self._to_keysresult(response)

    def test_and_delete(self, key, **argkv):
        """
        Remove a key from etcd.
        :param key: The key which will be delete.
        :param argkv: See other kv args in `etcd.Client.delete`.
        :return: A `etcd.EtcdKeysResult` object.
        """
        return self.delete(key, **argkv)

    def watch(self, key, waitindex=None, timeout=None, **argkv):
        """
        Blocks until a new event has been received or timeout.
        Raise a `etcd.EtcdReadTimeoutError` if timeout.
        :param key: The key which will be watched.
        :param waitindex:     Index to start from.
        Type is `int`. Defautls to `None`.
        If `None` use the newest index.
        :param timeout: Max seconds to wait.
        If `None`, use `etcd.Client.read_timeout`.
        If `0` means infinite waiting.
        :param argkv: Other kv args.
        `recursive(bool)`
        If want to watch a dir, set `True`.
        `waitIndex(int)`:
        If `waitindex` is `None`, use it.
        :return: A `etcd.EtcdKeysResult` object.
        """
        newest_v = self.get(key)

        if waitindex is None:
            waitindex = argkv.get("waitIndex")

        if waitindex is not None and 0 < waitindex <= newest_v.modifiedIndex:
            return newest_v
        else:
            waitindex = newest_v.etcd_index + 1
            return self._watch(key, waitindex, timeout, **argkv)

    def _watch(self, key, waitindex=None, timeout=None, **argkv):
        key = self._sanitize_key(key)

        params = self._generate_params(self._read_options, argkv)
        params["wait"] = "true"

        if waitindex is not None:
            params["waitIndex"] = waitindex

        # timeout is 0 means infinite waiting
        while True and timeout == 0:
            try:
                response = self.api_execute(self._keys_path + key, self._MGET, params=params, timeout=timeout)
                return self._to_keysresult(response)
            except EtcdIncompleteRead:
                pass

        timeout = timeout or self.read_timeout

        while True:
            st = time.time()
            try:
                response = self.api_execute(
                    self._keys_path + key, self._MGET, params=params, timeout=timeout, raise_read_timeout=True
                )
                return self._to_keysresult(response)
            except (EtcdIncompleteRead, EtcdReadTimeoutError):
                timeout = timeout - (time.time() - st)
                if timeout <= 0:
                    raise EtcdReadTimeoutError("Watch Timeout: " + key)

    def eternal_watch(self, key, waitindex=None, until=None, **argkv):
        """
        Blocks until the modify index of the key is ge than `until`.
        :param key: See `key` in `etcd.Client.watch`.
        :param waitindex: See `waitindex` in `etcd.Client.watch`.
        :param until: Break the loop when the modify index of the key is ge than it.
        If `None`, the loop will not be break. Defaults to `None`
        :param argkv: See other kv args in `etcd.Client.watch`.
        :return: It is an iterator. Each element is a `etcd.EtcdKeysResult` object.
        """
        local_index = waitindex
        while True:
            res = self._watch(key, waitindex=local_index, timeout=0, **argkv)
            if until is not None and res.modifiedIndex is not None:
                if res.modifiedIndex >= until:
                    yield res
                    return

            if local_index is not None:
                local_index = (res.modifiedIndex or local_index) + 1

            yield res

    def mkdir(self, key, ttl=None, **argkv):
        """
        Create a dir in the cluster.
        :param key: The key that will be created.
        :param ttl: Time in seconds of expiration.
        See `ttl` in `etcd.Client.write`.
        :param argkv:
        :return: A `etcd.EtcdKeysResult` object.
        """
        return self.write(key, ttl=ttl, dir=True, **argkv)

    def refresh(self, key, ttl=None, **argkv):
        """
        Update the `ttl` of the `key`.
        :param key: See `key` in `etcd.Client.write`.
        :param ttl: Time in seconds of expiration.
        See `ttl` in `etcd.Client.write`.
        :param argkv:
        :return: A `etcd.EtcdKeysResult` object.
        """
        argkv["prevExist"] = True
        return self.write(key, ttl=ttl, refresh=True, **argkv)

    def lsdir(self, key, **argkv):
        """
        Get all nodes of the dir with `key`.
        :param key: The key that will be got.
        See `key` in `etcd.Client.read`.
        :param argkv:
        :return: A `etcd.EtcdKeysResult` object.
        """
        return self.read(key, **argkv)

    def rlsdir(self, key, **argkv):
        argkv["recursive"] = True
        return self.read(key, **argkv)

    def deldir(self, key, **argkv):
        """
        Delete a dir in cluster with `key`.
        :param key: The key that will be deleted.
        See `key` in `etcd.Client.delete`.
        :param argkv:
        :return: A `etcd.EtcdKeysResult` object.
        """
        return self.delete(key, dir=True, **argkv)

    def rdeldir(self, key, **argkv):
        """
        Delete a dir in cluster with `key` recursively.
        :param key: The key that will be deleted.
        See `key` in `etcd.Client.delete`.
        :param argkv:
        :return: A `etcd.EtcdKeysResult` object.
        """
        argkv["recursive"] = True
        return self.delete(key, dir=True, **argkv)

    def add_member(self, *peerurls):
        """
        Add a new node in the cluster.

        Raise a `etcd.EtcdResponseError` if the cluster fails to process the request.

        Raise a `etcd.EtcdException` if the member exists in the cluster
        or existed in the cluster at some point in the past
        or any of the given peerURLs exists in the cluster.
        :param peerurls: The new node peerurls.
        Type is `list`, like`['http://127.0.0.1:2380',]`
        :return: A `dick`
        """
        if len(peerurls) == 0:
            raise EtcdException("no peer url found")

        data = {"peerURLs": peerurls}
        response = self.api_execute(self._mem_path, self._MPOST, params=data, bodyinjson=True)

        return self._to_dict(response)

    def del_member(self, mid):
        """
        Remove a member from the cluster.
        :param mid: The id of the node in the cluster.
        :return: nothing
        """
        if mid not in self.ids:
            logger.info("{mid} not in the cluster when delete member".format(mid=mid))
            return

        mid = self._sanitize_key(mid)
        self.api_execute(self._mem_path + mid, self._MDELETE)

    def change_peerurls(self, mid, *peerurls):
        """
        Change the peer urls of a given member.
        :param mid: The id of the node in the cluster.
        :param peerurls: The peerurls that will be set to the member.
        Type is `list`, like`['http://127.0.0.1:2380',]`
        :return: nothing
        """
        if mid not in self.ids:
            logger.info("{mid} not in the cluster when change peerurls".format(mid=mid))
            return

        if len(peerurls) == 0:
            raise EtcdException("no peer url found")

        mid = self._sanitize_key(mid)
        data = {"peerURLs": peerurls}

        self.api_execute(self._mem_path + mid, self._MPUT, params=data, bodyinjson=True)

    def _root_auth(self, password):
        return "root:%s" % (password)

    def create_root(self, password):
        """
        Create root user in the cluster.
        :param password: The password of the root user.
        :return: A `dict`, like`{"user":"root","roles":["root"]}`
        """
        path = self._user_path + "/root"
        params = {"user": "root", "password": password}

        res = self.api_execute(path, self._MPUT, params=params, bodyinjson=True)
        return self._to_dict(res)

    def enable_auth(self, root_password):
        """
        Enable authorization.
        :param root_password: The password of the root user.
        :return: nothing
        """
        self.basic_auth_account = self._root_auth(root_password)
        self.api_execute("/v2/auth/enable", self._MPUT)

    def disable_auth(self, root_password):
        """
        Disable authorization.
        :param root_password: The password of the root user.
        :return: nothing
        """
        self.basic_auth_account = self._root_auth(root_password)
        self.api_execute("/v2/auth/enable", self._MDELETE)

    def create_user(self, name, password, root_password, roles=None):
        """
        Create a user in the cluster.
        :param name: The name of the user.
        :param password: The password of user.
        :param root_password: The password of the root user.
        :param roles: The roles that will be granted to the user.
        A `list`, like`['r1', 'r2']`. Defaults to `None`.
        :return: A `dict`, like`{"user":"u1","roles":['r1']}`
        """
        self.basic_auth_account = self._root_auth(root_password)
        path = self._user_path + self._sanitize_key(name)
        if roles is not None:
            params = {"user": name, "password": password, "roles": roles}
        else:
            params = {"user": name, "password": password}

        res = self.api_execute(path, self._MPUT, params=params, bodyinjson=True)
        return self._to_dict(res)

    def create_role(self, name, root_password, permissions=None):
        """
        Create a role in the cluster.
        :param name: The name of the role.
        :param root_password: The password of the root user.
        :param permissions: A `dict`, like`{'read': ['/*'], 'write': ['/*']}`.
        Defaults to `None`.
        :return: A `dict`, like`{"role":"w_role","permissions":{"kv":{"read":["/*"],"write":["/*"]}}}`
        """
        self.basic_auth_account = self._root_auth(root_password)
        path = self._role_path + self._sanitize_key(name)
        if permissions is not None:
            params = {"role": name, "permissions": {"kv": permissions}}
        else:
            params = {"role": name}

        res = self.api_execute(path, self._MPUT, params=params, bodyinjson=True)
        return self._to_dict(res)

    def get_user(self, name, root_password):
        """
        Get the user information of the cluster.
        :param name: The name of the user.
        if `None`, return all users information.

        :param root_password: The password of the root user.
        :return: A `dict`
        """
        # {
        #     "user": "root",
        #     "roles": [
        #         {
        #             "role": "root",
        #             "permissions": {
        #                 "kv": {
        #                     "read": [
        #                         "/*"
        #                     ],
        #                     "write": [
        #                         "/*"
        #                     ]
        #                 }
        #             }
        #         }
        #     ]
        # }
        self.basic_auth_account = self._root_auth(root_password)
        if name is not None:
            path = self._user_path + self._sanitize_key(name)
        else:
            path = self._user_path

        res = self.api_execute(path, self._MGET)
        return self._to_dict(res)

    def get_role(self, name, root_password):
        """
        Get the role information of the cluster.
        :param name: The name of the role.
        if `None`, return all roles information.
        :param root_password: The password of the root user.
        :return: a dict
        """
        self.basic_auth_account = self._root_auth(root_password)
        if name is not None:
            path = self._role_path + self._sanitize_key(name)
        else:
            path = self._role_path

        res = self.api_execute(path, self._MGET)
        return self._to_dict(res)

    def grant_user_roles(self, name, root_password, roles):
        """
        Grant roles to user.
        :param name: The name of the user.
        :param root_password: The password of the root user.
        :param roles: The roles that will be granted to the user.
        A `list`, like`['r1', 'r2']`.
        :return: A `dict`, like`{u'user': u'u_test', u'roles': [u'r_test']}`
        """
        self.basic_auth_account = self._root_auth(root_password)
        path = self._user_path + self._sanitize_key(name)
        params = {"user": name, "grant": roles}

        res = self.api_execute(path, self._MPUT, params=params, bodyinjson=True)
        return self._to_dict(res)

    def revoke_user_roles(self, name, root_password, roles):
        """
        Grant roles to user.
        :param name: The name of the user.
        :param root_password: The password of the root user.
        :param roles: The roles that will be revoked from the user.
        A `list`, like`['r1', 'r2']`.
        :return: A `dict`, like`{u'user': u'u_test', u'roles': []}`
        """
        self.basic_auth_account = self._root_auth(root_password)
        path = self._user_path + self._sanitize_key(name)
        params = {"user": name, "revoke": roles}

        res = self.api_execute(path, self._MPUT, params=params, bodyinjson=True)
        return self._to_dict(res)

    def grant_role_permissions(self, name, root_password, permissions):
        """
        Grant permissions to the role.
        :param name: The name of the role.
        :param root_password: The password of the root user.
        :param permissions: The permissions that will be granted to the role.
        A `dict`, like`{'read': ['/*'], 'write': ['/*']}`.
        :return: A `dict`, like`{u'role': u'r_test', u'permissions': {u'kv': {u'read': [u'/*'], u'write': []}}}`
        """
        self.basic_auth_account = self._root_auth(root_password)
        path = self._role_path + self._sanitize_key(name)
        params = {"role": name, "grant": {"kv": permissions}}

        res = self.api_execute(path, self._MPUT, params=params, bodyinjson=True)
        return self._to_dict(res)

    def revoke_role_permissions(self, name, root_password, permissions):
        """
        Revoke permissions from the role.
        :param name: The name of the role.
        :param root_password: The password of the root user.
        :param permissions: The permissions that will be granted to the role.
        A `dict`, like`{'read': ['/*'], 'write': ['/*']}`.
        :return: A `dict`, like`{u'role': u'r_test', u'permissions': {u'kv': {u'read': [], u'write': []}}}`
        """
        self.basic_auth_account = self._root_auth(root_password)
        path = self._role_path + self._sanitize_key(name)
        params = {"role": name, "revoke": {"kv": permissions}}

        res = self.api_execute(path, self._MPUT, params=params, bodyinjson=True)
        return self._to_dict(res)

    def delete_user(self, user_name, root_password):
        """
        Delete the user of the cluster.
        :param user_name: The name of the user.
        :param root_password: The password of the root user.
        :return: nothing
        """
        self.basic_auth_account = self._root_auth(root_password)
        path = self._user_path + self._sanitize_key(user_name)
        self.api_execute(path, self._MDELETE)

    def delete_role(self, role_name, root_password):
        """
        Delete the role of the cluster.
        :param role_name: The name of the role.
        :param root_password: The password of the root user.
        :return: nothing
        """
        self.basic_auth_account = self._root_auth(root_password)
        path = self._role_path + self._sanitize_key(role_name)
        self.api_execute(path, self._MDELETE)
