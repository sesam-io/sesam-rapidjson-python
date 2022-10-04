from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension
import setuptools

__version__ = '0.1.13'

ext_modules = [
    Pybind11Extension(
        'sesam_rapidjson_pybind',
        ['src/main.cpp'],
        include_dirs=[
            "/opt/venv/include/site/python3.9",
            "/opt/venv/include/site/python3.10",
            "include"
        ],
        language='c++',
        extra_compile_args=["-O3"],
    ),
]


# As of Python 3.6, CCompiler has a `has_flag` method.
# cf http://bugs.python.org/issue26689
def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.cpp') as f:
        f.write('int main (int argc, char **argv) { return 0; }')
        try:
            compiler.compile([f.name], extra_postargs=[flagname])
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cpp_flag(compiler):
    """Return the -std=c++[11/14] compiler flag.

    The c++14 is prefered over c++11 (when it is available).
    """
    if has_flag(compiler, '-std=c++17'):
        return '-std=c++17'
    elif has_flag(compiler, '-std=c++14'):
        return '-std=c++14'
    elif has_flag(compiler, '-std=c++11'):
        return '-std=c++11'
    else:
        raise RuntimeError('Unsupported compiler -- at least C++11 support '
                           'is needed!')

setup(
    name='sesam_rapidjson',
    version=__version__,
    author='Tom Bech',
    author_email='tom.bech@sesam.io',
    url='https://github.com/tombech/foo',
    description='Streaming JSON parsers for Sesam using pybind11 and rapidjson',
    long_description='',
    packages=["sesam_rapidjson"],
    ext_modules=ext_modules,
    install_requires=['pybind11==2.6.2'],
    zip_safe=False,
)
