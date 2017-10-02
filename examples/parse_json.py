import argparse
import rapidjson
import time
from base64 import b64decode
from decimal import Decimal
from io import FileIO
from pprint import pprint
from queue import Queue
from threading import Thread

import ijson.backends.yajl2_cffi as ijson
import sesam_rapidjson
from sesam_rapidjson import RapidJSONParseError

from ext_types import URI, Nanoseconds, NI

args = None


def trans_escape(value):
    return value[1:]


transit_decode_map = {
    "f": Decimal,
    "r": URI,
    ":": NI,
    #"u": UUID,
    "t": Nanoseconds,
    "b": b64decode,
}


def transit_decode_string(value):
    if len(value) > 1 and value[0] == "~":
        value1 = value[1]

        func = transit_decode_map.get(value1)
        if func:
            return func(value[2:])
        else:
            if value1 == "~":
                return value[1:]

    return value


class JSONHandler:

    def __init__(self, queue, debug=False):
        self.entity_index = 0
        self.context = []
        self.name_context = []
        self._queue = queue
        self._debug = debug

    def handle_end_stream(self):
        if self._debug:
            print("Got a end-of-stream event!")
        self._queue.put(None)

    def handle_error(self, error_code, offset, line_no, column):
        if self._debug:
            print("Got a parse error!")
        self._queue.put(RapidJSONParseError(error_code, offset, line_no, column))
        self._queue.put(None)

    def handle_string(self, value):
        if self._debug:
            print("Python: got a string: ", value)

        if args.do_transit_decode:
            try:
                value = transit_decode_string(value)
            except BaseException as e:
                raise AssertionError("Decode error!")
    #            raise EntityParseError(entity_index=entity_index,
    #                                   offending_value=value,
    #                                   context=context,
    #                                   name_context=name_context,
    #                                   original_exception=e)

        ctxobj = self.context[-1]
        if type(ctxobj) is list:
            ctxobj.append(value)
        elif type(ctxobj) is dict:
            prop_name = self.name_context.pop()
            ctxobj[prop_name] = value
        else:
            raise Exception("WAT!")

    def handle_start_object(self):
        if self._debug:
            print("Python: got a StartObject")
        self.context.append({})

    def handle_end_object(self):
        if self._debug:
            print("Python: got a EndObject")
        entity = self.context.pop()
        if len(self.context) == 1 and type(self.context[0]) is list or len(self.context) == 0:  # allow reading a single entity
            self._queue.put(entity)
            self.entity_index += 1
        else:
            parent = self.context[-1]
            if type(parent) is dict:
                parent[self.name_context.pop()] = entity
            elif type(parent) is list:
                parent.append(entity)
            else:
                raise Exception("WAT!")

    def handle_value(self, value):
        if self._debug:
            print("Python got a non-string value object: ", value)
        ctxobj = self.context[-1]
        if type(ctxobj) is list:
            ctxobj.append(value)
        elif type(ctxobj) is dict:
            prop_name = self.name_context.pop()
            ctxobj[prop_name] = value
        else:
            raise Exception("WAT!")

    def handle_key(self, value):
        if self._debug:
            print("Python got a new key: ", value)
        self.name_context.append(value)

    def handle_start_array(self):
        if self._debug:
            print("Python: got a StartArray")
        self.context.append([])

    def handle_end_array(self):
        if self._debug:
            print("Python: got a EndArray")
        l = self.context.pop()
        if len(self.context) > 0:
            parent = self.context[-1]
            if type(parent) is list:
                parent.append(l)
            else:
                parent[self.name_context.pop()] = l

    def error_handler(self, error_code, offset, line_no, column):
        print("Got a parse error!")
        self._queue.put(RapidJSONParseError(error_code, offset, line_no, column))
        self._queue.put(None)


class JSONStringHandler:

    def __init__(self, queue, debug=False):
        self.entity_index = 0
        self.context = []
        self.name_context = []
        self._queue = queue
        self._debug = debug

    def handle_string(self, value):
        if self._debug:
            print("Python: got a string: ", value)

        def transit_deocode_entity(e):
            if isinstance(e, list):
                for i, item in enumerate(e):
                    if isinstance(item, str):
                        e[i] = transit_decode_string(item)
                    elif isinstance(e, (list, dict)):
                        e[i] = transit_deocode_entity(item)
            elif isinstance(e, dict):
                for key, item in e.items():
                    if isinstance(item, str):
                        item = transit_decode_string(item)
                    elif isinstance(value, (list, dict)):
                        item = transit_deocode_entity(item)

                    e[key] = item

            return e

        entity = rapidjson.loads(value)

        if args.do_transit_decode:
            entity = transit_deocode_entity(entity)

        self._queue.put(entity)

    def handle_end_stream(self):
        if self._debug:
            print("Got a end-of-stream event!")
        self._queue.put(None)

    def handle_error(self, error_code, offset, line_no, column):
        if self._debug:
            print("Got a parse error!")
        self._queue.put(RapidJSONParseError(error_code, offset, line_no, column))
        self._queue.put(None)


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

#        if self._counter % 10000 == 0:
#            print("Parsed ", self._counter, " entities. Current queue size: ", self._queue.qsize())

    def handle_end_stream(self):
        if self._debug:
            print("Got a end-of-stream event!")
        self._queue.put(None)

    def handle_error(self, error_code, offset, line_no, column):
        if self._debug:
            print("Got a parse error!")
        self._queue.put(RapidJSONParseError(error_code, offset, line_no, column))
        self._queue.put(None)


class IJSONParser:

    def __init__(self, stream, debug=False):
        self._debug = debug
        self._stream = stream

    def __iter__(self):
        entity_index = 0
        context = []
        name_context = []
        for event, value in ijson.basic_parse(self._stream):
            if event == 'start_map':
                context.append({})
            elif event == 'map_key':
                name_context.append(value)
            elif event == 'string':
                if args.do_transit_decode:
                    try:
                        value = transit_decode_string(value)
                    except BaseException as e:
                        raise AssertionError("Decode error!")
    #                    raise EntityParseError(entity_index=entity_index,
    #                                           offending_value=value,
    #                                           context=context,
    #                                           name_context=name_context,
    #                                           original_exception=e)

                ctxobj = context[-1]
                if type(ctxobj) is list:
                    ctxobj.append(value)
                elif type(ctxobj) is dict:
                    prop_name = name_context.pop()
                    ctxobj[prop_name] = value
                else:
                    raise Exception("WAT!")

            elif event in {'number', 'boolean', 'null'}:
                ctxobj = context[-1]
                if type(ctxobj) is list:
                    ctxobj.append(value)
                elif type(ctxobj) is dict:
                    prop_name = name_context.pop()
                    ctxobj[prop_name] = value
                else:
                    raise Exception("WAT!")

            elif event == 'end_map':
                entity = context.pop()
                if len(context) == 1 and type(context[0]) is list or len(context) == 0:  # allow reading a single entity
                    yield entity
                    entity_index += 1
                else:
                    parent = context[-1]
                    if type(parent) is dict:
                        parent[name_context.pop()] = entity
                    elif type(parent) is list:
                        parent.append(entity)
                    else:
                        raise Exception("WAT!")
            elif event == 'start_array':
                context.append([])
            elif event == 'end_array':
                l = context.pop()
                if len(context) > 0:
                    parent = context[-1]
                    if type(parent) is list:
                        parent.append(l)
                    else:
                        parent[name_context.pop()] = l


class JSONParser:

    def __init__(self, stream, debug=False):
        self._queue = Queue(maxsize=10000)
        self._debug = debug
        self._handler = JSONHandler(self._queue, debug=self._debug)
        self._stream = stream
        self._sentinel = None
        self._thread = Thread(name="JSONparser", target=self._run)

    def _run(self):
        sesam_rapidjson.parse(self._stream, self._handler)

    def __iter__(self):
        self._thread.start()

        for value in iter(self._queue.get, self._sentinel):
            if isinstance(value, RapidJSONParseError):
                raise value

            yield value

        self._thread.join()


class JSONStringParser:

    def __init__(self, stream, debug=False):
        self._queue = Queue(maxsize=10000)
        self._debug = debug
        self._handler = JSONStringHandler(self._queue, debug=self._debug)
        self._stream = stream
        self._sentinel = None
        self._thread = Thread(name="JSONStringParser", target=self._run)

    def _run(self):
        sesam_rapidjson.parse_strings(self._stream, self._handler)

    def __iter__(self):
        self._thread.start()

        for value in iter(self._queue.get, self._sentinel):
            if isinstance(value, RapidJSONParseError):
                raise value

            yield value

        self._thread.join()


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
        sesam_rapidjson.parse_dict(self._stream, self._handler, transit_mapping, False)

    def __iter__(self):
        self._thread.start()

        for value in iter(self._queue.get, self._sentinel):
            if isinstance(value, RapidJSONParseError):
                raise value

            yield value

        self._thread.join()


parser = argparse.ArgumentParser(description='Test JSON parsing')
parser.add_argument('-f', dest='file_name', required=True, help="File to parse")
parser.add_argument('--ijson', dest='use_ijson', action='store_true', required=False, help="Use the ijson parser")
parser.add_argument('--string', dest='use_string', action='store_true', required=False, help="Use the string parser")
parser.add_argument('--dict', dest='use_dict', action='store_true', required=False, help="Use the dict parser")
parser.add_argument('--transit-decode', dest='do_transit_decode', action='store_true', required=False, help="Transit decode")
parser.add_argument('--debug', dest='do_debug', action='store_true', required=False, help="Debug")

args = parser.parse_args()

stream = FileIO(args.file_name, "rb")

entities = 0

start_time = time.monotonic()

if args.use_ijson:
    print("Using ijson parser")
    parser = IJSONParser(stream)
elif args.use_string:
    print("Using string parser")
    parser = JSONStringParser(stream, debug=args.do_debug)
elif args.use_dict:
    print("Using dict parser")
    parser = JSONDictParser(stream, debug=args.do_debug)
else:
    print("Using rapidjson parser")
    parser = JSONParser(stream)

for entity in parser:
    entities += 1

    #if entities % 10000 == 0:
    #    print("Parsed %s entities" % entities)
    #pprint(entity)
    #time.sleep(5)

end_time = time.monotonic()
time_used = end_time - start_time

if entities != 0:
    per_sec = entities / time_used
else:
    per_sec = 0

print("Done. Parsed %s entities in %d seconds (%d entities/sec)" % (entities, time_used, per_sec))
stream.close()
