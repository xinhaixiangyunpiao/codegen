import clang

# 判断所有condtion是否都满足，都满足则为true，否则则为false
def all_of(*conditions):
    return lambda node: all(condition(node) for condition in conditions)

# 是其中的一个
def either_of(*conditions):
    return lambda node: any(condition(node) for condition in conditions)

# 判断是否为class，输入为clang.cindex.Cursor，输出为bool,返回一个函数，一个判断节点是否是满足conditions条件的class节点的函数
def is_class(*conditions):
    return lambda node: (node.kind == clang.cindex.CursorKind.CLASS_DECL \
                        or node.kind == clang.cindex.CursorKind.STRUCT_DECL) \
                        and node.is_definition() \
                        and all_of(*conditions)(node)

# 判断节点是否为enum
def is_enum(*conditions):
    return lambda node: node.kind == clang.cindex.CursorKind.ENUM_DECL \
                        and node.is_definition() \
                        and all_of(*conditions)(node)

# 判断节点是否为method
def is_method(*conditions):
    return lambda node: node.kind == clang.cindex.CursorKind.CXX_METHOD \
                        and all_of(*conditions)(node)

# 判断节点是否为field
def is_field(*conditions):
    return lambda node: node.kind == clang.cindex.CursorKind.FIELD_DECL \
                        and all_of(*conditions)(node)

# 判断节点是否为初始值
def is_initializer():
    return lambda node: node.kind == clang.cindex.CursorKind.INTEGER_LITERAL or node.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR

# 判断类是否是基类，返回满足条件的基类
def is_base_class(*conditions):
    return lambda node: node.kind == clang.cindex.CursorKind.CXX_BASE_SPECIFIER \
                        and all(condition(node) for condition in conditions)

# 在nodes中找到满足条件的nodes返回
# nodes: List[clang.cindex.Cursor] AST节点列表
# matchers 函数列表指针 每个函数输入是clang.cindex.Cursor，返回值为bool的函数
# List[clang.cindex.Cursor] nodes中，all matchers为true的节点
def get(nodes, *matchers):
    return [node for node in nodes if all(matcher(node) for matcher in matchers)]

# 得到root节点中所有字节中matcher返回值为true的节点
# root clang.cindex.Cursor AST中的某一个节点
# matchers 函数列表指针 每个函数输入是clang.cindex.Cursor，返回值为bool的函数
# List[clang.cindex.Cursor] root的子节点中，all matchers为true的节点
def get_nodes(root, *matchers):
    return get(root.walk_preorder(), *matchers)

# 得到root节点所有子节点中所有满足条件的节点
# root clang.cindex.Cursor AST中的某一个节点
# condition 函数列表指针 每个函数输入是clang.cindex.Cursor，返回值为bool的函数
# List[clang.cindex.Cursor] root的子节点中是class且condition为true的节点
def get_classes(root, *conditions):
    return get_nodes(root, is_class(), *conditions)

# 得到AST中的枚举节点
def get_enums(root, *conditions):
    return get_nodes(
        root,
        is_enum(),
        *conditions
    )

# 得到root下所有参数节点
def get_params(root):
    return get_nodes(
        root,
        lambda n: n.kind == clang.cindex.CursorKind.PARM_DECL
    )

# 得到root下所有初始值
def get_initializer(root):
    inits = get_nodes(root, is_initializer())
    if len(inits) == 1:
        return inits[0]
    else:
        return None

# 得到初始值节点
def get_initializer_expr(root):
    init_vals = get_nodes(
        root,
        either_of(
            lambda n: n.kind == clang.cindex.CursorKind.INTEGER_LITERAL,
            lambda n: n.kind == clang.cindex.CursorKind.CXX_BOOL_LITERAL_EXPR,
            lambda n: n.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR,
            lambda n: n.kind == clang.cindex.CursorKind.CHARACTER_LITERAL,
            lambda n: n.kind == clang.cindex.CursorKind.CXX_NULL_PTR_LITERAL_EXPR
        )
    )
    return init_vals[0] if init_vals else None

# 得到节点parent链中所有满足条件的节点
def get_parents(root, *matchers):
    parent = root.semantic_parent
    matching_parents = []
    while parent:
        if all(matcher(parent) for matcher in matchers):
            matching_parents.append(parent)
        parent = parent.semantic_parent
    return matching_parents[::-1]

# 筛选节点列表中满足条件的节点
def get(nodes, *matchers):
    return [node for node in nodes if all(matcher(node) for matcher in matchers)]

# 得到节点的孩子中所有满足条件的节点
def get_children(root, *matchers):
    return get(root.get_children(), *matchers)

# 满足条件就返回，不满足条件就返回空
def get_node(root, *matchers):
    results = get_nodes(root, *matchers)
    if len(results) == 1:
        return results[0]
    else:
        return None

    