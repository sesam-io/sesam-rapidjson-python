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

    def handle_error(self, error_code, offset, line_no, column):
        self._queue.put(RapidJSONParseError(error_code, offset, line_no, column))
        self._queue.put(None)


class JSONParser:

    def __init__(self, stream, handler=JSONDictHandler, transit_mapping=None):
        self._queue = Queue(maxsize=10000)
        self._handler = handler(self._queue)
        self._stream = stream
        self._sentinel = None
        self._transit_mapping = transit_mapping
        self._thread = Thread(name="JSONParser", target=self._run)

    def _run(self):
        parse_dict(self._stream, self._handler, self._transit_mapping)

    def __iter__(self):
        self._thread.start()

        for value in iter(self._queue.get, self._sentinel):
            if isinstance(value, RapidJSONParseError):
                raise value

            yield value

        self._thread.join()
