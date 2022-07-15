import sys
sys.path.append('../../commons')

from commons.taskinterface import ValidationTask, MissingLambdaInPipelineException
from commons.validation_tools import StepFunction, get_tf_module, is_step_function

class StepFunctionsTask(ValidationTask):

    def print_start_message(self):
        print('Checking if step functions can invoke lambdas defined in their JSON...')

    def perform_validation_task(self, dependencies):
        terraform_dictionaries = dependencies['terraform_dicts']
        return_messages  = []

        for terraform_file, terraform_dict in terraform_dictionaries.items():
            tf_module = get_tf_module(terraform_dict)
            if is_step_function(tf_module):
                step_func = StepFunction(terraform_file, tf_module)
                used_without_permission = step_func.generate_lambdas_used_without_permission_message()
                if used_without_permission:
                    return_messages.append(used_without_permission)

        return return_messages



    def post_validation_task(self, result):
        print('------------------------------------------------------------------------')
        print('Step Functions Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('\tLambdas were missing from the pipelines and/or locals file.')
        print()
        print(f'These step functions have declared these lambdas in their function definition, but do not have permission to invoke them.  Add the lambda to the step_function_lambdas argument:')
        for item in result: print(f'{item}')

        return MissingLambdaInPipelineException('Step function need permissions.')