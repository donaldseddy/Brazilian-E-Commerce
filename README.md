# 🇧🇷 Brazilian E-Commerce – Data Platform (End‑to‑End)

## 📌 Overview

This project is an **end‑to‑end data‑driven e‑commerce platform** built on a modern **Cloud & Data architecture**. It simulates a real Brazilian e‑commerce system by combining:

* **Transactional backend (OLTP)** with Django & PostgreSQL
* **Scalable data engineering pipeline** with AWS Glue & S3
* **Analytical warehouse (OLAP)** with Amazon Redshift
* **Business Intelligence dashboards** with Metabase
* **Infrastructure as Code & CI/CD** using Terraform and GitHub Actions

The project is designed to reflect **real enterprise‑grade architectures** used in data‑driven organizations.

---

## 🎯 Business Objectives

* Centralize e‑commerce transactional data
* Enable scalable analytics on sales, customers, and logistics
* Provide decision‑making dashboards for business teams
* Automate infrastructure deployment and application delivery

---

## 🧱 Global Architecture

**High‑level flow:**

```
Django API
   ↓
PostgreSQL (AWS RDS)
   ↓
S3 (Raw Zone)
   ↓
AWS Glue (PySpark ETL)
   ↓
S3 (Processed Zone)
   ↓
Amazon Redshift
   ↓
Metabase Dashboards
```

---

## ⚙️ Tech Stack

### Backend & Application

* **Django** – REST API & admin
* **PostgreSQL (AWS RDS)** – Transactional database
* **Docker** – Containerization

### Data Engineering & Analytics

* **AWS S3** – Data lake (raw / processed)
* **AWS Glue** – ETL with PySpark
* **Amazon Redshift** – Data warehouse (star schema)
* **Metabase** – BI & data visualization

### Cloud & DevOps

* **Terraform** – Infrastructure as Code
* **GitHub Actions** – CI/CD pipelines
* **AWS IAM / VPC / Security Groups**

---

## 🗄️ Data Model

### OLTP (PostgreSQL – Django)

* customers
* orders
* order_items
* products
* sellers
* payments
* deliveries

### OLAP (Redshift – Star Schema)

**Fact table**

* `fact_sales`

**Dimensions**

* `dim_customer`
* `dim_product`
* `dim_seller`
* `dim_time`
* `dim_location`

---

## 🔄 ETL Pipeline (AWS Glue)

* Extraction from PostgreSQL or CSV dataset
* Data cleaning & normalization
* Business transformations:

  * Revenue calculation
  * Delivery delay computation
  * Customer lifetime value
* Load into Redshift

ETL jobs are written in **PySpark** and orchestrated by AWS Glue.

---

## 📊 BI & Dashboards (Metabase)

Available dashboards:

* Global revenue & trends
* Orders volume by region (Brazil map)
* Delivery performance & delays
* Seller performance ranking
* Customer segmentation (RFM)

---

## 🚀 CI/CD Pipeline

**Automated workflow:**

1. Code linting & tests
2. Docker image build
3. Application deployment
4. Terraform plan & apply

CI/CD ensures **reproducibility, reliability, and scalability**.

---

## 🏗️ Infrastructure as Code (Terraform)

Terraform modules manage:

* VPC & networking
* PostgreSQL RDS
* S3 buckets
* Glue jobs
* Redshift cluster
* IAM roles & policies

---

## 📁 Project Structure

```
brazilian-ecommerce/
├── backend/
│   └── django_app/
├── data/
│   ├── raw/
│   └── processed/
├── glue/
│   └── etl_jobs.py
├── terraform/
│   ├── vpc.tf
│   ├── rds.tf
│   ├── s3.tf
│   ├── glue.tf
│   ├── redshift.tf
│   └── iam.tf
├── ci-cd/
│   └── github-actions.yml
└── README.md
```

---

## 📈 Use Cases & Analytics

* Sales forecasting
* Delivery delay analysis
* Customer lifetime value (CLV)
* Seller performance scoring
* Business KPI monitoring

---

## 🧪 Dataset

Based on the **Brazilian E‑Commerce public dataset (Olist‑inspired)**.

---

## 🔐 Security & Best Practices

* IAM least‑privilege policies
* Environment separation (dev / prod)
* Secrets managed via environment variables
* Private subnets for databases

---

## 🧠 Skills Demonstrated

* Data Engineering (ETL, PySpark, Warehousing)
* Cloud Architecture (AWS)
* Backend Development (Django)
* DevOps & CI/CD
* Infrastructure as Code
* Business Analytics

---

## 📌 Author

**Mr Seddy**
Data / AI Project Manager – Data Engineer

🔗 LinkedIn: *to be added*
📧 Contact: *to be added*

---

## ⭐ Why this project?

This project demonstrates the ability to **design, build, deploy and operate a complete data platform**, bridging **software engineering, data engineering, and business analytics** in a production‑like environment.
