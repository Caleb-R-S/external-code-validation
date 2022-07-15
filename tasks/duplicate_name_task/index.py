# Placeholder
from tasks.taskinterface import ValidationTask
from tasks.validation_tools import generate_location
import os
import yaml
import hcl

class DuplicateNameException(Exception): pass

class DuplicateNameTask(ValidationTask):

    def print_start_message(self):
        print('Looking for duplicate resource name in terraform...')

    def perform_validation_task(self, dependencies):
        lambda_paths = dependencies['lambda_paths']
        terraform_dicts = dependencies['terraform_dicts']

        rules = get_rules()
        property_checkers = [
            ModulePropertyChecker(rules),
            ResourcePropertyChecker(rules)
        ]

        duplicates = []
        for checker in property_checkers:
            duplicates += checker.find_duplicates(terraform_dicts)

        return duplicates


    def post_validation_task(self, result):

        print('------------------------------------------------------------------------')
        print('Duplicate Name Task')

        if (len(result) == 0):
            print('\tTask was successful!')
            return None

        print('\tDuplicate names were used in lambdas.')
        print()
        print(f'These names are duplicated:')
        for item in result: print(f'{item}')
        return DuplicateNameException('Duplicate names.')


def get_rules():
    with open(generate_location(1) + '/configs/duplicate-names.yml') as file:
        yaml_dict = yaml.safe_load(file)
        return yaml_dict['rules']

class ResourcePropertyChecker:
    class DuplicateMessage:
        def __init__(self, type, prop, value, files):
            self.type = type
            self.prop = prop
            self.value = value
            self.files = []
            for file in files:
                self.files.append(file)

        def add_file(self, file):
            self.files.append(file)

        def __str__(self):
            string = '\tRule: Resource\n' + \
                    f'\tType: {self.type}\n' + \
                    f'\tProp: {self.prop}\n' + \
                    f'\tValue: {self.value}\n' + \
                    f'\tFiles:\n'

            for file in self.files:
                string += f'\t\t{file}\n'
            return string 

    def __init__(self, rules):
        self.names = {}
        self.duplicate_names = {}
        self.rules = self.__parse_rules(rules)


    def find_duplicates(self, tf_dict_list):
        for filename, tf_dict in tf_dict_list.items():
            for resource in self.rules:
                type = resource['type']
                props = resource['props']
                props_dictionary_list = self.__parse_tf_dict(tf_dict, type, props)

                for props_dict in props_dictionary_list:
                    for prop in props_dict:
                        value = props_dict[prop]
                        key = self.__get_key(type, prop, value)
                        if key not in self.names:
                            self.names[key] = filename
                        else:
                            if key not in self.duplicate_names:
                                file2 = self.names[key]
                                duplicated_resource = self.DuplicateMessage(type, prop, value, [filename, file2])
                                self.duplicate_names[key] = duplicated_resource
                            else:
                                self.duplicate_names[key].add_file(filename)

        list_of_duplicates = []
        for key, value in self.duplicate_names.items():
            list_of_duplicates.append(str(value))
        return list_of_duplicates
                        
            

    def __parse_rules(self, rules):
        module_rules = rules['resources']
        return module_rules

    def __parse_tf_dict(self, tf_dict, resource_type, props_wanted):
        list_of_prop_dict = []
        if not (tf_resources := tf_dict.get('resource')):
            return []
        
        if tf_resources.get(resource_type):
            resource_type_data = tf_resources[resource_type]
            for key, value in resource_type_data.items():
                props = {}
                for prop in props_wanted:
                    if prop in value:
                        props[prop] = value[prop]
                list_of_prop_dict.append(props)

        return list_of_prop_dict

    def __get_key(self, type, prop, value):
        return str(type) + str(prop) + str(value)

        
class ModulePropertyChecker:
    class DuplicateMessage:
        def __init__(self, source, prop, value, files):
            self.rule = 'Module'
            self.source = source
            self.prop = prop
            self.value = value
            self.files = []
            for file in files:
                self.files.append(file)
        
        def add_file(self, file):
            self.files.append(file)

        def __str__(self):
            string = '\tRule: Module\n' + \
                    f'\tSource: {self.source}\n' + \
                    f'\tProp: {self.prop}\n' + \
                    f'\tValue: {self.value}\n' + \
                    f'\tFiles:\n'

            for file in self.files:
                string += f'\t\t{file}\n'
            return string 


    def __init__(self, rules):
        self.names = {}
        self.duplicate_names = {}
        self.rules = self.__parse_rules(rules)

    def find_duplicates(self, tf_dict_list):
        for filename, tf_dict in tf_dict_list.items():
            module_data = self.__parse_tf_dict(tf_dict)
            if module_data:
                source = module_data['source']
                props = self.rules.get(source)
                if props:
                    for prop in props:
                        value = module_data[prop]
                        key = self.__get_key(source, prop, value)
                        if key not in self.names:
                            self.names[key] = filename
                        else:
                            if key not in self.duplicate_names:
                                file2 = self.names[key]
                                message = self.DuplicateMessage(source, prop, value, [filename, file2])
                                self.duplicate_names[key] = message
                            else:
                                self.duplicate_names[key].add_file(filename)

        list_of_duplicates = []
        for key, value in self.duplicate_names.items():
            list_of_duplicates.append(str(value))
        return list_of_duplicates


    def __parse_tf_dict(self, tf_dict):
        if 'module' in tf_dict:
            module = tf_dict['module']
            module_name = list(module.keys())[0]
            module_data = module[module_name]
            return module_data
        return None

    def __parse_rules(self, rules):
        module_rules = rules['modules']
        source_to_props = {}
        for dictionary in module_rules:
            source = dictionary['source']
            props = dictionary['props']
            source_to_props[source] = props
        return source_to_props

    def __get_key(self, source, prop, value):
        return str(source) + str(prop) + str(value)

