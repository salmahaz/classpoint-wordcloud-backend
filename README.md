Backend Explanation – ClassPoint Word Cloud

This repository (classpoint-wordcloud-backend) represents the backend (server-side) implementation for the ClassPoint Word Cloud application. It works together with the frontend application available at:
https://github.com/salmahaz/classpoint-wordcloud-app

Purpose of the Backend

The backend is responsible for handling all server-side logic that the frontend depends on. Specifically, it:

Receives word submissions from users (students)

Stores and manages submitted data using a database

Handles real-time communication (e.g., live word updates) between users

Sends processed data back to the frontend so it can render the word cloud dynamically

In short, the frontend handles user interaction and visualization, while this backend handles data processing, persistence, and real-time updates.

Main Responsibilities

API Endpoints: Accept requests from the frontend (e.g., submitting words, retrieving word data)

Real-Time Communication: Uses socket-based communication to broadcast updates instantly to connected users

Database Interaction: Stores and retrieves word data through defined models and database utilities

Application Logic: Coordinates the flow between incoming requests, database operations, and outgoing responses

Database & Deployment Note

The database instance used by this backend is deployed on Render.

Render automatically spins down (suspends) inactive services, including database instances.
Because of this:

If the backend or database has been inactive for some time, it must be reactivated

Until the Render database is running again, the backend will not function correctly

As a result, the frontend may fail to load data or submit words

To run the project successfully, the database service on Render must be active, and any required environment variables (such as database connection strings) must be correctly configured.
