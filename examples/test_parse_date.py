import time

import sesam_rapidjson

from examples import ext_types

start_time = time.monotonic()
objects = 0
num_objects = 1000000


for i in range(num_objects):
    foo = sesam_rapidjson.parse8601("2001-01-01T00:01:02.12345678Z")
    objects += 1

end_time = time.monotonic()
time_used = end_time - start_time

if objects != 0:
    per_sec = objects / time_used
else:
    per_sec = 0

print(foo)
print("Done. Parsed %s dates in %d seconds (%d obj/sec)" % (objects, time_used, per_sec))

start_time = time.monotonic()
objects = 0

for i in range(num_objects):
    foo = ext_types.datetime_parse("2001-01-01T00:01:02.12345678Z")
    objects += 1

end_time = time.monotonic()
time_used = end_time - start_time

if objects != 0:
    per_sec = objects / time_used
else:
    per_sec = 0

print(foo)
print("Done. Parsed %s dates in %d seconds (%d obj/sec)" % (objects, time_used, per_sec))
