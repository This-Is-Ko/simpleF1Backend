# Simple F1 | Backend
Backend component of simplef1 project.

Frontend component can be found [here](https://github.com/This-Is-Ko/simpleF1Frontend)

Aims to provide data to display all essential race statistics in a simple, single view.

To run, configure the following env variables in an .env file and use `uvicorn main:app --reload` to run.
* FRONTEND_URI
* ATLAS_URI
* DB_NAME
* MONGODB_CLUSTER
* MONGODB_API_URI
* MONGODB_API_KEY
