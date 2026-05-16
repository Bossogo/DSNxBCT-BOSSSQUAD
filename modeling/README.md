# Reviewer Simulator Stack

A full-stack application designed to predict and simulate how a specific consumer would rate and review any unseen product or business. By combining historical reviewer styles, average ratings, typical lengths, and cultural expressions, the simulator generates highly authentic, personalized review previews.

The repository consists of two main folders:
1. **`agent/`** — FastAPI Backend (Retrieval-Augmented Generation engine, data pipelines, and FAISS indexing).
2. **`web/`** — React + TypeScript + Tailwind CSS v4 Frontend (A beautiful, jargon-free consumer dashboard).

---

## 🛠️ Prerequisites

Ensure you have the following installed on your machine:
* **Python 3.10 or higher** (for the backend engine)
* **Node.js 18 or higher** & **npm** (for the frontend app)

---

## ⚙️ Step-by-Step Development Setup

To run the full stack locally for development, follow the setup steps for both the backend and frontend.

### 1. Backend Setup (`agent/`)

The backend processes raw datasets, generates vector embeddings, performs semantic retrieval with FAISS, and runs predictions via Groq API.

1. **Navigate to the agent directory:**
   ```bash
   cd agent
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # On macOS/Linux:
   python3 -m venv .venv
   source .venv/bin/activate

   # On Windows (PowerShell):
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install the required packages:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the `agent` folder (or copy `.env.example` if available) and insert your Groq API Key:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

5. **Initialize fallback datasets (Optional):**
   If you need to quickly load fallbacks for Amazon or Goodreads before running full ingestion:
   ```bash
   python -m data.prepare_raw_data
   ```

6. **Build the FAISS vector index & ingest review data:**
   Process the dataset files to create the retrieval mapping:
   ```bash
   python -m data.ingest
   ```

7. **Start the FastAPI local development server:**
   ```bash
   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   * The API will now be running on **`http://127.0.0.1:8000`**
   * Live documentation will be available at **`http://127.0.0.1:8000/docs`**

---

### 2. Frontend Setup (`web/`)

The frontend is a hot-reloading React TypeScript app powered by Vite and Tailwind CSS. It communicates directly with the FastAPI server on port 8000.

1. **Open a new terminal session and navigate to the web directory:**
   ```bash
   cd web
   ```

2. **Install Node packages:**
   ```bash
   npm install
   ```

3. **Start the Vite development server:**
   ```bash
   npm run dev
   ```
   * The hot-reloading React frontend will spin up on **`http://localhost:5173`** (or the next available port).
   * Open `http://localhost:5173` in your web browser to interact with the Reviewer Simulator dashboard!

---

## 🔄 How They Work Together

```
   ┌────────────────────────────────┐
   │        React Client UI         │
   │    (http://localhost:5173)     │
   └───────────────┬────────────────┘
                   │
                   │ (HTTP POST /simulate, GET /platforms, GET /users)
                   ▼
   ┌────────────────────────────────┐
   │        FastAPI Server          │
   │    (http://127.0.0.1:8000)     │
   └───────────────┬────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌─────────────────┐ ┌─────────────────┐
│   FAISS Index   │ │    Groq LLM     │
│ (Local Vector)  │ │ (LLaMA 3 Cloud) │
└─────────────────┘ └─────────────────┘
```

1. The **React UI** loads a list of active reviewers from the FastAPI `/users` endpoint.
2. When you select a reviewer, enter product details, and hit **Predict Review**:
   * The client sends a request payload containing the selected reviewer ID, item details, and writing preference to the backend's `/simulate` endpoint.
   * The **FastAPI backend** performs a cosine similarity lookup over the FAISS vector index to pull actual past reviews written by this user.
   * The backend feeds the user's rating tendencies, length preferences, common topics, and semantic past reviews into LLaMA-3 (via Groq) to generate a predicted rating and review text.
   * The backend returns this predicted data, including the full array of `retrieved_reviews_used` (with product names, ratings, and original review texts).
3. The React app renders the prediction using a typewriter simulation alongside cards of their past reviews.

---

## 🛠️ Quick Troubleshooting Guide

* **CORS Blockage:** The backend FastAPI server has `CORSMiddleware` configured to allow all origins (`*`) by default, making development requests from local port 5173 seamless. Make sure the backend server runs on `http://127.0.0.1:8000`.
* **Port Already in Use:** If port 8000 or 5173 is occupied, you can kill the active process or let Vite auto-select another port (the API is configured to look for the backend on port 8000).
* **Missing Groq API Key:** If your simulations return an empty string or error, double-check that `.env` is loaded in the `agent` folder and your Groq API Key is active.
