import generic
import logging
from base import *

class HasOnlyDataMembers(AllOf):
    def __init__(self):
        super(HasOnlyDataMembers, self).__init__([
            AllSatisfy(
                lambda e: e.methods,
                AllOf([
                    Forbidden(
                        lambda e: '{} is a method in a model definition'.format(e.name),
                        CheckStatus.WARNING
                    )
                ]),
                lambda e: '{} has {} method(s) in a model definition'.format(e.name, str(len(e.methods)))
            ),
            AdHocCheck(
                lambda e: len(e.members) > 0,
                lambda e: 'No members found in model definition of {} '.format(e.name),
                CheckStatus.WARNING
            )
        ])

class HasOnlyMethods(AllOf):
    def __init__(self):
        super(HasOnlyMethods, self).__init__([
            AllSatisfy(
                lambda e: e.members,
                AllOf([
                    Forbidden(
                        lambda e: '{} is a member in a viewmodel definition'.format(e.name),
                        CheckStatus.WARNING
                    )
                ]),
                lambda e: '{} has {} member(s) in a viewmodel definition'.format(e.name, str(len(e.members)))
            ),
            AdHocCheck(
                lambda e: len(e.methods) > 0,
                lambda e: 'No members found in viewmodel definition of {} '.format(e.name),
                CheckStatus.WARNING
            )
        ])

class IsSharedPtr(IsContainer):
    def __init__(self, pointed_type):
        super(IsSharedPtr, self).__init__(
            'std::shared_ptr', pointed_type
        )

class IsSparkHandle(IsContainer):
    def __init__(self, pointed_type):
        super(IsSparkHandle, self).__init__(
            'spark::handle', pointed_type
        )

class IsCreateInstance(SingleCheck):
    def predicate(self, e):
        return e.name == 'CreateInstance'

    def build_message(self, e):
        return '{} is not a CreateInstance factory method'.format(e.name)

class AllMembers(AllSatisfy):
    def __init__(self, validator: AbstractValidator):
        super(AllMembers, self).__init__(
            lambda e: e.members,
            validator,
            lambda e: '{} does not satisfy all member validators'.format(e.name)
        )

class AllMembersPublic(AllSatisfy):
    def __init__(self):
        super(AllMembersPublic, self).__init__(
            lambda e: e.members,
            IsPublic(),
            lambda e: 'All members of {} must be public'.format(e.name)
        )

class AllMethods(AllSatisfy):
    def __init__(self, validator: AbstractValidator):
        super(AllMethods, self).__init__(
            lambda e: e.methods,
            validator,
            lambda e: '{} does not satisfy all method validators'.format(e.name)
        )

class InheritsFromVMInterface(AbstractValidator):
    def satisfies(self, entity: generic.DefinedClass) -> ValidatorResult:
        has_vm_base = any(base.name == 'IViewModel' for base in entity.bases)
        return ValidatorResult(
            CheckStatus.OK if has_vm_base else CheckStatus.CRITICAL,
            [('{} does not inherit from IViewModel'.format(entity.name), entity.location)] if not has_vm_base else [],
            1)

class InheritsFromServiceInterface(AbstractValidator):
    def satisfies(self, entity):
        has_vm_base = any(base.name == 'IService' for base in entity.bases)
        return ValidatorResult(
            CheckStatus.OK if has_vm_base else CheckStatus.CRITICAL,
            [('{} does not inherit from IService'.format(entity.name), entity.location)] if not has_vm_base else [],
            1)

class CallbackOkIfExists(OneOf):
    def __init__(self):
        def get_bases(e): return [base.template_args[0] for base in e.bases if base.name == 'NotificationHelper']
        super(CallbackOkIfExists, self).__init__([
            AdHocCheck(
                lambda e: not get_bases(e),
                lambda _: 'One or more callback classes found'
            ),
            AllSatisfy(
                get_bases,
                CallbackClassifier(),
                lambda e: '{} is not an OK callback'.format(e.name)
            )]
        )

class CreateInstanceParamsOk(AllOfSC):
    def __init__(self):
        super(CreateInstanceParamsOk, self).__init__([
            AdHocCheck(
                lambda e: len(e.param_types) >= 1,
                lambda e: '{} needs to have at least one param (ICoreFramework)'.format(e.name),
                CheckStatus.WARNING
            ),
            AllOf([
                AllSatisfy(
                    lambda e: e.param_types,
                    AllOf([IsConst(), IsLvalueRef()]),
                    lambda e: 'All parameters of {} need to be const reference'.format(e.name)
                ),
                OneSatisfies(
                    lambda e: e.param_types,
                    AllOf([IsSparkHandle('ICoreFramework')]),
                    lambda e: '{} needs to have a parameter of type spark::handle<ICoreFramework>'.format(e.name)
                )
            ])
        ])

class HasCreateInstance(AllOfSC):
    def __init__(self):
        def name_ok(m):
            return m.name == 'CreateInstance'
        super(HasCreateInstance, self).__init__([
            AdHocCheck(
                lambda e: len([m for m in e.methods if name_ok(m)]) == 1,
                lambda _: 'There needs to be exactly one CreateInstance factory method declared',
                CheckStatus.WARNING
            ),
            AllOf([CreateInstanceParamsOk()], lambda e: [m for m in e.methods if name_ok(m)][0])
        ])

class IsExceptionToInitializationRule(SingleCheck):
    # exceptions are here because the initial value being a constexpr doesn't seem to be picked up in the processing
    def predicate(self, e):
        return e.name in ["sortPriority", "spaceParticipantCountGroupMentionsThreshold", "contentIndex", "imgWidth", "imgHeight"]

    def build_message(self, e):
        return f'{e.name} is not exempted from Initialized check'

class HasInitialValue(SingleCheck):
    def predicate(self, e):
        return e.init_value is not None

    def build_message(self, e):
        return f'{e.name} is missing an initial value'

class IsInitialized(OneOf):
    def __init__(self):
        super(IsInitialized, self).__init__([
            Not(IsPrimitive(), lambda e: f'{e.name} is a primitive field'),
            AllOf([IsPrimitive(), OneOf([IsReference(), IsPointer(), IsDouble()])]),
            AllOf([IsPrimitive(), OneOf([HasInitialValue(), IsExceptionToInitializationRule()])])
        ])
    
    def satisfies(self, entity) -> ValidatorResult:
        result = super().satisfies(entity)
        if result.status != CheckStatus.OK:
            # force a failure, not just a warning
            result.status = CheckStatus.CRITICAL
            for (error, location) in result.errors:
                logging.error(f'{error} at {location.filename}:{location.line}')
        return result

class CallbackClassifier(AllOf):
    def __init__(self):
        super(CallbackClassifier, self).__init__([
            HasOnlyMethods(),
            AllMethods(
                AllOf([IsPublic(), IsVirtual(), IsAbstract(), ReturnsVoid()]))
        ])

class ModelClassifier(AllOf):
    def __init__(self):
        super(ModelClassifier, self).__init__([
            HasOnlyDataMembers(),
            AllMembers(
                AllOf([IsPublic(), IsNotConst(), IsNotCharPtr(), IsInitialized()]),
            )
        ])

class ViewModelClassifier(AllOf):
    def __init__(self):
        super(ViewModelClassifier, self).__init__([
            InheritsFromVMInterface(),
            HasOnlyMethods(),
            HasCreateInstance(),
            AllMethods(
                OneOf([
                    IsCreateInstance(),
                    AllOf([IsPublic(), IsVirtual(), IsAbstract()])
                ])
            ),
            CallbackOkIfExists()
        ])

class ServiceClassifier(AllOf):
    def __init__(self):
        super(ServiceClassifier, self).__init__([
            InheritsFromServiceInterface(),
            HasOnlyMethods(),
            AllMethods(
                OneOf([
                    IsCreateInstance(),
                    AllOf([IsPublic(), IsVirtual(), IsAbstract()])
                   ])
            )
        ])

class EnumClassifier(AllOf):
    def __init__(self):
        super(EnumClassifier, self).__init__([
            AdHocCheck(lambda e: isinstance(e, generic.DefinedEnum),
                       lambda e: '{} is not an Enum'.format(e.name))])
        # TODO values need to start from 0 and be contiguous
