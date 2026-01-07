# k3etcd

[![Action-CI](https://github.com/pykit3/k3etcd/actions/workflows/python-package.yml/badge.svg)](https://github.com/pykit3/k3etcd/actions/workflows/python-package.yml)
[![Documentation Status](https://readthedocs.org/projects/k3etcd/badge/?version=stable)](https://k3etcd.readthedocs.io/en/stable/?badge=stable)
[![Package](https://img.shields.io/pypi/pyversions/k3etcd)](https://pypi.org/project/k3etcd)

A python client for Etcd https://github.com/coreos/etcd This module will only work correctly with the etcd server version 2.3.x or later.

k3etcd is a component of [pykit3] project: a python3 toolkit set.


#   Description

A python client for Etcd https://github.com/coreos/etcd

This module will only work correctly with the etcd server version 2.3.x or later.




# Install

```
pip install k3etcd
```

# Synopsis

```python

import k3etcd

hosts=(
    ('192.168.0.100', 2379),
    ('192.168.0.101', 2379),
    ('192.168.0.102', 2379),
)

try:
    c = k3etcd.Client(host=hosts)
    c.set('test_key', 'test_val')
    res = c.get('test_key')
    # type(res) is EtcdKeysResult
    # res.key == 'test_key'
    # res.value == 'test_val'
    # res.dir == False
    # ...

    # c.st_leader
    # out type is `dict`
    # {
    #   "leader": "991200c666cc4678",
    #   "followers":{
    #       "183ebbe2e22ee250": {
    #           "latency": {
    #               "current": 0.00095,
    #               "average": 0.09798531413612557,
    #               "standardDeviation": 1.3282931634902915,
    #               "minimum": 0.000635,
    #               "maximum": 18.407235
    #           },
    #           "counts": {
    #               "fail": 0,
    #               "success": 191
    #           }
    #       },
    #       "291578612bc6deb": {
    #           "latency": {
    #               "current": 0.000949,
    #               "average": 0.001928250000000001,
    #               "standardDeviation": 0.0018525034545722491,
    #               "minimum": 0.000876,
    #               "maximum": 0.017505
    #           },
    #           "counts": {
    #               "fail": 0,
    #               "success": 188
    #           }
    #       },
    #   }
    # }

    # c.st_self
    # out type is `dict`
    #   {
    #       "name": "node_1",
    #       "id": "991200c666cc4678",
    #       "state": "StateLeader",
    #       "startTime": "2017-06-14T05:20:04.334273309Z",
    #       "leaderInfo": {
    #           "leader": "991200c666cc4678",
    #           "uptime": "4h41m55.43860796s",
    #           "startTime": "2017-06-14T05:20:04.477688456Z"
    #       },
    #       "recvAppendRequestCnt": 0,
    #       "sendAppendRequestCnt": 736
    #   }

    # c.st_store
    # out type is `dict`
    #   {
    #       "getsSuccess": 4,
    #       "getsFail": 7,
    #       "setsSuccess": 53,
    #       "setsFail": 0,
    #       "deleteSuccess": 24,
    #       "deleteFail": 2,
    #       "updateSuccess": 2,
    #       "updateFail": 0,
    #       "createSuccess": 7,
    #       "createFail": 1,
    #       "compareAndSwapSuccess": 3,
    #       "compareAndSwapFail": 1,
    #       "compareAndDeleteSuccess": 0,
    #       "compareAndDeleteFail": 0,
    #       "expireCount": 3,
    #       "watchers": 0
    #   }

    n = c.names
    # get names of etcd servers
    # n=['node1', 'node2', 'node3']

    ids = c.ids
    # get ids of etcd servers
    # ids=['fca771384ed46928', '991200c666cc4678', '4768ce54ee212c95']

    peerurls = ['http://192.168.0.103:2380']
    c.add_member(*peerurls)
    # only register new node
    # after it, start the server

    peerurls = ['http://192.168.0.102:4380']
    c.change_peerurls('fca771384ed46928', *peerurls)
except k3etcd.EtcdException as e:
    print(repr(e))

```

#   Author

Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>

#   Copyright and License

The MIT License (MIT)

Copyright (c) 2015 Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>


[pykit3]: https://github.com/pykit3