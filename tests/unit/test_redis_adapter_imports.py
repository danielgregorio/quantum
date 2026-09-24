"""The redis broker adapter imports from the installed package.

It imported `message_broker` by its bare name only, which exists just when the
file runs from its own folder. Imported as quantum.runtime.adapters.redis_adapter
it failed, the lazy loader turned that into None, and asking for the redis
broker said "requires 'redis' package" whether redis was installed or not.
"""


def test_the_module_imports_without_the_redis_package_being_needed():
    from quantum.runtime.adapters import redis_adapter
    assert redis_adapter.RedisAdapter.__name__ == 'RedisAdapter'


def test_the_lazy_loader_finds_the_class():
    from quantum.runtime.adapters import _get_redis_adapter
    assert _get_redis_adapter() is not None
