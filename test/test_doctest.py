import doctest

import k3etcd


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(k3etcd))
    return tests
