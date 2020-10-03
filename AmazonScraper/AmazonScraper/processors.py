"""
Created by Victor Wan
Custom ItemLoader processors
"""


class TakeLast(object):

    def __call__(self, values):
        for value in reversed(values):
            if value is not None and value != '':
                return value

class Sum(object):
    def __call__(self, values):
        return sum(int(x) for x in values)