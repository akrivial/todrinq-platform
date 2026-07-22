# ToDrinQ Platform

FastAPI-based decision-support platform for drinking-water quality monitoring, soft-sensor prediction, historical validation and source-to-tap operational risk translation. It was developed for the ToDrinQ EU Horizon project and the Waternet demonstration environment.

## Online platform

- Application: <https://qf3mvtw8ej.eu-central-1.awsapprunner.com/login>
- API documentation: <https://qf3mvtw8ej.eu-central-1.awsapprunner.com/docs>
- Health check: <https://qf3mvtw8ej.eu-central-1.awsapprunner.com/healthz>

Access credentials are shared separately and are not stored in this repository.

## Current implementation

The platform provides four connected operational modules:

- **Source / Intake:** RIWA hard-sensor context and SoSe #9 inlet-turbidity forecasting.
- **Treatment:** SoSe #8 coagulation outlet turbidity, RL #5 FeCl3 dosage support, SoSe #10 CT, SoSe #10.1 bromate and SoSe #10.2 microbial removal.
- **Distribution:** biological-stability monitoring; SoSe #11 remains explicitly under evaluation and no fake prediction is presented as an operational model result.
- **Risk:** threshold-based source-to-tap classification, operator guidance and mitigation actions.

The current demonstration uses Mock PIMS inputs through the same interfaces intended for future real-PIMS data. Model predictions are real outputs of the integrated trained models where those models are available; mock inputs and mock validation measurements are labelled in the UI.

### Prediction history and scheduling

The backend scheduler produces and stores hourly predictions for:

- SoSe #9 inlet turbidity (prediction target: +3 hours)
- SoSe #8 coagulation outlet turbidity
- SoSe #10 CT
- SoSe #10.1 bromate
- SoSe #10.2 microbial removal

Historical records are stored in **Amazon DynamoDB** in the deployed AWS environment and in **SQLite** during local development. The AWS scheduler runs independently of the browser and local computer. CT validation uses five 10-day samples across the previous 50 days, reflecting the expected future laboratory-measurement interval.

### Risk confirmation rule

Scientific/operational thresholds are evaluated first. A low-threshold result is Low Risk and a moderate-threshold result is Moderate Risk. For high-threshold results, three distinct consecutive predictions are used to avoid triggering an action from one isolated value:

- 1 of 3: early warning, displayed as Moderate
- 2 of 3: continued warning, displayed as Moderate
- 3 of 3: confirmed High Risk and mitigation action

Refreshing or repeating the same timestamp does not increase the count. A subsequent value outside the high threshold breaks the high-risk sequence.

## Architecture and interoperability

Operational path:

`Mock/real PIMS -> FastAPI -> trained models -> persistent history -> risk translation -> operator UI`

The containerized FIWARE-aligned path includes Orion-LD as the NGSI-LD Context Broker, QuantumLeap for time-series integration, CrateDB, MongoDB and Redis. NGSI-LD entity upsert and notification endpoints are implemented. This is implementation evidence, not a claim of formal FIWARE certification.

AWS deployment uses:

- Amazon ECR for the Docker image
- AWS App Runner for the continuously available application
- Amazon DynamoDB for persistent prediction and observation history
- an App Runner instance role with least-privilege DynamoDB access

See [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) for deployment details.

## Repository structure

```text
app/
  data_preprocessing/    model input preparation
  models/                integrated model artefacts
  routes/                prediction, history and risk APIs
  services/              persistence and hourly scheduler
  static/ui/             HTML, CSS, JavaScript, charts and illustrations
  main.py                FastAPI application
deploy/aws/              AWS role and DynamoDB policy documents
tests/                   automated backend tests
Dockerfile               production container definition
requirements.txt         Python dependencies
```

The complete UI is version-controlled under `app/static/ui/`, including `index.html`, `app.js`, `styles.css`, the local Chart.js bundle and the source/treatment/distribution illustrations.

## Run locally

```powershell
git clone https://github.com/akrivial/todrinq-platform.git
cd todrinq-platform
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:TODRINQ_APP_PASSWORD = "choose-a-local-password"
uvicorn app.main:app --reload
```

Open:

- UI: <http://127.0.0.1:8000/app>
- API documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/healthz>

## Docker

```powershell
docker build -t todrinq-platform .
docker run --rm -p 8000:8000 -e TODRINQ_APP_PASSWORD="choose-a-password" todrinq-platform
```

Runtime databases, virtual environments and credentials are intentionally excluded from Git. Dependencies are reproducible from `requirements.txt`, the image is reproducible from `Dockerfile`, and production history remains in DynamoDB rather than inside the container.

## Project context

- ToDrinQ EU Horizon Project, Grant Agreement No. 101082035
- Delft University of Technology (TU Delft)
- Waternet demonstration environment

## Author

**Akrivi Alexandraki**

Engineering Doctorate Candidate, Delft University of Technology

Faculty of Civil Engineering and Geosciences, Sanitary Engineering

## Status and scientific scope

This is a research and demonstration decision-support platform. Mock data are explicitly labelled and will be replaced by mapped real-PIMS signals after connection and validation. Reference lines and risk thresholds must be confirmed with stakeholders for the relevant organism, temperature, units and operational setting before production decision-making.
