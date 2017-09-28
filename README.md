Test of rapid json python parsing

pip install pybind11>=2.2
pip install -U .

Sax in python:
python parse_json.py -f combined.json

Sax in C++:
python parse_json.py -f combined.json --dict

Finding start/end of entity in stream, decode using rapidjson bindings in python (third party module)
python parse_json.py -f combined.json --string

Use IJson streaming using yakj_cffi:
python parse_json.py -f combined.json --isjon

Optional flags:
--debug and --transit-decode 
