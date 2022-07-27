from operator import mod
import sys
import os
import inspect
import importlib
from commons.taskinterface import ValidationTask
from commons.validation_tools import get_tf_module, get_main_yaml_vars, get_list_of_lambda_paths

class ModuleAndHandlerDifferenceException(Exception): pass

class ModuleHandlerComparisonTask(ValidationTask):

    def print_start_message(self):

        print('Checking Terraform Modules against Lambda Handlers')

    def perform_validation_task(self, dependencies):
        return_messages  = []
        terraform_dictionaries = dependencies['terraform_dicts']
        all_lambda_module_links = get_main_yaml_vars()['lambda_terraform_links']
        valid_lambda_paths = get_list_of_lambda_paths()
        path_to_lambdas = get_main_yaml_vars()['path_to_lambdas']
        for link in all_lambda_module_links:
            lambda_name = link['lambda_file_name']
            terraform_module_name = link['terraform_block_with_lambda']
            message = ''
            message += self.generate_invalid_lambda_error(path_to_lambdas + lambda_name, valid_lambda_paths)  
            message += self.generate_invalid_module_error(terraform_module_name, terraform_dictionaries)  
            if not message:
                # Add conditionals to check for third parameter
                message += self.generate_invalid_link_error(lambda_name, terraform_module_name, terraform_dictionaries)

            if message:
                return_messages.append(message)

        return return_messages


    def post_validation_task(self, result):
        print('------------------------------------------------------------------------')
        print('Check Lambda Handlers and Terraform Module Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('\tNot all Modules have correct lambda handlers')
        print()
        print(f'The lambda handlers in the following modules should be reviewed:')
        for item in result: print(f'{item}')

        return ModuleAndHandlerDifferenceException('Invalid Module Handler Pair')

    def generate_invalid_lambda_error(self, file_name, lambda_paths):
        if file_name not in lambda_paths:
            return f'The lambda {file_name} wasnt in the list of lambdas'
        return ''

    def generate_invalid_module_error(self, module_name, terraform_modules):
        for (terraform_file, terraform_dict) in terraform_modules.items():
            module = terraform_dict.get('module')
            if module:
                isValid = module.get(module_name)
                if isValid:
                    return ''

        return f'The module {module_name} wasnt in the list of terraform modules'

    def generate_invalid_link_error(self, lambda_name, terraform_module_name, terraform_dictionaries):
        # Get Info from terraform
        handler_module_name, handler_function_name = self.get_handler_info(terraform_module_name, terraform_dictionaries)
        # Compare it to lambdas and return
        return self.perform_lambda_handler_comparison(lambda_name, handler_module_name, handler_function_name)

            
    def get_handler_info(self, terraform_module_name, terraform_dictionaries):
        for (terraform_file, terraform_dict) in terraform_dictionaries.items():
            module = terraform_dict.get('module')
            if module and module.get(terraform_module_name):
                terraform_module = get_tf_module(terraform_dict)
                break
        handler = terraform_module['handler']   
        handler_module_name, handler_function_name = handler.split(".")
        return handler_module_name, handler_function_name
    
    def perform_lambda_handler_comparison(self, lambda_name, handler_module_name, handler_function_name):
        message = ''
        try:
            sys.path.append('.' + get_main_yaml_vars()['path_to_lambdas'])
            lambda_module = importlib.import_module(lambda_name + '.' + handler_module_name)
            if (hasattr(lambda_module, handler_function_name)):
                handler_function = getattr(lambda_module, handler_function_name)
                if (inspect.isfunction(handler_function)):
                    handler_function_parameters = inspect.signature(handler_function).parameters
                    if 'event' in handler_function_parameters and 'context' in handler_function_parameters:
                        pass # noop
                    else:
                        message += f'\tThe function {handler_function_name} from {lambda_module} doesn\'t have the correct parameters to be a lambda handler'
                        message += f'\tThe expected parameters are [\'event\', \'context\'], the received parameters were {[key for key in handler_function_parameters]}'
                else:
                    message += f'\tThe attribute {handler_function_name} from {lambda_module} is not a function'
            else:
                message += f'\tThere is no attribute called {handler_function_name} in the module {lambda_module}'

            return message
        except Exception as exception:
            return f'ERROR: {exception}'