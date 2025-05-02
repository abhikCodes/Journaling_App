# JournalMind - AI-Powered Journaling App

JournalMind is a modern journaling application with AI-powered insights to help you track your thoughts, feelings, and personal growth over time.

## Features

- ✏️ Write daily journal entries with a clean, intuitive interface
- 🏷️ Tag entries for easy organization and filtering
- 🤖 AI assistant to provide insights and answer questions about your journal
- 🔍 Search functionality to find specific entries
- 🔒 Secure authentication with Google OAuth

## Tech Stack

- **Backend**: FastAPI, Python, SQLite (via Tortoise ORM)
- **Frontend**: React, TailwindCSS, Framer Motion
- **Authentication**: Google OAuth

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Running the Backend

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables (create a `.env` file in the backend directory):
   ```
   SECRET_KEY=your-secret-key
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   DATABASE_URL=sqlite://db.sqlite3
   ```

4. Run the FastAPI server:
   ```
   uvicorn app.main:app --reload
   ```

5. The API will be available at http://localhost:8000 and the Swagger documentation at http://localhost:8000/docs

### Running the Frontend

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm run dev
   ```

4. The frontend will be available at http://localhost:5173

## Project Structure

```
journaling_app/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   ├── routes/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── config.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── styles/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── api.js
│   ├── package.json
│   └── index.html
└── docker-compose.yml
```

## Design Language

The application uses a Duolingo-inspired design language with:
- Rounded corners and playful elements
- Vibrant, friendly color palette
- Satisfying micro-interactions and animations
- Clean, accessible typography
