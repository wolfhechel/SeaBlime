import re


class CMakeCacheParser(object):

    cache_entry_re = re.compile('^([A-Za-z_0-9]*):([A-Z]*)=(.*)$')

    @staticmethod
    def value_to_bool(value):
        value = value.upper()

        if value in ('TRUE', 'ON'):
            bool_value = True
        elif value in ('FALSE', 'OFF'):
            bool_value = False
        else:
            bool_value = None

        return bool_value

    @classmethod
    def iterate(cls, cmake_cache):
        with open(cmake_cache, 'r') as cache:

            while True:
                line = cache.readline()

                if line == '':
                    break

                cache_entry = cls.cache_entry_re.match(line.strip())

                if cache_entry:
                    key, _type, value = cache_entry.groups()

                    if _type.upper() == 'BOOL':
                        value = cls.value_to_bool(value)

                    yield key, value

    @classmethod
    def parse(cls, cmake_cache):
        return {
            k: v for k, v in cls.iterate(cmake_cache)
        }

    @classmethod
    def find(cls, cmake_cache, key_to_find):
        for (key, value) in cls.iterate(cmake_cache):
            if key == key_to_find:
                return value

        raise KeyError('No cache entry for key %s' % key_to_find)
