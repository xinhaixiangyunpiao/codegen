from abc import ABCMeta, abstractmethod
from typing import List

import generic, ch_basic, ch_cpp_types
import utils

class AbstractGenericTypesVisitor:
    __metaclass__ = ABCMeta

    @abstractmethod
    def visit_abstract_type(self, at):
        pass

    @abstractmethod
    def visit_primitive_type(self, pt):
        pass

    @abstractmethod
    def visit_recursive_type(self, rt):
        pass

    @abstractmethod
    def visit_declared_class(self, dcc):
        pass

    @abstractmethod
    def visit_defined_class(self, dfc):
        pass

    @abstractmethod
    def visit_enum(self, en: generic.DefinedEnum):
        pass

class CHTypeConvertor(AbstractGenericTypesVisitor):
    def visit_abstract_type(self, at: generic.AbstractType):
        raise Exception('Nothing should be of this type')

    def visit_primitive_type(self, pt: generic.PrimitiveType):
        return ch_basic.CHType(name=pt.name, namespace=None, is_enum=False, is_const=False, ref_type=None,
                               header_with_def=None, container_type=None, alias=pt.original_typedef)

    def visit_recursive_type(self, rt: generic.RecursiveType):
        return ch_basic.CHType(name=rt.name, namespace=rt.namespace, is_enum=False, is_const=False, ref_type=None,
                               header_with_def=None, container_type=None, alias=rt.original_typedef)

    def visit_declared_class(self, dcc: generic.DeclaredClass):
        if dcc.template_args:
            fst_tmpl_arg = dcc.template_args[0]
            type_info = fst_tmpl_arg.accept_visitor(self)
            type_info.set_container(utils.create_full_container(dcc.name, dcc.namespace))
        else:
            type_info = ch_basic.CHType(name=dcc.name, namespace=dcc.namespace,
                                        is_enum=False, is_const=False, ref_type=None, header_with_def=dcc.header,
                                        container_type=None)

        if dcc.original_typedef:
            type_info.set_alias(dcc.original_typedef)

        return type_info

    def visit_defined_class(self, dfc):
        return self.visit_declared_class(dfc)

    def visit_enum(self, en):
        return ch_basic.CHType(name=en.name, namespace=en.namespace, is_enum=True, is_const=False, ref_type=None,
                               header_with_def=en.header, container_type=None)

def make_ch_model(adc):
    type_info = adc.accept_visitor(CHTypeConvertor())
    base_model = make_ch_model(adc.bases[0]) if adc.bases else None
    fields = [make_ch_field(member) for member in adc.members]
    return ch_cpp_types.ModelStruct(type_info=type_info, own_fields=fields,
                                    definition_header=adc.header, base_model=base_model)

def make_ch_field(af):
    type_info = af.type_info.accept_visitor(CHTypeConvertor())
    type_info.init_value = af.init_value
    type_info.set_traits(is_const=af.traits.is_const, ref_type=af.traits.ref_type)
    return ch_basic.CHField(name=af.name, type_info=type_info, initial_value=af.init_value)

def make_ch_callback(nh, check_annotation=False):
    type_info = nh.accept_visitor(CHTypeConvertor())
    if check_annotation:
        exposed_apis = [make_ch_callback_api(m) for m in nh.methods if m.has_codegen_tag()]
        unexposed_apis = [make_ch_callback_api(m) for m in nh.methods if not m.has_codegen_tag()]
    else:
        exposed_apis = [make_ch_callback_api(m) for m in nh.methods]
        unexposed_apis = []
    return ch_basic.CHCallback(type_info, exposed_apis, unexposed_apis)

def make_ch_callback_api(aa):
    api = make_ch_api(aa)
    return ch_basic.CHCallbackAPI(api.name, api.return_type, api.param_types, api.access_specifier,
                                  api.is_const, api.is_virtual, api.is_abstract)

def get_callback_class(base):
    return base.template_args[0]

def make_ch_viewmodel(adc):
    type_info = adc.accept_visitor(CHTypeConvertor())
    base_vm = None

    callback = None
    for b in adc.bases:
        if b.name == 'NotificationHelper':
            callback = make_ch_callback(get_callback_class(b))
        elif not base_vm:
            base_vm = make_ch_viewmodel(b)

    apis = [make_ch_api(m) for m in adc.methods]
    return ch_cpp_types.ViewModel(type_info=type_info, definition_header=adc.header, base_vm=base_vm, exposed_apis=apis,
                                  callback=callback)

def make_ch_api(aa):
    return_type_info = aa.returns.type_info.accept_visitor(CHTypeConvertor())
    return_type_info.set_traits(is_const=aa.returns.traits.is_const, ref_type=aa.returns.traits.ref_type)

    params = [make_ch_param(param) for param in aa.param_types]
    return ch_basic.CHApi(name=aa.name, return_type=return_type_info, param_types=params,
                          access_specifier=aa.access_specifier, is_const=aa.traits.is_const,
                          is_virtual=aa.traits.is_virtual, is_abstract=aa.traits.is_abstract,
                          is_static=aa.traits.is_static)

def make_ch_param(ap):
    type_info = ap.type_info.accept_visitor(CHTypeConvertor())
    type_info.set_traits(is_const=ap.traits.is_const, ref_type=ap.traits.ref_type)
    return ch_basic.CHParam(name=ap.name, type_info=type_info)

def make_scf_service(adc):
    type_info = adc.accept_visitor(CHTypeConvertor())
    apis = [make_ch_api(m) for m in adc.methods if m.has_codegen_tag()]

    callback = None
    for b in adc.bases:
        if b.name == 'NotificationHelper':
            callback = make_ch_callback(get_callback_class(b), True)

    return ch_cpp_types.SCFService(type_info=type_info, exposed_apis=apis,
                                   definition_header=adc.header, callback=callback)

def make_enum(ade):
    type_info = ade.accept_visitor(CHTypeConvertor())
    constants = [generic.EnumConstant(cs.name, cs.value) for cs in ade.constants]
    return ch_cpp_types.ModelEnum(type_info=type_info, constants=constants, definition_header=ade.header)
