import hcl
from commons.taskinterface import ValidationTask
from commons.validation_tools import generate_location
from commons.terraform_read_utility import yieldNextModule

class MissingLambdaARNException(Exception): pass


class ApiGatewayTask(ValidationTask):
    def api_filter(self, terraform_module):
        if 'source' in terraform_module: 
            return terraform_module['source'] == 'app.terraform.io/ICS/apigateway-simple-rest-lambda/aws'
        return False

    def print_start_message(self):
        print('Check that all lambda_arns are used in routes in api-gateway.tf ...')

    def perform_validation_task(self, dependencies):
        terraform_dictionaries = dependencies['terraform_dicts']
        for terraform_module in yieldNextModule(terraform_dictionaries, self.api_filter):
            lambda_arns = set(terraform_module['lambda_arns'])
            lambda_arns_in_routes =set([route['lambda_arn'] for route in terraform_module['routes']])
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


