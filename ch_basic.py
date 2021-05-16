import generic

# 初始化函数
def init(time_type = None):
    global platform_time_type
    if time_type is None:
        platform_time_type = 'time_t'
    else:
        platform_time_type = time_type

# 基本的特性类
class CHTypeTraits(object):
    def __init__(self, is_enum: bool = False, is_vector: bool = False, is_optional: bool = False,
                 is_shared_ptr: bool = False, is_const: bool = False, ref_type: generic.RefType = None):
        self.is_enum = is_enum
        self.is_vector = is_vector
        self.is_optional = is_optional
        self.is_shared_ptr = is_shared_ptr
        self.is_const = is_const
        self.ref_type = ref_type
        self.is_reference = self.ref_type == generic.RefType.LVALUE
        self.is_pointer = self.ref_type == generic.RefType.POINTER

    def has_any(self):
        return self.is_enum or self.is_vector or self.is_optional or self.is_const or self.ref_type is not None

    def accept_printer(self, printer):
        return printer.visit_traits(self)

# 基本的类型类
class CHType(object):
    def __init__(self, name, namespace, is_enum=False, is_const=False, ref_type=None, header_with_def=None, container_type=None, alias=None, init_value=None):
        self.name = name
        self.namespace = namespace
        self.alias = None
        self.container_type = None
        self.full_name = None
        self.set_alias(alias)
        self.set_container(container_type)
        self.set_full_name()
        self.header_with_def = header_with_def
        self.is_enum = is_enum
        self.init_value = init_value
        self.traits = None
        self.set_traits(is_const=is_const, ref_type=ref_type)

    def set_alias(self, alias):
        self.alias = alias
        self._process_time(self.alias)
        self.set_full_name()

    def set_full_name(self):
        self.full_name = self.namespace + '::' + self.name if self.namespace else self.name

    def set_container(self, full_container):
        self.container_type = full_container
        self._process_string(self.name, self.container_type)
        self.set_full_name()

    def set_traits(self, is_const, ref_type):
        is_vector = self.container_type == 'std::vector'
        is_optional = self.container_type == 'std::optional'
        is_shared_ptr = self.container_type == 'std::shared_ptr'
        self.traits = CHTypeTraits(is_enum=self.is_enum, is_vector=is_vector, is_optional=is_optional,
                                   is_shared_ptr=is_shared_ptr, is_const=is_const, ref_type=ref_type)

    def _process_string(self, name, container):
        if name == 'char' and (container == 'std::basic_string' or container == 'std::string'):
            self.name = 'string'
            self.namespace = 'std'
            self.container_type = None
        elif name == 'basic_string' and container == 'std::vector':
            self.name = 'string'
            self.namespace = 'std'
            self.container_type = 'std::vector'

        if name == 'wchar_t' and (container == 'std::basic_string' or container == 'std::wstring'):
            self.name = 'wstring'
            self.namespace = 'std'
            self.container_type = None

    def _process_time(self, alias):
        if alias and any(time_type in alias for time_type in ['spark::ms_time_t', 'spark::min_time_t']):
            self.name = platform_time_type

    def accept_printer(self, printer):
        return printer.visit_type(self)

# 基本的Field类
class CHField:
    def __init__(self, name, type_info, initial_value):
        self.name = name
        self.type_info = type_info
        self.initial_value = initial_value

    def accept_printer(self, printer):
        return printer.visit_field(self)

# 基本的参数类
class CHParam:
    def __init__(self, name, type_info):
        self.name = name
        self.type_info = type_info

    def accept_printer(self, printer):
        return printer.visit_param(self)

# 基本的函数类
class CHApi:
    def __init__(self, name, return_type, param_types, access_specifier, is_const=False, is_virtual=False, is_abstract=False, is_static=False):
        self.name = name
        self.return_type = return_type
        self.param_types = param_types
        self.access_specifier = access_specifier
        self.is_const = is_const
        self.is_virtual = is_virtual
        self.is_abstract = is_abstract
        self.is_static = is_static

    def accept_printer(self, printer):
        return printer.visit_api(self)

# 基本的回调函数类
class CHCallbackAPI(CHApi):
    pass

# 基本的回调类
class CHCallback:
    def __init__(self, type_info, exposed_apis, unexposed_apis=[]):
        self.type_info = type_info
        self.exposed_apis = exposed_apis
        self.unexposed_apis = unexposed_apis

    def accept_printer(self, printer):
        return printer.visit_callback(self)