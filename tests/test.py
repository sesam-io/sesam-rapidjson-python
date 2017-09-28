import sesam_rapidjson
from threading import Thread
from queue import Queue
import argparse
from pprint import pprint
from io import FileIO


class DictHandler:

    def __init__(self, queue, debug=False):
        self.entity_index = 0
        self.context = []
        self.name_context = []
        self._queue = queue
        self._debug = debug
        self._counter = 0

    def handle_dict(self, entity):
        if self._debug:
            print("Python: got a dict: ")
            pprint(entity)
            time.sleep(2)

            for key, item in entity.items():
                print(key, item, type(item))

        self._queue.put(entity)

        self._counter += 1

    def handle_end_stream(self):
        if self._debug:
            print("Got a end-of-stream event!")
        self._queue.put(None)

    def handle_error(self, error_code, offset, line_no, column):
        if self._debug:
            print("Got a parse error!")
        self._queue.put(RapidJSONParseError(error_code, offset, line_no, column))
        self._queue.put(None)


class JSONDictParser:

    def __init__(self, stream, debug=False):
        self._queue = Queue(maxsize=10000)
        self._debug = debug
        self._handler = DictHandler(self._queue, debug=self._debug)
        self._stream = stream
        self._sentinel = None
        self._thread = Thread(name="JSONDictParser", target=self._run)

    def _run(self):
        transit_mapping = args.do_transit_decode and transit_decode_map or None
        sesam_rapidjson.parse_dict(self._stream, self._handler, transit_mapping)

    def __iter__(self):
        self._thread.start()

        for value in iter(self._queue.get, self._sentinel):
            if isinstance(value, RapidJSONParseError):
                raise value

            yield value

        self._thread.join()


parser = argparse.ArgumentParser(description='Test JSON parsing')
parser.add_argument('--transit-decode', dest='do_transit_decode', action='store_true', required=False, help="Transit decode")
parser.add_argument('--debug', dest='do_debug', action='store_true', required=False, help="Debug")

args = parser.parse_args()

with FileIO("test.json", "rb") as stream:
    parser = JSONDictParser(stream, debug=args.do_debug)
    entities = [e for e in parser]

    assert len(entities) == 1

    assert e[0] == {
    }
