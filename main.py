import pathlib
import logging
import printers

from parsers import parse

# 得到文件的完整路径，输入一个文件列表，返回一个绝对路径列表
def _get_full_path(paths):
    return [x if pathlib.PurePath(x).is_absolute() else str(pathlib.Path(x).resolve()) for x in paths]

# 配置logging
logging.basicConfig(format = '%(levelname)s: %(module)s: %(lineno)s -- %(message)s', level = logging.WARNING)

# 所有需要解释的头文件名称
input_headers = ["./src/service/Service.h","./src/viewmodel/ITestViewModel.h", \
                 "./src/viewmodel/TestViewModel/TestModel.h","./src/viewmodel/TestViewModel/TestViewModel.h"]

# 得到所有头文件的绝对路径
full_paths = _get_full_path(input_headers)
print(str(pathlib.Path(input_headers[0]).resolve()))

# clang动态链接库的路径
libclang_path = r""

# stl的头文件路径
stl_headers = r""

# C头文件路径
c_headers = r""

# 其他宏
target_macros = []

# 头文件所在路径
header_paths = [r"./src/service", r"./src/viewmodel", r"./src/viewmodel/TestViewModel"]

# 将所有文件的实体解析出来
models, enums, viewmodels, services = parse(full_paths, libclang_path, stl_headers, c_headers, target_macros, header_paths)

# 打印解析出来的个数
print('Parsed'
        + (' models: %d' % len(models) if len(models) else '')
        + (' enums: %d' % len(enums) if len(enums) else '')
        + (' viewmodels: %d' % len(viewmodels) if len(viewmodels) else '')
        + (' services: %d' % len(services) if len(services) else ''))

# 打印model详细信息
for model in models:
    print(model.accept_printer(printers.JSONPrinter()))
for viewmodel in viewmodels:
    print(viewmodel.accept_printer(printers.JSONPrinter()))
for enum in enums:
    print(enum.accept_printer(printers.JSONPrinter()))
for service in services:
    print(service.accept_printer(printers.JSONPrinter()))
