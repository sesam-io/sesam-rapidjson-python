#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) Bouvet ASA - All Rights Reserved.

from sesam_rapidjson_pybind import parse
from sesam_rapidjson_pybind import parse_string
from sesam_rapidjson_pybind import parse_strings
from sesam_rapidjson_pybind import parse_dict
from sesam_rapidjson_pybind import parse8601
from .exceptions import RapidJSONParseError

__all__ = ["parse", "parse_string", "parse_strings", "parse_dict", "parse8601", "RapidJSONParseError"]

from threading import Thread
from queue import Queue


class JSONDictHandler:

    def __init__(self, queue):
        self.entity_index = 0
        self.context = []
        self.name_context = []
        self._queue = queue

    def handle_dict(self, entity):
        self._queue.put(entity)

    def handle_end_stream(self):
        self._queue.put(None)

    def handle_error(self, error_code, offset, line_no, column, fail_reason):
        self._queue.put(RapidJSONParseError(error_code, offset, line_no, column, fail_reason))
        self._queue.put(None)


class JSONParser:

    def __init__(self, stream, handler=JSONDictHandler, transit_mapping=None, do_float_as_int=False,
                 do_float_as_decimal=False):
        self._queue = Queue(maxsize=10000)
        self._handler = handler(self._queue)
        self._stream = stream
        self._sentinel = None
        self._transit_mapping = transit_mapping
        self._thread = Thread(name="JSONParser", target=self._run)
        # Output float as an int, if it has no fractions
        self._do_float_as_int = do_float_as_int
        # Parse floats as python Decimals, keeping the precision (i.e. [1.0, 2.00] -> [Decimal("1.0"), Decimal("2.00")]
        self._do_float_as_decimal = do_float_as_decimal
        # This is not a set but a generator expression (see PEP 289)
        self._parse_iter = (e for e in self.get_entities())

    def _run(self):
        try:
            parse_dict(self._stream, self._handler, self._transit_mapping, self._do_float_as_int,
                       self._do_float_as_decimal)
        except BaseException as e:
            self._queue.put(e)
            self._queue.put(None)

    def get_entities(self):
        self._thread.start()

        try:
            for value in iter(self._queue.get, self._sentinel):
                if isinstance(value, BaseException):
                    raise value

                yield value
        finally:
            self._thread.join()

    def __iter__(self):
        return self

    def as_iterable(self):
        return self._parse_iter

    def next(self):
        return next(self._parse_iter)

    __next__ = next
