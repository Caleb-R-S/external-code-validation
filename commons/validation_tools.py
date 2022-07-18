import re
from pathlib2 import Path
from pathlib2 import Path
import os
import hcl
import re
import json
import yaml

class CouldNotFindOrReadFile(Exception): pass

def generate_location(index):
    return str(Path(__file__).parents[index])

def get_main_yaml_vars():
    with open(generate_location(2) + '/configs/main.yaml') as file:
        yaml_dict = yaml.safe_load(file)
        return yaml_dict

def get_tf_module(tf_dict):
    module = tf_dict.get('module')
    if not module:
        return {}
    
    module_name = list(module.keys())[0]

    module_dict = module.get(module_name)
    if module_dict:
        return module_dict
    else:
        return {}

def is_step_function(tf_module):
    if tf_module.get('step_function_definition'):
        return True
    return False

def get_list_of_lambda_paths():
    lambda_paths = []
    for (dirpath, dirnames, filenames) in os.walk(generate_location(3) + get_main_yaml_vars()['path_to_lambdas']):
        if os.path.exists(dirpath +"/index.py"):
            lambda_paths.append(dirpath.split("lambdas" + os.sep)[1])
    return lambda_paths

def get_dict_of_terraform_dicts():
    terraform_dicts = {}
    location = generate_location(3)
    terraform_path = '/terraform'
    for (dirpath, dirnames, filenames) in os.walk(location + terraform_path):
        for name in filenames:
            tf_filepath = os.path.join(dirpath, name)
            if tf_filepath.endswith('.tf'):
                with open(tf_filepath) as file:
                    terraform_dicts[name] = hcl.load(file)
    return terraform_dicts


def get_paths_to_lambdas_from_locals_file() -> dict:
    name_to_path = {}
    try:
        with open(f'{generate_location(3)}/terraform/locals.tf') as file:
            terraform_dict = hcl.load(file)
            locals_dict = terraform_dict['locals']
            for key, value in locals_dict.items():
                if key.split('_')[-1] == 'path':
                    unparsed_path = re.search("/lambdas/(.*?).zip", value).group(1)
                    unparsed_path = unparsed_path.split('/')
                    unparsed_path.pop()
                    path = 'lambdas/'
                    for string in unparsed_path:
                        path += (string + '/')
                    path += 'index.py'

                    if path:
                        name_to_path[key] = path

    except:
        raise CouldNotFindOrReadFile('Could Not Read Locals File')

    return name_to_path


def make_module_name_to_lambda_path_dict():
    path_dict = {}
    try:
        for filename in os.listdir(f'{generate_location(3)}/terraform'):
            filepath = os.path.join(f'{generate_location(3)}/terraform', filename)
            if os.path.isfile(filepath) and filename.split('-')[0] == 'lambda':
                with open(filepath) as file:
                    terraform_dict = hcl.load(file)
                    module_name = list(terraform_dict['module'].keys())[0]
                    unparsed_path = terraform_dict['module'][module_name]['filename']
                    path = unparsed_path.split('.')[1]

                    path_dict[module_name] = path
    except:
        raise CouldNotFindOrReadFile('Could not find or read terraform directory')
    return path_dict


def get_lambda_handler_from_file(filepath):
    lambda_handler = []
    try:
        with open(f'{generate_location(3)}/{filepath}') as file:
            lines = file.readlines()
            copy_line = False
            for line in lines:
                if copy_line is False and 'def lambda_handler(' in line:
                    copy_line = True
                elif copy_line is True and len(line) > 0 and line[0].isalpha():
                    return lambda_handler

                if copy_line:
                    line = line.strip()
                    lambda_handler.append(line)
    except:
        raise CouldNotFindOrReadFile('Could not read python file.')
    return lambda_handler


class StepFunction:
    def __init__(self, filename, tf_module, ignore_generics=True):
        self.filename = filename
        self.function_text = tf_module['step_function_definition']
        self.lambda_permissions = self.__extract_lambda_permissions(tf_module)
        self.subroutine_permissions = self.__extract_subroutine_permissions(tf_module)
        self.lambdas_used, self.subroutines_used = self.__extract_used_lambdas_and_subroutines(self.function_text)

        self.ignore_generics = ignore_generics
        self.is_generic = self.check_if_generic(self.function_text)



    def __extract_lambda_permissions(self, tf_module):
        lambda_permissions = set()

        step_function_lambdas = tf_module.get('step_function_lambdas')
        step_function_lambda_arns = tf_module.get('step_function_lambda_arns')

        if step_function_lambdas is None:
            step_function_lambdas = []
        if step_function_lambda_arns is None:
            step_function_lambda_arns = []

        for permission in step_function_lambdas:
            module, name, type = permission.split('.')
            lambda_permissions.add(name)
        for permission in step_function_lambda_arns:
            module, name, type = permission.split('.')
            lambda_permissions.add(name)

        return lambda_permissions

    def __extract_subroutine_permissions(self, tf_module):
        subroutine_permissions = set()

        subroutine_arns = tf_module.get('step_function_subroutine_arns')
        if subroutine_arns:
            for permission in subroutine_arns:
                module, name, type = permission.split('.')
                subroutine_permissions.add(name)
        

        return subroutine_permissions

    def __extract_used_lambdas_and_subroutines(self, function_text):
        lambdas_used = set()
        subroutines_used = set()

        lines = function_text.split('\n')
        for line in lines:
            lambda_results = re.search("module.(.*?).function_name", line)
            if lambda_results:
                lambdas_used.add(lambda_results.group(1))
            subroutine_result = re.search("module.(.*?).step_function_arn", line)
            if subroutine_result:
                subroutines_used.add(subroutine_result.group(1))
        return (lambdas_used, subroutines_used)

    def check_if_generic(self, function_text):
        lines = function_text.split('\n')
        for line in lines:
            if "FunctionName.$" in line:
                return True
        return False
    
    def generate_unused_permission_message(self):
        message = ''

        if self.ignore_generics and self.is_generic:
            return message

        unused_lambdas = self.lambda_permissions - self.lambdas_used
        unused_subroutines = self.subroutine_permissions - self.subroutines_used

        if unused_lambdas or unused_subroutines:
            message += f'\nFile: {self.filename}'

        if unused_lambdas:
            message += f'\nNot Using These Lambda Permissions:'
            for permission in unused_lambdas:
                message += f'\n\t{permission}'

        if unused_subroutines:
            message += f'\nNot Using These Subroutines Permissions:'
            for permission in unused_subroutines:
                message += f'\n\t{permission}'

        return message

    def generate_lambdas_used_without_permission_message(self):
        message = ''

        lambdas_without_permission = self.lambdas_used - self.lambda_permissions
        subroutines_without_permission = self.subroutines_used - self.subroutine_permissions

        if lambdas_without_permission or subroutines_without_permission:
            message += f'\nFile: {self.filename}'

        if lambdas_without_permission:
            message += f'\nLambdas used without permission:'
            for permission in lambdas_without_permission:
                message += f'\n\t{permission}'

        if subroutines_without_permission:
            message += f'\nSubroutines used without permission:'
            for permission in subroutines_without_permission:
                message += f'\n\t{permission}'

        return message

    def generate_invalid_json_message(self):
        message = ''

        try:
            json.loads(self.function_text)
        except ValueError as error:
            message += f'\nFile: {self.filename}'
            message += f'\nInvalid JSON detected'
            message += f'\n{error}'

        return message
