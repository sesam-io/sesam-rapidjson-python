#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <iostream>
#include <cstdio>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
#include <cerrno>
#include <limits>
#include <iomanip>

#include "date.h"

#include "rapidjson/filereadstream.h"
#include "rapidjson/reader.h"

#define BUFFER_SIZE 1048576

using namespace pybind11::literals;
namespace py = pybind11;
using namespace rapidjson;
using namespace std;

std::string pad_left(std::string const& str, size_t s, const char padding_char)
{
    if ( str.size() < s )
        return std::string(s-str.size(), padding_char) + str;
    else
        return str;
}

std::string pad_right(std::string const& str, size_t s, const char padding_char)
{
    if ( str.size() < s )
        return str + std::string(s-str.size(), padding_char);
    else
        return str;
}

static bool ends_with(const std::string& str, const std::string& suffix)
{
    return str.size() >= suffix.size() && 0 == str.compare(str.size()-suffix.size(), suffix.size(), suffix);
}

// This class is used to grab the python GIL and hold it until the instance of this class
// goes out of scope.
class GILHolder {
  public:
    GILHolder() {
      this->gstate = PyGILState_Ensure();
    }
    ~GILHolder() {
      PyGILState_Release(this->gstate);
    };
  private:
     PyGILState_STATE gstate;
};


// This class is used to release the python GIL and grab it again when instance of this class
// goes out of scope.
class GILReleaser {
  public:
    GILReleaser() {
      this->save_ = PyEval_SaveThread();
    }

    ~GILReleaser() {
        PyEval_RestoreThread(this->save_);
    }
  private:
    PyThreadState* save_;
};

// This function returns a shared_ptr that will call Py_DECREF on the python object once the
// last shared_ptr to it is gone. The purpose of this is to avoid having to manually remember to
// call Py_DECREF() correctly.
std::shared_ptr<PyObject> make_decref_python_ptr(PyObject* py_object) {
  return std::shared_ptr<PyObject>(py_object, [](PyObject* py_object) {
    if(py_object != nullptr) {
      // TODO: check if it is expensive to call PyGILState_Check here
      if (!PyGILState_Check()) {
        std::cerr << "make_decref_python_ptr deleter was called without holding the GIL! ";
        std::cerr.flush();
        {
          std::cerr << "The python object looks like this:\n" << std::endl;
          GILHolder gil_holder;
          PyObject_Print(py_object, stderr, Py_PRINT_RAW);
          std::cerr << std::endl;
        }
        std::cerr.flush();

        throw std::runtime_error("make_decref_python_ptr deleter was called without holding the GIL!");
      }
      //std::cout << "make_decref_python_ptr deleter calling Py_DECREF()" << std::endl; std::cout.flush();
      const auto refcount = Py_REFCNT(py_object);
      if (refcount > 0) {
        Py_DECREF(py_object);
      } else {
        std::cerr << std::endl << "make_decref_python_ptr deleter got an object with an invalid refcount: " << refcount << std::endl;
        std::cerr.flush();
      }
      //std::cout << "make_decref_python_ptr deleter successfully called Py_DECREF()" << std::endl; std::cout.flush();
    }
  });
}

py::int_ parse8601(const std::string &date_str)
{
    using namespace date;

    std::istringstream is{date_str};
    std::string save;
    is >> save;
    std::istringstream in{save};
    size_t str_len = date_str.length();
    date::sys_time<std::chrono::milliseconds> tp;

    if (str_len == 10) {
        //cout << "Normal date!" << endl;

        save = save + "T00:00:00Z";
    } else if (str_len == 11 and ends_with(save, "Z")) {

        save = save.substr(0, 10) + "T00:00:00Z";
        //cout << "Fixed: " << date_str << " to " << save << endl;
    }

    //cout << "Date with nanoseconds!" << endl;

    std::istringstream in_sub{save.substr(0, 19) + "Z"};

    in_sub.exceptions(std::ios::failbit);
    in_sub >> date::parse("%FT%TZ", tp);

    //cout << "tp: " << tp << endl;

    std::string nano_digits = save.substr(19+1);
    nano_digits = nano_digits.substr(0, nano_digits.length()-1);
    nano_digits = pad_right(nano_digits, 9, '0');
    //cout << "Nano digits: " << nano_digits << endl;

    py::int_ ms(std::chrono::duration_cast<std::chrono::milliseconds>(tp.time_since_epoch()).count());
    py::int_ nanos(atoi(nano_digits.c_str()));

    //cout << "ms:" << ms << endl;

    py::object mul = ms.attr("__mul__");

    ms = mul(1000000);

    py::object add = ms.attr("__add__");

    return add(nanos);
}

class StreamWrapper {
private:
    py::object py_io_stream;
    py::object py_io_read;
    size_t cursor;
    size_t buffer_cursor;
    size_t line_number;
    size_t column;
    std::string buffer;

    StreamWrapper(const StreamWrapper&);
    StreamWrapper& operator=(const StreamWrapper&);

public:
    typedef char Ch;

    StreamWrapper(py::object py_io_stream) : py_io_stream(py_io_stream) {
        cursor = 0;
        py_io_read = py_io_stream.attr("read");

        // Create a buffer to read into
        buffer = "";
        buffer_cursor = 0;
        line_number = 0;
        column = 0;
    }

    Ch Peek() { // 1
        if (buffer.empty() || buffer_cursor >= buffer.length()) {
            // Get new buffer from stream
            buffer = py_io_read(BUFFER_SIZE).cast<std::string>();
            buffer_cursor = 0;

            // cout << "Peek(): New buffer loaded!" << endl;
        }

        if (buffer.empty()) {
            // cout << "Peek(): EOF!" << endl;
            return '\0';
        }

        int c = (int)buffer[buffer_cursor];

        return c == std::char_traits<char>::eof() ? '\0' : (Ch)c;
    }

    Ch Take() { // 2
        if (buffer.empty() || buffer_cursor >= buffer.length()) {
            // Get new buffer from stream
            buffer = py_io_read(BUFFER_SIZE).cast<std::string>();
            buffer_cursor = 0;

            // cout << "Take(): New buffer loaded!" << endl;
        }

        if (buffer.empty() || buffer_cursor >= buffer.length()) {
            // cout << "Take(): EOF!" << endl;
            return '\0';
        }

        int c = (int)buffer[buffer_cursor++];
        cursor++;

        if (c == std::char_traits<char>::eof()) {
            // cout << "Take(): EOF!" << endl;
            return '\0';
        }

        Ch result = (Ch)c;

        if (result == '\n') {
            line_number++;
            column = 0;
        }
        else {
            column++;
        }

        return result;
    }

    size_t Tell() const { return cursor; } // 3

    size_t GetLine() const { return line_number+1; }
    size_t GetColumn() const { return column+1; }

    Ch* PutBegin() { assert(false); return 0; }
    void Put(Ch) { assert(false); }
    void Flush() { assert(false); }
    size_t PutEnd(Ch*) { assert(false); return 0; }

};


class TrackingStreamWrapper {
private:
    py::object py_io_stream;
    py::object py_io_read;
    size_t cursor;
    size_t buffer_cursor;
    size_t line_number;
    size_t column;

    std::string buffer;

    TrackingStreamWrapper(const TrackingStreamWrapper&);
    TrackingStreamWrapper& operator=(const TrackingStreamWrapper&);

public:
    typedef char Ch;
    std::string accumulated_buffer;

    TrackingStreamWrapper(py::object py_io_stream) : py_io_stream(py_io_stream) {
        cursor = 0;
        py_io_read = py_io_stream.attr("read");

        // Create a buffer to read into
        buffer = "";
        accumulated_buffer = "";
        buffer_cursor = 0;
        line_number = 0;
        column = 0;
    }

    Ch Peek() { // 1
        if (buffer.empty() || buffer_cursor >= buffer.length()) {
            // Get new buffer from stream
            buffer = py_io_read(BUFFER_SIZE).cast<std::string>();
            buffer_cursor = 0;

            //cout << "Peek(): New buffer loaded!" << endl;
        }

        if (buffer.empty()) {
            //cout << "Peek(): EOF!" << endl;
            return '\0';
        }

        int c = (int)buffer[buffer_cursor];

        //cout << "Peek(): " << c << endl;

        return c == std::char_traits<char>::eof() ? '\0' : (Ch)c;
    }

    Ch Take() { // 2
        if (buffer.empty() || buffer_cursor >= buffer.length()) {
            // Get new buffer from stream
            buffer = py_io_read(BUFFER_SIZE).cast<std::string>();
            buffer_cursor = 0;

            //cout << "Take(): New buffer loaded!" << endl;
        }

        if (buffer.empty() || buffer_cursor >= buffer.length()) {
            //cout << "Take(): EOF!" << endl;
            return '\0';
        }

        int c = (int)buffer[buffer_cursor++];
        cursor++;

        if (c == std::char_traits<char>::eof()) {
            //cout << "Take(): EOF!" << endl;
            return '\0';
        }

        Ch result = (Ch)c;

        if (result == '\n') {
            line_number++;
            column = 0;
        }
        else {
            column++;
        }

        accumulated_buffer += result;

        //cout << "Take(): " << result << " (" << c << ")" << endl;

        return result;
    }

    void reset_accumulated_buffer(void) {
        accumulated_buffer.clear();
    }

    size_t Tell() const { return cursor; } // 3

    size_t GetLine() const { return line_number+1; }
    size_t GetColumn() const { return column+1; }

    Ch* PutBegin() { assert(false); return 0; }
    void Put(Ch) { assert(false); }
    void Flush() { assert(false); }
    size_t PutEnd(Ch*) { assert(false); return 0; }

};


struct MyHandlerDebug : public BaseReaderHandler<UTF8<>, MyHandlerDebug> {
    bool Null() { cout << "Null()" << endl; return true; }
    bool Bool(bool b) { cout << "Bool(" << boolalpha << b << ")" << endl; return true; }
    bool Int(int i) { cout << "Int(" << i << ")" << endl; return true; }
    bool Uint(unsigned u) { cout << "Uint(" << u << ")" << endl; return true; }
    bool Int64(int64_t i) { cout << "Int64(" << i << ")" << endl; return true; }
    bool Uint64(uint64_t u) { cout << "Uint64(" << u << ")" << endl; return true; }
    bool Double(double d) { cout << "Double(" << d << ")" << endl; return true; }
    bool String(const char* str, SizeType length, bool copy) {
        cout << "String(" << str << ", " << length << ", " << boolalpha << copy << ")" << endl;
        return true;
    }
    bool StartObject() { cout << "StartObject()" << endl; return true; }
    bool Key(const char* str, SizeType length, bool copy) {
        cout << "Key(" << str << ", " << length << ", " << boolalpha << copy << ")" << endl;
        return true;
    }
    bool EndObject(SizeType memberCount) { cout << "EndObject(" << memberCount << ")" << endl; return true; }
    bool StartArray() { cout << "StartArray()" << endl; return true; }
    bool EndArray(SizeType elementCount) { cout << "EndArray(" << elementCount << ")" << endl; return true; }
};


class MyHandler : public BaseReaderHandler<UTF8<>, MyHandler> {
private:
    py::object py_handler;
    py::object key_handler;
    py::object string_handler;
    py::object value_handler;
    py::object start_object_handler;
    py::object end_object_handler;
    py::object start_array_handler;
    py::object end_array_handler;

public:
    bool Null() { value_handler(NULL); return true; }
    bool Bool(bool b) { value_handler(b); return true; }
    bool Int(int i) { value_handler(i); return true; }
    bool Uint(unsigned u) { value_handler(u); return true; }
    bool Int64(int64_t i) { value_handler(i); return true; }
    bool Uint64(uint64_t u) { value_handler(u); return true; }
    bool Double(double d) { value_handler(d); return true; }
    bool String(const char* str, SizeType length, bool copy) { string_handler(str); return true; }
    bool StartObject() { start_object_handler(); return true; }
    bool Key(const char* str, SizeType length, bool copy) { key_handler(str); return true; }
    bool EndObject(SizeType memberCount) { end_object_handler(); return true; }
    bool StartArray() { start_array_handler(); return true; }
    bool EndArray(SizeType elementCount) { end_array_handler(); return true; }

    MyHandler(py::object py_handler) : py_handler(py_handler) {
        key_handler = py_handler.attr("handle_key");
        string_handler = py_handler.attr("handle_string");
        value_handler = py_handler.attr("handle_value");
        start_object_handler = py_handler.attr("handle_start_object");
        end_object_handler = py_handler.attr("handle_end_object");
        start_array_handler = py_handler.attr("handle_start_array");
        end_array_handler = py_handler.attr("handle_end_array");
    }
};


class MyHandlerDict : public BaseReaderHandler<UTF8<>, MyHandlerDict> {
private:
    py::object py_handler;
    py::object dict_handler;
    py::object py_Decimal;
    bool try_float_as_int;
    bool do_float_as_decimal;
    std::vector<py::object> context_stack;
    std::vector<py::str> name_context;
    std::map <std::string, py::object> transit_map;

public:
    std::string fail_reason;

    bool Null() {
        if (context_stack.size() == 0) {
            // Literal, we don't support it
            return false;
        }

        py::object context_obj = context_stack.back();

        if (py::isinstance<py::dict>(context_obj)) {
            // key:value
            py::str prop_name = name_context.back();
            name_context.pop_back();
            py::dict parent_dict = (py::dict)context_obj;
            parent_dict[prop_name] = py::none();
        }
        else {
            // [value1, value2]
            py::list parent_list = (py::list)context_obj;
            parent_list.append(py::none());
        }

        return true;
    }

    bool Bool(bool value) {
        if (context_stack.size() == 0) {
            // Literal, we don't support it
            return false;
        }

        py::object context_obj = context_stack.back();

        if (py::isinstance<py::dict>(context_obj)) {
            // key:value
            py::str prop_name = name_context.back();
            name_context.pop_back();
            py::dict parent_dict = (py::dict)context_obj;
            parent_dict[prop_name] = value;
        }
        else {
            // [value1, value2]
            py::list parent_list = (py::list)context_obj;
            parent_list.append(value);
        }

        return true;
    }

    bool Int(int value) {
        if (context_stack.size() == 0) {
            // Literal, we don't support it
            return false;
        }

        py::object context_obj = context_stack.back();

        if (py::isinstance<py::dict>(context_obj)) {
            // key:value
            py::str prop_name = name_context.back();
            name_context.pop_back();
            py::dict parent_dict = (py::dict)context_obj;
            parent_dict[prop_name] = value;
        }
        else {
            // [value1, value2]
            py::list parent_list = (py::list)context_obj;
            parent_list.append(value);
        }

        return true;
    }

    bool Uint(unsigned value) {
        if (context_stack.size() == 0) {
            // Literal, we don't support it
            return false;
        }

        py::object context_obj = context_stack.back();

        if (py::isinstance<py::dict>(context_obj)) {
            // key:value
            py::str prop_name = name_context.back();
            name_context.pop_back();
            py::dict parent_dict = (py::dict)context_obj;
            parent_dict[prop_name] = value;
        }
        else {
            // [value1, value2]
            py::list parent_list = (py::list)context_obj;
            parent_list.append(value);
        }

        return true;
    }

    bool Int64(int64_t value) {
        if (context_stack.size() == 0) {
            // Literal, we don't support it
            return false;
        }

        py::object context_obj = context_stack.back();

        if (py::isinstance<py::dict>(context_obj)) {
            // key:value
            py::str prop_name = name_context.back();
            name_context.pop_back();
            py::dict parent_dict = (py::dict)context_obj;
            parent_dict[prop_name] = value;
        }
        else {
            // [value1, value2]
            py::list parent_list = (py::list)context_obj;
            parent_list.append(value);
        }

        return true;
    }

    bool Uint64(uint64_t value) {
        if (context_stack.size() == 0) {
            // Literal, we don't support it
            return false;
        }

        py::object context_obj = context_stack.back();

        if (py::isinstance<py::dict>(context_obj)) {
            // key:value
            py::str prop_name = name_context.back();
            name_context.pop_back();
            py::dict parent_dict = (py::dict)context_obj;
            parent_dict[prop_name] = value;
        }
        else {
            // [value1, value2]
            py::list parent_list = (py::list)context_obj;
            parent_list.append(value);
        }

        return true;
    }

    bool is_integer(const std::string &str) {
        return (str.find_first_not_of("-0123456789") == std::string::npos);
    }

    bool RawNumber(const char* str, SizeType length, bool copy) {
        if (context_stack.size() == 0) {
            // Literal, we don't support it
            return false;
        }

        py::object py_value;

        std::string s_str(str);

        if (is_integer(s_str)) {
            // no fraction or exponent - definately an integer
            //cout << "it's an int!" << endl;
            py::str tmp(s_str);
            py_value = tmp.cast<py::int_>();
        } else {
            //cout << "it's a float!" << endl;
            py_value = py_Decimal(str);

            if (try_float_as_int == true) {
                // If no fractional value, cast to int
                py::int_ int_value = py_value.cast<py::int_>();
                py::object func_eq = py_value.attr("__eq__");
                if (func_eq(int_value).cast<bool>() == true) {
                    //cout << "The float can be cast to an int!" << endl;
                    py_value = int_value;
                }
            }
        }

        py::object context_obj = context_stack.back();

        if (py::isinstance<py::dict>(context_obj)) {
            // key:value
            py::str prop_name = name_context.back();
            name_context.pop_back();
            py::dict parent_dict = (py::dict)context_obj;

            parent_dict[prop_name] = py_value;
        }
        else {
            // [value1, value2]
            py::list parent_list = (py::list)context_obj;
            parent_list.append(py_value);
        }

        return true;
    }

    bool Double(double value) {
        if (context_stack.size() == 0) {
            // Literal, we don't support it
            return false;
        }

        if (try_float_as_int == true) {
            // Special case: reproduce ijson 2.3 bug: treat non-fractional floats as ints
            double intpart;
            if (modf(value, &intpart) == 0.0) {
                return Int64((int64_t)value);
            }
        }


        py::object context_obj = context_stack.back();

        if (py::isinstance<py::dict>(context_obj)) {
            // key:value
            py::str prop_name = name_context.back();
            name_context.pop_back();
            py::dict parent_dict = (py::dict)context_obj;

            parent_dict[prop_name] = value;
        }
        else {
            // [value1, value2]
            py::list parent_list = (py::list)context_obj;
            parent_list.append(value);
        }

        return true;
    }

    bool String(const char* str, SizeType length, bool copy) {
        if (context_stack.size() == 0) {
            // Literal, we don't support it
            return false;
        }

        py::object context_obj = context_stack.back();

        std::string s_str(str);

        py::object result_value;

        if (!transit_map.empty()) {
            if (s_str.length() > 1 && s_str[0] == '~') {
                std::string prefix = s_str.substr(1, 1);
                std::string value = s_str.substr(2);

                // cout << "Prefix: " << prefix << endl;
                // cout << "Value: " << value << endl;

                if (transit_map.count(prefix) > 0) {
                    py::object decode_func = transit_map[prefix];

                    if (prefix[0] == 't') {
                        // Parse dates in C++
                        try {
                            result_value = decode_func(parse8601(value));
                        } catch (py::error_already_set& ex) {
                            std::stringstream reason;
                            reason << "Failed to transit decode value '" << s_str << "'. Exception raised: " << ex.what();
                            fail_reason = reason.str();
                            ex.restore();
                            PyErr_Clear();

                            return false;
                        } catch (std::exception& ex) {
                            std::stringstream reason;
                            reason << "Failed to transit decode value '" << s_str << "'. Most likely not a ISO8601 date. Exception raised: " << ex.what();
                            fail_reason = reason.str();
                            return false;
                        }
                    } else {
                        try {
                            result_value = decode_func(value);
                        } catch (py::error_already_set& ex) {
                            std::stringstream reason;
                            reason << "Failed to transit decode value '" << s_str << "'. Exception raised: " << ex.what();
                            fail_reason = reason.str();
                            ex.restore();
                            PyErr_Clear();

                            return false;
                        }
                    }
                }
            }
        }

        if (result_value == NULL || py::isinstance<py::none>(result_value)) {
            try {
                result_value = py::str(s_str);
            } catch (std::exception& ex) {
              std::stringstream orig_reason;

              if (PyErr_Occurred()) {
                PyObject *type, *value, *traceback;
                PyErr_Fetch(&type, &value, &traceback);
                PyErr_NormalizeException(&type, &value, &traceback);

                auto type_decref = make_decref_python_ptr(type);
                auto value_decref = make_decref_python_ptr(value);
                auto traceback_decref = make_decref_python_ptr(traceback);

                if (value != nullptr) {
                    PyObject *py_str_value = PyObject_Str(value);
                    auto decref_py_str_value = make_decref_python_ptr(py_str_value);

                    const char* raw_python_error_msg = PyUnicode_AsUTF8(py_str_value);
                    std::string s_python_error_msg(raw_python_error_msg);
                    orig_reason << s_python_error_msg;
                }

                PyErr_Clear();
              } else {
                    orig_reason << ex.what();
              }

              // Try to convert the original string to a more suitable format for the error message
              PyObject *orig_str = PyUnicode_DecodeUTF8(str, (size_t)length, "backslashreplace");

              auto orig_str_decref = make_decref_python_ptr(orig_str);

              const char* raw_python_orig_str = PyUnicode_AsUTF8(orig_str);
              std::string s_raw_python_orig_str(raw_python_orig_str);

              std::stringstream reason;
              reason << "Failed to decode string '" << s_raw_python_orig_str << "'. Exception raised: " << orig_reason.str();

              fail_reason = reason.str();
              return false;
            }
        }

        if (py::isinstance<py::dict>(context_obj)) {
            // key:value
            py::str prop_name = name_context.back();
            name_context.pop_back();
            py::dict parent_dict = (py::dict)context_obj;
            parent_dict[prop_name] = result_value;
        }
        else {
            // [value1, value2]
            py::list parent_list = (py::list)context_obj;

            parent_list.append(result_value);
        }

        return true;
    }

    bool StartObject() {
        context_stack.push_back(py::dict());
        return true;
    }

    bool Key(const char* str, SizeType length, bool copy) {
        try {
          py::str key_value = py::str(str);
          name_context.push_back(key_value);
        } catch (std::exception& ex) {
          std::stringstream orig_reason;

          if (PyErr_Occurred()) {
            PyObject *type, *value, *traceback;
            PyErr_Fetch(&type, &value, &traceback);
            PyErr_NormalizeException(&type, &value, &traceback);

            auto type_decref = make_decref_python_ptr(type);
            auto value_decref = make_decref_python_ptr(value);
            auto traceback_decref = make_decref_python_ptr(traceback);

            if (value != nullptr) {
                PyObject *py_str_value = PyObject_Str(value);
                auto decref_py_str_value = make_decref_python_ptr(py_str_value);

                const char* raw_python_error_msg = PyUnicode_AsUTF8(py_str_value);
                std::string s_python_error_msg(raw_python_error_msg);
                orig_reason << s_python_error_msg;
            }

            PyErr_Clear();
          } else {
            orig_reason << ex.what();
          }

          // Try to convert the original string to a more suitable format for the error message
          PyObject *orig_str = PyUnicode_DecodeUTF8(str, (size_t)length, "backslashreplace");

          auto orig_str_decref = make_decref_python_ptr(orig_str);

          const char* raw_python_orig_str = PyUnicode_AsUTF8(orig_str);
          std::string s_raw_python_orig_str(raw_python_orig_str);

          std::stringstream reason;
          reason << "Failed to decode string '" << s_raw_python_orig_str << "'. Exception raised: " << orig_reason.str();

          fail_reason = reason.str();
          return false;
        }

        return true;
    }

    bool EndObject(SizeType memberCount) {
        py::object entity = context_stack.back();

        context_stack.pop_back();

        if (context_stack.size() == 1 && py::isinstance<py::list>(context_stack.back())) {
            // End of entity in a normal list of entities

            dict_handler(entity);
        }
        else if (context_stack.size() == 0) {
            // Allow single object JSON

            dict_handler(entity);
        }
        else {
            py::object parent = context_stack.back();

            if (py::isinstance<py::dict>(parent)) {
                // Parent is a dict, add the object to the current property
                py::str prop_name = name_context.back();
                name_context.pop_back();
                py::dict parent_dict = (py::dict)parent;
                parent_dict[prop_name] = entity;
            }
            else {
                // Parent is a list, append the object
                py::list parent_list = (py::list)parent;
                parent_list.append(entity);
            }
        }

        return true;
    }

    bool StartArray() {
        context_stack.push_back(py::list());
        return true;
    }

    bool EndArray(SizeType elementCount) {
        py::object list = context_stack.back();
        context_stack.pop_back();

        if (context_stack.size() > 0) {
            py::object parent = context_stack.back();

            if (py::isinstance<py::dict>(parent)) {
                py::str prop_name = name_context.back();
                name_context.pop_back();
                py::dict parent_dict = (py::dict)parent;
                parent_dict[prop_name] = list;
            }
            else {
                py::list parent_list = (py::list)parent;
                parent_list.append(list);
            }
        }

        return true;
    }

    MyHandlerDict(py::object py_handler, py::object py_transit_map, py::object do_float_as_int) {
        dict_handler = py_handler.attr("handle_dict");

        py_Decimal = py::module::import("decimal").attr("Decimal");

        if (!py::isinstance<py::none>(do_float_as_int)) {
            try_float_as_int = do_float_as_int.cast<py::bool_>();
        } else
            try_float_as_int = false;

        if (!py::isinstance<py::none>(py_transit_map)) {
            py::dict transit_decode_map = (py::dict)py_transit_map;

            for (auto item : transit_decode_map) {
                py::object py_key = item.first.cast<py::object>();
                std::string key = py_key.cast<std::string>();
                py::object py_value = item.second.cast<py::object>();
                transit_map.emplace(key, py_value);
            }
        }
    }
};


class MyHandlerString : public BaseReaderHandler<UTF8<>, MyHandlerString> {
private:
    py::object py_handler;
    py::object string_handler;
    std::vector<int> cursor_stack;
    TrackingStreamWrapper *tracking_stream;
    py::object context;

public:
    bool Null() { return true; }
    bool Bool(bool b) { return true; }
    bool Int(int i) { return true; }
    bool Uint(unsigned u) { return true; }
    bool Int64(int64_t i) { return true; }
    bool Uint64(uint64_t u) { return true; }
    bool Double(double d) { return true; }
    bool String(const char* str, SizeType length, bool copy) { return true; }
    bool StartObject() {
        // cout << "Start Object" << endl;

        if (cursor_stack.size() == 0) {
            // Clear the accumulation buffer when we start on a toplevel entity
            tracking_stream->reset_accumulated_buffer();
        }
        cursor_stack.push_back(tracking_stream->Tell());
        return true;
    }
    bool Key(const char* str, SizeType length, bool copy) { return true; }
    bool EndObject(SizeType memberCount) {
        //cout << "End Object" << endl;

        cursor_stack.pop_back();

        if (cursor_stack.size() == 0) {
            // End of entity

            std::string json_data = tracking_stream->accumulated_buffer;
            json_data += "}";

            string_handler(json_data);

            // Clear the accumulation buffer
            tracking_stream->reset_accumulated_buffer();
        }

        return true;
    }
    bool StartArray() {
        // cout << "Start Array" << endl;
        return true;
    }
    bool EndArray(SizeType elementCount) {
        //cout << "End Array" << endl;
        return true;
    }

    MyHandlerString(py::object py_handler, TrackingStreamWrapper *stream) {
        string_handler = py_handler.attr("handle_string");
        tracking_stream = stream;
    }
};

int parse_strings(py::object stream, py::object handler) {

    Reader reader;

    TrackingStreamWrapper stream_wrapper(stream);
    MyHandlerString my_handler(handler, &stream_wrapper);

    reader.IterativeParseInit();
    while (!reader.IterativeParseComplete() && !reader.HasParseError()) {
        reader.IterativeParseNext<kParseDefaultFlags>(stream_wrapper, my_handler);
        // Your handler has been called once.
        //cout << "Handler was called!" << endl;
    }

    if (reader.HasParseError()) {
        py::object handle_error = handler.attr("handle_error");

        if (handle_error != NULL && !py::isinstance<py::none>(handle_error)) {
            int error_code = (int)reader.GetParseErrorCode();
            size_t offset = reader.GetErrorOffset();
            size_t line_no = stream_wrapper.GetLine();
            size_t column = stream_wrapper.GetColumn();

            handle_error(error_code, offset, line_no, column);
        }
    }

    py::object handle_end_stream = handler.attr("handle_end_stream");
    handle_end_stream();

    //cout << "Finished parsing file" << endl;

    return 0;
}

int parse_dict(py::object stream, py::object handler, py::object transit_decode_map,
               py::object do_float_as_int, py::object py_do_float_as_decimal) {
    Reader reader;

    StreamWrapper stream_wrapper(stream);
    MyHandlerDict my_handler(handler, transit_decode_map, do_float_as_int);

    reader.IterativeParseInit();
    bool parse_success = true;
    bool do_float_as_decimal = false;
    const unsigned int parseFlags = kParseDefaultFlags;

    if (!py::isinstance<py::none>(py_do_float_as_decimal)) {
        do_float_as_decimal = py_do_float_as_decimal.cast<py::bool_>();
    }

    while (!reader.IterativeParseComplete() && !reader.HasParseError()) {
        if (do_float_as_decimal)
            parse_success = reader.IterativeParseNext<kParseDefaultFlags|kParseNumbersAsStringsFlag>(stream_wrapper, my_handler);
        else
            parse_success = reader.IterativeParseNext<kParseDefaultFlags>(stream_wrapper, my_handler);
        // Your handler has been called once.
        //cout << "Handler was called! ParseErrorCode = " << reader.GetParseErrorCode() << " Result was: " << parse_success << endl;
    }

    //cout << "IterativeParseNext finished. Error code = " << reader.GetParseErrorCode() << endl;

    if (reader.HasParseError()) {
        py::object handle_error = handler.attr("handle_error");

        if (handle_error != NULL && !py::isinstance<py::none>(handle_error)) {
            int error_code = (int)reader.GetParseErrorCode();
            size_t offset = reader.GetErrorOffset();
            size_t line_no = stream_wrapper.GetLine();
            size_t column = stream_wrapper.GetColumn();

            handle_error(error_code, offset, line_no, column, my_handler.fail_reason);
        }
    }

    py::object handle_end_stream = handler.attr("handle_end_stream");
    handle_end_stream();

    //cout << "Finished parsing file" << endl;

    return 0;
}


int parse_string(py::str py_string, py::object handler) {
    Reader reader;

    std::string c_str = py_string.cast<std::string>();

    StringStream stream(c_str.c_str());
    MyHandlerDebug my_handler;

    reader.IterativeParseInit();
    while (!reader.IterativeParseComplete() && !reader.HasParseError()) {
        reader.IterativeParseNext<kParseDefaultFlags>(stream, my_handler);
        // Your handler has been called once.
        //cout << "Handler was called!" << endl;
    }

    if (reader.HasParseError()) {
        py::object handle_error = handler.attr("handle_error");

        if (handle_error != NULL && !py::isinstance<py::none>(handle_error)) {
            int error_code = (int)reader.GetParseErrorCode();
            size_t offset = reader.GetErrorOffset();
            size_t line_no = 0;
            size_t column = 0;

            handle_error(error_code, offset, line_no, column);
        }
    }

    py::object handle_end_stream = handler.attr("handle_end_stream");
    handle_end_stream();

    //cout << "Finished parsing file" << endl;

    return 0;
}



int parse(py::object stream, py::object handler) {

    MyHandler my_handler(handler);

    Reader reader;

    StreamWrapper stream_wrapper(stream);

    reader.IterativeParseInit();
    while (!reader.IterativeParseComplete() && !reader.HasParseError()) {
        reader.IterativeParseNext<kParseDefaultFlags>(stream_wrapper, my_handler);
        // Your handler has been called once.
        //cout << "Handler was called!" << endl;
    }

    if (reader.HasParseError()) {
        py::object handle_error = handler.attr("handle_error");

        if (handle_error != NULL && !py::isinstance<py::none>(handle_error)) {
            int error_code = (int)reader.GetParseErrorCode();
            size_t offset = reader.GetErrorOffset();
            size_t line_no = stream_wrapper.GetLine();
            size_t column = stream_wrapper.GetColumn();

            handle_error(error_code, offset, line_no, column);
        }
    }

    py::object handle_end_stream = handler.attr("handle_end_stream");
    handle_end_stream();

    //cout << "Finished parsing file" << endl;

    return 0;
}

PYBIND11_MODULE(sesam_rapidjson_pybind, m) {
    m.doc() = R"pbdoc(
        Pybind11 sesam streaming rapidjson parser plugin
        ------------------------------------------------

        The parse functions generally take a python IO stream as input and calls given the 'handler' python method
        with the result of the parse. The different parse implementations expect different methods to exist in
        the handler object. See the 'parse_json.py' test file for examples.

        The 'parse_dict' function can optionally be given a mapping of 'transit' prefixes to constructor methods to
        automatically decode transit encoded JSON.

        .. currentmodule:: sesam_rapidjson_pybind

        .. autosummary::
           :toctree: _generate

    )pbdoc";

    m.def("parse", &parse, R"pbdoc(
        SAX parser where the event callback handler is in python
    )pbdoc");

    m.def("parse8601", &parse8601, R"pbdoc(
        Parse iso8601 date strings (UTC only)
    )pbdoc");

    m.def("parse_strings", &parse_strings, R"pbdoc(
        Parser that handles back all top level objects/entities it finds in the JSON stram as a string
    )pbdoc");

    m.def("parse_string", &parse_string, R"pbdoc(
        Parser that parses a single JSON string and delivers it to the python handler as a dict
    )pbdoc");

    m.def("parse_dict", &parse_dict, R"pbdoc(
        Parser that delivers python dicts for all top level objects in the JSON stream
    )pbdoc");

#ifdef VERSION_INFO
    m.attr("__version__") = VERSION_INFO;
#else
    m.attr("__version__") = "dev";
#endif
}
