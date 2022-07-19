import sys
sys.path.append('../../commons')

from commons.taskinterface import ValidationTask, Warning
from commons.validation_tools import StepFunction
import re 
class UnusedPermissions(Warning): pass

class GenericStepFunctionTask(ValidationTask):

    def print_start_message(self):
        print('Checking if Generic Step Functions lack or have too many permissions...')

    def perform_validation_task(self, dependencies):
        terraform_dictionaries = dependencies['terraform_dicts']

        messages = []
        generic_step_functions_filenames = []
        step_functions_using_generics_filenames = []

        for terraform_file, terraform_dict in terraform_dictionaries.items():
            function_text = get_step_func_text(terraform_dict)
            if check_if_generic(function_text):
                generic_step_functions_filenames.append(terraform_file)
            
        for terraform_file, terraform_dict in terraform_dictionaries.items():
            function_text = get_step_func_text(terraform_dict)
            if check_if_using_generic(terraform_dictionaries, generic_step_functions_filenames, function_text):
                step_functions_using_generics_filenames.append(terraform_file)


        step_functions_using_generics_modules = []
        for filename in step_functions_using_generics_filenames:
            module = get_module_dict(terraform_dictionaries[filename])
            step_functions_using_generics_modules.append(module)

        for filename in generic_step_functions_filenames:
            tf_module = get_module_dict(terraform_dictionaries[filename])
            module_name = get_module_name(terraform_dictionaries[filename])

            step_function = GenericStepFunction(filename, tf_module, module_name, step_functions_using_generics_modules)

            unused_permissions = step_function.generate_unused_permission_message()
            used_without_permission = step_function.generate_lambdas_used_without_permission_message()

            if unused_permissions:
                messages.append(unused_permissions)
            if used_without_permission:
                messages.append(used_without_permission)
        return messages



    def post_validation_task(self, result):
        print('------------------------------------------------------------------------')
        print('Generic Step Functions Permission Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('Warning!!!')
        print('These step functions have unused permissions or are using lambdas without permission.')
        print()
        for item in result: print(f'{item}')

        return UnusedPermissions('Generic step function have too many permissions or are missing permissions')



def get_step_func_text(hcl_dictionary):
    module = hcl_dictionary.get('module')
    if not module:
        return None
    
    module_name = list(module.keys())[0]
    module_dict = module[module_name]
    function_text = module_dict.get('step_function_definition')

    return function_text

def check_if_generic(function_text):
    if not function_text:
        return False
    lines = function_text.split('\n')
    for line in lines:
        if "FunctionName.$" in line:
            return True
    return False

def check_if_using_generic(tf_dict, generic_func_names, function_text):
    
    if not function_text:
        return False
    lines = function_text.split('\n')
    for line in lines:
        for file in generic_func_names:
            name = get_module_name(tf_dict[file])
            if name in line:
                return True
    return False

def get_module_name(tf_dict):
    module = tf_dict.get('module')
    if not module:
        return None
    
    module_name = list(module.keys())[0]
    return module_name

def get_module_dict(tf_dict):
    module = tf_dict.get('module')
    if not module:
        return None
    
    module_name = list(module.keys())[0]
    return module.get(module_name)

class GenericStepFunction(StepFunction):
    def __init__(self, filename, tf_module, module_name, tf_modules_using_generic):
        super().__init__(filename, tf_module)
        self.module_name = module_name
        self.ignore_generics = False
        for module in tf_modules_using_generic:
            self.add_used_lambdas_from_other_step_function(module)


    def add_used_lambdas_from_other_step_function(self, tf_module):
        get_parameters = False
        function_text = tf_module['step_function_definition']
        lines = function_text.split('\n')
        for line in lines:
            if self.module_name in line:
                get_parameters = True
            if get_parameters:
                lambda_results = re.search("module.(.*?).function_name", line)
                if lambda_results:
                    self.lambdas_used.add(lambda_results.group(1))
            if 'OutputPath' in line:
                get_parameters = False
        
