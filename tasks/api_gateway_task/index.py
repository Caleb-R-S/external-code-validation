
from tasks.taskinterface import ValidationTask, MissingLambdaInPipelineException, LamdaAWSNameTooLongException, UnableToParseYmlException
from tasks.validation_tools import generate_location
import hcl

class MissingLambdaARNException(Exception): pass


class ApiGatewayTask(ValidationTask):

    def print_start_message(self):
        print('Check that all lambda_arns are used in routes in api-gateway.tf ...')

    def perform_validation_task(self, dependencies):
        lambda_paths = dependencies['lambda_paths']

        lambda_arns = set()
        lambda_arns_in_routes = set()

        with open(f'{generate_location(3)}/terraform/api-gateway.tf') as file:
            obj = hcl.load(file)
            lambda_arns = set(obj['module']['simple-rest-lambda']['lambda_arns'])
            list_of_routes = obj['module']['simple-rest-lambda']['routes']
            for route in list_of_routes:
                lambda_arns_in_routes.add(route['lambda_arn'])

        if lambda_arns != lambda_arns_in_routes:
            return list(lambda_arns - lambda_arns_in_routes) + list(lambda_arns_in_routes - lambda_arns)

        return []

    def post_validation_task(self, result):
        print('------------------------------------------------------------------------')
        print('Api Gateway Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('\tNot all lambda_arns were used or lambdar_arns used not declared before routes in api-gateway.tf.')
        print()
        print(f'Make sure these lambda_arns are in lambda_arns and routes:')
        for item in result: print(f'\t{item}')
        return MissingLambdaARNException('Routes and Lambda_arns not set up correctly in api-gateway.tf')