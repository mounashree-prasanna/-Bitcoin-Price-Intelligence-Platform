# 💰  Bitcoin Price Intelligence Platform

An automated, scalable ELT pipeline for ingesting, transforming, and visualizing live cryptocurrency market data using **Apache Airflow**, **Snowflake**, **dbt**, and **Superset**.

---

## 🚀 Project Overview

This project aims to automate the ingestion and transformation of live cryptocurrency data for real-time analytics. Using **Apache Airflow**, the pipeline orchestrates regular extraction of price and volume data from public APIs, loads raw data into **Snowflake**, and transforms it using **dbt** models. The cleaned data is visualized through **Superset dashboards**, enabling stakeholders to track market trends and make timely decisions.

---

## 🛠️ Tech Stack

| Category           | Tools Used                     |
|--------------------|--------------------------------|
| Orchestration      | Apache Airflow                 |
| Data Warehouse     | Snowflake                      |
| Transformation     | dbt (data build tool)          |
| Visualization      | Apache Superset                |
| Language           | Python, SQL                    |
| Deployment         | Docker (optional), Cloud-hosted (optional) |

---

## 🌟 Key Features

- End-to-end ELT automation using open-source tools
- Modular, reusable dbt models for scalable transformation
- Reduced manual reporting effort by 50%
- Instant insights from live crypto market data

---

## ⚙️ How It Works

1. **Airflow DAG** is scheduled to run every X minutes:
   - Extracts live crypto data via coinAPI
   - Loads raw data into a Snowflake staging table using ETL pipeline

2. **dbt models**:
   - Clean, transform, and normalize raw data
   - Create analytics-ready tables such as daily prices, volumes, trends

3. **Superset Dashboards**:
   - Visualize trends like price changes, volume spikes, moving averages
   - Filterable by time window, coin type, or exchange

---

