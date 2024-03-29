import json


class ConfigurationManager():

    ''' Allows to acces all configuration data from one object '''


    def __init__(self, config_file_path):

        '''
        Params
        ------
        config_path (str) : path to the configuration file
        '''

        self.config_file_path = config_file_path
        self.load_config_file()
    

    def load_config_file(self):

        ''' loads configuration data from specified file '''

        with open(self.config_file_path) as config_f:
            self.config_data = json.load(config_f)
            config_f.close()


class HubConfigurationManager(ConfigurationManager):
    
    ''' Config manager specific to the hub '''

    def __init__(self, config_path):
        super().__init__(config_path)


class NodeConfigurationManager(ConfigurationManager):
    
    ''' Config manager specific to the node '''

    def __init__(self, config_path):
        super().__init__(config_path)
