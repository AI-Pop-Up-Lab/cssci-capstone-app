# cssci-capstone-app (Mechanical Pollster)

Application for the Mechanical Pollster of the AI-Popup Lab. This application lets users explore polling results for countries using synthetic polls on AI personae. Charts can be explored, as well as the feature to chat to the personae included in the synthetic polls.

The (aim of the) application also automatically generate polling results from the personae weekly. This is not complete yet, and is still being developed.


## Framework overview
The frontend uses the React.js javascript framework, found inside the `ai-popup-lab-frontend/` folder. 

The backend uses Python's FastAPI library. This is in the `ai-popup-lab-backend/` folder. 

There are also python files and R files for running weekly data generation in this folder.

Those two parts of the backend folder have respective Dockerfiles inside the folder. Locally, you have the choice to run the API and frontend locally through their respective commands (covered later in the README), or by building and running the containers.

This is all hosted on azure, and automatically deployed with GitHub actions using the .yml workflows in `.github/workflows/`

The docker containers are built and pushed to azure, and the frontend is simply pushed to azure

## Application overview
### Frontend
Found in `ai-popup-lab-frontend/`. This is the React App. All components are in `/src`, with the app entries in App.js and index.js. All whole pages are in `/pages`. All components are in `/modules`, and components that are specifically either for the polling or persona chat pages/features have their own folders.

### Backend
Found in `ai-popup-lab-backend/`. 
- main.py: the entry point for the API.
- `/api_endpoints`: All endpoints for the API and their functions
- `/user_limiting`: functions which limits requests to the persona chat feature/endpoint
- `/country_data`: All data used for data generation and application functionality.
- `/data_generation`: Functions and processes for running weekly data generation to make new AI Personae polling responses

### GitHub Actions and Azure
`.github/workflows/` has workflow files which do multiple things:
- Push the frontend to Azure when its folder is updated on main
- Build the docker containers of the API and the weekly data generation 'worker' container when the backend folder is updated
- Trigger a weekly CRON job (scheduled job) every 23:00 on Sunday UCT, so midnight Amsterdam time which runs the worker container

### Weekly data generation
The container which runs weekly data generation retrieves all necessary data from Azure storage, making API calls for the personae poll responses, and then running an R script for extending stratification frames. All of this is then stored on Azure.

## Branches
#### main
Anything pushed to main will be automatically deployed to Azure. Only merge into or update if fully ready and tested.

#### web-app
Development branch, make changes here to your heart's desire, when good enough for main, bring it there to deploy.

#### pilot-study-app
The early version of the application used for our pilot study fieldwork. Had its reasons to stay around for a flimsy deployment for a bit, now kept as a snapshot for archival/fun.

#### stratification-frame-collection
Early data analysis and creation, moved to another repository but kept for archival.

### Running/Testing Locally
#### Running Back-End Locally

First make your working directory the *ai-popup-lab-backend* folder found within the repository.

To run the back-end API, run ```uvicorn main:app --reload```. This is using the python 'uvicorn' module to run the instance/variable 'app' defined in the main.py file, and --reload reloads the server/api if any changes are made.

If this doesn't work on Mac, try ```uvicorn app.main:app --reload --host 127.0.0.1 --port 8000```, which specifies the host address and port for correct functionality in testing.

To stop the server, press the keys **Ctrl+C** in the terminal.

#### Running Front-End Locally

Node.js/npm must first be installed on your computer. In the terminal make your working directory the *ai-popup-lab-application* folder found within the repository.

To download the dependent modules, run ```npm install```.

To run the application, run ```npm start```.
To stop the application, press the keys **Ctrl+C** in the terminal.

**Note**: For correct front-end functionality, the back-end should be running too, thus have two terminals open running both the front and back end, ideally running the back-end *first*.

##### Running Both in VS Code

This repository includes a VS Code task that starts both services for you.

Open the repository in VS Code, then run:
`Terminal` -> `Run Task...` -> `Start Frontend + Backend`

Before first run, install dependencies with:
`Terminal` -> `Run Task...` -> `Setup Project Dependencies`

You can also run the individual tasks:
- `Create Python Env`
- `Setup Project Dependencies`
- `Install Backend Dependencies`
- `Install Frontend Dependencies`
- `Start Backend`
- `Start Frontend`

You can also use the `Run and Debug` panel at the top of VS Code.
Select:
`Full Stack: Frontend + Backend`

Other available debug entries:
- `Backend: FastAPI`
- `Frontend: React`

The backend Python dependencies are listed in [ai-popup-lab-backend/requirements.txt](/Volumes/ADATA-SE900G/Documents/Jelle/Study/CulturalData&AI/MA Thesis/Repos/cssci-capstone-app/ai-popup-lab-backend/requirements.txt).

#### .env requirements for running locally

Any API calls will not work unless you have the .env file configured locally, as this is not pushed to github. Request from a group member. Along with this, the .env should have a value ```ENV="development"``` which will remove limits placed on deployment users.

#### Packages and environment
Use npm install on the package.json file in the frontend to download required packages

and use pip install on
- requirements-api.txt
- requirements-worker.txt
- requirements.txt (should be updated to be a master of the two but doesn't always happen in practice)

Download R and Rscript if not installed and wanting to run the R scripts locally.

Have Docker installed if wishing to build and run docker containers locally.