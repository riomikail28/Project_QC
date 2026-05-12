# QC Enterprise — Smart Kitchen Quality Control & Traceability Platform

Enterprise-grade Quality Control, Food Safety Monitoring, and Digital Traceability System for Central Kitchen Operations.

Built with modern web architecture using Flask, Supabase, Vercel, and real-time monitoring technologies.

---

# 🚀 Overview

QC Enterprise is an intelligent monitoring and traceability platform designed for food production facilities, cloud kitchens, and central kitchen operations.

The system helps operational teams monitor production quality, food safety, temperature compliance, barcode traceability, and staff QC activities in real-time through a modern analytics dashboard.

username admin
password admin123
---

# ✨ Core Features

## 📊 Admin Analytics Dashboard
- Real-time production analytics
- QC performance metrics
- Batch monitoring overview
- Failed QC tracking
- Staff productivity insights
- Temperature anomaly alerts
- Audit trail monitoring

---

## 🌡️ Temperature Monitoring
Monitor:
- Freezer temperature
- Chiller temperature
- Room temperature

Features:
- Real-time monitoring
- Threshold alerts
- Historical logs
- Auto anomaly detection
- Temperature photo evidence

---

## 🧾 QC Inspection System
Digital QC workflow for food production:
- Receiving inspection
- Production QC
- Packaging QC
- Final QC release

Supports:
- Photo uploads
- Corrective action logs
- Approval/rejection workflow
- Staff verification
- Timestamp tracking

---

## 📦 Barcode & Traceability
Track every production batch:
- Barcode label generation
- Batch history tracking
- Product traceability
- Production timeline
- Staff activity logs

---

## 📷 Photo Evidence System
Upload and manage:
- Temperature check photos
- Barcode label photos
- Product inspection photos
- QC documentation

Powered by Supabase Storage.

---

## 🔐 Authentication & Security
- Role-based access control
- Admin & Staff permissions
- Protected admin routes
- JWT authentication
- Secure Supabase session validation

---

# 🏗️ Tech Stack

## Frontend
- HTML5
- CSS3
- JavaScript
- Chart.js
- Responsive Enterprise UI

## Backend
- Python Flask
- REST API Architecture
- Modular Services

## Database & Cloud
- Supabase Database
- Supabase Auth
- Supabase Storage
- Realtime Subscriptions

## Deployment
- Vercel (Frontend)
- GitHub Actions CI/CD

---

# 📁 Project Structure

```bash
Project_QC/
│
├── frontend/
│   ├── admin/
│   ├── staff/
│   ├── assets/
│   ├── js/
│   └── css/
│
├── backend/
│   ├── api/
│   ├── services/
│   ├── auth/
│   ├── database/
│   ├── monitoring/
│   └── utils/
│
├── supabase/
│   ├── migrations/
│   ├── policies/
│   └── seed/
│
├── tests/
├── docs/
├── .github/workflows/
├── requirements.txt
├── vercel.json
└── README.md
