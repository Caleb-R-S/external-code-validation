from asyncio import tasks
from webbrowser import get
from tasks.api_gateway_task.index import ApiGatewayTask
from tasks.check_json_task.index import CheckJsonTask
from tasks.duplicate_name_task.index import DuplicateNameTask
from tasks.environment_variable_task.index import EnvironmentVariableTask
from tasks.generic_step_function_task.index import GenericStepFunctionTask
from tasks.glp_task.index import GLPTask
from tasks.lambda_in_local_files_task.index import LambdaInLocalFilesTask
from tasks.local_variable_task.index import LocalVarTask
from tasks.name_length_task.index import NameLengthTask
from tasks.path_parameter_task.index import PathParameterTask
# from tasks.step_functions_task.index import StepFunctionsTask
# from tasks.unit_test_task.index import UnitTestTask
# from tasks.unused_step_function_task.index import UnusedStepFunctionPermissionsTask
from commons.taskinterface import Warning
from commons.validation_tools import get_list_of_lambda_paths, get_dict_of_terraform_dicts, generate_location

def main():
    print('\033[92m' + generate_location(0) + '\033[37m') 
    print('\033[92m' + generate_location(1) + '\033[37m') 
    print('\033[92m' + generate_location(2) + '\033[37m') 
    print('\033[92m' + generate_location(3) + '\033[37m') 

    tasks = [
        # ApiGatewayTask(),
        # CheckJsonTask(),
        # DuplicateNameTask(),
        # EnvironmentVariableTask(), 
        # GenericStepFunctionTask(), 
        # GLPTask(),
        # LambdaInLocalFilesTask(),
        LocalVarTask(),
        # NameLengthTask(),
        # PathParameterTask(), # Almost exclusively for finance, come back if time permits
        # StepFunctionsTask(),
        # UnitTestTask(),
        # UnusedStepFunctionPermissionsTask(),
    ]
    exceptions = []
    warnings = []

    for task in tasks:
        task.print_start_message()

    dependencies = {
        'lambda_paths' : get_list_of_lambda_paths(),
        'terraform_dicts': get_dict_of_terraform_dicts()
    }

    task_report = list(map(lambda current_task: current_task.perform_validation_task(dependencies), tasks))

    for task, report in zip(tasks, task_report):
        exception = task.post_validation_task(report)
        if exception:
            if issubclass(type(exception), Exception):
                exceptions.append(exception)
            elif issubclass(type(exception), Warning):
                warnings.append(exception)

    print('------------------------------------------------------------------------')
    if not exceptions:
        print('All lambdas are in GLP and PR pipelines, all are accounted for in the locals file, '
              'and all step functions are properly configured with the lambda permissions.  Proceed!')

        if warnings:
            print(f'Warnings: {warnings}')
    else:
        print('Please fix all configuration errors before proceeding.  Thank you!')
        raise Exception(exceptions)

if __name__ == '__main__':
    main()
