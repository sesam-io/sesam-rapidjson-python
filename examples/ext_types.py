# -*- coding: utf-8 -*-
# Copyright (C) Bouvet ASA - All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.

from datetime import datetime

EPOCH = datetime.utcfromtimestamp(0)  # NOTE: this is a datetime with tzinfo=None


def datetime_format(dt_int):
    seconds = (dt_int//1000000000)
    nanoseconds = dt_int-(dt_int//1000000000)*1000000000
    nanoseconds_str = ("%09d" % nanoseconds).rstrip("0")
    dt = datetime.utcfromtimestamp(seconds)
    if len(nanoseconds_str) > 0:
        return '%04d' % dt.year + dt.strftime("-%m-%dT%H:%M:%S") + "." + nanoseconds_str + "Z"
    else:
        return '%04d' % dt.year + dt.strftime("-%m-%dT%H:%M:%SZ")


def int_as_datetime(dt_int):
    seconds = dt_int/1000000000
    # Note that this will lose precision as python datetime only supports microseconds
    return datetime.utcfromtimestamp(seconds)


def datetime_parse(dt_str):
    if len(dt_str) <= 27:  # len('2015-11-24T07:58:53.123456Z') == 27
        if len(dt_str) == 10:  # len('2015-11-24') == 10
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
            return datetime_as_int(dt)
        elif len(dt_str) <= 20:  # len('2015-11-24T07:58:53Z') == 27
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
            return datetime_as_int(dt)
        else:
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            return datetime_as_int(dt)
    elif len(dt_str) > 30:  # len('2015-07-28T09:46:00.123456789Z') == 30
        raise Exception("Invalid date string: %s" % dt_str)
    else:
        dt = datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S")  # len('2015-11-24T07:58:53') == 19
        dt_str_digits = dt_str[19+1:-1]  # get number between . and Z
        #print("str digits: " + dt_str_digits)
        dt_str_nanos = dt_str_digits.ljust(9, "0")
        #print("Nano digits: " + dt_str_nanos)
        return datetime_as_int(dt) + int(dt_str_nanos)


def datetime_as_int(dt):
    # convert to naive UTC datetime
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
        dt = dt.replace(tzinfo=None)

    time_delta = dt - EPOCH

    r = int(time_delta.total_seconds()) * 1000000000
    t = time_delta.microseconds * 1000

    if t > 0 and time_delta.days < 0:
        t = -1000000000 + t

    return r + t


NoneType = type(None)


class URI:

    __slots__ = '_value'

    def __init__(self, value):
        self._value = value

    def __eq__(self, other):
        return isinstance(other, URI) and self._value == other.value

    def __lt__(self, other):
        return isinstance(other, URI) and self._value < other.value

    def __gt__(self, other):
        return isinstance(other, URI) and self._value > other.value

    def __le__(self, other):
        return isinstance(other, URI) and self._value <= other.value

    def __ge__(self, other):
        return isinstance(other, URI) and self._value >= other.value

    def __hash__(self):
        return hash(self._value)

    def __repr__(self):
        return "URI(\"%s\")" % self._value

    @property
    def value(self):
        return self._value


class Nanoseconds:

    __slots__ = '_value'

    def __init__(self, value):
        if isinstance(value, str):
            self._value = datetime_parse(value)
        else:
            self._value = value

    def from_str(self, value):
        return Nanoseconds(datetime_parse(value))

    def __eq__(self, other):
        return isinstance(other, Nanoseconds) and self._value == other.value

    def __lt__(self, other):
        return isinstance(other, Nanoseconds) and self._value < other.value

    def __gt__(self, other):
        return isinstance(other, Nanoseconds) and self._value > other.value

    def __le__(self, other):
        return isinstance(other, Nanoseconds) and self._value <= other.value

    def __ge__(self, other):
        return isinstance(other, Nanoseconds) and self._value >= other.value

    def __add__(self, other):
        if isinstance(other, Nanoseconds):
            return Nanoseconds(self._value + other._value)
        elif isinstance(other, int):
            return Nanoseconds(self._value + other)

        raise TypeError("Can't add types %s and %s!" % (type(self), type(other)))

    def __sub__(self, other):
        if isinstance(other, Nanoseconds):
            return Nanoseconds(self._value - other._value)
        elif isinstance(other, int):
            return Nanoseconds(self._value - other)

        raise TypeError("Can't subtract types %s and %s!" % (type(self), type(other)))

    def __hash__(self):
        return hash(self._value)

    def __repr__(self):
        return "Nanoseconds(%s)" % self._value

    def __int__(self):
        return self._value

    def iso_format(self):
        return datetime_format(self._value)

    def to_datetime(self):
        """
        Convert to a datetime object. Note that this will lose precision as only microseconds are supported by
        python.
        :return: datetime object
        """
        return int_as_datetime(self._value)

    @property
    def value(self):
        return self._value


class NI:  # IS-3848: NamespacedIdentifier
    __slots__ = '_value'

    def __init__(self, value):
        self._value = value

    def __eq__(self, other):
        return isinstance(other, NI) and self._value == other.value

    def __lt__(self, other):
        return isinstance(other, NI) and self._value < other.value

    def __gt__(self, other):
        return isinstance(other, NI) and self._value > other.value

    def __le__(self, other):
        return isinstance(other, NI) and self._value <= other.value

    def __ge__(self, other):
        return isinstance(other, NI) and self._value >= other.value

    def __hash__(self):
        return hash(self._value)

    def __repr__(self):
        return "NI(\"%s\")" % self._value

    @property
    def value(self):
        return self._value
