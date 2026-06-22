# PetCentre# PetCentre

## Overview

PetCentre is a combined web-based system designed for improving the health and welfare of animals by making veterinary services readily available. Pet owners, rescuers, adopters, pharmacies, and animal welfare organizations commonly communicate over telephone, social media, and informal means. This often makes veterinary services less accessible, timely, and uncoordinated, among many other issues.

PetCentre solves this problem by providing a complete online platform that enables users to:

## Key Features

### Medicine & Pharmacy Services
- **Search for medicines** by species, diseases, strengths, price, and manufacturers
- **Find veterinary pharmacies** located near you
- Browse medicine catalogs and compare options

### Animal Management
- **Record animal profiles** with detailed medical and personal information
- **Post lost and found pets** to help reunite animals with their owners
- **Submit adoption requests** for rescue animals
- **Report animal cruelty** and connect with welfare organizations

### Appointment & Health Services
- **Schedule appointments** with veterinary clinics
- **Receive reminders** for vaccinations, check-ups, and post-operative treatment appointments
- **Blood donation module** that connects suitable donor pets with recipients to increase animal health and well-being

### Administration & Security
- **Role-based access control system** to manage different user categories
- **Secure mobile OTP authentication** for enhanced security
- **Administration portal** for managing:
  - Users and permissions
  - Medicines and pharmaceutical inventory
  - Pharmacy information
  - Reports and analytics
  - Appointment bookings and reminders
  - Adoption bookings and requests
  - Other necessary entities
- **Real-time notification and communication system** to keep users informed and engaged

## Technology Framework

### Frontend
- **Progressive Web Application (PWA)** for cross-device accessibility without requiring native app installation
- **Framework:** Django
- **Styling:** Tailwind CSS

### Backend
- **Architecture:** Monolithic full-stack architecture
- **Framework:** Django for UI components and WebSocket-based real-time communication
- **Real-Time Features:** WebSocket support for live communication and instant push notifications

### Database
- **Primary Database:** PostgreSQL for reliable data management
- **Geospatial Capability:** PostGIS extension enabled for advanced location-based features:
  - Finding nearest pharmacy
  - Locating blood donors by proximity
  - Map-based rescue reporting

### Authentication
- **Email Verification:** Primary authentication method
- **SMS-based Authentication:** Twilio integration for secure mobile OTP authentication

### Real-Time Communication
- **WebSockets:** Live pharmacy chat and instant push notifications for users
- **Chatbot:** Intent-based chatbot to handle common user queries

### DevOps and Deployment
- **Containerization:** Docker for consistent deployment environments
- **Cloud Platform:** AWS for scalable cloud deployment
- **CI/CD Pipeline:** GitHub Actions for automated testing and deployment
- **Infrastructure as Code:** Automated deployment pipeline for continuous integration and delivery

## Project Goals

- Make veterinary services more accessible and timely
- Improve coordination among pet owners, rescuers, adopters, pharmacies, and animal welfare organizations
- Create a unified platform for all animal health-related services
- Promote animal welfare through better health management and communication
