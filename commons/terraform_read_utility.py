from validation_tools import get_tf_module 

def yieldNextModule(terraform_dictionaries, filter):
    for terraform_file, terraform_dict in terraform_dictionaries.items():
        terraform_module = get_tf_module(terraform_dict)
        if filter(terraform_module):
            yield terraform_module

