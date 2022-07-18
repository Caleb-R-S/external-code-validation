import sys
sys.path.append('../../commons')

from commons.taskinterface import ValidationTask, MissingLambdaInPipelineException, LamdaAWSNameTooLongException, UnableToParseYmlException
from commons.validation_tools import get_paths_to_lambdas_from_locals_file
from commons.validation_tools import generate_location
import re
import os
import hcl
import glob
import yaml


class IncorrectlyConfiguredEnvironmentVariables(Exception): pass


class EnvironmentVariableTask(ValidationTask):

    def print_start_message(self):
        print('Finding unused environment variables...')

    def perform_validation_task(self, dependencies):
        lambda_paths = dependencies['lambda_paths']
        terraform_dicts = dependencies['terraform_dicts']
        failed_lambdas = []


        module_path_to_code_path = get_paths_to_lambdas_from_locals_file()
        code_path_to_env_vars = get_code_path_to_env_vars(lambda_paths)
        module_path_to_env_vars = combine_dictionaries(module_path_to_code_path, code_path_to_env_vars)
        sources = generate_source_packages()

        for filename, tf_dict in terraform_dicts.items():
            if validation_object := validation_object_factory(tf_dict, module_path_to_env_vars, sources):
                    result = validation_object.execute()
                    if result:
                        failed_lambdas.append(result)

        return failed_lambdas


    def post_validation_task(self, result):
        print('------------------------------------------------------------------------')
        print('Environment Variables Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('\tSome environment variables are not being used!')
        print()
        print(f'These environment variables are set but not used:')
        for item in result: print(f'{item}\n')
        return IncorrectlyConfiguredEnvironmentVariables('Make sure environment variables are correctly set up.')


class EnvironmentVarVerification:
    def execute(self):
        # Not done yet
        return None


class SimpleVerificationAction:
    def __init__(self, hcl_dictionary, module_path_to_code_vars):
        self.hcl_dictionary = hcl_dictionary
        self.module_path_to_code_vars = module_path_to_code_vars

    def execute(self):
        module = self.hcl_dictionary['module']
        module_name = list(module.keys())[0]
        env_vars_dict = module[module_name].get('environment_variables')
        filename_path = module[module_name].get('filename')
        path = ''
        env_vars = set()

        if env_vars_dict:
            env_vars = set(env_vars_dict.keys())

        if filename_path:
            split = filename_path.split('.')
            prefix, path = split[0], split[1]
            if prefix != 'local':
                return None
                
            if env_vars == self.module_path_to_code_vars[path]:
                return None

        return f"\tMISMATCH: {module_name}\n" \
               f"Code:      \t{self.module_path_to_code_vars.get(path)}\n" \
               f"Terraform: \t{env_vars}"


class ErrorLoggingVerificationAction:
    def __init__(self, hcl_dictionary, module_path_to_code_vars, source):
        self.hcl_dictionary = hcl_dictionary
        self.module_path_to_code_vars = module_path_to_code_vars
        self.source = source

    def execute(self):
        env_vars = self.source['error-logging-lambda-sqs']['lambda-log-to-error-queue']
        module = self.hcl_dictionary['module']
        module_name = list(module.keys())[0]
        path = module[module_name]['lambda_path'].split('.')[1]

        if env_vars == self.module_path_to_code_vars[path]:
            return None
        else:
            return f"\tMISMATCH: {module_name}\n" \
                   f"Code:      \t{self.module_path_to_code_vars[path]}\n" \
                   f"Terraform: \t{env_vars}"


class ApiToStepFunctionVerificationAction:
    def __init__(self, hcl_dictionary, module_path_to_code_vars, source):
        self.hcl_dictionary = hcl_dictionary
        self.module_path_to_code_vars = module_path_to_code_vars
        self.source = source

    def execute(self):
        api_to_sqs_env_vars = self.source['api-to-step-function']['lambda-api-to-sqs']
        sqs_to_step_func_env_vars = self.source['api-to-step-function']['lambda-sqs-to-step-function']

        module = self.hcl_dictionary['module']
        module_name = list(module.keys())[0]
        api_to_sqs_path = module[module_name]['api_to_sqs_function_path'].split('.')[1]
        sqs_to_step_func_path = module[module_name]['sqs_to_lambda_function_path'].split('.')[1]

        if api_to_sqs_env_vars != self.module_path_to_code_vars[api_to_sqs_path]:
            return f"\tMISMATCH: {module_name} - Api To Sqs\n" \
                   f"Code:      \t{self.module_path_to_code_vars[api_to_sqs_path]}\n" \
                   f"Terraform: \t{api_to_sqs_env_vars}"

        if sqs_to_step_func_env_vars != self.module_path_to_code_vars[sqs_to_step_func_path]:
            return f"\tMISMATCH: {module_name} - Sqs To Step\n" \
                   f"Code:      \t{self.module_path_to_code_vars[sqs_to_step_func_path]}\n" \
                   f"Terraform: \t{sqs_to_step_func_env_vars}"
        return None


def validation_object_factory(hcl_dictionary, module_path_to_code_vars, source_dict):
    # Guard statements filter out the terraform files that aren't associated with a lambda.
    if (module := hcl_dictionary.get('module')) is None:
        return None
    if (module_name := list(module.keys())[0]) is None:
        return None
    if module[module_name].get('function_name') is None\
            and module[module_name].get('step_function_lambdas') is None \
            and module[module_name].get('lambda_name') is None:
        return None
    if (source := module[module_name].get('source')) is None:
        return None

    env_var_verification = EnvironmentVarVerification()
    if 'git' in source:
        env_var_verification.verify = SimpleVerificationAction(hcl_dictionary, module_path_to_code_vars)
    elif 'error-logging-lambda-sqs' in source:
        env_var_verification.verify = ErrorLoggingVerificationAction(hcl_dictionary, module_path_to_code_vars, source_dict)
    elif 'api-to-step-function' in source:
        env_var_verification.verify = ApiToStepFunctionVerificationAction(hcl_dictionary, module_path_to_code_vars, source_dict)
    else:
        assert True, 'Should not reach this point. Please make sure each source is handled by the factory.'

    return env_var_verification


def get_env_var_from_python_file(filepath):
    env_vars = set()
    with open(f'{filepath}') as file:
        lines = file.readlines()
        copy_line = False
        for line in lines:
            if (raw_var := re.search("getenv\((.*?)\)", line)):
                var = raw_var.group(1)
                var = var.replace('"', '')
                var = var.replace("'", '')
                env_vars.add(var)
    return env_vars


def get_code_path_to_env_vars(lambda_paths):
    dictionary = {}
    for path in lambda_paths:
        env_vars = get_env_var_from_python_file(f'{generate_location(3)}/lambdas/{path}/index.py')
        # TODO: his needs to be changed to source direct
        dictionary[f'lambdas/{path}/index.py'] = env_vars
    return dictionary


def combine_dictionaries(dict1, dict2):
    combined_dictionary = {}
    for key, value in dict1.items():
        combined_dictionary[key] = dict2[value]
    return combined_dictionary


def generate_source_packages():
    sources = {}
    path = f'{generate_location(3)}/terraform'
    sub_directories = [file.path for file in os.scandir(path) if file.is_dir()]
    for dir in sub_directories:
        sub_source = {}
        for filename in glob.glob(f'{dir}/*.tf'):
            with open(filename) as file:
                terraform_dict = hcl.load(file)
                if (env_vars := get_env_vars_from_tf(terraform_dict)) is not None:
                    key = filename.split(os.sep)[-1]
                    key = key.split('.')[0]
                    sub_source[key] = env_vars
        dir_name = dir.split('/')[-1]
        sources[dir_name] = sub_source

    return sources


def get_env_vars_from_tf(hcl_dictionary):
    if (module := hcl_dictionary.get('module')) is None:
        return None
    if (module_name := list(module.keys())[0]) is None:
        return None
    if (env_vars_dict := module[module_name].get('environment_variables')) is None:
        return None

    env_vars = set(env_vars_dict.keys())
    return env_vars


