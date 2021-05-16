import generic
import utils
import re
import tree_matchers as matchers

from clang.cindex import CursorKind, AccessSpecifier

def memoize_entity(f):
    memo = {}
    def helper(name, original_name, node, template_node, *args, **kwargs):
        node_usr = node.get_usr() if node else ''
        template_node_usr = template_node.get_usr() if template_node else ''
        key = (name or '') + (original_name or '') + node_usr + template_node_usr
        if key not in memo:
            result = f(name, original_name, node, template_node, *args, **kwargs)
            if not isinstance(result, generic.RecursiveType):
                memo[key] = result
            else:
                return result
        return memo[key]
    return helper

# 转换location
def _convert_location(location):
    return generic.Location(str(location.file), str(location.line), str(location.column))

# 移除namespace
def _remove_namespace(typename):
    return re.sub(r'[a-zA-Z_0-9]+::', '', typename) if typename else ''

# 是子列表
def _is_sublist(list1, list2):
    if len(list1) > len(list2):
        return False
    for i in range(len(list2) - len(list1) + 1):
        if all(list1[j] == list2[i:][j] for j in range(len(list1))):
            return True
    return False

# 定义present
def _typedef_present(complete_name, original_token):
    original_tokens_list = [_remove_namespace(part) for part in original_token.split()]
    return not _is_sublist(_remove_namespace(complete_name).split(), original_tokens_list)

# 得到访问属性
def _get_access_specifier(node):
    acc_spec = node.access_specifier
    if acc_spec == AccessSpecifier.PUBLIC:
        return generic.AccessSpecifier.PUBLIC
    elif acc_spec == AccessSpecifier.PROTECTED:
        return generic.AccessSpecifier.PROTECTED
    elif acc_spec == AccessSpecifier.PRIVATE:
        return generic.AccessSpecifier.PRIVATE
    else:
        raise Exception('Invalid access specifier encountered')

# 创造实体信息
@memoize_entity
def _create_entity_info(basic_name, original_typename, def_node, template_class,tu, scf_path, prev):
    if template_class:
        type_info = get_abstract_entity(template_class, tu, scf_path, prev)
    else:
        type_info = get_abstract_entity(def_node, tu, scf_path, prev) \
            if def_node else generic.PrimitiveType(basic_name)
    if _typedef_present(type_info.complete_name(), original_typename):
        type_info.original_typedef = original_typename
    return type_info

# 获取field初始值
def _get_init_value(field_node, tu):
    initializer = matchers.get_initializer_expr(field_node)
    if initializer:
        token = list(tu.get_tokens(None, initializer.extent))[0]
        return token.spelling
    else:
        return None

# 得到field信息
def _get_field_info(field_node, tu, scf_path, prev):
    field_type, def_node, template_class = utils.get_type_info(field_node.type, tu, scf_path)
    type_info = _create_entity_info(field_type.name, field_node.type.spelling, def_node, template_class,
                                    tu, scf_path, prev)
    return generic.Field(name=field_node.spelling, access_specifier=_get_access_specifier(field_node),
                         type_info=type_info,
                         traits=generic.TypeTraits(
                                     field_type.traits.is_const, field_type.traits.ref_type),
                         init_value=_get_init_value(field_node, tu), location=_convert_location(field_node.location))

# 得到参数
def _get_param(param_node, tu, scf_path, prev):
    param_type, def_node, template_class = utils.get_type_info(param_node.type, tu, scf_path)
    type_info = _create_entity_info(param_type.name, param_node.type.spelling, def_node, template_class,
                                    tu, scf_path, prev)
    return generic.Param(name=param_node.spelling, type_info=type_info,
                         traits=generic.TypeTraits(param_type.traits.is_const, param_type.traits.ref_type),
                         location=_convert_location(param_node.location))

# 得到注释
def _get_annotation(node):
    annotations = matchers.get_children(node, lambda n: n.kind == CursorKind.ANNOTATE_ATTR)
    return annotations[0].spelling if annotations else None

# 获取method信息
def _get_api(api_node, tu, scf_path, prev):
    params = [_get_param(param_node, tu, scf_path, prev) for param_node in matchers.get_params(api_node)]
    return_type, ret_def_node, template_class = utils.get_type_info(api_node.result_type, tu, scf_path)

    return_type_info = _create_entity_info(return_type.name, api_node.result_type.spelling, ret_def_node,
                                           template_class, tu, scf_path, prev)

    traits = generic.ApiTraits(
        is_const=api_node.is_const_method(),
        is_virtual=api_node.is_virtual_method(),
        is_abstract=api_node.is_pure_virtual_method(),
        is_static=api_node.is_static_method(),
        annotation=_get_annotation(api_node))

    return generic.Api(name=api_node.spelling, access_specifier=_get_access_specifier(api_node),
                       param_types=params, traits=traits,
                       returns=generic.ApiReturns(return_type_info, generic.TypeTraits(
                           return_type.traits.is_const, return_type.traits.ref_type)),
                       location=_convert_location(api_node.location))

# 从节点提取实体
def from_node(node, tu, scf_path):
    return get_abstract_entity(node, tu, scf_path, [])

# 从节点提取抽象实体
def get_abstract_entity(node, tu, scf_path, prev):
    ns = utils.get_namespace(node)
    full_name = ns + '::' + node.spelling if ns else node.spelling
    if any(full_name == p for p in prev):
        return generic.RecursiveType(node.spelling, ns)
    if node.kind == CursorKind.ENUM_DECL:
        return get_abstract_enum(node, tu, scf_path)
    else:
        return get_abstract_class(node, tu, scf_path, prev)

# 从节点提取enum
def get_abstract_enum(node, tu, scf_path):
    enum_constant_nodes = matchers.get_children(node, lambda n: n.kind == CursorKind.ENUM_CONSTANT_DECL)
    full_namespace = utils.get_namespace(node)
    constants = [generic.EnumConstant(cons.spelling, cons.enum_value) for cons in enum_constant_nodes]
    return generic.DefinedEnum(name=node.spelling, namespace=full_namespace, constants=constants, \
                               defined_in_header=utils.get_header(node, tu, scf_path), \
                               location=_convert_location(node.location))

# 从节点提取class
def get_abstract_class(node, tu, scf_path, prev):
    ns = utils.get_namespace(node)
    full_name = ns + '::' + node.spelling if ns else node.spelling

    base_nodes = matchers.get_children(node, matchers.is_base_class())
    base_type_infos = [utils.get_type_info(base_node.type, tu, scf_path) for base_node in base_nodes]
    base_classes = [_create_entity_info(base_type.name, base_node.type.spelling, \
                    def_node, template_class, tu, scf_path, prev + [full_name]) \
                    for (base_node, (base_type, def_node, template_class)) in zip(base_nodes, base_type_infos)]

    field_nodes = matchers.get_children(node, matchers.is_field())
    fields = [_get_field_info(field_node, tu, scf_path, prev + [full_name]) for field_node in field_nodes]

    api_nodes = matchers.get_children(node, matchers.is_method())
    apis = [_get_api(api_node, tu, scf_path, prev + [full_name]) for api_node in api_nodes]

    annotation = _get_annotation(node)

    template_args = [node.type.get_template_argument_type(i) for i in range(node.type.get_num_template_arguments())]
    if template_args:
        template_args_entities = [
            generic.PrimitiveType(
                utils.get_primitive_type(templ_arg)) if utils.is_primitive(templ_arg)
            else get_abstract_entity(templ_arg.get_declaration(), tu, scf_path, prev + [full_name])
            for templ_arg in template_args]

        header = utils.get_header(node, tu, scf_path)
        if header or not scf_path:
            return generic.DefinedClass(name=node.spelling, namespace=utils.get_namespace(node),
                                        template_args=template_args_entities, members=fields, methods=apis,
                                        bases=base_classes, defined_in_header=header,
                                        location=_convert_location(node.location), annotation=annotation)
        else:
            return generic.DeclaredClass(node.spelling, utils.get_namespace(node), template_args_entities, None)
    else:
        type_info, _, _ = utils.get_type_info(node.type, tu, scf_path)
        if type_info.header_with_def or not scf_path:
            return generic.DefinedClass(name=type_info.name, namespace=type_info.namespace, template_args=[],
                                        members=fields, methods=apis, bases=base_classes,
                                        defined_in_header=type_info.header_with_def,
                                        location=_convert_location(node.location), annotation=annotation)
        else:
            return generic.DeclaredClass(type_info.name, type_info.namespace, [], None)

