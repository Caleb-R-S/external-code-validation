# Placeholder
from tasks.taskinterface import ValidationTask
from tasks.validation_tools import StepFunction, get_tf_module, is_step_function

class CheckJsonTaskException(Exception): pass

class CheckJsonTask(ValidationTask):

    def print_start_message(self):

        print('Checking JSON properties listed in the check-json-config file in terraform')

    def perform_validation_task(self, dependencies):
        terraform_dictionaries = dependencies['terraform_dicts']
        return_messages  = []

        for terraform_file, terraform_dict in terraform_dictionaries.items():
            tf_module = get_tf_module(terraform_dict)
            if is_step_function(tf_module):
                step_func = StepFunction(terraform_file, tf_module)
                invalid_json = step_func.generate_invalid_json_message()
                if invalid_json:
                    return_messages.append(invalid_json)

        return return_messages


    def post_validation_task(self, result):
        print('------------------------------------------------------------------------')
        print('Check JSON Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('\tInvalid JSON was detected')
        print()
        print(f'These step functions have definitions that include invalid JSON:')
        for item in result: print(f'{item}')

        return CheckJsonTaskException('Invalid JSON')
