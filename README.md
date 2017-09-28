Sesam Rapidjson bindings
========================

Installation
------------

The installation is in two parts. The pybind11 package must be pre-installed before you install this package. The reason for this is that pip/setuptools doesn't support build requirements yet. 
It means that if you intend to use this package in your own project, you must also include the pybind dependency explicitly in addition to this package.

    pip install "pybind11>=2.2"
    pip install -U .


Usage
-----

    import sesam_rapidjson
    from pprint import pprint
    from io import FileIO
    
    with FileIO("test.json", "rb") as stream:
        parser = sesam_rapidjson.JSONParser(stream)
        entities = [e for e in parser]
    
        assert len(entities) == 1
    
        assert entities[0] == {'hello': 'world', 't': True, 'f': False, 'i': 123, 'pi': 3.1416, 'a': [1, 2, 3, 4]}
    
        pprint(entities)

