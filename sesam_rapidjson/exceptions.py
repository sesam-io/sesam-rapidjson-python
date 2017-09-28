#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) Bouvet ASA - All Rights Reserved.


class RapidJSONParseError(ValueError):

    json_error_msg = {
        0: "No error",
        1: "The document is empty",
        2: "The document root must not follow by other values",
        3: "Invalid value",
        4: "Missing a name for object member",
        5: "Missing a colon after a name of object member",
        6: "Missing a comma or '}' after an object member",
        7: "Missing a comma or ']' after an array element",
        8: "Incorrect hex digit after \\u escape in string",
        9: "The surrogate pair in string is invalid",
        10: "Invalid escape character in string",
        11: "Missing a closing quotation mark in string",
        12: "Invalid encoding in string",
        13: "Number too big to be stored in double",
        14: "Miss fraction part in number",
        15: "Miss exponent in number",
        16: "Parsing was terminated",
        17: "Unspecific syntax error"
    }

    def __init__(self, error_code, offset, line_no, column):
        self._error_code = error_code
        self._offset = offset
        self._line_no = line_no
        self._column = column

        msg = "JSON parse error while decoding stream: %s at line %s, column %s (position %s)" % \
              (self.json_error_msg.get(self.error_code), line_no, column, offset)

        ValueError.__init__(self, msg)

    @property
    def error_code(self):
        return self._error_code

    @property
    def offset(self):
        return self._offset

    @property
    def line_no(self):
        return self._line_no

    @property
    def column(self):
        return self._column
