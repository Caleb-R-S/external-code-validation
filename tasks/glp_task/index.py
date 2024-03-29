
from commons.taskinterface import ValidationTask, MissingLambdaInPipelineException, LamdaAWSNameTooLongException, UnableToParseYmlException
from commons.validation_tools import generate_location, get_main_yaml_vars, global_split
import yaml
class GLPTask(ValidationTask):

    def print_start_message(self):
        print('Finding GLP lambdas not in PR pipeline...')

    def check_configuration_matches(self, lambda_path, list_of_glp_configurations):
        is_namespaced = get_main_yaml_vars()['is_namespaced']
        if is_namespaced:
            namespace, lambda_name = global_split(lambda_path)[-2], global_split(lambda_path)[-1]
            for glp_configuration in list_of_glp_configurations:
                if glp_configuration.get("namespace") == namespace and glp_configuration.get("lambdaName") == lambda_name:
                    return True
        else:
            lambda_name = global_split(lambda_path)[-1]
            for glp_configuration in list_of_glp_configurations:
                if glp_configuration.get("lambdaName") == lambda_name:
                    return True
        return False

    def perform_validation_task(self, dependencies):
        lambda_paths = dependencies['lambda_paths']

        glp_pipeline_file = generate_location(3) + get_main_yaml_vars()['path_to_packager']
        lambdas_not_found_in_glp = []
        with open(glp_pipeline_file, "r") as stream:
            try:
                glp_configuration = yaml.safe_load(stream)
                list_of_glp_configurations = glp_configuration.get("parameters")[0].get("default")
                for lambda_path in lambda_paths:
                    if not self.check_configuration_matches(lambda_path, list_of_glp_configurations):
                        lambdas_not_found_in_glp.append(lambda_path)
            except yaml.YAMLError as exc:
                UnableToParseYmlException("Unable to parse YML")
        return lambdas_not_found_in_glp


    def post_validation_task(self, result):

        print('------------------------------------------------------------------------')
        print('GLP Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('\tLambdas were missing from the pipelines and/or locals file.')
        print()
        print(f'These are missing from GLP:')
        for item in result: print(f'\t{item}')
        return MissingLambdaInPipelineException('Missing Files in GLP')



