from sesam_rapidjson import JSONParser, RapidJSONParseError
from pprint import pprint
from io import FileIO, StringIO
from decimal import Decimal
from ext_types import datetime_parse

trans_dict = {
    "t": int,
    "f": Decimal,
}

with StringIO('{"a": "~t0001-01-01T00:00:00.000000000Z", '
              '"b": "~t9999-12-31T23:59:59.000000000Z",'
              '"c": "~t2015-11-24",'
              '"d": null,'
              '"e": "~t2010-12-30T01:20:30.123456Z"'
              '}') as stream:
    parser = JSONParser(stream, transit_mapping=trans_dict, do_float_as_int=True)
    entities = [e for e in parser]

    assert len(entities) == 1
    pprint(entities)

    print(datetime_parse("2010-12-30T01:20:30.123456Z"))
    print(entities[0]["e"])

    assert datetime_parse("0001-01-01T00:00:00.000000000Z") == entities[0]["a"]
    assert datetime_parse("9999-12-31T23:59:59.000000000Z") == entities[0]["b"]
    assert datetime_parse("2015-11-24") == entities[0]["c"]
    assert datetime_parse("2010-12-30T01:20:30.123456Z") == entities[0]["e"]

    assert entities[0] == {'a': -62135596800000000000, "b": 253402300799000000000,
                           "c": 1448323200000000000, 'd': None, 'e': 1293672030123456000}

with FileIO("test.json", "rb") as stream:
    parser = JSONParser(stream)
    entities = [e for e in parser]

    assert len(entities) == 1

    pprint(entities)

    assert entities[0] == {'hello': 'world', 't': True, 'f': False, "n": None,
                           'i': 123, 'pi': 3.1416, 'a': [1, 2, 3, 4]}

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



