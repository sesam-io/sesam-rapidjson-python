import rapidjson
from pprint import pprint
import python_example
from queue import Queue
from threading import Thread
import rapidjson
from io import StringIO

from pprint import pprint


json_data = """[{"foo": "bar"},]"""


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


class JSONStringHandler:

    def __init__(self, queue, debug=False):
        self.entity_index = 0
        self.context = []
        self.name_context = []
        self._queue = queue
        self._debug = debug

    def handle_string(self, value):
        print("Python: got a string: ", value)

        entity = rapidjson.loads(value)

        self._queue.put(entity)

    def end_stream_handler(self):
        print("Got a end-of-stream event!")
        self._queue.put(None)

    def handle_error(self, error_code, offset, line_no, column):
        print("Got a parse error!")
        self._queue.put(RapidJSONParseError(error_code, offset, line_no, column))
        self._queue.put(None)


class JSONStringParser:

    def __init__(self, stream, debug=False):
        self._queue = Queue(maxsize=10000)
        self._debug = debug
        self._handler = JSONStringHandler(self._queue, debug=self._debug)
        self._stream = stream
        self._sentinel = None
        self._thread = Thread(name="JSONStringParser", target=self._run)

    def _run(self):
        python_example.parse_strings(self._stream, self._handler)

    def __iter__(self):
        self._thread.start()

        for value in iter(self._queue.get, self._sentinel):
            if isinstance(value, RapidJSONParseError):
                raise value

            yield value

        self._thread.join()


class JSONStaticStringParser:

    def __init__(self, static_string, debug=False):
        self._queue = Queue(maxsize=10000)
        self._debug = debug
        self._handler = JSONStringHandler(self._queue, debug=self._debug)
        self._static_string = static_string
        self._sentinel = None
        self._thread = Thread(name="JSONStringParser", target=self._run)

    def _run(self):
        python_example.parse_string(self._static_string, self._handler)

    def __iter__(self):
        self._thread.start()

        for value in iter(self._queue.get, self._sentinel):
            if isinstance(value, RapidJSONParseError):
                raise value

            yield value

        self._thread.join()


#stream = StringIO(json_data)
#parser = JSONStringParser(stream)

parser = JSONStaticStringParser(json_data)

for entity in parser:
    pprint(entity)

#entity = rapidjson.loads(json_data)
#pprint(entity)

# python_example.parse_test()

