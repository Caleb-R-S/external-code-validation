import sys
sys.path.append('../../commons')

from commons.taskinterface import ValidationTask, MissingLambdaInPipelineException
from commons.validation_tools import generate_location
import os
class UnitTestTask(ValidationTask):

    def print_start_message(self):
        print('Finding lambdas not in pull request pipeline...')

    def perform_validation_task(self, dependencies):
        lambda_paths = dependencies['lambda_paths']

        lambdas_not_found_in_pipeline = []
        unit_test_pipeline_file = generate_location(2) + "/unit-tests/pr.yml"
        with open(unit_test_pipeline_file, "r") as file:
            data = file.read().replace('\n', '')
            for lambda_path in lambda_paths:
                try:
                    data.index(lambda_path)
                except ValueError:
                    lambdas_not_found_in_pipeline.append(lambda_path)
        return lambdas_not_found_in_pipeline


    def post_validation_task(self, result):
        print('------------------------------------------------------------------------')
        print('PR Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('\tLambdas were missing from the pipelines and/or locals file.')
        print()
        print(f'These are missing from PR:')
        for item in result: print(f'\t{item}')

        return MissingLambdaInPipelineException('Lambdas missing from pipelines and/or local files.')