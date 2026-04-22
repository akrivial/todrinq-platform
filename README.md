# 💧 ToDrinQ Platform

A modular **FastAPI-based decision-support platform** for drinking water quality monitoring, soft-sensor integration, and **source-to-tap risk translation**, developed in the context of the **ToDrinQ EU Horizon project** and tailored to the **Waternet** use case.

---

## 🚀 Overview

The ToDrinQ Platform integrates predictive models, treatment-process intelligence, and operational risk interpretation into a unified digital environment for drinking water systems.

The platform is structured around four core modules:

* **Source / Intake**
* **Treatment**
* **Distribution**
* **Risk**

Its main purpose is to support water utilities in moving from raw model outputs to **actionable operational understanding**, including:

* hazard identification  
* likelihood estimation  
* severity assessment  
* consequence evaluation  
* mitigation and operational actions  

---

## 🔗 Model → Risk Integration

Each soft sensor is **automatically connected to its corresponding risk assessment function**.

Prediction → Risk Classification → Operator Guidance

✔ Works in:
- manual mode  
- live streaming mode (mock PIMS → real PIMS-ready)  

✔ The **Treatment module remains model-focused**  
✔ The **Risk module displays only risk-relevant outputs**

---

## 🧩 Current Implemented Soft Sensors

### 🔹 Source / Intake

* **SoSe #9** – Early prediction of turbidity in DWTP inlet  
  Predicts raw water turbidity up to 3 hours ahead.

---

### 🔹 Treatment – Coagulation

* **SoSe #8** – Estimation of turbidity of the coagulation-flocculation process  
  Predicts turbidity after coagulation.

* **RL #5** – RL Optimal FeCl₃ dosage for coagulation process  
  Recommends optimal ferric chloride dosage.

---

### 🔹 Treatment – Ozonation

* **SoSe #10** – Prediction of the ozonation exposure (CT)  
  Estimates disinfection capacity.

* **SoSe #10.1** – Bromate formation model  
  Predicts bromate formation risk.

* **SoSe #10.2** – Coliform removal model  
  Predicts microbial removal efficiency.

---

### 🔹 Distribution

* **SoSe #11** – Aeromonas prediction model  
  Supports biological instability assessment (under evaluation).

---

### 🔹 Hard Sensor Placeholder

* **BactoSense #4** – Placeholder for future operational integration.

---

## ⚙️ Main Functionalities

* Modular FastAPI backend  
* Interactive web-based UI  
* Soft-sensor prediction interfaces  
* Automatic **prediction → risk translation**  
* Mock / live-ready **PIMS-style integration**  
* Risk evaluation across:

  * source conditions  
  * coagulation performance  
  * RL dosage recommendation  
  * ozonation performance  
  * distribution instability  
  * treatment-wide risk  
  * full system (source-to-tap) risk  

* Docker-ready deployment  

---

## 🏗️ Platform Architecture

Source → Treatment → Distribution → Risk  

Extended pipeline:

SCADA → PIMS → API → Models → Risk → Operator Actions  

---

## 📁 Repository Structure

soft_sensors_api/  
├── app/  
│   ├── data_preprocessing/  
│   ├── models/  
│   ├── routes/  
│   ├── services/  
│   ├── static/ui/  
│   ├── main.py  
│   └── model_registry.py  
├── Dockerfile  
├── requirements.txt  
├── README.md  
└── .gitignore  

---

## ⚙️ Installation & Running

### 1. Clone

git clone https://github.com/akrivial/todrinq-platform.git  
cd todrinq-platform  
cd soft_sensors_api  

### 2. Environment

python -m venv .venv  
.\.venv\Scripts\Activate.ps1  

### 3. Install

pip install -r requirements.txt  

### 4. Run

uvicorn app.main:app --reload  

---

## 📊 Access

UI:  
http://127.0.0.1:8000/app  

Swagger:  
http://127.0.0.1:8000/docs  

---

## 🐳 Docker

docker build -t todrinq-platform .  
docker run -p 8000:8000 todrinq-platform  

---

## 🔌 Integration with Waternet (PIMS)

The platform is designed to connect directly to **Waternet PIMS**.

### Steps:

1. Replace mock endpoints with real PIMS data  
2. Map input variables to:
   - turbidity  
   - FeCl₃ dosage  
   - temperature  
   - pH  
   - flow  
   - ozone dosage  

3. Connect PIMS → FastAPI endpoints  
4. Validate model inputs and scaling  
5. Enable continuous live streaming  

---

## 🔧 Development Notes

* Built with **FastAPI (Python)**  
* UI uses **vanilla JS + Chart.js**  
* Models are loaded via `model_registry.py`  
* Risk logic is implemented in `routes/risk.py`  
* Fully compatible with **FIWARE architecture (future NGSI-LD integration)**  
* Designed for **Docker deployment in Waternet infrastructure**

---

## 🌍 Project Context

Developed within:

* 🇪🇺 ToDrinQ – EU Horizon Project (Grant Agreement No. 101082035)  
* 🎓 Delft University of Technology (TU Delft)  
* 💧 Waternet  

The platform supports:

* digital water treatment monitoring  
* soft sensor deployment  
* risk-based decision support  
* modular and interoperable architectures  

---

## 👩‍💻 Author

**Akrivi Alexandraki**  
Engineering Doctorate Candidate – TU Delft  
ToDrinQ Project  

---

## ⚠️ Disclaimer

As of **22 April 2026**, the **only fully operational model integrated with real logic is**:

* **SoSe #8 – Coagulation model (developed by KWR)**  

All other models are:

* structurally integrated  
* connected to the risk framework  
* currently using mock or pre-configured logic  

⚠️ This list will be continuously updated as additional validated models are integrated and connected to real PIMS data.
