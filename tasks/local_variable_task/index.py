import sys
sys.path.append('../../commons')

from commons.taskinterface import ValidationTask, MissingLambdaInPipelineException, LamdaAWSNameTooLongException, UnableToParseYmlException
from commons.validation_tools import generate_location
import os


class UnusedLocalVarException(Exception): pass

class LocalVarTask(ValidationTask):

    def print_start_message(self):
        print('Looking for unused local variables...')



    def perform_validation_task(self, dependencies):
        lambda_paths = dependencies['lambda_paths']

        local_vars_in_locals = get_local_vars()
        local_vars_in_tf = get_all_local_vars_use_in_tf()
        unused_vars = list(local_vars_in_locals - local_vars_in_tf)
        return unused_vars


    def post_validation_task(self, result):

        print('------------------------------------------------------------------------')
        print('Local Variable Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('\tSome variables in locals.tf are not being used.')
        print()
        print(f'These variables are unused:')
        for item in result: print(f'\t{item}')
        return UnusedLocalVarException('Some variables in locals.tf are not being used in terraform.')


def get_local_vars():
    local_vars = set()
    with open(f'{generate_location(3)}/terraform/locals.tf') as file:
        lines = file.readlines()
        for line in lines:
            if len((split_line := line.split('='))) > 1:
                lhs = split_line[0]
                local_vars.add(lhs.strip())

    return local_vars

def get_all_local_vars_use_in_tf():
    local_vars = set()
    for (dirpath, dirnames, filenames) in os.walk(f'{generate_location(3)}/terraform'):
        for file in filenames:
            tf_filepath = os.path.join(dirpath, file)
            vars = get_local_vars_from_tf(tf_filepath)
            local_vars.update(vars)
    return local_vars


def get_local_vars_from_tf(tf_filepath):
    local_vars = set()
    with open(tf_filepath) as file:
        lines = file.readlines()
        for line in lines:
            if len((split_line := line.split('='))) > 1:
                rhs = split_line[1]
                if 'local.' in rhs:
                    local_vars.add(rhs.split('.')[1].strip())
    return local_vars

