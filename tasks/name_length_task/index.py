# Placeholder
# Locals task goes here
from tasks.taskinterface import ValidationTask, UnableToParseYmlException, LamdaAWSNameTooLongException
from tasks.validation_tools import generate_location
import os
class NameLengthTask(ValidationTask):

    def print_start_message(self):
        print('Checking if lambda names are too long...')

    def perform_validation_task(self, dependencies):
        lambda_paths = dependencies['lambda_paths']

        locals_file = generate_location(3) + "/terraform/locals.tf"
        name_length_max = 64
        entry_too_long = []
        with open(locals_file, "r") as stream:
            try:
                locals_entries = {}
                locals_lines = stream.read().split("\n")
                for line in locals_lines:
                    parts = line.split("=")
                    if len(parts) == 2:
                        locals_entries[parts[0].strip()] = parts[1].strip().replace("\"", "")
                for lambda_path in lambda_paths:
                    namespace, lambda_name = lambda_path.split("/")
                    (name_key, name_value) = self.generate_name_key_and_value(namespace, lambda_name)
                    entry_value = locals_entries.get(name_key)
                    if entry_value:
                        length_result = len(entry_value.replace("${var.ENV}", "123") + "-exec")
                        if length_result > name_length_max:
                            entry_too_long.append((lambda_path, length_result-name_length_max))
            except yaml.YAMLError as exc:
                UnableToParseYmlException("Unable to parse YML")
        return entry_too_long


    def post_validation_task(self, result):
        print('------------------------------------------------------------------------')
        print('Name Length Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None


        print(f'\tThese lambda names go over the aws name length limit with suffix added:')
        print()
        for name, count in result: print(f'\t{name} is {count} chars too long.')
        return LamdaAWSNameTooLongException('Lambdas names are too long.')

    def generate_name_key_and_value(self, namespace, name):
        namespace_value = namespace if namespace == "api" else "stepFunctionStates"
        name_key = name.replace("-", "_") + "_lambda_name"
        name_value = "finance-" + namespace_value + "-" + name + "-${var.ENV}"
        return (name_key, name_value)