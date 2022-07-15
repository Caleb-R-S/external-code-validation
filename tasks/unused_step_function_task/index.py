# Placeholder
# Put Step Functions task here
from tasks.taskinterface import ValidationTask, Warning
from tasks.validation_tools import StepFunction, get_tf_module, is_step_function

class UnusedPermissions(Warning): pass

class UnusedStepFunctionPermissionsTask(ValidationTask):

    def print_start_message(self):
        print('Checking if step functions can invoke lambdas defined in their JSON...')

    def perform_validation_task(self, dependencies):
        terraform_dictionaries = dependencies['terraform_dicts']
        return_messages  = []

        for terraform_file, terraform_dict in terraform_dictionaries.items():
            tf_module = get_tf_module(terraform_dict)
            if is_step_function(tf_module):
                step_func = StepFunction(terraform_file, tf_module)
                unused_permissions = step_func.generate_unused_permission_message()
                if unused_permissions:
                    return_messages.append(unused_permissions)

        return return_messages


    def post_validation_task(self, result):
        print('------------------------------------------------------------------------')
        print('Unused Step Functions Permission Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('Warning!!!')
        print('\tThese step functions have unused permissions.')
        print()
        print(f'These step functions have permission to invoke these lambdas, but are not using them.')
        for item in result: print(f'{item}')

        return UnusedPermissions('Check Unused Step Functions Permission Task')
    