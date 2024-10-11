import sys
import os
import requests as req
import json
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *

class MyScript(Script):

    def __init__(self):
        super(MyScript,self).__init__()

        #configure logging

        log_file = os.path.join(os.environ["SPLUNK_HOME"], 'etc','apps','tfl_accidentstats_modular_input','bin','logfile.log')
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(message)s'
        )
        logging.debug("Initialized MyScript")

    def get_scheme(self):
        # Returns scheme.
        logging.debug("Entering get_scheme")
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
        
        logging.debug("Exiting get_scheme")
        return scheme
    
    def tfl_api_call(self, requestURL,parameters):
        logging.info(f"Making API call to {requestURL} with parameters {parameters}")
        try:
            response = req.get(url=requestURL, params=parameters)
            logging.debug(f"Received response with status code {response.status_code}")
            response.raise_for_status()  # Raises HTTPError for bad responses
            data = response.json()
            logging.info("API call successful, parsed JSON data")
            return data
        except req.exceptions.RequestException as e:
            logging.error(f"API call failed: {e}")
            sys.exit(f"API call failed: {e}")
    
    def get_accidentstats(self,Ocp_Apim_Subscription_Key,year):
        logging.debug(f"Entering get_accidentstats with year {year}")
        requestURL = "https://api.tfl.gov.uk/AccidentStats/{year}"
        parameters = {"Ocp-Apim-Subscription-Key":Ocp_Apim_Subscription_Key,"year":year}
        data = self.tfl_api_call(requestURL, parameters)
        logging.info(f"Exiting get_accidentstats with data length {len(data)}")
        return data
    
    def checkpoint(self,checkpoint_file,acc_id):
        logging.debug(f"Checking checkpoint for acc_id {acc_id}")
        try:
            with open(checkpoint_file, 'r') as file:
                id_list = file.read().splitlines()
                exists = acc_id in id_list
                logging.debug(f"acc_id {acc_id} exists: {exists}")
                return exists
        except FileNotFoundError:
            logging.debug(f"Checkpoint file {checkpoint_file} not found, treating as new")
            return False
        except Exception as e:
            logging.error(f"Error reading checkpoint file: {e}")
            return False
        
    def write_to_checkpoint_file(self,checkpoint_file,acc_id):
        logging.debug(f"Writing acc_id {acc_id} to checkpoint file {checkpoint_file}")
        try:
            os.makedirs(os.path.dirname(checkpoint_file), exist_ok=True)
            with open(checkpoint_file, 'a') as file:
                file.writelines(acc_id + "\n")
        except Exception as e:
            logging.error(f"Error writing to checkpoint file: {e}")


    def stream_to_splunk(self,checkpoint_file,result):
        logging.info("Entering stream_to_splunk")
        events_to_return = []
        for dt in result:
            try:
                acc_id = str(dt["id"])
                if self.checkpoint(checkpoint_file, acc_id):
                    logging.debug(f"acc_id {acc_id} already processed, skipping")
                    continue
                else:
                    self.write_to_checkpoint_file(checkpoint_file, acc_id)
                    events_to_return.append(dt)
            except Exception as e:
                logging.error(f"Error processing event: {e}")
        logging.info(f"Exiting stream_to_splunk with {len(events_to_return)} new events")
        return json.dumps(events_to_return)

    def validate_input(self, validation_definition):
        # Validates input.
        logging.debug("Validating input")
        pass

    def stream_events(self, inputs, ew):
        # Splunk Enterprise calls the modular input, 
        # streams XML describing the inputs to stdin,
        # and waits for XML on stdout describing events.
        # {"input_stanza1":{"Ocp_Apim_Subscription_Key":value,"year":value}, "input_stanza2": {"Ocp_Apim_Subscription_Key":value, "year":value}...}
        logging.info("Starting stream_events")
        try:
            for input_name, input_item in inputs.inputs.items():
                logging.info(f"Processing input {input_name}")
                Ocp_Apim_Subscription_Key = input_item["Ocp_Apim_Subscription_Key"]
                year = input_item["year"]

                result = self.get_accidentstats(Ocp_Apim_Subscription_Key, year)
                logging.info(f"Retrieved {len(result)} records from API")

                checkpoint_file = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'tfl_accidentstats_modular_input','bin', 'checkpoint', 'checkpoint.txt')

                processed_results_json=self.stream_to_splunk(checkpoint_file,result)
                processed_results = json.loads(processed_results_json)

                logging.info(f"Streaming {len(processed_results)} events to Splunk")

                for r in processed_results:
                    event = Event()
                    event.stanza = input_name
                    event.data = json.dumps(r)
                    ew.write_event(event)
            logging.info("Completed stream_events")
        except Exception as e:
            logging.error(f"Error in stream_events: {e}")

if __name__ == "__main__":
    try:
        sys.exit(MyScript().run(sys.argv))
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)