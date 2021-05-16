import abstract_entity
import classifiers
import logging
import functools
import os

from enum import Enum

# 提取实体的类别
class MetaClass(Enum):
    MODEL = 1
    VIEWMODEL = 2
    ENUMERATION = 3
    SERVICE = 4
    UNKNOWN = 5
    UNUSED = 6

# 得到错误率
def _get_fail_rate(classification):
    return len(classification.errors) / float(classification.total_checks)

# 得到location信息
def _get_location_info(location_info):
    if not location_info:
        return ''
    path = os.path.relpath(location_info.filename, os.path.join(os.path.dirname(__file__), '../..'))
    return "{}:{}:{}: ".format(path, location_info.line, location_info.column)

# 根据location信息分组
def group_by_location(acc, elem):
    def new_entry(e): return [e[0]], e[1]
    if len(acc) == 0 or acc[-1][1] != elem[1]:
        acc.append(new_entry(elem))
    else:
        acc[-1][0].append(elem[0])
    return acc

# 打印错误列表
def _print_errors_list(errors_list):
    for errors, loc in functools.reduce(group_by_location, errors_list, []):
        for error in errors:
            logging.info('  %s%s', _get_location_info(loc), error)

# 打印实体信息
def _print_entity_info(entity, metaclass, errors_list):
    logging.info('Composing %s as %s', entity, metaclass)
    _print_errors_list(errors_list)

# 比较实体更接近MODEL还是更接近VIEWMODEL
def _handle_non_matching_entity(generic_entity, model_classification, viewmodel_classification, warnings_allowed, suppress_errors):
    model_fail_rate = _get_fail_rate(model_classification)
    viewmodel_fail_rate = _get_fail_rate(viewmodel_classification)
    logging.debug('Fail rates for model: %s viewmodel: %s', model_fail_rate, viewmodel_fail_rate)

    if model_fail_rate > viewmodel_fail_rate:
        errors_list = viewmodel_classification.errors
        if warnings_allowed and viewmodel_classification.status == classifiers.CheckStatus.WARNING:
            _print_entity_info(generic_entity, 'VIEWMODEL', errors_list if not suppress_errors else [])
            return MetaClass.VIEWMODEL
    else:
        errors_list = model_classification.errors
        if warnings_allowed and model_classification.status == classifiers.CheckStatus.WARNING:
            _print_entity_info(generic_entity, 'MODEL', errors_list if not suppress_errors else [])
            return MetaClass.MODEL

    _print_entity_info(generic_entity, 'UNCLASSIFIED', errors_list if not suppress_errors else [])
    return MetaClass.UNKNOWN

# 从节点中提取实体信息
def get_entity_from_node(node, tu, scf_path, warnings_allowed=True, suppress_errors=False):
    # 提取实体信息
    generic_entity = abstract_entity.from_node(node, tu, scf_path)

    # 判断实体是否满足ENUMERATION
    enum_classification = classifiers.EnumClassifier().satisfies(generic_entity)
    if enum_classification.status == classifiers.CheckStatus.OK:
        logging.info('Composing %s as ENUMERATION', generic_entity)
        return generic_entity, MetaClass.ENUMERATION

    # 判断实体是否满足MODEL
    model_classification = classifiers.ModelClassifier().satisfies(generic_entity)
    if model_classification.status == classifiers.CheckStatus.OK:
        logging.info('Composing %s as MODEL', generic_entity)
        return generic_entity, MetaClass.MODEL

    # 判断实体是否满足VIEWMODEL
    viewmodel_classification = classifiers.ViewModelClassifier().satisfies(generic_entity)
    if viewmodel_classification.status == classifiers.CheckStatus.OK:
        logging.info('Composing %s as VIEWMODEL', generic_entity)
        return generic_entity, MetaClass.VIEWMODEL

    # 判断实体是否满足SERVICE
    service_classification = classifiers.ServiceClassifier().satisfies(generic_entity)
    if service_classification.status == classifiers.CheckStatus.OK:
        logging.info('Composing %s as SERVICE', generic_entity)
        return generic_entity, MetaClass.SERVICE

    # 判断实体是否满足回调类UNUSED，未用到
    callback_classification = classifiers.CallbackClassifier().satisfies(generic_entity)
    if callback_classification.status == classifiers.CheckStatus.OK:
        logging.info('Composing %s as CALLBACK, ignoring', generic_entity)
        return generic_entity, MetaClass.UNUSED

    # 判断实体更接近MODEL还是VIEWMODEL，都不满足则会UNKNOW
    entity_class = _handle_non_matching_entity(generic_entity, model_classification, viewmodel_classification,
                                               warnings_allowed, suppress_errors)
    return generic_entity, entity_class

