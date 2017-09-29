from sesam_rapidjson import JSONParser
from io import FileIO
import argparse
import time
import json

parser = argparse.ArgumentParser(description='Test JSON parsing')
parser.add_argument('-f', dest='file_name', required=True, help="File to parse")
parser.add_argument('-o', dest='output_file_name', required=True, help="File to write to")

args = parser.parse_args()

with FileIO(args.file_name, "rb") as stream:
    with open(args.output_file_name, "w") as output_file:
        output_file.write("[")

        entities = 0

        start_time = time.monotonic()

        parser = JSONParser(stream)

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

    end_time = time.monotonic()
    time_used = end_time - start_time

    if entities != 0:
        per_sec = entities / time_used
    else:
        per_sec = 0

    print("Done. Parsed %s entities in %d seconds (%d entities/sec)" % (entities, time_used, per_sec))
