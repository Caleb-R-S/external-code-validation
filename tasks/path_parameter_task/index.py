import sys
sys.path.append('../../commons')

from commons.taskinterface import ValidationTask
from commons.validation_tools import get_paths_to_lambdas_from_locals_file, make_module_name_to_lambda_path_dict, get_lambda_handler_from_file
from commons.validation_tools import generate_location
import re
import os
import hcl


class CouldNotFindOrReadFile(Exception): pass
class CouldNotReadPathParameterConstantFile(Exception): pass
class PathParametersDoNotMatch(Exception): pass


class PathParameterTask(ValidationTask):
    def print_start_message(self):
        print('Checking if path parameters in lambda match parameters in api-gateway...')

    def perform_validation_task(self, dependencies: [str]) -> []:
        lambda_paths = dependencies['lambda_paths']

        paths_to_lambdas_dict = get_paths_to_lambdas_from_locals_file()
        path_parameter_constants_dict = get_path_parameter_constants()
        lambda_verification_objects = get_api_gateway_routes()
        module_name_to_locals_path = make_module_name_to_lambda_path_dict()

        # lambda_verification_objects are modified in below 2 functions
        link_verification_object_to_python_file(lambda_verification_objects, module_name_to_locals_path, paths_to_lambdas_dict)
        set_lambda_handler_parameters(lambda_verification_objects, path_parameter_constants_dict)

        mismatches = verify_parameters_match(lambda_verification_objects)

        return mismatches

    def post_validation_task(self, result: [str]) -> Exception:
        print('------------------------------------------------------------------------')
        print('Path Parameter Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('\tPath Parameters in api-gateway.tf do not match path parameters in lambdas.')
        print()
        print(f'These lambdas path parameters do not match')
        for item in result: print(f'\t{item}')

        return PathParametersDoNotMatch('Some path parameters in api-gateway.tf do not match path parameters in lambdas.')




class LambdaVerificationObject:
    api_path_parameters = set()
    handler_path_parameters = set()
    module_name = ''
    path_to_lambda = ''

    def __init__(self, name, parameters):
        self.module_name = name
        self.api_path_parameters = parameters


    def __repr__(self):
        return f'\nModule Name: {self.module_name}\n' \
               f'Path to Lambda: {self.path_to_lambda}\n' \
               f'Api Path Params: {self.api_path_parameters}\n' \
               f'Handler Path Params: {self.handler_path_parameters}' \
               f'\n'

def get_path_parameter_constants():
    path_parameters = {}
    try:
        with open(f'{generate_location(3)}/lambdas/msadm/constants/path_parameters.py') as file:
            lines = file.readlines()
            for line in lines:
                split_line = line.split('=')
                if len(split_line) == 2:
                    key = split_line[0].strip()
                    value = split_line[1].strip()
                    value = re.search('"(.*?)"', value).group(1)
                    path_parameters[key] = value
    except:
        raise CouldNotFindOrReadFile('Could not find or read msadm/constants/path_parameters.py')
    return path_parameters


def get_api_gateway_routes():
    data = []
    try:
        with open(f'{generate_location(3)}/terraform/api-gateway.tf') as file:
            terraform_dict = hcl.load(file)
            list_of_routes = terraform_dict['module']['simple-rest-lambda']['routes']
            for route in list_of_routes:
                module_name = re.search("module.(.*?).lambda_arn", route['lambda_arn']).group(1)
                path_params = set(re.findall("{(.*?)}", route['path']))

                if 'api_to_step' not in module_name:
                    data.append(LambdaVerificationObject(module_name, path_params))
    except:
        raise CouldNotFindOrReadFile('Could not find or read api-gateway.tf')
    return data


def link_verification_object_to_python_file(verification_objects, module_name_to_locals_name, locals_name_to_path):
    for item in verification_objects:
        locals_name = module_name_to_locals_name.get(item.module_name)
        filepath = locals_name_to_path.get(locals_name)
        item.path_to_lambda = filepath


def set_lambda_handler_parameters(config_data_list, constants_dict):
    for item in config_data_list:
        lambda_handler = get_lambda_handler_from_file(item.path_to_lambda)
        path_params_as_constants = get_path_parameters_from_lambda_handler(lambda_handler)
        item.handler_path_parameters = set(get_parameter_values(constants_dict, path_params_as_constants))


def get_path_parameters_from_lambda_handler(lambda_list):
    parameters = []

    for string in lambda_list:
        if 'path_parameters.' in string:
            raw_parameters = re.findall("event(.*?)\)", string)

            for raw_parameter in raw_parameters:
                parameter = ''

                if 'path_parameters.' in raw_parameter:
                    raw_parameter += ')'
                    parameter = re.search("path_parameters.(.*?)\)", raw_parameter).group(1)
                else:
                    raw_parameter = raw_parameter.replace(',', '')
                    raw_parameter = raw_parameter.replace('"', '')
                    parameter = raw_parameter.strip()

                parameters.append(parameter)
    return parameters


def get_parameter_values(constant_dictionary, parameters):
    values = []
    for parameter in parameters:
        if value := constant_dictionary.get(parameter):
            values.append(value)
        else:
            values.append(parameter)
    return values


def verify_parameters_match(config_data_list):
    not_matches = []
    for item in config_data_list:
        if item.handler_path_parameters != item.api_path_parameters:
            not_matches.append(item)

    return not_matches
