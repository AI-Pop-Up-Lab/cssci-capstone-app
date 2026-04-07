# Guide for implementing new countries to tool

For any new country implemented, there are some steps to take before functionality.

### country_data_info.json

Firstly, in country_data_info.json (in ai-popup-lab-backend/country_data), the country must be added as a root key, lowercase. the way it is entered here must be how it is referenced anywhere else. Avoid spaces, this can be handled later, thus if needed, shorten the name (e.g. The Netherlands --> netherlands).

Now the relevant data must be entered for the country.
- stratification_frame_filename = filename of the country's stratification frame
- daily_sample_filename = filename for the current sample of the country (SUBJECT TO CHANGE)
- demographic_search_columns = the columns that will be provided to the user in demographic searches
- column_unique_vals = unique values for the above columns that can be selected
- next_GE_vote_colname = the column name referencing the personae's predicted vote, so that it can be renamed to next GE vote in the frontend
- all_placeholder = how column names should be presented for the 'all' option, to ensure correct language (e.g. for "education" --> "all education levels")
- search_sentence_order = the order in which columns should appear in the demographic search on the polling results page, to ensure fluidity in the sentence
- party_colours = a dict that references the party abbreviations used in the data, and the party's respective colour as a hex code
- seat_allocation_function_name = the method/function used in the frontend to calculate allocated seats from the data
- total_seats = total seats in the country's parliament


### countrySwitch.js

(ai-popup-lab-application\src\modules\countrySwitch.js)

the country's name used to reference it throughout the code must be added to list 'countryOptions'


### Flag icons

A .png of the country must be added to ai-popup-lab-application\src\assets\images\flags.


### seatVisualisation.js

(ai-popup-lab-application\src\modules\polling_results_modules\seatVisualisation.js)

The country's seat allocation method must be made as function in this component. The component receives the required method name from the backend, thus in the chooseSeatAllocationFunction function, an if statement must be made to return the newly created function if the method passed from the backend matches.


### Country name edge cases

In personaChatExample.js and landingPage.js (ai-popup-lab-application\src\modules\personaChatExample.js and ai-popup-lab-application\src\pages\landingPage.js), there is a function "modifyCountryNameEdgeCases". If the name of the added country is an 'edge case', such that the used variable in the code does not match it's real name, add an else if to the existing if statement, where the variable modifiedCountry will be changed to the country's full name.