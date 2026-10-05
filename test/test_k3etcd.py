import base64
import http.server
import json
import ssl
import threading
import time
import unittest

import k3ut
import k3utdocker
import k3utfjson
import trustme

import k3etcd

dd = k3ut.dd


HOSTS = (
    ("192.168.52.30", 3379),
    ("192.168.52.31", 3379),
    ("192.168.52.32", 3379),
    ("192.168.52.33", 3379),
    ("192.168.52.34", 3379),
)

ETCD_NAMES = (
    "etcd_t0",
    "etcd_t1",
    "etcd_t2",
    "etcd_t3",
    "etcd_t4",
)
ETCD_NODES = (
    "node_0",
    "node_1",
    "node_2",
    "node_3",
    "node_4",
)

etcd_test_tag = "quay.io/coreos/etcd:v3.5.0"


class TestEtcdKeysResult(unittest.TestCase):
    def test_get_subtree_1_level(self):
        response = {
            "node": {
                "key": "/test",
                "value": "hello",
                "expiration": None,
                "ttl": None,
                "modifiedIndex": 5,
                "createdIndex": 1,
                "newKey": False,
                "dir": False,
            }
        }
        result = k3etcd.EtcdKeysResult(**response)
        for k, v in list(response["node"].items()):
            self.assertEqual(v, getattr(result, k))

        self.assertListEqual([result], list(result.get_subtree(leaves_only=False)))
        self.assertListEqual([result], list(result.get_subtree(leaves_only=True)))
        self.assertListEqual([result], list(result.leaves))

    def test_get_subtree_2_level(self):
        leaf0 = {
            "key": "/test/leaf0",
            "value": "hello1",
            "expiration": None,
            "ttl": None,
            "modifiedIndex": 5,
            "createdIndex": 1,
            "newKey": False,
            "dir": False,
        }
        leaf1 = {
            "key": "/test/leaf1",
            "value": "hello2",
            "expiration": None,
            "ttl": None,
            "modifiedIndex": 6,
            "createdIndex": 2,
            "newKey": False,
            "dir": False,
        }
        testnode = {
            "node": {
                "key": "/test/",
                "expiration": None,
                "ttl": None,
                "modifiedIndex": 6,
                "createdIndex": 2,
                "newKey": False,
                "dir": True,
                "nodes": [leaf0, leaf1],
            }
        }
        result = k3etcd.EtcdKeysResult(**testnode)
        for k, v in list(testnode["node"].items()):
            if not hasattr(result, k):
                continue

            self.assertEqual(v, getattr(result, k))

        self.assertListEqual(result._children, testnode["node"]["nodes"])

        subtree = list(result.get_subtree(leaves_only=True))
        self.assertEqual("/test/leaf0", subtree[0].key)
        self.assertEqual("/test/leaf1", subtree[1].key)
        self.assertEqual(len(subtree), 2)
        self.assertListEqual(subtree, list(result.leaves))

        subtree = list(result.get_subtree(leaves_only=False))
        self.assertEqual("/test/", subtree[0].key)
        self.assertEqual("/test/leaf0", subtree[1].key)
        self.assertEqual("/test/leaf1", subtree[2].key)
        self.assertEqual(len(subtree), 3)

    def test_get_subtree_3_level(self):
        leaf0 = {
            "key": "/test/mid0/leaf0",
            "value": "hello1",
        }
        leaf1 = {
            "key": "/test/mid0/leaf1",
            "value": "hello2",
        }
        leaf2 = {
            "key": "/test/mid1/leaf2",
            "value": "hello1",
        }
        leaf3 = {
            "key": "/test/mid1/leaf3",
            "value": "hello2",
        }
        mid0 = {"key": "/test/mid0/", "dir": True, "nodes": [leaf0, leaf1]}
        mid1 = {"key": "/test/mid1/", "dir": True, "nodes": [leaf2, leaf3]}
        testnode = {"node": {"key": "/test/", "dir": True, "nodes": [mid0, mid1]}}

        result = k3etcd.EtcdKeysResult(**testnode)
        for k, v in list(testnode["node"].items()):
            if not hasattr(result, k):
                continue

            self.assertEqual(v, getattr(result, k))

        self.assertListEqual(result._children, testnode["node"]["nodes"])

        subtree = list(result.get_subtree(leaves_only=True))
        self.assertEqual("/test/mid0/leaf0", subtree[0].key)
        self.assertEqual("/test/mid0/leaf1", subtree[1].key)
        self.assertEqual("/test/mid1/leaf2", subtree[2].key)
        self.assertEqual("/test/mid1/leaf3", subtree[3].key)
        self.assertEqual(len(subtree), 4)
        self.assertListEqual(subtree, list(result.leaves))

        subtree = list(result.get_subtree(leaves_only=False))
        self.assertEqual("/test/", subtree[0].key)
        self.assertEqual("/test/mid0/", subtree[1].key)
        self.assertEqual("/test/mid0/leaf0", subtree[2].key)
        self.assertEqual("/test/mid0/leaf1", subtree[3].key)
        self.assertEqual("/test/mid1/", subtree[4].key)
        self.assertEqual("/test/mid1/leaf2", subtree[5].key)
        self.assertEqual("/test/mid1/leaf3", subtree[6].key)
        self.assertEqual(len(subtree), 7)

    def test_eq_ne(self):
        cases = (
            (
                {"node": {"key": "key1"}},
                {"node": {"key": "key2"}},
                False,
            ),
            (
                {"node": {"key": "key1"}},
                {"node": {"key": "key1"}},
                True,
            ),
            (
                {"node": {"key": "key1", "value": "val1"}},
                {"node": {"key": "key1", "value": "val2"}},
                False,
            ),
        )

        for node1, node2, expected_res in cases:
            res1 = k3etcd.EtcdKeysResult(**node1)
            res2 = k3etcd.EtcdKeysResult(**node2)
            self.assertEqual(res1 == res2, expected_res)


class TestException(unittest.TestCase):
    def test_errorcode_exception(self):
        cases = (
            ({"errorCode": 100, "message": "foo", "cause": "bar"}, k3etcd.EcodeKeyNotFound, "foo : bar"),
            ({"errorCode": 101, "message": "foo", "cause": "bar"}, k3etcd.EcodeTestFailed, "foo : bar"),
            ({"errorCode": 102, "message": "foo", "cause": "bar"}, k3etcd.EcodeNotFile, "foo : bar"),
            ({"errorCode": 103, "message": "foo", "cause": "bar"}, k3etcd.EtcdException, "foo : bar"),
            ({"errorCode": 104, "message": "foo", "cause": "bar"}, k3etcd.EcodeNotDir, "foo : bar"),
            ({"errorCode": 105, "message": "foo", "cause": "bar"}, k3etcd.EcodeNodeExist, "foo : bar"),
            ({"errorCode": 106, "message": "foo", "cause": "bar"}, k3etcd.EtcdKeyError, "foo : bar"),
            ({"errorCode": 107, "message": "foo", "cause": "bar"}, k3etcd.EcodeRootROnly, "foo : bar"),
            ({"errorCode": 108, "message": "foo", "cause": "bar"}, k3etcd.EcodeDirNotEmpty, "foo : bar"),
            ({"errorCode": 110, "message": "foo", "cause": "bar"}, k3etcd.EcodeInscientPermissions, "foo : bar"),
            ({"errorCode": 200, "message": "foo", "cause": "bar"}, k3etcd.EtcdValueError, "foo : bar"),
            ({"errorCode": 201, "message": "foo", "cause": "bar"}, k3etcd.EcodePrevValueRequired, "foo : bar"),
            ({"errorCode": 202, "message": "foo", "cause": "bar"}, k3etcd.EcodeTTLNaN, "foo : bar"),
            ({"errorCode": 203, "message": "foo", "cause": "bar"}, k3etcd.EcodeIndexNaN, "foo : bar"),
            ({"errorCode": 209, "message": "foo", "cause": "bar"}, k3etcd.EcodeInvalidField, "foo : bar"),
            ({"errorCode": 210, "message": "foo", "cause": "bar"}, k3etcd.EcodeInvalidForm, "foo : bar"),
            ({"errorCode": 300, "message": "foo", "cause": "bar"}, k3etcd.EtcdInternalError, "foo : bar"),
            ({"errorCode": 301, "message": "foo", "cause": "bar"}, k3etcd.EtcdInternalError, "foo : bar"),
            ({"errorCode": 400, "message": "foo", "cause": "bar"}, k3etcd.EtcdWatchError, "foo : bar"),
            ({"errorCode": 401, "message": "foo", "cause": "bar"}, k3etcd.EtcdWatchError, "foo : bar"),
            ({"errorCode": 500, "message": "foo", "cause": "bar"}, k3etcd.EtcdInternalError, "foo : bar"),
            (
                {"errorCode": 501, "message": "foo", "cause": "bar"},
                k3etcd.EtcdException,
                "Unable to decode server response",
            ),
            ({}, k3etcd.EtcdException, "Unable to decode server response"),
        )

        for res_body, e, expect_msg in cases:
            res = k3etcd.Response(body=k3utfjson.dump(res_body))
            self.assertRaisesRegex(e, expect_msg, k3etcd.EtcdError.handle, res)


class TestResponse(unittest.TestCase):
    def test_from_http_decodes_body(self):
        # k3http.Client.read_body() returns bytes; Response.data stays str.
        class FakeHttp:
            def __init__(self):
                self.status = 200
                self.headers = {}

            def read_body(self, size):
                return "中".encode()

        res = k3etcd.Response.from_http(FakeHttp())
        self.assertEqual("中", res.data)


class _FakeEtcdHandler(http.server.BaseHTTPRequestHandler):
    def _serve(self):
        size = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(size)

        fake = self.server.fake
        fake.requests.append({"path": self.path, "headers": self.headers, "body": body})

        status, headers, resp_body = fake.reply(self.path)
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)

    do_GET = _serve
    do_PUT = _serve
    do_POST = _serve
    do_DELETE = _serve

    def log_message(self, *args):
        pass


class FakeEtcd:
    """
    An HTTP server on 127.0.0.1 that records each request in `requests`.
    It answers with `reply(path)`, which returns `(status, headers, body)`.
    With `ssl_context`, it serves HTTPS.
    """

    def __init__(self, reply, ssl_context=None):
        self.reply = reply
        self.requests = []

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _FakeEtcdHandler)
        if ssl_context is not None:
            self.server.socket = ssl_context.wrap_socket(self.server.socket, server_side=True)
        self.server.fake = self
        self.port = self.server.server_address[1]

        th = threading.Thread(target=self.server.serve_forever, daemon=True)
        th.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class TestRequest(unittest.TestCase):
    def test_json_body_length(self):
        fake = FakeEtcd(lambda path: (201, {}, b'{"user": "u1"}'))
        self.addCleanup(fake.close)

        c = k3etcd.Client(host="127.0.0.1", port=fake.port, allow_reconnect=False)
        c.create_user("u1", "中", "root_password")

        body = fake.requests[0]["body"]
        self.assertEqual({"user": "u1", "password": "中"}, json.loads(body))

    def test_redirect_limit(self):
        def reply(path):
            return 307, {"Location": f"http://127.0.0.1:{fake.port}{path}"}, b""

        fake = FakeEtcd(reply)
        self.addCleanup(fake.close)

        c = k3etcd.Client(host="127.0.0.1", port=fake.port, allow_reconnect=False)
        with self.assertRaisesRegex(k3etcd.EtcdException, "too many redirects"):
            c.get("foo")

        self.assertEqual(k3etcd.Client._MAX_REDIRECTS + 1, len(fake.requests))

    def test_redirect_to_other_server_drops_auth(self):
        # The same IP with another port is another server.
        target = FakeEtcd(lambda path: (200, {}, b'{"action": "get", "node": {"key": "/foo", "value": "bar"}}'))
        self.addCleanup(target.close)

        location = f"http://127.0.0.1:{target.port}/v2/keys/foo"
        fake = FakeEtcd(lambda path: (307, {"Location": location}, b""))
        self.addCleanup(fake.close)

        c = k3etcd.Client(host="127.0.0.1", port=fake.port, allow_reconnect=False, basic_auth_account="root:pw")
        res = c.get("foo")
        self.assertEqual("bar", res.value)

        auth = "Basic " + base64.b64encode(b"root:pw").decode()
        self.assertEqual(auth, fake.requests[0]["headers"].get("Authorization"))
        self.assertIsNone(target.requests[0]["headers"].get("Authorization"))

    def test_redirect_to_same_server_keeps_auth(self):
        def reply(path):
            if path == "/v2/keys/foo":
                return 307, {"Location": f"http://127.0.0.1:{fake.port}/v2/keys/bar"}, b""
            return 200, {}, b'{"action": "get", "node": {"key": "/bar", "value": "x"}}'

        fake = FakeEtcd(reply)
        self.addCleanup(fake.close)

        c = k3etcd.Client(host="127.0.0.1", port=fake.port, allow_reconnect=False, basic_auth_account="root:pw")
        res = c.get("foo")
        self.assertEqual("x", res.value)

        auth = "Basic " + base64.b64encode(b"root:pw").decode()
        sent = [r["headers"].get("Authorization") for r in fake.requests]
        self.assertEqual([auth, auth], sent)

    def test_https(self):
        ca = trustme.CA()
        server_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ca.issue_cert("127.0.0.1").configure_cert(server_ctx)

        body = b'{"action": "get", "node": {"key": "/foo", "value": "bar"}}'
        fake = FakeEtcd(lambda path: (200, {}, body), server_ctx)
        self.addCleanup(fake.close)

        client_ctx = ssl.create_default_context()
        ca.configure_trust(client_ctx)

        c = k3etcd.Client(
            host="127.0.0.1", port=fake.port, protocol="https", https_context=client_ctx, allow_reconnect=False
        )
        res = c.get("foo")
        self.assertEqual("bar", res.value)
        self.assertEqual(f"https://127.0.0.1:{fake.port}", c.base_uri)

    def test_https_untrusted_certificate(self):
        ca = trustme.CA()
        server_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ca.issue_cert("127.0.0.1").configure_cert(server_ctx)

        fake = FakeEtcd(lambda path: (200, {}, b"{}"), server_ctx)
        self.addCleanup(fake.close)

        # The default context does not trust the test CA.
        c = k3etcd.Client(host="127.0.0.1", port=fake.port, protocol="https", allow_reconnect=False)
        with self.assertRaises(k3etcd.EtcdSSLError):
            c.get("foo")

        self.assertEqual([], fake.requests)


class TestClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        k3utdocker.pull_image(etcd_test_tag)

    def setUp(self):
        _start_etcd_server(HOSTS, ETCD_NAMES, ETCD_NODES)
        self._clear_all()

    def _clear_all(self):
        while True:
            try:
                c = k3etcd.Client(host=HOSTS)
                res = c.get("", recursive=True)
                for n in res._children:
                    c.delete(n["key"], dir="dir" in n and n["dir"], recursive=True)
                break
            except k3etcd.EtcdException as e:
                dd(repr(e))
                time.sleep(1)
                break

    def test_machine_cache(self):
        machine = list(HOSTS)
        machine.pop(0)
        machine = [f"http://{ip}:{port}" for ip, port in machine]
        cases = (
            (HOSTS, 3379, True, machine),
            ("192.168.52.30", 3379, True, machine),
            (HOSTS, 3379, False, []),
            ("192.168.52.30", 3379, False, []),
        )

        for host, port, allow_reconnect, expected_machines in cases:
            c = k3etcd.Client(host=host, port=port, allow_reconnect=allow_reconnect)
            self.assertEqual("http://192.168.52.30:3379", c._base_uri)
            self.assertListEqual(expected_machines, c._machines_cache)

    def test_property(self):
        cases = (
            ("192.168.52.30", 3379, "http", 10, True),
            ("192.168.52.31", 3379, "http", 20, False),
        )

        for host, port, protocol, timeout, allow_redirect in cases:
            c = k3etcd.Client(
                host=host, port=port, protocol=protocol, read_timeout=timeout, allow_redirect=allow_redirect
            )
            self.assertEqual(host, c.host)
            self.assertEqual(port, c.port)
            self.assertEqual(protocol, c.protocol)
            self.assertEqual(timeout, c.read_timeout)
            self.assertEqual(allow_redirect, c.allow_redirect)
            self.assertEqual(f"{protocol}://{host}:{port}", c.base_uri)

    def test_members(self):
        c = k3etcd.Client(host=HOSTS)

        mems = c.members
        for h, p in HOSTS:
            succ = False
            for m in mems:
                if f"http://{h}:{p}" == m["clientURLs"][0]:
                    succ = True
                    break
            self.assertTrue(succ)

    def test_leader(self):
        c = k3etcd.Client(host=HOSTS)

        leader = c.leader
        self.assertIsNotNone(leader)
        self.assertIn(leader, c.members)

    def test_version(self):
        c = k3etcd.Client(host=HOSTS)

        ver = c.version
        self.assertIn("etcdserver", ver)
        self.assertIn("etcdcluster", ver)

    def test_nomoremachine_exception(self):
        k3utdocker.stop_container(*ETCD_NAMES)
        c = k3etcd.Client(host=HOSTS, read_timeout=1)
        self.assertRaises(k3etcd.NoMoreMachineError, c.get, "/key")

    def test_etcdreadtimeouterror_exception(self):
        k3utdocker.stop_container(*ETCD_NAMES)
        c = k3etcd.Client(host=HOSTS, read_timeout=1)
        self.assertRaises(
            k3etcd.EtcdReadTimeoutError, c.api_execute, "/v2/keys/abc", "GET", timeout=1, raise_read_timeout=True
        )

    def test_etcdrequestserror_exception(self):
        c = k3etcd.Client(host=HOSTS)
        self.assertRaises(
            k3etcd.EtcdRequestError, c._request, "http://192.168.52.30:3379/v2/keys/abc", "GETTT", None, None, None
        )
        self.assertRaises(k3etcd.EtcdRequestError, c.write, dir=True, value="val", key="key")

    def test_etcdincompleteread_exception(self):
        res = k3etcd.Response(body="abc")
        c = k3etcd.Client(host=HOSTS)
        self.assertRaises(k3etcd.EtcdIncompleteRead, c._to_dict, res)

    def test_next_server(self):
        k3utdocker.stop_container("etcd_t0")
        c = k3etcd.Client(host=HOSTS, read_timeout=2)
        c.set("key", "val")
        self.assertIn("key", c)

    def test_set_and_get(self):
        cases = (
            ("foo", "f"),
            ("123", "456"),
            ("12foo", "1f"),
            ("*-@", "special"),
            ("/bar", "bb"),
            ("/789", "1000"),
            ("/12bar", "1bb"),
            ("/$*-", "specialss"),
        )

        cli = k3etcd.Client(host=HOSTS)
        for key, val in cases:
            cli.set(key, val)
            res = cli.get(key)
            self.assertEqual(val, res.value)

    def test_decode(self):
        cases = (
            ("key1", k3utfjson.dump("我", encoding=None), '"\\u6211"'),
            # when save '"\xb6\xd4"' with k3etcd but the k3etcd cannot
            # convert them, so the default '\ufffd\ufffd' was saved.
            # when get it from k3etcd, '\ufffd\ufffd' was converted into
            # '"\xef\xbf\xbd\xef\xbf\xbd"'.
            ("key2", k3utfjson.dump("对", encoding=None), '"\\u5bf9"'),
            ("key3", k3utfjson.dump("我", encoding=None), '"\\u6211"'),
            ("key4", k3utfjson.dump('{"我": "我"}', encoding=None), '"{\\"\\u6211\\": \\"\\u6211\\"}"'),
            ("key5", k3utfjson.dump(("我",), encoding=None), '["\\u6211"]'),
        )
        cli = k3etcd.Client(host=HOSTS)
        for count, (key, val, expected) in enumerate(cases):
            print(count)
            cli.set(key, val)
            res = cli.get(key)
            self.assertEqual(expected, res.value)

    def test_ttl(self):
        c = k3etcd.Client(host=HOSTS)

        c.set("abc", "val", ttl=1)
        self.assertIn("abc", c)
        time.sleep(2)
        self.assertNotIn("abc", c)

    def test_get_conditions(self):
        c = k3etcd.Client(host=HOSTS)

        kv = (
            ("key1", "val1", False),
            ("key2", "val2", False),
            ("dir1", None, True),
            ("dir1/key3", "val3", False),
        )
        for k, v, d in kv:
            print(k, v, d)
            c.test_and_set(k, v, dir=d)

        nodes = c.get("", sorted=True)._children
        self.assertEqual("/dir1", nodes[0]["key"])
        self.assertEqual("/key1", nodes[1]["key"])
        self.assertEqual("/key2", nodes[2]["key"])

        nodes = c.get("", sorted=True, recursive=False)._children
        self.assertNotIn("nodes", nodes[0])
        nodes = c.get("", sorted=True, recursive=True)._children
        self.assertIn("nodes", nodes[0])

    def test_set_conditions(self):
        c = k3etcd.Client(host=HOSTS)

        c.test_and_set("foo", "val")
        c.test_and_set("foo", "val", prevExist=True)
        self.assertRaises(k3etcd.EcodeNodeExist, c.test_and_set, "foo", "val", prevExist=False)

        res = c.test_and_set("foo", "val1", prevValue="val")
        self.assertEqual("val1", res.value)
        self.assertRaises(k3etcd.EcodeTestFailed, c.test_and_set, "foo", "val1", prevValue="val1000")

        res = c.test_and_set("foo", "val2", prevIndex=res.modifiedIndex)
        self.assertEqual("val2", res.value)

        res = c.test_and_set("foo", None, refresh=True, ttl=2)
        self.assertEqual(2, res.ttl)

    def test_set_append(self):
        c = k3etcd.Client(host=HOSTS)

        c.test_and_set("dd", None, dir=True)
        c.test_and_set("dd", "val1", append=True)
        c.test_and_set("dd", "val2", append=True)

        res = c.get("dd")
        self.assertEqual(2, len(res._children))
        for n in res.leaves:
            self.assertIn(n.value, ["val1", "val2"])

    def test_watch(self):
        c = k3etcd.Client(host=HOSTS)

        res = c.set("abc", "val")
        self.assertEqual(res.value, c.watch("abc", waitindex=res.modifiedIndex).value)
        self.assertRaises(k3etcd.EtcdReadTimeoutError, c.watch, "abc", waitindex=res.modifiedIndex + 1, timeout=1)

        start_index = res.modifiedIndex
        for i in range(4):
            res = c.set("abc", f"val{i}")
            end_index = res.modifiedIndex

        result = []
        for res in c.eternal_watch("abc", waitindex=start_index + 1, until=end_index):
            result.append(res.value)

        self.assertListEqual(["val0", "val1", "val2", "val3"], result)

    def test_update(self):
        c = k3etcd.Client(host=HOSTS)

        res = c.set("key", "val")
        res.value += "abc"
        res = c.update(res)

        self.assertEqual("valabc", res.value)

    def test_delete(self):
        c = k3etcd.Client(host=HOSTS)
        kv = (
            ("key1", "val1", False),
            ("dir1", None, True),
            ("dir1/key2", "val2", False),
        )
        for k, v, d in kv:
            c.test_and_set(k, v, dir=d)

        c.delete("key1")
        self.assertNotIn("key1", c)

        self.assertRaises(k3etcd.EcodeNotFile, c.delete, "dir1")
        self.assertRaises(k3etcd.EcodeDirNotEmpty, c.delete, "dir1", dir=True)

        c.delete("dir1", recursive=True, dir=True)
        self.assertNotIn("dir1", c)

    def test_mkdir(self):
        c = k3etcd.Client(host=HOSTS)

        res = c.mkdir("d")
        self.assertTrue(res.dir)
        self.assertEqual("/d", res.key)
        self.assertIn("d", c)

    def test_refresh(self):
        c = k3etcd.Client(host=HOSTS)

        c.set("key", "val")
        res = c.refresh("key", ttl=1)
        self.assertEqual(1, res.ttl)

    def test_lsdir(self):
        c = k3etcd.Client(host=HOSTS)

        c.test_and_set("dir1", None, dir=True)
        res = c.lsdir("dir1")
        self.assertTrue(res.dir)
        self.assertEqual("/dir1", res.key)

    def test_rlsdir(self):
        c = k3etcd.Client(host=HOSTS)

        c.test_and_set("dir1", None, dir=True)
        c.test_and_set("dir1/key", "val")
        res = c.rlsdir("dir1")
        self.assertTrue(res.dir)
        self.assertEqual("/dir1", res.key)
        self.assertEqual(1, len(res._children))
        self.assertEqual("val", res._children[0]["value"])

    def test_deldir(self):
        c = k3etcd.Client(host=HOSTS)

        c.test_and_set("dir1", None, dir=True)
        c.deldir("dir1")
        self.assertNotIn("dir1", c)

    def test_rdeldir(self):
        c = k3etcd.Client(host=HOSTS)

        c.test_and_set("dir1", None, dir=True)
        c.test_and_set("dir1/key", "val")
        c.rdeldir("dir1")
        self.assertNotIn("dir1", c)

    def _set_auth(self, hosts):
        root_pwd = "123456"
        c = k3etcd.Client(host=hosts)
        c.create_root(root_pwd)
        c.enable_auth(root_pwd)
        c.revoke_role_permissions("guest", root_pwd, {"write": ["/*"], "read": ["/*"]})
        c.create_role("rw_role", root_pwd, {"write": ["/*"], "read": ["/*"]})
        c.create_user("rw_user", "654321", root_pwd, ["rw_role"])
        time.sleep(1)

    def test_auth(self):
        hosts = (
            ("192.168.52.90", 3379),
            ("192.168.52.91", 3379),
            ("192.168.52.92", 3379),
        )
        names = (
            "etcd_au0",
            "etcd_au1",
            "etcd_au2",
        )
        nodes = (
            "node_au0",
            "node_au1",
            "node_au2",
        )
        _start_etcd_server(hosts, names, nodes)
        time.sleep(10)

        try:
            self._set_auth(hosts)
            c = k3etcd.Client(host=hosts)
            self.assertRaises(k3etcd.EcodeInscientPermissions, c.set, "key", "val")
            self.assertRaises(k3etcd.EcodeInscientPermissions, c.get, "")
            c = k3etcd.Client(host=hosts, basic_auth_account="rw_user:654321")
            c.set("key", "val")
            self.assertIn("key", c)
            res = c.get("key")
            self.assertEqual("val", res.value)

            c.disable_auth("123456")
            c = k3etcd.Client(host=hosts)
            c.set("key1", "val1")
            self.assertIn("key1", c)
            res = c.get("key1")
            self.assertEqual("val1", res.value)
        finally:
            k3utdocker.remove_container(*names)

    def test_st_leader(self):
        c = k3etcd.Client(host=HOSTS)
        leader = c.st_leader
        self.assertIn("leader", leader)
        self.assertEqual(4, len(leader["followers"]))

    def test_st_store(self):
        c = k3etcd.Client(host=HOSTS)
        store = c.st_store

        expected_res = [
            "getsSuccess",
            "getsFail",
            "setsSuccess",
            "setsFail",
            "deleteSuccess",
            "deleteFail",
            "updateSuccess",
            "updateFail",
            "createSuccess",
            "createFail",
            "compareAndSwapSuccess",
            "compareAndSwapFail",
            "compareAndDeleteSuccess",
            "compareAndDeleteFail",
            "expireCount",
            "watchers",
        ]

        self.assertEqual(set(expected_res), set(store.keys()))

    def test_st_self(self):
        c = k3etcd.Client(host=HOSTS)
        s = c.st_self

        self.assertTrue(type(s) is dict)
        self.assertTrue(len(s) > 0)

    def test_exception(self):
        c = k3etcd.Client(host=HOSTS)
        self.assertRaises(k3etcd.EcodeKeyNotFound, c._st, "/XXX")

    def test_names(self):
        c = k3etcd.Client(host=HOSTS)
        expected_res = [
            "node_0",
            "node_1",
            "node_2",
            "node_3",
            "node_4",
        ]

        self.assertEqual(set(expected_res), set(c.names))

    def test_ids(self):
        c = k3etcd.Client(host=HOSTS)
        self.assertEqual(5, len(c.ids))

    def test_clienturls(self):
        expected_res = [f"http://{ip}:{port}" for ip, port in HOSTS]
        c = k3etcd.Client(host=HOSTS)
        self.assertEqual(set(expected_res), set(c.clienturls))

    def test_peerurls(self):
        expected_res = [f"http://{ip}:3380" for ip, _ in HOSTS]
        c = k3etcd.Client(host=HOSTS)
        self.assertEqual(set(expected_res), set(c.peerurls))

    def test_change_peerurls(self):
        c = k3etcd.Client(host=HOSTS)
        mem = c.members[0]
        old_urls = mem["peerURLs"]
        new_urls = [old_urls[0] + "1"]

        c.change_peerurls(mem["id"], *new_urls)
        self.assertIn(new_urls[0], c.peerurls)

        c.change_peerurls(mem["id"], *old_urls)
        self.assertIn(old_urls[0], c.peerurls)

        self.assertRaises(k3etcd.EtcdException, c.change_peerurls, mem["id"], [])

    def test_del_member(self):
        hosts = (
            ("192.168.52.50", 3379),
            ("192.168.52.51", 3379),
            ("192.168.52.52", 3379),
        )
        names = ("etcd_d0", "etcd_d1", "etcd_d2")
        nodes = (
            "node_d0",
            "node_d1",
            "node_d2",
        )
        _start_etcd_server(hosts, names, nodes)

        time.sleep(10)
        c = k3etcd.Client(host=hosts, read_timeout=1)

        try:
            for i in range(2):
                ids = c.ids
                c.del_member(ids[0])
                self.assertEqual(2 - i, len(c.members))
                time.sleep(10)
        finally:
            k3utdocker.remove_container(*names)

    def test_add_member(self):
        hosts = [
            ("192.168.52.70", 3379),
            ("192.168.52.71", 3379),
        ]
        names = ["etcd_a0", "etcd_a1"]
        nodes = ["node_a0", "node_a1"]
        _start_etcd_server(hosts, names, nodes)
        time.sleep(10)

        cases = (
            ("192.168.52.72", "etcd_a2", "node_a2", 3),
            ("192.168.52.73", "etcd_a3", "node_a3", 4),
        )

        c = k3etcd.Client(host=hosts)
        try:
            for ip, name, node, count in cases:
                c.add_member(*[f"http://{ip}:3380"])
                hosts.append((ip, 3379))
                nodes.append(node)
                names.append(name)

                k3utdocker.start_container(
                    name, etcd_test_tag, ip, _generate_command(len(hosts) - 1, hosts, nodes, state="existing")
                )

                time.sleep(10)

                self.assertEqual(count, len(c.members))
        finally:
            k3utdocker.remove_container(*names)

    def _clear_users_roles(self, root_pwd):
        c = k3etcd.Client(host=HOSTS)

        users = c.get_user(None, root_pwd)
        if users is not None and users["users"] is not None:
            for u in users["users"]:
                try:
                    c.delete_user(u["user"], root_pwd)
                except k3etcd.EtcdException:
                    continue

        roles = c.get_role(None, root_pwd)
        if roles is not None and roles["roles"] is not None:
            for r in roles["roles"]:
                try:
                    c.delete_role(r["role"], root_pwd)
                except k3etcd.EtcdException:
                    continue

    def test_create_root(self):
        c = k3etcd.Client(host=HOSTS)
        res = c.create_root("123")

        self.assertEqual("root", res["user"])

    def test_create_and_get_user(self):
        c = k3etcd.Client(host=HOSTS)

        cases = (
            ("u1", "p1"),
            ("u2", "p2"),
            ("u3", "p3"),
            ("u4", "p4"),
        )

        all_users = {"users": []}
        try:
            for u, p in cases:
                c.create_user(u, p, "")
                res = c.get_user(u, "")
                self.assertEqual({"user": u}, res)

                all_users["users"].append(res)
                res = c.get_user(None, "")
                self.assertEqual(all_users, res)
        finally:
            self._clear_users_roles("")

    def test_create_and_get_role(self):
        c = k3etcd.Client(host=HOSTS)

        cases = ("r1", "r2", "r3", "r4")

        # default role cannot delete
        all_roles = [{"role": "root", "permissions": {"kv": {"read": ["/*"], "write": ["/*"]}}}]

        try:
            for r in cases:
                c.create_role(r, "")
                res = c.get_role(r, "")
                expected = {"role": r, "permissions": {"kv": {"read": None, "write": None}}}
                self.assertEqual(expected, res)

                all_roles.insert(-1, res)
                res = c.get_role(None, "")
                self.assertEqual(all_roles, res["roles"])
        finally:
            self._clear_users_roles("")

    def test_grant_revoke_user_roles(self):
        c = k3etcd.Client(host=HOSTS)
        c.create_user("u_test", "11", "")
        c.create_role("r_test", "")

        try:
            c.grant_user_roles("u_test", "", ["r_test"])
            res = c.get_user("u_test", "")
            self.assertEqual("r_test", res["roles"][0]["role"])

            c.revoke_user_roles("u_test", "", ["r_test"])
            res = c.get_user("u_test", "")
            self.assertNotIn("roles", res)
        finally:
            self._clear_users_roles("")

    def test_grant_revoke_role_permissions(self):
        c = k3etcd.Client(host=HOSTS)
        c.create_role("r_test", "")

        try:
            c.grant_role_permissions("r_test", "", {"read": ["/*"]})
            r = c.get_role("r_test", "")
            self.assertEqual(["/*"], r["permissions"]["kv"]["read"])

            c.revoke_role_permissions("r_test", "", {"read": ["/*"]})
            r = c.get_role("r_test", "")
            self.assertEqual([], r["permissions"]["kv"]["read"])
        finally:
            self._clear_users_roles("")


def _generate_command(index, hosts, nodes, state="new"):
    node = nodes[index]
    ip, _ = hosts[index]
    cluster = ""
    for i in range(len(hosts)):
        cluster += f"{nodes[i]}=http://{hosts[i][0]}:3380,"

    cluster = cluster[:-1]

    # etcd v3.x requires explicit binary path and --enable-v2 for v2 API
    return f"/usr/local/bin/etcd --enable-v2 --name {node} \
           --initial-advertise-peer-urls http://{ip}:3380 \
           --listen-peer-urls http://{ip}:3380 \
           --advertise-client-urls http://{ip}:3379 \
           --listen-client-urls http://{ip}:3379 \
           --initial-cluster {cluster} \
           --initial-cluster-state {state} \
           --initial-cluster-token test_etcd_token"


def _start_etcd_server(hosts, names, nodes, state="new"):
    k3utdocker.create_network()

    for i in range(len(hosts)):
        name = names[i]
        ip, _ = hosts[i]
        command = _generate_command(i, hosts, nodes, state=state)

        k3utdocker.start_container(name, etcd_test_tag, ip, command)
