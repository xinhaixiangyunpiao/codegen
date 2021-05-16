import generic
import tree_matchers
import ch_basic

from clang.cindex import CursorKind, TypeKind

# 返回基础编译选项
def get_base_args():
    return ['-x', 'c++', '-std=c++17', '-ferror-limit=0', '-fdouble-square-bracket-attributes', '-DSPARK_CODEGEN=1']

# 得到参数
def get_args(stl_headers, c_headers, scf_path, target_macros, header_paths):
    header_path_list = ['-I' + stl_headers, '-I' + c_headers, '-I' + scf_path]
    for path in header_paths:
        header_path_list.append('-I' + path)
    args = get_base_args()
    args.extend(header_path_list)
    args.extend(target_macros)
    return args

# 得到节点命名空间
def get_namespace(node):
    if node.type.kind == TypeKind.ENUM:
        return '::'.join(node.type.spelling.split('::')[:-1]) if '::' in node.type.spelling else None
    else:
        parents = tree_matchers.get_parents(node, lambda n: n.kind == CursorKind.NAMESPACE)
        return '::'.join([parent.spelling for parent in parents if '__' not in parent.spelling]) if parents else None

# 得到去掉公共前缀之后的字符
def get_ch_subpath(header, scf_path):
    prefix_index = header.lower().rfind(scf_path.lower())
    ch_subpath = header[len(scf_path) + 1:].replace('\\', '/') if 0 <= prefix_index < len(header) else header
    return None if ch_subpath.startswith('codegen') else ch_subpath

# 得到node的header信息
def get_header(node, tu, scf_path):
    header = node.location.file.name
    scf = scf_path
    if header.lower().startswith(scf.lower()):
        return get_ch_subpath(header, scf)

# 判断一个类型是不是原始类型
def is_primitive(a_type):
    return a_type.get_declaration().kind == CursorKind.NO_DECL_FOUND

# 判断获取原始类型
def get_primitive_type(node_type):
    if node_type.kind == TypeKind.VOID:
        return 'void'
    elif node_type.kind == TypeKind.BOOL:
        return 'bool'
    elif node_type.kind == TypeKind.INT:
        return 'int'
    elif node_type.kind == TypeKind.UINT:
        return 'unsigned int'
    elif node_type.kind == TypeKind.USHORT:
        return 'unsigned short'
    elif node_type.kind == TypeKind.UCHAR:
        return 'unsigned char'
    elif node_type.kind == TypeKind.CHAR_S:
        return 'char'
    elif node_type.kind == TypeKind.DOUBLE:
        return 'double'
    elif node_type.kind == TypeKind.FLOAT:
        return 'float'
    elif node_type.kind == TypeKind.WCHAR:
        return 'wchar_t'
    else:
        return None

# 创建一个原始类型
def _create_primitive_type(resolved_type, reference_type, is_const, container=None):
    return ch_basic.CHType(
        name = get_primitive_type(resolved_type), namespace=None, container_type=container,
        is_const = is_const, ref_type=reference_type
    )

# 得到class的模板信息
def get_template_class(node):
    if node.type.get_num_template_arguments() > 0:
        template_type = node.type.get_declaration()
        if template_type.kind == CursorKind.TYPE_ALIAS_DECL:
            template_type = template_type.underlying_typedef_type.get_declaration()
        return template_type, get_namespace(template_type)
    elif node.kind == CursorKind.TYPE_ALIAS_TEMPLATE_DECL:
        alias = tree_matchers.get_node(node, lambda n: n.kind == CursorKind.TYPE_ALIAS_DECL)
        get_template_class(alias)
    else:
        return None, None

# 递归获取类型
def _recursively_apply(node, predicate):
    results = tree_matchers.get_children(node, predicate)
    return _recursively_apply(results[0], predicate) if results else node

# 获取类型的所有子类型
def _resolve_typedefs(node):
    def predicate(n): return n.kind == CursorKind.TYPE_REF and n.type.kind == TypeKind.TYPEDEF
    result = _recursively_apply(node, predicate)
    return result.type.get_declaration() if result != node else node

# 创建一个container类型
def create_full_container(container, container_ns):
    if not container:
        return None
    return '::'.join([container_ns, container]) if container_ns else container

# 得到引用的类型
def _get_reference_qualifier(node_type):
    if node_type.kind == TypeKind.LVALUEREFERENCE:
        return generic.RefType.LVALUE
    elif node_type.kind == TypeKind.RVALUEREFERENCE:
        return generic.RefType.RVALUE
    elif node_type.kind == TypeKind.POINTER:
        return generic.RefType.POINTER
    else:
        return None

# 得到类的指针类型和引用类型
def _get_pointed_type(starting_type):
    new_node = None
    ref_type = _get_reference_qualifier(starting_type)
    pointee = starting_type.get_pointee()
    while pointee.kind != TypeKind.INVALID:
        new_node = pointee
        pointee = pointee.get_pointee()

    return new_node if new_node else starting_type, ref_type

# 得到类的类型信息
def get_type_info(input_type, tu, scf_path):
    base_type, reference_type = _get_pointed_type(input_type)
    base_type_node = base_type.get_declaration()
    is_const = base_type.is_const_qualified()

    if is_primitive(base_type):
        return _create_primitive_type(base_type, reference_type, is_const), None, None

    container, container_namespace = get_template_class(base_type_node)
    aliased_node = _resolve_typedefs(base_type_node)

    final_type, reference_type_new = _get_pointed_type(
        aliased_node.underlying_typedef_type if aliased_node.kind == CursorKind.TYPE_ALIAS_DECL
        else aliased_node.type
    )

    if is_primitive(final_type):
        return _create_primitive_type(final_type, reference_type if reference_type else reference_type_new, is_const),\
               None, None

    if container:
        template_arg_type = container.type.get_template_argument_type(0)
        if is_primitive(template_arg_type):
            return _create_primitive_type(template_arg_type, reference_type if reference_type else reference_type_new,
                                          is_const, create_full_container(container.spelling, container_namespace)),\
                   None, container
        ending_node = template_arg_type.get_declaration()
    else:
        ending_node = final_type.get_declaration()

    return (ch_basic.CHType(
        name=ending_node.spelling,
        namespace=get_namespace(ending_node),
        header_with_def=get_header(ending_node, tu, scf_path) if tu and scf_path else None,
        container_type=create_full_container(container.spelling if container else None, container_namespace),
        is_enum=ending_node.type.kind == TypeKind.ENUM,
        is_const=is_const,
        ref_type=reference_type if reference_type else reference_type_new
    ), ending_node, container)