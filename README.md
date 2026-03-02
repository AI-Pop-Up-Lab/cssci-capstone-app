# cssci-capstone-app


### Working within virtual environment

If running either the front and/or back-end of the AI Pollster which are in this repository, it is suggested to enter the virtual environment (venv). All packages and prerequisites will be installed in this virtual environment (apart from Node modules, explanation in next section), on the same version, to ensure the application runs with no conflict between machines.

When in project directory, on mac use:
```source env/bin/activate``` and on Windows use ```env\Scripts\activate``` in the *terminal* to work within the virtual environment. 

Run ```source deactivate``` to exit on Mac and ```deactivate``` on Windows

#### Running Back-End

First make your working directory the *ai-popup-lab-backend* folder found within the repository.

To run the back-end API, run ```uvicorn main:app --reload```. This is using the python 'uvicorn' module to run the instance/variable 'app' defined in the main.py file, and --reload reloads the server/api if any changes are made.

To stop the server, press the keys **Ctrl+C** in the terminal.

#### Running Front-End

Node.js/npm must first be installed on your computer. In the terminal make your working directory the *ai-popup-lab-application* folder found within the repository.

To download the dependent modules, run ```npm install```.

To run the application, run ```npm start```.
To stop the application, press the keys **Ctrl+C** in the terminal.

**Note**: For correct front-end functionality, the back-end should be running too, thus have two terminals open running both the front and back end, ideally running the back-end *first*.

