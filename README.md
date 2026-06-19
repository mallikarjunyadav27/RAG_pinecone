# Pinecone Document Upload System

A full-stack application for uploading and managing documents with Pinecone vector database integration and a React frontend.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Setup](#project-setup)
3. [Backend Setup](#backend-setup)
4. [Frontend Setup](#frontend-setup)
5. [Running the Application](#running-the-application)
6. [Document Upload](#document-upload)

---

## Prerequisites

Before you begin, ensure you have the following installed on your local machine:

- **Python 3.8 or higher** - [Download Python](https://www.python.org/downloads/)
- **Node.js (v14 or higher)** and **npm** - [Download Node.js](https://nodejs.org/)
- **Git** - [Download Git](https://git-scm.com/)
- **Pinecone API Key** - [Get API Key](https://www.pinecone.io/)

---

## Project Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd RAG_pinecone
```

### 2. Create a Virtual Environment (Backend)

Navigate to the backend directory and create a Python virtual environment:

```bash
cd backend
python -m venv venv
```

#### Activate Virtual Environment

**On Windows (PowerShell):**
```bash
.venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```bash
venv\Scripts\activate.bat
```

**On macOS/Linux:**
```bash
source venv/bin/activate
```

---

## Backend Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the `backend` directory and add your Pinecone API credentials:

```
PINECONE_API_KEY=your_api_key_here
PINECONE_INDEX_NAME=your_index_name
```

### 3. Run the Backend Server

```bash
uvicorn main:app --reload --port 8000
```

The backend API will be available at: `http://localhost:8000`

---

## Frontend Setup

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Start the Development Server

```bash
npm start
```

The frontend will open automatically in your browser at: `http://localhost:3000`

---

## Running the Application

### Start Backend

```bash
cd backend
# Activate virtual environment (if not already active)
.venv\Scripts\Activate.ps1  # Windows PowerShell
source venv/bin/activate     # macOS/Linux

# Run the server
uvicorn main:app --reload --port 8000
```

### Start Frontend (in a new terminal)

```bash
cd frontend
npm start
```

Both services should now be running:
- **Backend API:** `http://localhost:8000`
- **Frontend:** `http://localhost:3000`

---

## Document Upload

### How to Upload Documents

1. Open the application in your browser at `http://localhost:3000`
2. Navigate to the upload section
3. Select your document files (PDF, TXT, DOCX, etc.)
4. Click the **Upload** button
5. Wait for the document processing to complete
6. Your documents are now indexed in Pinecone and ready for queries

### Supported Formats

- PDF (.pdf)
- Text (.txt)
- Word Documents (.docx)
- Markdown (.md)

---

## Project Structure

```
RAG_pinecone/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── venv/
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   ├── App.css
│   │   └── index.js
│   ├── public/
│   │   └── index.html
│   └── package.json
└── README.md
```

---

## Troubleshooting

### Backend Issues

- **Module not found:** Ensure the virtual environment is activated and dependencies are installed
- **Port 8000 in use:** Change port with `--port 8001` in the uvicorn command
- **Pinecone connection error:** Verify your API key in the `.env` file

### Frontend Issues

- **npm install fails:** Try clearing npm cache with `npm cache clean --force`
- **Port 3000 in use:** Node will automatically use port 3001 or higher
- **Module errors:** Delete `node_modules` and `package-lock.json`, then run `npm install` again

---

## Support

For issues or questions, please contact the development team or create an issue in the repository.

---

**Last Updated:** June 2026