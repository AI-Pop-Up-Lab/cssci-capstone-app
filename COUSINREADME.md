# yo cousin

I hear u wanna add some charts... nice.

Deets for running the application is in the README, message me if there's issues... i hope not.

Page that contains the charts and calls the api for the info is found in ```ai-popup-lab-application\src\pages\pollingResults.js```

In the folder ```ai-popup-lab-application\src\modules\polling_results_modules``` is where all the components for each chart or set of charts are. each has their own css file but css is still global in react, so try keep your id's and classes localised and specific if u do so.

i have left it very un-styled, waiting to coordinate with sasha on exact stylistic direction, and also wanted the charts too to think of how to position stuff

when u r done i'll add the section below to filter personas and start a chat with one.

### okay some more technical stuff to know:

each component for the charts u will work in takes the pollingData variable, which is a list of dicts/js objects where the keys are the column names and the values the cell value - representing each cell of the sample.

there is a component called *demographicCharts.js*, this takes ```chosenDemographic```, which is a dict/object that looks like ```{"municipality":"all","gender":"female","age_group":"all","education":"all"}```
oh yeah, good to mention i added the option to select all (which is also the default), so take note of that.

what else uhhhh....

oh yeah i mean the ```chosenDemographic``` variable will automaticaly update when the chosen demographic is... changed :0

alright think that's all, shoot me a message on either whatsapp or slack or instagram or all 3 i'd probably see the message quickest on whatsapp and slowest on instagram.

good luck and thanks cousin appreciate it

oh also remember to follow the README to run the application


## knew i forgot something

there is a file ```ai-popup-lab-backend\country_data\country_data_info.json``` which kind of is like a master file for info over data, with the idea that it is expandable in the future.

its base level keys are country names (just 'netherlands' for THE netherlands though), and the idea is that it will have the file name for strat frames, daily samples (in the future, right now the 'daily sample' is just the pre gend one). it also holds the relevant columns for demographic search dropdowns, and the unique values of columns (these get sent by the api to the component at ```ai-popup-lab-application\src\modules\polling_results_modules\demographicChoiceDropdown.js``` to determine what will be in the dropdown).

right now the unique vals are generated from the notebook ```create_unique_column_vals.ipynb```, and i used the sample to generate them, just so for the pilot there isn't a mismatch between what u can pick and what we r working with whatever, we should discuss this at some point of how it would look in final product.

last thing to mention which isn't necessary just thought i'd grant some relatively useless knowledge, the notebook ```add_indexes_to_csv.ipynb``` right now is set to just add an index column to the "netherlands_daily_sample.csv" (the sample u generated), just cause i will need them later for entering persona chat and finding/passing data correctly. don't need to do anything with this i think, like if you generate a new sample i believe u won't need to worry about even running this.

all right that is all cheers and good luck and cheers and good luck and che