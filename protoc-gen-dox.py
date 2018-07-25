#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals

import sys

from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf.descriptor_pb2 import FieldDescriptorProto as desc

LOCATION_MSG_TYPE = 4
LOCATION_ENUM_TYPE = 5
LOCATION_NESTED_ENUM_TYPE = 4
LOCATION_NESTED_MSG_TYPE = 3
LOCATION_VALUE_TYPE = 2
LOCATION_ONEOF_TYPE = 8

if sys.version_info >= (3, 0):
    STDERR_STREAM = sys.stderr.buffer
    STDIN_STREAM  = sys.stdin.buffer
    STDOUT_STREAM = sys.stdout.buffer
else:
    STDERR_STREAM = sys.stderr
    STDIN_STREAM  = sys.stdin
    STDOUT_STREAM = sys.stdout

def trace(s):
    STDERR_STREAM.write(s.encode("utf-8"))
    STDERR_STREAM.write("\n".encode("utf-8"))

def start_doxygen_bloc():
    """Start doxygen comment bloc"""
    return "/**\n"

def end_doxygen_bloc():
    """End doxygen comment bloc"""
    return " */\n"

def html_table_begin():
    return "<table>\n"

def html_caption(label):
    return "<caption id=\""+ label + "\">" + label + "</caption>\n"

def html_table_end():
    return "</table>\n"

def html_raw():
    return "<tr>"

def html_col_title(title):
    return "<th> " + title

def html_col(text, **kwargs):
    doc = "<td"
    for key, value in kwargs.items():
        doc += " " + key + "=\"" + str(value) + "\""
    doc += ">"

    if isinstance(text, unicode) or isinstance(text, str):
        doc += text
    else:
        doc += str(text).encode('utf-8')
    doc += "</td>\n"

    return doc


def add_doxygen_cmd(cmd, name):
    """
    Add doxygen entry
    if it's a subpage, add as list
    """
    insert_dash = False
    if cmd == "subpage":
        insert_dash = True
    prefix = ""
    if insert_dash:
        prefix = " - "

    return "%s@%s\t%s\n" % (prefix, cmd, name)

def protobuf_label2str(label):
    if label == desc.LABEL_REQUIRED:
        return "required"
    elif label == desc.LABEL_OPTIONAL:
        return "optional"
    elif label == desc.LABEL_REPEATED:
        return "repeated"
    else:
        return "unknown"

def protobuf_type2desc(field_desc):
    """
    Convertie les type protobuf en texte.
    Pour les type enum et message, imprime le nom du type avec un lien vers sa
    description
    Le premier caractère étant un '.' il est retiré pour ces deux types là
    """
    if field_desc.type == desc.TYPE_BOOL:
        return "bool"
    elif field_desc.type == desc.TYPE_BYTES:
        return "bytes array"
    elif field_desc.type == desc.TYPE_DOUBLE:
        return "double"
    elif field_desc.type == desc.TYPE_ENUM:
        return "@ref " + field_desc.type_name[1:]
    elif field_desc.type == desc.TYPE_FIELD_NUMBER:
        return ""
    elif field_desc.type == desc.TYPE_FIXED32:
        return "fixed point 32"
    elif field_desc.type == desc.TYPE_FIXED64:
        return "fixed point 64"
    elif field_desc.type == desc.TYPE_FLOAT:
        return "float"
    elif field_desc.type == desc.TYPE_GROUP:
        return ""
    elif field_desc.type == desc.TYPE_INT32:
        return "int32"
    elif field_desc.type == desc.TYPE_INT64:
        return "int64"
    elif field_desc.type == desc.TYPE_MESSAGE:
        return "@ref " + field_desc.type_name[1:]
    elif field_desc.type == desc.TYPE_NAME_FIELD_NUMBER:
        return ""
    elif field_desc.type == desc.TYPE_SFIXED32:
        return "signed fixed point 32"
    elif field_desc.type == desc.TYPE_SFIXED64:
        return "signed fixed point 64"
    elif field_desc.type == desc.TYPE_SINT32:
        return "signed int32"
    elif field_desc.type == desc.TYPE_SINT64:
        return "signed int64"
    elif field_desc.type == desc.TYPE_STRING:
        return "string"
    elif field_desc.type == desc.TYPE_UINT32:
        return "uint32"
    elif field_desc.type == desc.TYPE_UINT64:
        return "uint64"

class ProtoDox(object):
    """
    base class
    each undocument element return "No doc string !"
    """
    def __init__(self, name, prefix=""):
        self._basename = name.split('.', 1)[0]
        self._name = ""
        if prefix:
            self._name += prefix + "."
        self._name += name
        self._doc_string = "<b><i>No doc_string !</i></b>"

    def set_doc_string(self, doc_string):
        if doc_string:
            self._doc_string = doc_string

    def to_doxygen(self):
        return self._doc_string


class ProtoOneOfDox(ProtoDox):
    def __init__(self, field_desc):
        ProtoDox.__init__(self, field_desc.name)

    def to_doxygen(self):
        doc = html_raw()
        doc += html_col("<b>" + self._name + "</b>")
        doc += html_col("<b>oneof</b>")
        doc += html_col("<b>-</b>", align="center")
        doc += html_col("<b>-</b>", align="center")
        doc += html_col(self._doc_string)
        return doc

class ProtoFieldDox(ProtoDox):
    def __init__(self, field_desc):
        ProtoDox.__init__(self, field_desc.name)
        self._type = protobuf_type2desc(field_desc)
        self._id = field_desc.number
        self._label = protobuf_label2str(field_desc.label)
        if hasattr(field_desc, "oneof_index") and \
           field_desc.HasField("oneof_index"):
            self._oneof_index = field_desc.oneof_index
        else:
            self._oneof_index = None

    def is_part_of_oneof(self):
        return self._oneof_index is not None

    def to_doxygen(self):
        doc = html_raw()

        if self.is_part_of_oneof():
            doc += html_col("<i>" + self._name + "</i>", align="right")
            doc += html_col("-", align="center")
        else:
            doc += html_col(self._name)
            doc += html_col(self._label)

        doc += html_col(self._id)
        doc += html_col(self._type)
        doc += html_col(self._doc_string)
        return doc

class ProtoMessageDox(ProtoDox):
    def __init__(self, name, prefix="", nested=False):
        ProtoDox.__init__(self, name, prefix)
        self._nested = nested
        self._nested_enums = list()
        self._nested_messages = list()
        self._oneofs = list()
        self._fields = list()

    def parse_field(self, fields):
        for f in fields:
            if hasattr(f, "oneof_index") and f.HasField("oneof_index"):
                pass #trace("is part of oneof " + str(f.oneof_index))
            self._fields.append(ProtoFieldDox(f))

    def parse_enums(self, enums):
        for enum in enums:
            self._nested_enums.append(ProtoEnumDox(enum.name, self._name, True))
            self._nested_enums[-1].parse_value(enum.value)

    def parse_nested(self, messages):
        for msg in messages:
            self._nested_messages.append(ProtoMessageDox(msg.name, self._name, True))
            self._nested_messages[-1].parse_oneof(msg.oneof_decl)
            self._nested_messages[-1].parse_enums(msg.enum_type)
            self._nested_messages[-1].parse_nested(msg.nested_type)
            self._nested_messages[-1].parse_field(msg.field)

    def parse_oneof(self, oneofs):
        for oneof in oneofs:
            self._oneofs.append(ProtoOneOfDox(oneof))

    def set_elem_doc_string(self, location, index_offset):
        elem_type = location.path[index_offset]
        elem_idx = location.path[index_offset + 1]
        path_len = len(location.path)

        if (elem_type == LOCATION_NESTED_ENUM_TYPE):
            elem = self._nested_enums[elem_idx]
        elif (elem_type == LOCATION_NESTED_MSG_TYPE):
            elem = self._nested_messages[elem_idx]
        elif (elem_type == LOCATION_VALUE_TYPE):
            elem = self._fields[elem_idx]
        elif (elem_type == LOCATION_ONEOF_TYPE):
            elem = self._oneofs[elem_idx]
        else:
            return

        if (path_len == (index_offset + 2)):
            if isinstance(elem, ProtoFieldDox):
                doc_string = location.trailing_comments
            else:
                doc_string = location.leading_comments
            elem.set_doc_string(doc_string)
        elif not isinstance(elem, ProtoFieldDox):
            elem.set_elem_doc_string(location, index_offset + 2)

    def to_doxygen(self):
        doc = ""

        if self._nested:
            doc += add_doxygen_cmd("subsubsection", self._basename)
        else:
            doc += add_doxygen_cmd("subsection", self._basename)

        doc += self._doc_string

        doc += html_table_begin()
        doc += html_caption(self._name)
        doc += html_raw()
        doc += html_col_title("Nom")
        doc += html_col_title("Label")
        doc += html_col_title("Id")
        doc += html_col_title("Type")
        doc += html_col_title("Description")

        cur_oneof_idx = None
        for field in self._fields:
            if field.is_part_of_oneof() and cur_oneof_idx != field._oneof_index:
                cur_oneof_idx = field._oneof_index
                doc += self._oneofs[cur_oneof_idx].to_doxygen()

            doc += field.to_doxygen()

            if not field.is_part_of_oneof() and cur_oneof_idx is not None:
                cur_oneof_idx = None

        doc += html_table_end()

        for enum in self._nested_enums:
            doc += enum.to_doxygen()

        for nested in self._nested_messages:
            doc += nested.to_doxygen()

        return doc


class ProtoEnumValueDox(ProtoDox):
    def __init__(self, name, value):
        ProtoDox.__init__(self, name)
        self._value = value

    def to_doxygen(self):
        doc = html_raw()
        doc += html_col(self._name)
        doc += html_col(self._value)
        doc += html_col(self._doc_string)
        return doc


class ProtoEnumDox(ProtoDox):
    def __init__(self, name, prefix="", nested=False):
        ProtoDox.__init__(self, name, prefix)
        self._nested = nested
        self._values = list()

    def parse_value(self, values):
        for v in values:
            self._values.append(ProtoEnumValueDox(v.name, v.number))

    def set_elem_doc_string(self, location, index_offset):
        elem_type = location.path[index_offset]
        elem_idx = location.path[index_offset + 1]
        path_len = len(location.path)

        if (elem_type == LOCATION_VALUE_TYPE):
            elem = self._values[elem_idx]
        else:
            return

        if (path_len == (index_offset + 2)):
            doc_string = location.trailing_comments
            elem.set_doc_string(doc_string)

    def to_doxygen(self):
        doc = ""

        if self._nested:
            doc += add_doxygen_cmd("subsubsection", self._basename)
        else:
            doc += add_doxygen_cmd("subsection", self._basename)

        doc += self._doc_string
        doc += html_table_begin()
        doc += html_caption(self._name)
        doc += html_raw()
        doc += html_col_title("Nom")
        doc += html_col_title("Valeur")
        doc += html_col_title("Description")

        for value in self._values:
            doc += value.to_doxygen()

        doc += html_table_end()

        return doc


class ProtoFileDox(ProtoDox):
    def __init__(self, filename, package):
        ProtoDox.__init__(self, filename)
        self._prefix = package
        self._enums = list()
        self._messages = list()

    def parse_enums(self, enums):
        for enum in enums:
            self._enums.append(ProtoEnumDox(enum.name, self._prefix))
            self._enums[-1].parse_value(enum.value)

    def parse_messages(self, messages):
        for msg in messages:
            self._messages.append(ProtoMessageDox(msg.name, self._prefix))
            self._messages[-1].parse_oneof(msg.oneof_decl)
            self._messages[-1].parse_enums(msg.enum_type)
            self._messages[-1].parse_nested(msg.nested_type)
            self._messages[-1].parse_field(msg.field)

    def parse_source_code_locations(self, locations):
        for location in locations:
            path_len = len(location.path)

            if (path_len < 2) or (path_len % 2 == 1):
                continue

            elem_type = location.path[0]
            elem_idx = location.path[1]


            if (elem_type == LOCATION_MSG_TYPE):
                elem = self._messages[elem_idx]
            elif (elem_type == LOCATION_ENUM_TYPE):
                elem = self._enums[elem_idx]
            else:
                continue

            if (path_len == 2):
                doc_string = location.leading_comments
                elem.set_doc_string(doc_string)
            else:
                elem.set_elem_doc_string(location, 2)


    def to_doxygen(self):
        self._doc_string = start_doxygen_bloc()
        self._doc_string += add_doxygen_cmd("file", self._name)
        self._doc_string += add_doxygen_cmd("page", self._name)
        self._doc_string += add_doxygen_cmd("tableofcontents", "")
        self._doc_string += add_doxygen_cmd("section", self._basename)

        for enum in self._enums:
            self._doc_string += enum.to_doxygen()

        for message in self._messages:
            self._doc_string += message.to_doxygen()

        self._doc_string += end_doxygen_bloc()

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

    data = STDIN_STREAM.read()

    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(data)

    response = plugin.CodeGeneratorResponse()
    generate_code(request, response)

    output = response.SerializeToString()
    STDOUT_STREAM.write(output)
