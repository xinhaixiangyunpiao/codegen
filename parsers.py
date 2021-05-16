import clang
import pathlib
import logging
import itertools

import tree_matchers
import generic_composer
import convertors

from enum import Enum
from utils import get_args
from clang.cindex import TranslationUnit, Diagnostic

# 判断函数是否是定义且在本地文件中
def _is_local_definition(input_headers):
    return lambda x: x.is_definition() and str(x.location.file) in input_headers

# 过滤显式的注释
def _filter_by_explicit_annotation(entities, explicit_annotation):
    filtered = []

    class CodeGenMode(Enum):
        EXPLICIT = 1
        IMPLICIT = 2

    def has_annotation(entity, annotation):
        found_annotation = getattr(entity, 'annotation', None)
        return found_annotation == annotation if found_annotation else False

    def filter_by_mode(items, mode):
        if mode == CodeGenMode.IMPLICIT:
            return items
        elif mode == CodeGenMode.EXPLICIT:
            return [item for item in items if has_annotation(item[0], explicit_annotation)]

    for _, group in itertools.groupby(entities, key=lambda et: et[0].header):
        mode_for_header = CodeGenMode.IMPLICIT
        entities_in_header = list(group)
        if any(has_annotation(item[0], explicit_annotation) for item in entities_in_header):
            mode_for_header = CodeGenMode.EXPLICIT
        filtered.extend(filter_by_mode(entities_in_header, mode_for_header))
    return filtered

# 将AST根节点解析成带有信息的实体
# tu: all-src.cpp       clang.cindex.TranslationUnit    语法树根节点
# input_headers:        List[str]                       头文件列表，用来验证实体是否属于这些头文件
# scf_path:             str                             文件夹路径，用于提取header信息
# entities_with_info：                                  带有信息的实体
def parse_constructs(tu, input_headers, scf_path):
    # 提取class节点和enum节点
    class_nodes = tree_matchers.get_classes(tu.cursor, _is_local_definition(input_headers))
    enum_nodes = tree_matchers.get_enums(tu.cursor, _is_local_definition(input_headers))

    # 从节点中提取实体信息并分类
    entities_with_info = [generic_composer.get_entity_from_node(node,tu,scf_path) for node in class_nodes + enum_nodes]
    
    # 根据header信息将文件分组并准备转换
    entities_to_generate = _filter_by_explicit_annotation(entities_with_info, 'explicit_codegen')

    # 提取出model信息
    models = [convertors.make_ch_model(entity) for entity, metaclass in entities_to_generate
              if metaclass == generic_composer.MetaClass.MODEL]

    # 提取出viewmodel信息
    viewmodels = [convertors.make_ch_viewmodel(entity) for entity, metaclass in entities_to_generate
                  if metaclass == generic_composer.MetaClass.VIEWMODEL]

    # 提取出service信息
    services = [convertors.make_scf_service(entity) for entity, metaclass in entities_to_generate
                if metaclass == generic_composer.MetaClass.SERVICE]

    # 提取出enum信息
    enums = [convertors.make_enum(entity) for entity, metaclass in entities_to_generate
             if metaclass == generic_composer.MetaClass.ENUMERATION]
    
    return models, enums, viewmodels, services

# 将所有头文件解析成信息实体返回
# input_headers:  List[str]    所有需要解析的头文件相对路径
# libclang_path:  str          libclang库的路径，已经设置可以用就置为空
# stl_headers:    str          stl头文件所在路径，暂未用到
# c_headers:      str          C头文件所在路径，暂未用到
# target_macros:  List[str]    其他编译宏
# header_paths:   List[str]    头文件路径
# return: 带有信息的实体对象，枚举或类或函数或变量
def parse(input_headers, libclang_path, stl_headers, c_headers, target_macros, header_paths):
    # 设置libclang库路径
    if libclang_path and not clang.cindex.Config.library_path:
        clang.cindex.Config.set_library_path(libclang_path)
    
    # 设置scf_path, 整个工程的目录
    scf_path = str(pathlib.Path(__file__).resolve().parent.parent)

    # 组装all_src.cpp文件，依次包含所有头文件
    all_src = '\n'.join(['#include "{}"'.format(x) for x in input_headers])

    # 组装文件和文件的句柄
    full_headers = [(x, open(x)) for x in input_headers]
    
    # 得到clang的解析参数
    args = get_args(stl_headers, c_headers, scf_path, target_macros, header_paths)

    # 使用clang解析，得到语法树根节点
    tu = TranslationUnit.from_source('all-src.cpp', args, unsaved_files=[('all-src.cpp', all_src)] + full_headers)

    # 关闭所有文件
    for _, f in full_headers:
        f.close()
    
    # 如果解析文件错误，则停止程序，报告错误信息
    for diag in tu.diagnostics:
        if diag.severity == Diagnostic.Fatal:
            logging.error("Parse Error (severity=%s, location=%s, type=%s)",
                          diag.severity, diag.location, diag.spelling)
            exit(diag.severity)

    # 从语法树中提取信息
    return parse_constructs(tu, input_headers, scf_path)