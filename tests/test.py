import sesam_rapidjson
from pprint import pprint
from io import FileIO

with FileIO("test.json", "rb") as stream:
    parser = sesam_rapidjson.JSONParser(stream)
    entities = [e for e in parser]

    assert len(entities) == 1

    assert entities[0] == {'hello': 'world', 't': True, 'f': False, 'i': 123, 'pi': 3.1416, 'a': [1, 2, 3, 4]}

    pprint(entities)
