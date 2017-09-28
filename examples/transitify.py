import python_example
from io import FileIO
from queue import Queue
from threading import Thread
import argparse
import time
import json

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
            print("Python: got a dict: ", entity)
            time.sleep(2)

        self._queue.put(entity)
        self._counter += 1

        if self._counter % 10000 == 0:
            print("Parsed ", self._counter, " entities. Current queue size: ", self._queue.qsize())

    def end_stream_handler(self):
        if self._debug:
            print("Got a end-of-stream event!")
        self._queue.put(None)


class JSONDictParser:

    def __init__(self, stream, debug=False):
        self._queue = Queue(maxsize=20000)
        self._debug = debug
        self._handler = DictHandler(self._queue, debug=self._debug)
        self._stream = stream
        self._sentinel = None
        self._thread = Thread(name="JSONDictParser", target=self._run)

    def _run(self):
        python_example.parse_dict(self._stream, self._handler)

    def __iter__(self):
        self._thread.start()

        for value in iter(self._queue.get, self._sentinel):
            yield value

        self._thread.join()


parser = argparse.ArgumentParser(description='Test JSON parsing')
parser.add_argument('-f', dest='file_name', required=True, help="File to parse")
parser.add_argument('-o', dest='output_file_name', required=True, help="File to write to")

args = parser.parse_args()

stream = FileIO(args.file_name, "rb")
output_file = open(args.output_file_name, "w")

output_file.write("[")

entities = 0

start_time = time.monotonic()

parser = JSONDictParser(stream, debug=False)

for entity in parser:

    tmp = {}
    for key, value in entity.items():
        if key == "birth_date":
            value = "~t%sT00:00:00Z" % value
        elif key.startswith('column'):
            value = "~u%s" % value
        elif key == "home_page":
            value = "~r%s" % value
        elif key == "credit_card":
            value = "~f%s" % value

        tmp[key] = value

    entities += 1

    s = json.dumps(tmp) + ",\n"
    output_file.write(s)
    #print(entity)

output_file.write("]")
output_file.close()

end_time = time.monotonic()
time_used = end_time - start_time

if entities != 0:
    per_sec = entities / time_used
else:
    per_sec = 0

print("Done. Parsed %s entities in %d seconds (%d entities/sec)" % (entities, time_used, per_sec))
stream.close()
