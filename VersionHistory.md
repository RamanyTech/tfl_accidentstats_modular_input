Version History

Modular Input: TFL_AccidentStats

Version 1.0.0: October_11_2024

1. Created basic modular input script "tfl_accidentstats.py" in Splunk using Splunk SDK for Python.
2. Integrated TFL API to fetch the data.
3. Implemented data fetching and added checkpointing logic to avoid duplicate entries.
4. Improved checkpointing logic using stream_to_splunk function.
5. Added a new variable called "processed_result_json" to store the list of new events(data) and return it as JSON.
6. Added separate variable called "processed_results" to load the JSON back into list of events.
7. Implemented logging to track script execution.
8. Added exception handling to capture and log unexpected error.
9. Created a new file called "logfile.log" in tfl_accidentstats_modular_input/bin to store the log entires.