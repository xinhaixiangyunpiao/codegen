from enum import Enum

# 抽象类型
class AbstractType(object):
    def __init__(self, name):
        self.name = name
        self.original_typedef = None

    def complete_name(self):
        pass

    def accept_printer(self, printer):
        pass

    def accept_visitor(self, visitor):
        raise Exception('This type should never be directly visited')

    def __str__(self):
        return self.complete_name()

# 得到全名
def cat_ns(namespace, name):
    return '::'.join([namespace, name]) if namespace else name    

# 原始类型
class PrimitiveType(AbstractType):
    def __init__(self, name):
        super(PrimitiveType, self).__init__(name)

    def complete_name(self):
        return self.name

    def accept_printer(self, printer):
        return printer.visit_primitive_type(self)

    def accept_visitor(self, visitor):
        return visitor.visit_primitive_type(self)

# 递归类型
class RecursiveType(AbstractType):
    def __init__(self, name, namespace):
        super(RecursiveType, self).__init__(name)
        self.namespace = namespace

    def complete_name(self):
        return cat_ns(self.namespace, self.name)

    def accept_printer(self, printer):
        return printer.visit_recursive_type(self)

    def accept_visitor(self, visitor):
        return visitor.visit_recursive_type(self)

# 枚举成员类型
class EnumConstant:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def accept_printer(self, printer):
        return printer.visit_enum_constant(self)

# location类型
class Location:
    def __init__(self, filename: str, line: str, column: str):
        self.filename = filename
        self.line = line
        self.column = column

# 枚举类型
class DefinedEnum(AbstractType):
    def __init__(self, name, namespace, constants, defined_in_header, location):
        super(DefinedEnum, self).__init__(name)
        self.namespace = namespace
        self.header = defined_in_header
        self.constants = constants
        self.location = location

    def complete_name(self):
        return cat_ns(self.namespace, self.name)

    def accept_printer(self, printer):
        return printer.visit_abstract_defined_enum(self)

    def accept_visitor(self, visitor):
        return visitor.visit_enum(self)

# 引用类型
class RefType(Enum):
    LVALUE = 1
    RVALUE = 2
    POINTER = 3

# 访问属性
class AccessSpecifier(Enum):
    PRIVATE = 1
    PROTECTED = 2
    PUBLIC = 3

# Api（类中的method）的特性类
class ApiTraits(object):
    def __init__(self, is_const, is_virtual, is_abstract, is_static, annotation=None):
        self.is_const = is_const
        self.is_virtual = is_virtual
        self.is_abstract = is_abstract
        self.is_static = is_static
        self.annotation = annotation

# Api（类中的方法类）类
class Api(object):
    def __init__(self, name, access_specifier, returns, param_types, traits, location):
        self.name = name
        self.access_specifier = access_specifier
        self.returns = returns
        self.param_types = param_types
        self.traits = traits
        self.location = location

    def accept_printer(self, printer):
        return printer.visit_abstract_api(self)

    def has_codegen_tag(self):
        return self.traits.annotation == 'generate_binds'

# Field类
class Field(object):
    def __init__(self, name, access_specifier, type_info, traits, init_value, location):
        self.name = name
        self.access_specifier = access_specifier
        self.type_info = type_info
        self.traits = traits
        self.init_value = init_value
        self.location = location

    def accept_printer(self, printer):
        return printer.visit_abstract_field(self)

# 函数参数类
class Param(object):
    def __init__(self, name, type_info, traits, location):
        self.name = name
        self.type_info = type_info
        self.traits = traits
        self.location = location

    def accept_printer(self, printer):
        return printer.visit_abstract_param(self)

# 函数返回值类
class ApiReturns(object):
    def __init__(self, type_info, traits):
        self.type_info = type_info
        self.traits = traits

    def accept_printer(self, printer):
        return printer.visit_api_return_type(self)

# Trait类
class TypeTraits(object):
    def __init__(self, is_const, ref_type):
        self.is_const = is_const
        self.ref_type = ref_type

# 类原型类
class DeclaredClass(AbstractType):
    def __init__(self, name, namespace, template_args, header):
        super(DeclaredClass, self).__init__(name)
        self.namespace = namespace
        self.header = header
        self.template_args = template_args

    def complete_name(self):
        full_name = cat_ns(self.namespace, self.name)
        if self.template_args:
            arg_name = self.template_args[0].complete_name()
            return full_name + '<' + (arg_name if arg_name else '') + '>'
        else:
            return full_name

    def accept_printer(self, printer):
        return printer.visit_abstract_declared_class(self)

    def accept_visitor(self, visitor):
        return visitor.visit_declared_class(self)

# 类类型
class DefinedClass(DeclaredClass):
    def __init__(self, name, namespace, template_args, members, methods, bases, defined_in_header, location, annotation=None):
        super(DefinedClass, self).__init__(name, namespace, template_args, defined_in_header)
        self.members = members
        self.methods = methods
        self.bases = bases
        self.location = location
        self.dependent_headers = None
        self.annotation = annotation

    def complete_name(self):
        return super(DefinedClass, self).complete_name()

    def accept_printer(self, printer):
        return printer.visit_abstract_defined_class(self)

    def accept_visitor(self, visitor):
        return visitor.visit_defined_class(self)
