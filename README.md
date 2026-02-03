# Docsign - E-Signature Service

A comprehensive e-signature application similar to DocuSign, built with FastAPI and deployable to Vercel.

## Features

- 📝 Document upload and management
- ✍️ Hand-drawn signature capture
- 👥 Multiple signers support
- 📍 Visual drag-and-drop field placement
- 🔒 JWT authentication
- 📄 PDF generation with signatures
- ☁️ Cloud-ready (Vercel Postgres + Blob Storage)

## Local Development

### Prerequisites

- Python 3.9+
- pip

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   python3 -m uvicorn app.main:app --reload
   ```

4. Open http://localhost:8000 in your browser

### Local Storage

By default, the app uses SQLite for the database and local filesystem for file storage. No configuration needed!

## Deploying to Vercel

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Create Vercel Postgres Database

1. Go to your Vercel dashboard
2. Navigate to Storage → Create Database → Postgres
3. Copy the `DATABASE_URL` connection string

### Step 3: Create Vercel Blob Storage

1. In your Vercel dashboard
2. Navigate to Storage → Create Store → Blob
3. Copy the `BLOB_READ_WRITE_TOKEN`

### Step 4: Set Environment Variables

In your Vercel project settings, add:

- `DATABASE_URL` - Your Postgres connection string
- `BLOB_READ_WRITE_TOKEN` - Your Blob storage token
- `SECRET_KEY` - A secure random string for JWT signing

### Step 5: Deploy

```bash
vercel --prod
```

## Environment Variables

See `.env.example` for all available environment variables.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: SQLite (local) / PostgreSQL (production)
- **Storage**: Local filesystem / Vercel Blob
- **PDF**: pypdf, reportlab
- **Auth**: JWT with passlib (Argon2)
- **Frontend**: Vanilla HTML/CSS/JavaScript with pdf.js

## License

MIT
