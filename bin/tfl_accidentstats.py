import sys
import os
import requests as req
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *

class MyScript(Script):

    def get_scheme(self):
        # Returns scheme.
        scheme = Scheme("TFL_AccidentStats")
        scheme.use_external_validation = False
        scheme.use_single_instance = False
        scheme.description = "Modular Input to gather TFl Accident Stats"

        Ocp_Apim_Subscription_Key = Argument("Ocp_Apim_Subscription_Key")
        Ocp_Apim_Subscription_Key.title = "Primary Key / Secondary Key"
        Ocp_Apim_Subscription_Key.data_type = Argument.data_type_string
        Ocp_Apim_Subscription_Key.description = "Primary Key / Secondary Key"
        Ocp_Apim_Subscription_Key.required_on_create = True
        Ocp_Apim_Subscription_Key.required_on_edit=True
        scheme.add_argument(Ocp_Apim_Subscription_Key)

        year=Argument("year")
        year.title = "Year"
        year.data_type = Argument.data_type_number
        year.description = "Year should be from 2005 to 2019"
        year.required_on_create = True
        year.required_on_edit=True
        scheme.add_argument(year)

        return scheme
    
    def tfl_api_call(self, requestURL,parameters):
        response = req.get(url=requestURL,params=parameters)
        if response.status_code!=200:
            sys.exit(1)
        data = response.json()
        return data
    
    def get_accidentstats(self,Ocp_Apim_Subscription_Key,year):
        requestURL = "https://api.tfl.gov.uk/AccidentStats/{year}"
        parameters = {"Ocp-Apim-Subscription-Key":Ocp_Apim_Subscription_Key,"year":year}
        return self.tfl_api_call(requestURL,parameters)
    
    def checkpoint(self,checkpoint_file,acc_id):
        with open(checkpoint_file,'r') as file:
            id_list = file.read().splitlines()
            return(acc_id in id_list)
        
    def write_to_checkpoint_file(self,checkpoint_file,acc_id):
        with open(checkpoint_file,'a') as file:
            file.writelines(acc_id+"\n")


    def stream_to_splunk(self,checkpoint_file,result):
        events_to_return = []
        for dt in result:
            if self.checkpoint(checkpoint_file,str(dt["id"])):
                continue
            else:
                self.write_to_checkpoint_file(checkpoint_file,str(dt["id"]))
                events_to_return.append(dt)

        return json.dumps(events_to_return)

    def validate_input(self, validation_definition):
        # Validates input.
        pass

    def stream_events(self, inputs, ew):
        # Splunk Enterprise calls the modular input, 
        # streams XML describing the inputs to stdin,
        # and waits for XML on stdout describing events.
        # {"input_stanza1":{"Ocp_Apim_Subscription_Key":value,"year":value}, "input_stanza2": {"Ocp_Apim_Subscription_Key":value, "year":value}...}
        for input_name, input_item in inputs.inputs.items():
            Ocp_Apim_Subscription_Key = input_item["Ocp_Apim_Subscription_Key"]
            year = input_item["year"]
            
            result = self.get_accidentstats(Ocp_Apim_Subscription_Key,year)
            checkpoint_file=os.path.join(os.environ["SPLUNK_HOME"],'etc','apps','tfl_accidentstats_modular_input','bin','checkpoint','checkpoint.txt')
            processed_results_json=self.stream_to_splunk(checkpoint_file,result)
            processed_results = json.loads(processed_results_json)
            #print(result)
            #with open(os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'tfl_accidentstats_modular_input', 'bin', 'debug_processed_results.txt'), 'w') as debug_file:
            #   debug_file.write(processed_results)

            for r in processed_results:
                event=Event()
                event.stanza = input_name
                event.data = json.dumps(r)
                ew.write_event(event)

if __name__ == "__main__":
    sys.exit(MyScript().run(sys.argv))
