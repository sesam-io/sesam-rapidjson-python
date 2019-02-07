from sesam_rapidjson import JSONParser, RapidJSONParseError, parse8601
from pprint import pprint
from io import FileIO, StringIO
from decimal import Decimal
from ext_types import Nanoseconds, datetime_parse

trans_dict = {
    "t": int,
    "f": Decimal,
}

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


with StringIO('{"a": "~t1969-03-27T09:28-18.923Z"}') as stream:
    parser = JSONParser(stream, transit_mapping=trans_dict)
    try:
        entities = [e for e in parser]
        print("Should have got an error!!")
    except RapidJSONParseError as e:
        if e.fail_reason.find("Most likely not a ISO8601 date") > -1:
            print("Got expected error!")
        else:
            print("Got unexpected error! %s" % repr(e))
    except BaseException as e:
        print("Got unexpected error! %s" % repr(e))

trans_dict = {
    "t": Nanoseconds,
    "f": Decimal,
}

with StringIO('{"a": "~t0001-01-01T00:00:00Z", '
              '"b": "~t9999-12-31T23:59:59.000000000Z",'
              '"c": "~t2015-11-24",'
              '"d": null,'
              '"e": "~t2010-12-30T01:20:30.123456Z",'
              '"f": "~f1.1"'
              '}') as stream:
    parser = JSONParser(stream, transit_mapping=trans_dict, do_float_as_int=True)
    entities = [e for e in parser]

    assert len(entities) == 1
    pprint(entities)

    assert Nanoseconds("0001-01-01T00:00:00Z") == entities[0]["a"]

    assert Nanoseconds("0001-01-01T00:00:00.000000000Z") == entities[0]["a"]
    assert Nanoseconds("9999-12-31T23:59:59.000000000Z") == entities[0]["b"]
    assert Nanoseconds("2015-11-24") == entities[0]["c"]
    assert Nanoseconds("2010-12-30T01:20:30.123456Z") == entities[0]["e"]

    assert Decimal("1.1") == entities[0]["f"]
    assert type(entities[0]["f"]) == Decimal

    assert entities[0] == {'a': Nanoseconds(-62135596800000000000), "b": Nanoseconds(253402300799000000000),
                           "c": Nanoseconds(1448323200000000000), 'd': None, 'e': Nanoseconds(1293672030123456000),
                           "f": Decimal("1.1")}


with StringIO('{"f": 1.12345678900, "i": 1.0, "u": 1}') as stream:
    parser = JSONParser(stream, transit_mapping=trans_dict, do_float_as_int=True, do_float_as_decimal=True)
    entities = [e for e in parser]

    assert len(entities) == 1
    pprint(entities)

    assert Decimal("1.12345678900") == entities[0]["f"]
    assert type(entities[0]["f"]) == Decimal

    assert entities[0]["i"] == 1
    assert type(entities[0]["i"]) == int


for foo in [
    "0001-01-01",
    "0001-01-01T00:00:00Z",
    "0001-01-01T00:00:00.0Z",
    "0001-01-01T00:00:00.00Z",
    "0001-01-01T00:00:00.000Z",
    "0001-01-01T00:00:00.00000000Z",
    "0001-01-01T00:00:00.1Z",
    "0001-01-01T00:00:00.10Z",
    "0001-01-01T00:00:00.100Z",
    "0001-01-01T00:00:00.1000Z",
    "0001-01-01T00:00:00.10001Z",
    "9999-12-31T23:59:59.000000000Z",
    "2010-12-30T01:20:30.123456Z",
    "1969-03-27T09:28:18.9234Z"]:

    a = parse8601(foo)
    b = datetime_parse(foo)

    if a != b:
        print(foo, "a != b!", a, b)

print("\nTesting iterator..")
with StringIO('{"a": "~t0001-01-01T00:00:00Z", '
              '"b": "~t9999-12-31T23:59:59.000000000Z",'
              '"c": "~t2015-11-24",'
              '"d": null,'
              '"e": "~t2010-12-30T01:20:30.123456Z"'
              '}') as stream:
    parser = JSONParser(stream, transit_mapping=trans_dict, do_float_as_int=True)
    pprint(next(parser))

    try:
        pprint(next(parser))
    except StopIteration:
        print("Got expected StopIteration error!")

print("\nTesting JSON int literal..")
with StringIO('1234') as stream:
    parser = JSONParser(stream, transit_mapping=trans_dict, do_float_as_int=True)
    try:
        pprint(next(parser))
    except RapidJSONParseError as e:
        print("Got expected error!")
    except BaseException as e:
        print("Got unexpected error! %s" % repr(e))

print("\nTesting JSON string literal..")
with StringIO('"1234"') as stream:
    parser = JSONParser(stream, transit_mapping=trans_dict, do_float_as_int=True)
    try:
        pprint(next(parser))
    except RapidJSONParseError as e:
        print("Got expected error!")
    except BaseException as e:
        print("Got unexpected error! %s" % repr(e))
