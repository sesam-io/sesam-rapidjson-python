from decimal import Decimal
import time

start_time = time.monotonic()
objects = 0

for i in range(1000000):
    foo = Decimal("123456.6")
    objects += 1

end_time = time.monotonic()
time_used = end_time - start_time

if objects != 0:
    per_sec = objects / time_used
else:
    per_sec = 0

print("Done. Created %s objects in %d seconds (%d obj/sec)" % (objects, time_used, per_sec))