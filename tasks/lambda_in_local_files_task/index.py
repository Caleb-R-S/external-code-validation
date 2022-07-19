import sys
sys.path.append('../../commons')

from commons.taskinterface import ValidationTask, UnableToParseYmlException, MissingLambdaInPipelineException
from commons.validation_tools import generate_location, get_main_yaml_vars
import yaml
import os

class LambdaInLocalFilesTask(ValidationTask):

    def print_start_message(self):
        print('Finding lambdas not in locals file...')

    def perform_validation_task(self, dependencies):
        lambda_paths = dependencies['lambda_paths']

        locals_file = generate_location(3) + "/terraform/locals.tf"
        lambdas_not_found_in_locals = []
        with open(locals_file, "r") as stream:
            try:
                locals_content = stream.read().replace('\n', '')
                for lambda_path in lambda_paths:
                    print(lambda_path)
                    split = lambda_path.split("/")
                    if (get_main_yaml_vars['is_namespaced']):
                        namespace = split[0]
                        lambda_name = split[1]
                        try:
                            artifact_path = self.generate_artifact_path_from_namespace_and_name(namespace, lambda_name)
                            locals_content.index(artifact_path)
                        except ValueError:
                            lambdas_not_found_in_locals.append(lambda_path)
                    else:
                        print('success')
            except yaml.YAMLError as exc:
                UnableToParseYmlException("Unable to parse YML")
        return lambdas_not_found_in_locals


    def post_validation_task(self, result):
        print('------------------------------------------------------------------------')
        print('Lambda in Local Files Task')


        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        suggested_path = []
        for lambda_not_found in result:
            namespace, lambda_name = lambda_not_found.split(os.sep)
            artifact_path = self.generate_artifact_path_from_namespace_and_name(namespace, lambda_name)
            suggested_path.append(str(artifact_path))

        print('\tLambdas were missing from the pipelines and/or locals file.')
        print()
        print(f'These paths are missing from locals file (or you may have formatted them incorrectly):')
        for item in result: print(f'\t{item}')
        print()

        print(f'Try using this path in the locals file')
        for path in suggested_path: print(f'\t{path}')
        return MissingLambdaInPipelineException('Lambdas missing in local files.')

    def generate_artifact_path_from_namespace_and_name(self, namespace, name):
        return "../src/artifacts/" + namespace + "_"+name+"_drop/lambdas/"+ namespace +"/"+ name +"/"+name+".zip"