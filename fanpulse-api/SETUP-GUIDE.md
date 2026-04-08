# FanPulse World Cup 2026 — Complete Setup Guide
# Two repos: fanpulse-api (Cloudflare Workers) + fanpulse-frontend (Cloudflare Pages)

════════════════════════════════════════════════════════
PART 1 — GITHUB
════════════════════════════════════════════════════════

Step 1: Delete your old repository on GitHub
  1. Go to github.com → your old FanPulse repo
  2. Settings → scroll to bottom → Danger Zone → Delete this repository
  3. Type the repo name to confirm

Step 2: Create two new repositories
  Repo 1: fanpulse-api      (this is the Cloudflare Worker — backend)
  Repo 2: fanpulse-frontend (this is the Cloudflare Pages — frontend)
  Both: set to Public, do NOT add README or .gitignore (we have our own)

Step 3: Push fanpulse-api to GitHub
  On your computer, open a terminal in the fanpulse-api folder and run:

    git init
    git add .
    git commit -m "initial: FanPulse API on Cloudflare Workers"
    git branch -M main
    git remote add origin https://github.com/YOUR-USERNAME/fanpulse-api.git
    git push -u origin main

Step 4: Push fanpulse-frontend to GitHub
  In a terminal in the fanpulse-frontend folder:

    git init
    git add .
    git commit -m "initial: FanPulse frontend on Cloudflare Pages"
    git branch -M main
    git remote add origin https://github.com/YOUR-USERNAME/fanpulse-frontend.git
    git push -u origin main


════════════════════════════════════════════════════════
PART 2 — SUPABASE (keep existing project, just run schema)
════════════════════════════════════════════════════════

Step 5: Run the database schema
  1. Go to supabase.com → your existing project
  2. Click SQL Editor in the left sidebar
  3. Click New Query
  4. Open the file: fanpulse-api/schema.sql
  5. Copy the entire contents and paste into the SQL editor
  6. Click Run (green button)
  7. You should see: "Success. No rows returned."

  NOTE: The schema.sql starts with DROP TABLE IF EXISTS statements.
  This safely wipes any old tables and rebuilds them cleanly.
  Your existing Supabase URL and service key do not change.


════════════════════════════════════════════════════════
PART 3 — CLOUDFLARE WORKERS (backend API)
════════════════════════════════════════════════════════

Step 6: Install Wrangler CLI (Cloudflare's deploy tool)
  In your terminal, run:

    npm install -g wrangler

Step 7: Log in to Cloudflare via Wrangler
    wrangler login

  This opens your browser. Log in and authorise Wrangler.

Step 8: Install dependencies
  In the fanpulse-api folder:

    npm install

Step 9: Set your secret environment variables
  Run each of these commands one at a time.
  It will prompt you to paste the value — do not type it directly in the command.

    npx wrangler secret put SUPABASE_URL
    npx wrangler secret put SUPABASE_SERVICE_KEY
    npx wrangler secret put JWT_SECRET
    npx wrangler secret put RAPIDAPI_FOOTBALL_KEY
    npx wrangler secret put SPORTSDB_API_KEY
    npx wrangler secret put YOUTUBE_API_KEY
    npx wrangler secret put NEWS_API_KEY
    npx wrangler secret put ANTHROPIC_API_KEY

  Where to find each value:
    SUPABASE_URL            → Supabase Dashboard → Settings → API → Project URL
    SUPABASE_SERVICE_KEY    → Supabase Dashboard → Settings → API → service_role key
    JWT_SECRET              → make up any random string, at least 32 characters
    RAPIDAPI_FOOTBALL_KEY   → RapidAPI dashboard → your API-Football subscription
    SPORTSDB_API_KEY        → TheSportsDB → your API key
    YOUTUBE_API_KEY         → Google Cloud Console → YouTube Data API v3
    NEWS_API_KEY            → newsapi.org → your account → API key
    ANTHROPIC_API_KEY       → console.anthropic.com → API Keys

Step 10: Deploy the Worker
    npx wrangler deploy

  On success you will see something like:
    Published fanpulse-api (0.5 sec)
    https://fanpulse-api.YOUR-SUBDOMAIN.workers.dev

  COPY THAT URL. You need it in the next step.

Step 11: Test your Worker is live
  Open your browser and visit:

    https://fanpulse-api.YOUR-SUBDOMAIN.workers.dev/health

  You should see:
    {"status":"ok","service":"FanPulse API","runtime":"Cloudflare Workers",...}

  Test the news endpoint:
    https://fanpulse-api.YOUR-SUBDOMAIN.workers.dev/api/news/live

  Test WC 2026 fixtures:
    https://fanpulse-api.YOUR-SUBDOMAIN.workers.dev/api/matches/wc2026


════════════════════════════════════════════════════════
PART 4 — UPDATE FRONTEND WITH YOUR WORKER URL
════════════════════════════════════════════════════════

Step 12: Update API_URL in index.html
  Open fanpulse-frontend/index.html
  Find this line near the bottom (inside the <script> tag):

    const API_URL = 'https://fanpulse-api.YOUR-SUBDOMAIN.workers.dev';

  Replace YOUR-SUBDOMAIN with your actual Cloudflare subdomain from Step 10.

  Save the file, then commit and push:

    cd fanpulse-frontend
    git add index.html
    git commit -m "feat: connect to live Cloudflare Worker"
    git push


════════════════════════════════════════════════════════
PART 5 — CLOUDFLARE PAGES (frontend)
════════════════════════════════════════════════════════

Step 13: Connect fanpulse-frontend to Cloudflare Pages
  1. Go to dash.cloudflare.com
  2. Click Workers & Pages in the left sidebar
  3. Click Create application → Pages → Connect to Git
  4. Select your fanpulse-frontend GitHub repository
  5. Configure the build:
       Framework preset:    None
       Build command:       (leave blank)
       Build output directory: / (root — just a dot)
  6. Click Save and Deploy

  Cloudflare Pages will deploy your index.html and give you a URL like:
    https://fanpulse-frontend.pages.dev

  Every time you push to GitHub, Pages auto-redeploys. Takes about 30 seconds.

Step 14: Update CORS in wrangler.toml
  Now that you have your Pages URL, update the FRONTEND_URL in wrangler.toml:

  Open fanpulse-api/wrangler.toml, find:
    FRONTEND_URL = "https://fanpulse.pages.dev"

  Change it to your actual Pages URL, e.g.:
    FRONTEND_URL = "https://fanpulse-frontend.pages.dev"

  Then redeploy the Worker:
    npx wrangler deploy

Step 15: Add custom domain (optional but recommended)
  In Cloudflare Pages:
    Your project → Custom domains → Add a custom domain
  In Cloudflare Workers:
    Your worker → Settings → Triggers → Custom Domains → Add Custom Domain


════════════════════════════════════════════════════════
PART 6 — LOCAL DEVELOPMENT
════════════════════════════════════════════════════════

To develop locally without deploying:

  1. Copy .dev.vars.example to .dev.vars in fanpulse-api:
       cp .dev.vars.example .dev.vars

  2. Fill in your real values in .dev.vars (this file is gitignored)

  3. Run the Worker locally:
       npm run dev
     → API available at: http://localhost:8787

  4. Update API_URL in index.html temporarily to http://localhost:8787

  5. Open index.html directly in your browser (or use: npx serve . in the frontend folder)


════════════════════════════════════════════════════════
PART 7 — WHAT YOU GET
════════════════════════════════════════════════════════

Backend endpoints (all at https://fanpulse-api.YOUR-SUBDOMAIN.workers.dev):

  GET  /health                        → Worker health check
  POST /api/auth/register             → Create account
  POST /api/auth/login                → Sign in, get JWT
  GET  /api/auth/me                   → My profile (auth required)
  PATCH /api/auth/profile             → Update profile (auth required)
  GET  /api/matches/live              → All live matches
  GET  /api/matches/today             → Today's matches
  GET  /api/matches/wc2026            → WC 2026 fixtures (direct from API-Football)
  GET  /api/matches/fixtures          → Upcoming fixtures
  GET  /api/matches/:id               → Match detail + AI prediction
  GET  /api/matches/:id/events        → Goals, cards, subs
  GET  /api/matches/:id/lineups       → Starting XIs
  GET  /api/matches/:id/highlights    → YouTube highlights
  GET  /api/matches/:id/standings     → League table
  GET  /api/news                      → Published articles
  GET  /api/news/live                 → Live WC news (NewsAPI proxy)
  POST /api/news                      → Create article (admin)
  GET  /api/news/:slug                → Single article
  POST /api/predictions               → Submit prediction (auth required)
  GET  /api/predictions/me            → My predictions (auth required)
  GET  /api/predictions/match/:id     → Score distribution for a match
  GET  /api/predictions/ai/:matchId   → AI model prediction
  GET  /api/leaderboard               → Top fans
  GET  /api/leaderboard/countries     → Country battle standings
  GET  /api/leaderboard/user/:id      → Single user rank
  GET  /api/highlights/wc             → WC highlights
  GET  /api/highlights/league/:name   → League highlights
  GET  /api/highlights/search         → Search highlights
  GET  /api/chat/rooms                → Chat rooms
  GET  /api/chat/:roomId              → Messages in a room
  POST /api/chat/:roomId              → Send a message (auth required)
  POST /api/ai/chat                   → AI assistant (Claude, Pro Plus)
  GET  /api/ai/preview/:matchId       → AI match preview

Cron jobs (run automatically via Cloudflare):
  Every 1 min  → live score sync from API-Football
  Every 2 min  → score finished match predictions
  Every 6 hrs  → league standings sync
  Every 12 hrs → AI predictions for upcoming matches


════════════════════════════════════════════════════════
TROUBLESHOOTING
════════════════════════════════════════════════════════

Problem: /health returns an error
  → Check: npx wrangler deploy ran without errors
  → Check: the Worker name in wrangler.toml matches what Cloudflare shows

Problem: /api/news/live returns supabase_fallback
  → Your NEWS_API_KEY is not set or is invalid
  → Run: npx wrangler secret put NEWS_API_KEY   (paste your key when prompted)
  → Then redeploy: npx wrangler deploy

Problem: /api/matches/wc2026 returns empty matches
  → This is EXPECTED before the tournament starts
  → API-Football publishes WC 2026 fixtures 3-6 months before June 2026
  → The frontend shows demo data automatically in this case

Problem: CORS errors in browser console
  → Make sure FRONTEND_URL in wrangler.toml matches your Pages URL exactly
  → Redeploy after changing it: npx wrangler deploy

Problem: "Invalid token" errors after logging in
  → Make sure JWT_SECRET is set: npx wrangler secret put JWT_SECRET
  → It must be the same value every deployment (don't change it after users register)

Problem: AI chat returns 503
  → ANTHROPIC_API_KEY is not set
  → Run: npx wrangler secret put ANTHROPIC_API_KEY
