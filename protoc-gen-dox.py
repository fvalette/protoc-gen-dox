#!/usr/bin/python3

import sys

from google.protobuf.compiler import plugin_pb2 as plugin


def start_doxygen_bloc():
    return "/**\n"

def end_doxygen_bloc():
    return " */\n"

def add_doxygen_cmd(cmd, name):
    insert_dash = False
    if cmd == "subpage":
        insert_dash = True
    prefix = ""
    if insert_dash:
        prefix = " - "

    return " * %s@%s\t%s\n" % (prefix, cmd, name)


class ProtoDox(object):
    '''Classe de base'''
    def __init__(self, name):
        self._name = name
        self._doc_string = "No doc_string !"

    def set_doc_string(self, doc_string):
        self._doc_string = doc_string

    def to_doxygen(self):
        return self._doc_string

class ProtoFieldDoc(ProtoDox):
    def __init__(self, name, ftype, fid, label):
        ProtoDox.__init__(self, name)
        self._type = ftype
        self._id = fid
        self._label = label

    def to_doxygen(self):
        return "Field %s : %s\n" % (self._name, self._doc_string)

class ProtoMessageDox(ProtoDox):
    def __init__(self, name):
        ProtoDox.__init__(self, name)
        self._fields = list()

    def parse_field(self, fields):
        for f in fields:
            ftype = f.type
            if ftype == "TYPE_ENUM":
                ftype = "enum %s" % (f.type_name)
            elif ftype == "TYPE_MESSAGE":
                ftype = "message %s" % (f.type_name)

            self._fields.append(ProtoFieldDoc(f.name, ftype, f.number, f.label))

    def set_elem_doc_string(self, index, doc_string):
        self._fields[index].set_doc_string(doc_string)

    def to_doxygen(self):
        doc = start_doxygen_bloc()
        doc += add_doxygen_cmd("inpage", "Protobuf.demo")
        doc += add_doxygen_cmd("page", self._name)
        doc += add_doxygen_cmd("brief", self._doc_string)

        #for field in self._fields:
        #    doc_string += field.to_doxygen()

        doc += end_doxygen_bloc()
        return doc


class ProtoEnumValueDox(ProtoDox):
    def __init__(self, name, value):
        ProtoDox.__init__(self, name)
        self._value = value

    def to_doxygen(self):
        return "%s = %d : %s\n" % (self._name, self._value, self._doc_string)


class ProtoEnumDox(ProtoDox):
    def __init__(self, name):
        ProtoDox.__init__(self, name)
        self._values = list()

    def parse_value(self, values):
        for v in values:
            self._values.append(ProtoEnumValueDox(v.name, v.number))

    def set_elem_doc_string(self, index, doc_string):
        self._values[index].set_doc_string(doc_string)

    def to_doxygen(self):
        doc_string = "Enum %s : %s\n" % (self._name, self._doc_string)
        for value in self._values:
            doc_string += value.to_doxygen()
        return doc_string


class ProtoFileDox(ProtoDox):
    def __init__(self, filename, package):
        ProtoDox.__init__(self, filename)
        self._package = package
        self._prefix = "Protobuf." + self._package
        self._enums = list()
        self._messages = list()

    def parse_enums(self, enums):
        for enum in enums:
            name = self._prefix + "." + enum.name
            self._enums.append(ProtoEnumDox(name))
            self._enums[-1].parse_value(enum.value)

    def parse_messages(self, messages):
        for msg in messages:
            name = self._prefix + "." + msg.name
            self._messages.append(ProtoMessageDox(name))
            self._messages[-1].parse_field(msg.field)

    def parse_source_code_locations(self, locations):
        for location in locations:
            path_len = len(location.path)

            if (path_len < 2):
                continue

            # Extract type and index
            elem_type = location.path[0]
            elem_idx = location.path[1]

            if (elem_type == 4):
                elem = self._messages[elem_idx]
            elif (elem_type == 5):
                elem = self._enums[elem_idx]
            else:
                continue

            if (path_len == 2):
                doc_string = location.leading_comments
                elem.set_doc_string(doc_string)
            # Extract comment for a value/field
            elif (path_len == 4):
                sub_elem_index = location.path[3]
                doc_string = location.trailing_comments
                elem.set_elem_doc_string(sub_elem_index, doc_string)


    def to_doxygen(self):
        self._doc_string = start_doxygen_bloc()
        self._doc_string += add_doxygen_cmd("file", self._name)
        self._doc_string += add_doxygen_cmd("ingroup", "Protobuf")
        self._doc_string += add_doxygen_cmd("page", self._prefix)

        for enum in self._enums:
            self._doc_string += add_doxygen_cmd("subpage", enum._name)

        for message in self._messages:
            self._doc_string += add_doxygen_cmd("subpage", message._name)

        self._doc_string += end_doxygen_bloc()

        for enum in self._enums:
            self._doc_string += enum.to_doxygen()

        for message in self._messages:
            self._doc_string += message.to_doxygen()
        return self._doc_string


def generate_code(request, response):
    for proto_file in request.proto_file:
        proto_file_dox = ProtoFileDox(proto_file.name, proto_file.package)
        proto_file_dox.parse_enums(proto_file.enum_type)
        proto_file_dox.parse_messages(proto_file.message_type)
        proto_file_dox.parse_source_code_locations(proto_file.source_code_info.location)

        f = response.file.add()
        f.name = proto_file.name + '.dox'
        f.content = proto_file_dox.to_doxygen()


if __name__ == '__main__':

    data = sys.stdin.buffer.read()

    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(data)

    response = plugin.CodeGeneratorResponse()
    generate_code(request, response)

    output = response.SerializeToString()
    sys.stdout.buffer.write(output)
