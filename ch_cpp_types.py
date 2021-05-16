from typing import List
import generic, ch_basic

# 处理model
def process_model(model):
    base_model_header = model.base_model.type_info.header_with_def if model.base_model else None
    ret_val = set.union(
        {header for header in [field.type_info.header_with_def for field in model.fields if field.type_info] if header}
        , {base_model_header} if base_model_header else {}
    )
    if model.definition_header in ret_val:
        ret_val.remove(model.definition_header)
    return ret_val

# 处理viewmodel的方法
def _process_viewmodel_api(api):
    return_type_header = api.return_type.header_with_def
    return set.union(
        {header for header in [param.type_info.header_with_def for param in api.param_types] if header}
        , {return_type_header} if return_type_header else {}
    )

# 处理viewmodel
def process_viewmodel(viewmodel):
    if viewmodel.exposed_apis:
        ret_val = set.union(*[_process_viewmodel_api(api) for api in viewmodel.exposed_apis])
        if viewmodel.definition_header in ret_val:
            ret_val.remove(viewmodel.definition_header)
        return ret_val
    else:
        return set()

# Struct类
class ModelStruct:
    def __init__(self, type_info, own_fields, definition_header, base_model=None):
        self.type_info = type_info
        self.base_model = base_model
        self.own_fields = own_fields
        self.derived_fields = self._get_derived_fields()
        self.fields = self.own_fields + self.derived_fields
        self.definition_header = definition_header
        self.dependent_headers = process_model(self)

    def _get_derived_fields_impl(self, base_model):
        return base_model.own_fields + self._get_derived_fields_impl(base_model.base_model) if base_model else []

    def _get_derived_fields(self):
        return self._get_derived_fields_impl(self.base_model)

    def accept_printer(self, printer):
        return printer.visit_model_struct(self)

    @classmethod
    def simple(cls, type_info, fields, definition_header):
        return cls(type_info, fields, definition_header)

    @classmethod
    def with_base(cls, type_info, fields, definition_header, base):
        return cls(type_info, fields, definition_header, base)

# Enum类
class ModelEnum:
    def __init__(self, type_info, constants, definition_header):
        self.type_info = type_info
        self.constants = constants
        self.definition_header = definition_header

    def accept_printer(self, printer):
        return printer.visit_model_enum(self)

# ViewModel类
class ViewModel:
    def __init__(self, type_info, exposed_apis, callback, base_vm, definition_header):
        self.type_info = type_info
        self.exposed_apis = exposed_apis
        self.base_vm = base_vm
        self.callback = callback
        self.definition_header = definition_header
        self.dependent_headers = process_viewmodel(self)

    def accept_printer(self, printer):
        return printer.visit_vm(self)

# SCFService类
class SCFService:
    def __init__(self, type_info, exposed_apis, definition_header, callback):
        self.type_info = type_info
        self.exposed_apis = exposed_apis
        self.definition_header = definition_header
        self.callback = callback

    def accept_printer(self, printer):
        return printer.visit_service(self)
