from sesam_rapidjson import JSONParser, RapidJSONParseError
from pprint import pprint
from io import FileIO, StringIO
from decimal import Decimal

with FileIO("test.json", "rb") as stream:
    parser = JSONParser(stream)
    entities = [e for e in parser]

    assert len(entities) == 1

    assert entities[0] == {'hello': 'world', 't': True, 'f': False, 'i': 123, 'pi': 3.1416, 'a': [1, 2, 3, 4]}

    pprint(entities)


trans_dict = {
    "t": int,
    "f": Decimal,
}

with StringIO('{"a": "~t1969-03-27T09:28:18.923Z", "b": 1.0, "c": "~f1.1"}') as stream:
    parser = JSONParser(stream, transit_mapping=trans_dict, do_float_as_int=True)
    entities = [e for e in parser]

    assert len(entities) == 1
    pprint(entities)

    assert entities[0] == {'a': -24157901077000000, "b": 1, "c": Decimal("1.1")}


with StringIO('{"a": "~t1969-03-27T09:28-18.923Z"') as stream:
    parser = JSONParser(stream, transit_mapping=trans_dict)
    try:
        entities = [e for e in parser]
    except RapidJSONParseError as e:
        if e.fail_reason.find("Most likely not a ISO8601 date") > -1:
            print("Got expected error!")
        else:
            print("Got unexpected error!")
    except BaseException as e:
        print("Got unexpected error!")
