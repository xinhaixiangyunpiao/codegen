import json
from abc import ABCMeta, abstractmethod
from collections import OrderedDict

import ch_cpp_types, ch_basic, generic

class AbstractPrinter:
    __metaclass__ = ABCMeta

    @abstractmethod
    def visit_type(self, type_info):
        pass

    @abstractmethod
    def visit_traits(self, traits):
        pass

    @abstractmethod
    def visit_field(self, field):
        pass

    @abstractmethod
    def visit_param(self, param):
        pass

    @abstractmethod
    def visit_model_struct(self, model):
        pass

    @abstractmethod
    def visit_enum_constant(self, constant):
        pass

    @abstractmethod
    def visit_model_enum(self, enum):
        pass

    @abstractmethod
    def visit_api(self, api):
        pass

    @abstractmethod
    def visit_api_return_type(self, art):
        pass

    @abstractmethod
    def visit_vm(self, vml):
        pass

    @abstractmethod
    def visit_callback(self, cb):
        pass

    @abstractmethod
    def visit_service(self, sv):
        pass

    @abstractmethod
    def visit_abstract_field(self, af):
        pass

    @abstractmethod
    def visit_abstract_defined_class(self, adc):
        pass

    @abstractmethod
    def visit_abstract_declared_class(self, adc):
        pass

    @abstractmethod
    def visit_abstract_param(self, ap):
        pass

    @abstractmethod
    def visit_abstract_api(self, aa):
        pass

    @abstractmethod
    def visit_primitive_type(self, pt):
        pass

    @abstractmethod
    def visit_abstract_defined_enum(self, en):
        pass

    @abstractmethod
    def visit_recursive_type(self, rt):
        pass


class JSONPrinter(AbstractPrinter):
    def visit_type(self, type_info):
        type_json = OrderedDict()
        type_json['type'] = str(type_info.full_name)

        if type_info.container_type:
            type_json['container'] = type_info.container_type

        traits_str = type_info.traits.accept_printer(self)
        if traits_str:
            type_json['traits'] = traits_str

        return type_json

    def visit_traits(self, traits):
        return ('const ' if traits.is_const else '') + ('&' if traits.is_reference else '')

    def visit_field(self, field):
        type_json = field.type_info.accept_printer(self)
        return {field.name: type_json}

    def visit_abstract_field(self, af):
        field_json = OrderedDict()
        type_json = af.type_info.accept_printer(self)
        field_json.update(type_json)
        field_json['access'] = str(af.access_specifier)

        return {af.name: field_json}

    def visit_abstract_param(self, ap):
        param_json = OrderedDict()
        type_json = ap.type_info.accept_printer(self)
        param_json.update(type_json)

        return {ap.name: param_json}

    def visit_api_return_type(self, art):
        param_json = OrderedDict()
        type_json = art.type_info.accept_printer(self)
        param_json.update(type_json)

        return param_json

    def visit_param(self, param):
        type_json = param.type_info.accept_printer(self)
        return {param.name: type_json}

    def visit_model_struct(self, model):
        model_json = OrderedDict()
        name = model.type_info.full_name
        model_json['model name'] = name
        model_json['def header'] = model.definition_header
        if model.base_model:
            model_json['base'] = model.base_model.type_info.full_name
        model_json['fields'] = OrderedDict()
        for field in model.fields:
            model_json['fields'].update(field.accept_printer(self))

        return json.dumps(model_json, indent=4, separators=(',', ': '))

    def visit_abstract_defined_class(self, adc):
        type_json = OrderedDict()
        type_json['name'] = adc.name

        if adc.namespace:
            type_json['namespace'] = adc.namespace

        if adc.header:
            type_json['defined in'] = adc.header

        if adc.template_args:
            t_args = []
            for ta in adc.template_args:
                t_args.append(ta.accept_printer(self))

            type_json['template args'] = t_args

        if adc.bases:
            b_clss = []
            for b in adc.bases:
                b_clss.append(b.accept_printer(self))
            type_json['base classes'] = b_clss

        if adc.members:
            type_json['fields'] = OrderedDict()
            for f in adc.members:
                type_json['fields'].update(f.accept_printer(self))

        if adc.methods:
            type_json['apis'] = OrderedDict()
            for a in adc.methods:
                type_json['apis'].update(a.accept_printer(self))

        return type_json

    def visit_abstract_declared_class(self, adc):
        type_json = OrderedDict()
        type_json['meta'] = 'declared only'
        type_json['name'] = adc.name
        if adc.namespace:
            type_json['namespace'] = adc.namespace
        if adc.header:
            type_json['defined in'] = adc.header

        if adc.template_args:
            t_args = []
            for ta in adc.template_args:
                t_args.append(ta.accept_printer(self))

            type_json['template args'] = t_args

        return type_json

    def visit_enum_constant(self, constant):
        return {constant.name: constant.value}

    def visit_model_enum(self, enum):
        enum_json = OrderedDict()
        name = enum.type_info.full_name
        enum_json['enum name'] = name
        enum_json['def header'] = enum.definition_header
        enum_json['constants'] = OrderedDict()
        for constant in enum.constants:
            enum_json['constants'].update(constant.accept_printer(self))

        return json.dumps(enum_json, indent=4, separators=(',', ': '))

    def visit_abstract_defined_enum(self, en):
        enum_json = OrderedDict()
        name = en.name
        enum_json['meta'] = 'enumeration'
        enum_json['name'] = name
        if en.namespace:
            enum_json['namespace'] = en.namespace
        enum_json['def header'] = en.header
        enum_json['constants'] = OrderedDict()
        for constant in en.constants:
            enum_json['constants'].update(constant.accept_printer(self))

        return enum_json

    def visit_api(self, api):
        param_types = OrderedDict()
        for param in api.param_types:
            param_types.update(param.accept_printer(self))

        vm_api = OrderedDict()
        vm_api.update({'returns': api.return_type.accept_printer(self)})
        vm_api.update({'params': param_types})
        vm_api.update({'access': str(api.access_specifier)})

        return {api.name: vm_api}

    def visit_abstract_api(self, aa):
        param_types = OrderedDict()
        for param in aa.param_types:
            param_types.update(param.accept_printer(self))

        abstract_api = OrderedDict()
        abstract_api.update({'returns': aa.returns.accept_printer(self)})
        abstract_api.update({'params': param_types})
        abstract_api.update({'access': str(aa.access_specifier)})

        return {aa.name: abstract_api}

    def visit_callback(self, cb):
        apis_json = OrderedDict()
        for api in cb.exposed_apis:
            apis_json.update(api.accept_printer(self))
        for api in cb.unexposed_apis:
            apis_json.update(api.accept_printer(self))

        return apis_json

    def visit_vm(self, vm):
        vm_json = OrderedDict()
        name = vm.type_info.full_name
        vm_json['viewmodel'] = name
        vm_json['def header'] = vm.definition_header
        if vm.base_vm:
            vm_json['base'] = vm.base_vm.type_info.full_name
        vm_json['apis'] = OrderedDict()
        for api in vm.exposed_apis:
            vm_json['apis'].update(api.accept_printer(self))
        if vm.callback:
            vm_json['callback apis'] = vm.callback.accept_printer(self)

        return json.dumps(vm_json, indent=4, separators=(',', ': '))

    def visit_service(self, sv):
        sv_json = OrderedDict()
        name = sv.type_info.full_name
        sv_json['service'] = name
        sv_json['def header'] = sv.definition_header
        sv_json['apis'] = OrderedDict()
        for api in sv.exposed_apis:
            sv_json['apis'].update(api.accept_printer(self))
        if sv.callback:
            sv_json['callback apis'] = sv.callback.accept_printer(self)

        return json.dumps(sv_json, indent=4, separators=(',', ': '))

    def visit_primitive_type(self, pt):
        return {'prim type': pt.name}

    def visit_recursive_type(self, rt):
        return {'meta': 'recursive',
                'type': {'name': rt.name, 'namespace': rt.namespace}}