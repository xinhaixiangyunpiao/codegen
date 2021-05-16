import functools
import generic

from abc import ABCMeta, abstractmethod
from typing import Tuple, List, Optional, Generator
from enum import Enum

class CheckStatus(Enum):
    OK = 1
    WARNING = 2
    CRITICAL = 3

def combine_statuses_and(s1: CheckStatus, s2: CheckStatus):
    if s1 == CheckStatus.CRITICAL or s2 == CheckStatus.CRITICAL:
        return CheckStatus.CRITICAL
    elif s1 == CheckStatus.WARNING or s2 == CheckStatus.WARNING:
        return CheckStatus.WARNING
    else:
        return CheckStatus.OK

def combine_statuses_or(s1: CheckStatus, s2: CheckStatus):
    if s1 == CheckStatus.OK or s2 == CheckStatus.OK:
        return CheckStatus.OK
    elif s1 == CheckStatus.WARNING or s2 == CheckStatus.WARNING:
        return CheckStatus.WARNING
    else:
        return CheckStatus.CRITICAL

class ValidatorResult(object):
    def __init__(self, success: CheckStatus, errors: List[Tuple[str, Optional[generic.Location]]], total_checks: int):
        self.status = success
        self.errors = errors
        self.total_checks = total_checks

class AbstractValidator:
    __metaclass__ = ABCMeta

    @abstractmethod
    def satisfies(self, entity) -> ValidatorResult:
        pass

def short_circuit_evaluator(validators, items, pred):
    for validator in validators:
        for item in items:
            result = validator.satisfies(item)
            yield result
            if pred(result):
                return

class AllSatisfy(AbstractValidator):
    def __init__(self, get_items, validator, build_message, short_circuit=False):
        self.get_items = get_items
        self.validator = validator
        self.build_message = build_message
        self.short_circuit = short_circuit

    def satisfies(self, entity) -> ValidatorResult:
        results = short_circuit_evaluator([self.validator], self.get_items(entity),
                                          (lambda r: r.status != CheckStatus.OK) if self.short_circuit
                                          else lambda _: False)
        final_val = combine_and(results)
        aggregate_errors = [] if final_val.status == CheckStatus.OK \
            else [(self.build_message(entity), entity.location)] + final_val.errors
        return ValidatorResult(
            final_val.status,
            aggregate_errors,
            final_val.total_checks)

def combine_and(results: Generator[ValidatorResult, None, None]) -> ValidatorResult:
    return functools.reduce(lambda x, y: ValidatorResult(combine_statuses_and(x.status, y.status),
                                                         x.errors + y.errors,
                                                         x.total_checks + y.total_checks),
                            results, ValidatorResult(CheckStatus.OK, [], 0))

def combine_or(results: List[ValidatorResult]):
    errors = []
    total_checks = 0
    status = CheckStatus.CRITICAL
    for res in results:
        if res.status == CheckStatus.OK:
            return ValidatorResult(CheckStatus.OK, [], res.total_checks)
        else:
            errors.extend(res.errors)
            total_checks += res.total_checks
            status = combine_statuses_or(status, res.status)
    return ValidatorResult(status, errors, total_checks)

class AllOf(AbstractValidator):
    def __init__(self, validators: List[AbstractValidator], get_item=lambda e: e, short_circuit=False):
        self.validators = validators
        self.get_item = get_item
        self.short_circuit = short_circuit
    def satisfies(self, entity) -> ValidatorResult:
        results = short_circuit_evaluator(self.validators, [self.get_item(entity)],
                                          (lambda r: r.status != CheckStatus.OK) if self.short_circuit
                                          else lambda _: False)
        return combine_and(results)

class AllOfSC(AllOf):
    def __init__(self, validators: List[AbstractValidator], get_item=lambda e: e):
        super(AllOfSC, self).__init__(validators, get_item, True)

class OneSatisfies(AbstractValidator):
    def __init__(self, get_items, validator, build_message):
        self.get_items = get_items
        self.validator = validator
        self.build_message = build_message

    def satisfies(self, entity) -> ValidatorResult:
        results = [self.validator.satisfies(entity) for entity in self.get_items(entity)]
        final_val = combine_or(results)
        aggregate_errors = [] if final_val.status == CheckStatus.OK \
            else [(self.build_message(entity), entity.location)] + final_val.errors
        return ValidatorResult(
            final_val.status,
            aggregate_errors,
            final_val.total_checks)

class OneOf(AbstractValidator):
    def __init__(self, validators: List[AbstractValidator], get_item=lambda e: e):
        self.validators = validators
        self.get_item = get_item

    def satisfies(self, entity) -> ValidatorResult:
        results = [validator.satisfies(self.get_item(entity)) for validator in self.validators]
        return combine_or(results)

class SingleCheck(AbstractValidator):
    def __init__(self, severity=CheckStatus.CRITICAL):
        self.severity = severity

    @abstractmethod
    def predicate(self, e):
        pass

    @abstractmethod
    def build_message(self, e):
        pass

    def satisfies(self, entity) -> ValidatorResult:
        if self.predicate(entity):
            return ValidatorResult(CheckStatus.OK, [], 1)
        else:
            return ValidatorResult(self.severity, [(self.build_message(entity), entity.location)], 1)

class AdHocCheck(SingleCheck):
    def __init__(self, predicate, build_msg, severity=CheckStatus.CRITICAL):
        super(AdHocCheck, self).__init__(severity)
        self.predicate = predicate
        self.build_msg = build_msg

    def predicate(self, e):
        return self.predicate(e)

    def build_message(self, e):
        return self.build_msg(e)

class Not(AbstractValidator):
    def __init__(self, validator: AbstractValidator, build_msg, severity=CheckStatus.CRITICAL):
        self.validator = validator
        self.build_message = build_msg
        self.severity = severity

    def satisfies(self, e):
        result = self.validator.satisfies(e)
        if result.status == CheckStatus.OK:
            return ValidatorResult(self.severity, [(self.build_message(e), e.location)], 1)
        else:
            return ValidatorResult(CheckStatus.OK, [], 1)

class Forbidden(SingleCheck):
    def __init__(self, build_msg, severity=CheckStatus.CRITICAL):
        super(Forbidden, self).__init__(severity)
        self.build_msg = build_msg

    def predicate(self, _):
        return False

    def build_message(self, e):
        return self.build_msg(e)


class IsPrimitive(SingleCheck):
    def predicate(self, e):
        return isinstance(e.type_info, generic.PrimitiveType)

    def build_message(self, e):
        return '{} is not a primitive type'.format(e.name)

class IsDouble(SingleCheck):
    def predicate(self, e):
        return e.type_info.name == "double"

    def build_message(self, e):
        return '{} is not a double'.format(e.name)

class IsPublic(SingleCheck):
    def predicate(self, e):
        return e.access_specifier == generic.AccessSpecifier.PUBLIC

    def build_message(self, e):
        return '{} is not public'.format(e.name)


class IsVirtual(SingleCheck):
    def predicate(self, e):
        return e.traits.is_virtual

    def build_message(self, e):
        return '{} is not virtual'.format(e.name)


class IsPointer(SingleCheck):
    def predicate(self, e):
        return e.traits.ref_type == generic.RefType.POINTER

    def build_message(self, e):
        return '{} is not pointer'.format(e.name)


class IsReference(SingleCheck):
    def predicate(self, e):
        return e.traits.ref_type is not None 

    def build_message(self, e):
        return '{} is not reference'.format(e.name)


class IsAbstract(SingleCheck):
    def __init__(self):
        super(IsAbstract, self).__init__(CheckStatus.WARNING)

    def predicate(self, e):
        return e.traits.is_abstract

    def build_message(self, e):
        return '{} is not abstract'.format(e.name)


class IsStaticMethod(SingleCheck):
    def __init__(self):
        super(IsStaticMethod, self).__init__(CheckStatus.WARNING)

    def predicate(self, e):
        return e.traits.is_static

    def build_message(self, e):
        return '{} is not static'.format(e.name)


class IsConst(SingleCheck):
    def __init__(self):
        super(IsConst, self).__init__(CheckStatus.WARNING)

    def predicate(self, e):
        return e.traits.is_const

    def build_message(self, e):
        return '{} is not const'.format(e.name)

class IsNotConst(SingleCheck):
    def __init__(self):
        super(IsNotConst, self).__init__(CheckStatus.WARNING)

    def predicate(self, e):
        return not e.traits.is_const

    def build_message(self, e):
        return '{} is const'.format(e.name)


class IsLvalueRef(SingleCheck):
    def __init__(self):
        super(IsLvalueRef, self).__init__(CheckStatus.WARNING)

    def predicate(self, e):
        return e.traits.ref_type == generic.RefType.LVALUE

    def build_message(self, e):
        return '{} is not an lvalue reference'.format(e.name)


class ReturnsVoid(SingleCheck):
    def __init__(self):
        super(ReturnsVoid, self).__init__(CheckStatus.WARNING)

    def predicate(self, e):
        return e.returns.type_info.name == 'void'

    def build_message(self, e):
        return '{} does not have a void return type'.format(e.name)


class IsNotCharPtr(AbstractValidator):
    def satisfies(self, entity: generic.DefinedClass) -> ValidatorResult:
        is_char = True if hasattr(entity.type_info, 'name') and entity.type_info.name == 'char' else False
        is_ptr  = True if hasattr(entity.traits, 'ref_type') and entity.traits.ref_type == generic.RefType.POINTER else False
        return ValidatorResult(
            CheckStatus.CRITICAL if is_char and is_ptr else CheckStatus.OK,
            [('char* is not a supported type for member \'{}\''.format(entity.name), entity.location)] if is_char and is_ptr else [],
            1)


class IsContainer(AbstractValidator):
    def __init__(self, container_type, pointed_type):
        self.container_type = container_type
        self.pointed_type = pointed_type

    @staticmethod
    def make_full_name(type_info):
        return '::'.join([type_info.namespace, type_info.name]) \
            if hasattr(type_info, 'namespace') and type_info.namespace else type_info.name

    def satisfies(self, entity) -> ValidatorResult:  # TODO rewrite
        if not self.make_full_name(entity.type_info) == self.container_type:
            return ValidatorResult(
                CheckStatus.WARNING,
                [('{} is not of type {}'.format(entity.name, self.container_type), entity.location)],
                1)

        if not (len(entity.type_info.template_args) == 1
                and entity.type_info.template_args[0].name == self.pointed_type):
            return ValidatorResult(
                CheckStatus.WARNING,
                [('{} is not a {} to {}'.format(entity.name, self.container_type, self.pointed_type), entity.location)],
                2)

        return ValidatorResult(CheckStatus.OK, [], 2)