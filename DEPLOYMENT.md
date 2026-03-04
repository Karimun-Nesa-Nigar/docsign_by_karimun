# Deployment Guide: Vercel + Supabase

This application uses **Supabase** (Free Tier) for its Database (PostgreSQL) and File Storage, and **Vercel** for hosting.

## 1. Setup Supabase
1.  Go to [Supabase.com](https://supabase.com) and sign up.
2.  Create a **New Project**.
3.  Once the project is ready:
    -   Go to **Project Settings** -> **Database**.
    -   Copy the **Connection String (URI)**. It should look like: `postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres`
    -   **Important**: Vercel requires the `?sslmode=require` parameter usually, but our code handles appending it if missing.
    -   Go to **Project Settings** -> **API**.
    -   Copy the **Project URL** (`SUPABASE_URL`) and **anon public key** (`SUPABASE_KEY`).

## 2. Configure Storage in Supabase
1.  Go to **Storage** in the Supabase Dashboard.
2.  Create a new **Bucket** named `uploads`.
    -   Make it **Public** (or keep private if you implement signed URLs, but our code assumes it can download with the key).
    -   *Note*: For this demo, making it Public is easiest for viewing, but our code uses the server-side client which has admin rights if you use the `service_role` key. However, we are using the standard key.
    -   **Recommendation**: For simplicty, make the bucket **Public**.
3.  Create another Bucket named `signed_docs`.
    -   Make it **Public**.

## 3. Deploy to Vercel
1.  Push this code to your GitHub repository.
2.  Go to [Vercel.com](https://vercel.com) and **Add New Project**.
3.  Import your GitHub repository.
4.  In the **Environment Variables** section, add:
    -   `DATABASE_URL`: Your Supabase Connection String (from Step 1).
    -   `SUPABASE_URL`: Your Supabase Project URL.
    -   `SUPABASE_KEY`: Your Supabase Anon Key.
5.  Click **Deploy**.

## 4. Run Migration (First Time Only)
The application uses SQLAlchemy. In a real production app, you should use Alembic for migrations.
For this simple app, the tables are created automatically when the app starts if they don't exist, **BUT** Vercel functions might check this on every request which is slow.
*Check `app/database.py` and `app/main.py`*: The current code creates tables on startup: `models.Base.metadata.create_all(bind=engine)`.
This works fine for this scale!

## Troubleshooting
-   **500 Error on Upload**: Check if your Supabase Buckets (`uploads`, `signed_docs`) exist and permissions are correct.
-   **Database Error**: Ensure your `DATABASE_URL` is correct and you replaced `[YOUR-PASSWORD]` with your actual password.
