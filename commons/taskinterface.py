from abc import ABC, abstractmethod

class MissingLambdaInPipelineException(Exception):pass
class LamdaAWSNameTooLongException(Exception):pass
class UnableToParseYmlException(Exception):pass

# Declare interface here
class ValidationTask(ABC):
    @abstractmethod
    def print_start_message(self):
        pass

    @abstractmethod
    def perform_validation_task(self, lambda_paths: [str]) -> [str]:
        pass

    @abstractmethod
    def post_validation_task(self, result: [str]) -> Exception:
        pass

class Warning():
    def __init__(self, warning_text):
        self.warning_text = warning_text
    def __repr__(self):
        return self.warning_text










