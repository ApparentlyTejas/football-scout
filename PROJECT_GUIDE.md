projectguide.md
AI Football Scout — Master Project Guide
0. Project Overview
We are building an AI-powered football scouting and recruitment platform for a two-person Master's project.

The system allows a coach, scout, or sporting director to describe the type of player they need in natural language.

Example:

Find me a U23 defensive midfielder under €15M who fits a high-pressing 4-3-3.

The system will:

Parse the scouting request.
Convert it into structured requirements.
Filter players using football data.
Calculate advanced player features.
Normalize statistics across leagues and positions.
Rank players using machine learning/statistical models.
Calculate tactical compatibility.
Find statistically/tactically similar players.
Use an LLM to explain the recommendations.
Present the results in an interactive scouting dashboard.
The project must be designed as a serious software engineering + machine learning + AI Master's project, not as a simple LLM wrapper.

1. Main Objective
Build:

An AI football scouting platform that combines football statistics, machine learning, tactical analysis, player similarity, financial constraints, and LLM-based reasoning to identify and explain suitable transfer targets.

The system should answer:

Who should we scout?
Why is this player suitable?
How well does the player fit our tactical system?
How does the player compare to our existing players?
Who are similar players?
What are the player's strengths and weaknesses?
Is the player financially realistic?
What are the risks?
Which candidates are the best alternatives?
2. Project Constraints
We are two Master's students.

We want:

$0 development/data cost where possible.
Open/free football datasets.
A strong backend.
A real ML component.
A real AI component.
A professional frontend.
Reproducible experiments.
Dockerized development.
Proper testing.
Good documentation.
Avoid unnecessary complexity.

Do NOT initially build:

Full-match computer vision.
Real-time video analysis.
Kubernetes.
Large microservice architecture.
Kafka unless genuinely required.
Multiple vector databases.
Autonomous AI agents.
Paid commercial football-data APIs.
The architecture should be a modular monolith with background workers.

3. Data Sources
3.1 API-Football
Use the free tier where possible.

Purpose:

Players
Teams
Leagues
Fixtures
General statistics
Transfers
Injuries
Other metadata
Important:

The free tier has a limited request quota.

Therefore:

Never call API-Football directly from the frontend.
Cache API responses.
Store useful data in PostgreSQL.
Use background jobs for ingestion.
Avoid repeated requests.
Design the system to work from our own database after ingestion.
3.2 StatsBomb Open Data
Use StatsBomb Open Data for research-quality event data.

Potential uses:

Passes
Shots
Carries
Pressure
Defensive actions
Events
Lineups
Match context
360 data where available
Use this dataset primarily for:

Feature engineering.
Tactical analysis.
Event-based player profiles.
Research experiments.
Credit StatsBomb appropriately.

3.3 SkillCorner Open Data
Optional advanced/research component.

Use if time allows.

Potential uses:

Player tracking.
Off-ball movement.
Physical metrics.
Tactical movement.
Passing.
Phases of play.
Do NOT make SkillCorner a hard dependency for the MVP.

If identity matching between datasets becomes difficult, keep the datasets logically separate and use SkillCorner only for specific research experiments.

4. High-Level Architecture
                    USER
                     |
                     v
              NEXT.JS FRONTEND
                     |
                     v
                FASTAPI API
                     |
        +------------+-------------+
        |            |             |
        v            v             v
   SCOUT ENGINE   PLAYER API   AI SERVICE
        |
        +----------------------+
        |                      |
        v                      v
   ML/RANKING              PGVECTOR
        |                      |
        +----------+-----------+
                   |
                   v
              POSTGRESQL
                   ^
                   |
             DATA PIPELINE
                   ^
          +--------+---------+
          |        |         |
          v        v         v
    API-Football StatsBomb SkillCorner
          |
          v
    RAW / CLEANED DATA

Background processing:

                REDIS
                  |
                  v
               CELERY
                  |
       +----------+----------+
       |          |          |
       v          v          v
   Data ETL   ML Jobs   Embedding Jobs

5. Technology Stack
Frontend
Next.js
TypeScript
Tailwind CSS
shadcn/ui
TanStack Query
Recharts
Backend
Python
FastAPI
Pydantic
SQLAlchemy
Database
PostgreSQL
pgvector
Data/ML
Pandas
NumPy
scikit-learn
XGBoost
SciPy where useful
AI
LLM API
Embedding model
Keep the LLM provider abstracted behind our own AI service.

Background processing
Redis
Celery
Testing
Pytest
FastAPI TestClient
Playwright
Frontend unit tests
Infrastructure
Docker
Docker Compose
GitHub Actions
6. Repository Structure
Use a monorepo.

ai-football-scout/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── lib/
│   ├── hooks/
│   ├── types/
│   └── tests/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── scout/
│   │   ├── ai/
│   │   ├── ml/
│   │   └── main.py
│   │
│   └── tests/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── external/
│   └── README.md
│
├── ml/
│   ├── notebooks/
│   ├── experiments/
│   ├── training/
│   ├── evaluation/
│   └── models/
│
├── scripts/
│   ├── ingest/
│   ├── processing/
│   └── database/
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── ml.md
│   ├── data.md
│   └── research.md
│
├── docker/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── PROJECT_GUIDE.md

7. Database Architecture
Use PostgreSQL as the central database.

Core tables:

users
clubs
leagues
seasons
players
player_positions
player_stats
player_season_stats
player_contracts
transfers
matches
match_events
team_profiles
player_profiles
player_embeddings
scouting_queries
scouting_results
scouting_reports
model_versions

8. Player Model
A player should contain:

id
name
date_of_birth
age
nationality
current_club_id
primary_position
secondary_positions
preferred_foot
market_value
contract_expiry
height

Do not duplicate large statistical datasets directly into the player table.

Keep statistics in separate tables.

9. Statistics Model
Store statistics by:

player
season
competition
team
position
minutes

Example metrics:

goals
assists
xg
xa
shots
shots_on_target
passes
progressive_passes
progressive_carries
key_passes
dribbles
pressures
tackles
interceptions
recoveries
duels
aerial_duels
ball_losses

Only use metrics appropriate to the available data.

Never invent missing data.

10. Data Pipeline
The data pipeline must be reproducible.

External Source
      |
      v
Raw Data
      |
      v
Validation
      |
      v
Cleaning
      |
      v
Identity Resolution
      |
      v
Normalization
      |
      v
Feature Engineering
      |
      v
PostgreSQL
      |
      v
ML Dataset

Each pipeline step should be independently executable.

11. Data Identity Resolution
This is an important research/software problem.

Different sources may use different IDs for the same player.

Create an internal:

player_id

and mapping tables such as:

player_external_ids

Example:

internal_player_id
source
external_player_id

Sources:

api_football
statsbomb
skillcorner

Never assume IDs from different providers are interchangeable.

12. Feature Engineering
Raw football statistics should not directly determine the final ranking.

Create meaningful features.

Examples:

goals_per_90
assists_per_90
xg_per_90
xa_per_90
progressive_passes_per_90
progressive_carries_per_90
pressures_per_90
tackles_per_90
interceptions_per_90

Also calculate:

Percentiles.
Position-adjusted scores.
League-adjusted scores.
Minutes reliability.
Age-adjusted potential.
Team-context-adjusted statistics where possible.
13. Position-Specific Models
Do NOT use exactly the same scoring formula for every position.

Example:

Striker
Important:

xG
Goals
Shots
Shot quality
Pressing
Touches in box
Progressive runs

Winger
Important:

Progressive carries
Dribbles
xA
Key passes
Crosses
Chance creation
Pressing

Defensive midfielder
Important:

Progressive passes
Pass completion
Interceptions
Recoveries
Press resistance
Progressive carries
Defensive actions

Centre-back
Important:

Defensive actions
Aerials
Interceptions
Progressive passes
Ball progression
Errors
Passing

The exact weights must be experimentally evaluated rather than arbitrarily claimed to be correct.

14. League Normalization
A major research component.

Raw statistics from different leagues cannot always be directly compared.

Possible approaches:

Percentile within competition.
Z-score within competition.
Position + league normalization.
League-strength adjustment.
Compare multiple approaches experimentally.

Document the methodology.

15. Player Profile Vector
Create a standardized player representation.

Example:

[
  finishing,
  chance_creation,
  progression,
  passing,
  ball_retention,
  pressing,
  defensive_work,
  dribbling,
  aerial_ability,
  physicality
]

Values should be normalized.

This vector can be used for:

Similarity.
Clustering.
Visualization.
Tactical fit.
ML models.
16. Player Embeddings
Use pgvector.

Store a vector representing the player's football profile.

Example:

player_id
embedding
model_version
created_at

Use embeddings for:

Find players similar to Player X.

And:

Find players similar to a desired tactical profile.

Do not claim that embeddings are inherently "football intelligence."

Evaluate whether they actually improve retrieval quality.

17. Scouting Query Pipeline
User:

Find me a U23 defensive midfielder under €15M who fits a high-pressing 4-3-3.

Pipeline:

Natural language
      |
      v
Query Parser
      |
      v
Structured Query
      |
      v
Hard Filters
      |
      v
Statistical Ranking
      |
      v
Tactical Fit
      |
      v
Similarity Search
      |
      v
Risk / Financial Analysis
      |
      v
Top Candidates
      |
      v
LLM Explanation

18. Structured Scouting Query
Example:

{
  "position": "defensive_midfielder",
  "max_age": 23,
  "max_market_value": 15000000,
  "formation": "4-3-3",
  "playing_style": [
    "high_press"
  ],
  "priority_attributes": [
    "pressing",
    "progression",
    "ball_retention"
  ]
}

The LLM can help parse the natural-language request, but the backend must validate the resulting structure.

Never blindly trust LLM-generated filters.

19. Candidate Filtering
Start with cheap database filters.

Example:

10,000 players
      |
      +-- Age
      +-- Position
      +-- Minutes
      +-- Market value
      +-- League
      |
      v
500 candidates

Do not run expensive ML or LLM operations on thousands of players unnecessarily.

20. Scout Scoring
Initial model:

Scout Score =
    Tactical Fit
    +
    Performance
    +
    Potential
    +
    Financial Fit
    -
    Risk

Do not permanently hard-code arbitrary percentages.

Instead:

Create a baseline.
Build an ML model.
Evaluate it.
Compare different weighting strategies.
Document the results.
21. Machine Learning
Start simple.

Baseline:

Weighted statistical score.
Then experiment with:

Logistic regression.
Random forest.
XGBoost.
K-means clustering.
PCA.
Nearest-neighbor similarity.
Do not use deep learning unless the data and research question justify it.

22. What Is the ML Model Predicting?
This must be explicitly defined.

Possible research targets:

Option A — Tactical fit
Predict whether a player fits a given tactical profile.

Option B — Player role classification
Classify players into tactical roles.

Option C — Similar-player retrieval
Find players with similar performance/tactical profiles.

Option D — Future performance
Predict future performance based on previous seasons.

Choose one primary ML research problem.

Do not attempt all four as equal thesis objectives.

23. Tactical Team Profile
Represent a team's desired style.

Example:

formation:
4-3-3

pressing:
high

possession:
high

build_up:
short

attack_width:
high

transition:
fast

defensive_line:
high

Convert tactical requirements into measurable player attributes.

Example:

High press
    ↓
pressures
counterpressing actions
defensive work
recovery actions

24. Tactical Fit
Example:

Player Profile
       +
Team Tactical Profile
       |
       v
Tactical Compatibility

Output:

Tactical Fit: 91/100

Pressing:       95
Progression:    88
Ball retention: 84
Defensive work: 90

Every score must have an explainable calculation.

25. AI Architecture
The LLM should NOT be the main ranking engine.

Correct:

Football Data
     |
     v
ML / Rules
     |
     v
Ranked Players
     |
     v
LLM
     |
     v
Explanation

Incorrect:

Football Data
     |
     v
LLM
     |
     v
"Player X is best"

The second architecture is difficult to validate and vulnerable to hallucinations.

26. AI Tools
The AI service may expose internal tools such as:

search_players()
get_player_profile()
get_player_statistics()
get_tactical_fit()
get_similar_players()
compare_players()
get_team_profile()
get_transfer_information()

The LLM can call these tools to answer questions.

27. AI Questions
Support questions such as:

Why is Player X ranked first?

Who is similar to Player X?

What are Player X's weaknesses?

How does Player X compare to our current midfielder?

Why is Player Y cheaper but ranked lower?

Which player is the safest transfer?

Which player has the highest potential?

Find me alternatives to Player X.

28. Explainability
Every recommendation should have evidence.

Example:

Player A — 92/100

Why:
+ 94th percentile progressive passing
+ 91st percentile pressing
+ 89th percentile ball retention
+ Age 21
+ Estimated value within budget

Concern:
- Limited top-level minutes
- Lower aerial contribution

The frontend should allow the user to inspect the underlying metrics.

29. Frontend Pages
Build:

/
├── Dashboard
│
├── /scout
│   ├── Natural-language search
│   ├── Filters
│   └── Results
│
├── /players
│   ├── Player list
│   └── Player profile
│
├── /players/:id
│   ├── Overview
│   ├── Statistics
│   ├── Tactical profile
│   ├── Similar players
│   └── AI analysis
│
├── /compare
│   └── Player comparison
│
├── /teams/:id
│   └── Team tactical profile
│
└── /reports/:id
    └── AI scouting report

30. Player Profile UI
Example:

PLAYER NAME
Position | Age | Club | Value

--------------------------------
SCOUT SCORE
92 / 100

TACTICAL FIT
91 / 100

PERFORMANCE
88 / 100

POTENTIAL
95 / 100

FINANCIAL FIT
90 / 100
--------------------------------

ATTRIBUTES

Pressing       ██████████ 94
Progression    █████████  89
Passing        █████████   87
Creativity     ████████    81
Defending      █████████   88

--------------------------------

AI SCOUT REPORT

[Why sign him?]

--------------------------------

SIMILAR PLAYERS

Player A
Player B
Player C

31. API Design
Example endpoints:

GET /api/v1/players
GET /api/v1/players/{id}
GET /api/v1/players/{id}/stats
GET /api/v1/players/{id}/similar
GET /api/v1/players/{id}/tactical-fit

GET /api/v1/teams
GET /api/v1/teams/{id}

POST /api/v1/scout/search
POST /api/v1/scout/compare
POST /api/v1/scout/report

GET /api/v1/reports/{id}

POST /api/v1/ai/query

Keep API versioning from the beginning:

/api/v1/

32. Authentication
For MVP:

Email/password or OAuth.
JWT/session authentication.
User roles.
Possible roles:

admin
scout
coach

Do not spend excessive time on authentication.

The core research/product functionality matters more.

33. Background Jobs
Use Celery + Redis.

Jobs:

fetch_api_football_data
process_statsbomb_data
process_skillcorner_data
normalize_statistics
calculate_player_features
generate_player_embeddings
recalculate_player_scores
generate_report

The frontend should not wait for long-running data processing.

34. Caching
Redis can cache:

popular player profiles
player searches
similar-player results
team profiles
AI responses where appropriate

But do not cache everything blindly.

35. Error Handling
Backend must handle:

External API failure.
Rate limits.
Invalid player IDs.
Missing statistics.
Missing seasons.
LLM failures.
Database errors.
Background job failures.
Return useful API errors.

Never expose internal stack traces to users.

36. Testing Strategy
Unit Tests
Test:

Statistics calculations.
Per-90 calculations.
Percentiles.
League normalization.
Scout scoring.
Tactical fit.
Query parsing.
Data validation.
Integration Tests
Test:

API
+
PostgreSQL
+
Scout Engine

End-to-End Tests
Test:

User enters scouting query
        ↓
Results appear
        ↓
Player profile opens
        ↓
AI report loads

37. ML Evaluation
This is essential for the Master's project.

Do not simply say:

Our model works.

Define evaluation metrics.

Depending on the chosen ML task:

Precision
Recall
F1
ROC-AUC
MAE
RMSE
NDCG
Precision@K
Recall@K

For player ranking/retrieval, consider:

Precision@5
Precision@10
NDCG@10

38. Baselines
Always compare your model against simple baselines.

Example:

Baseline 1:
Rank by goals/90

Baseline 2:
Rank by position-specific statistics

Baseline 3:
Weighted statistical model

Model:
XGBoost / ML model

Model + Tactical Fit:
Final system

This makes the research significantly stronger.

39. Train/Test Splitting
Do not randomly mix all seasons if that causes data leakage.

Prefer temporal evaluation where appropriate.

Example:

2019-2022 → training
2023 → validation
2024 → test

The exact years depend on the available dataset.

The goal is to simulate:

Could the model have made this recommendation using only information available at the time?

40. Data Leakage
Be extremely careful.

Do not use future information to predict past outcomes.

For example:

If predicting 2023 performance:

Do not include:

2024 statistics.
Later transfer value.
Future injuries.
Future team performance.
Document all feature timestamps.

41. Model Versioning
Store:

model_name
version
training_date
dataset_version
features
metrics

Example:

tactical_fit_model
v1.2
trained: 2026-05-10
NDCG@10: 0.81

This makes experiments reproducible.

42. Data Versioning
Maintain dataset versions.

Example:

dataset_v1
dataset_v2
dataset_v3

Record:

Source.
Download date.
Processing version.
Number of players.
Number of matches.
Number of events.
43. Docker Architecture
Docker Compose:

services:

frontend
backend
worker
postgres
redis

Development:

docker compose up

Everything should start locally.

44. Environment Variables
Use:

DATABASE_URL
REDIS_URL

API_FOOTBALL_KEY

LLM_API_KEY
EMBEDDING_API_KEY

JWT_SECRET

Never commit secrets.

Provide:

.env.example

45. Git Workflow
Use GitHub.

Branches:

main
develop

feature/player-api
feature/scout-engine
feature/ml-model
feature/frontend-dashboard

Pull requests should include:

Description.
Tests.
Screenshots where relevant.
Related issue.
46. Two-Person Team Split
Student 1 — Backend/Data/ML
Responsible for:

Database.
API.
Data ingestion.
ETL.
Feature engineering.
ML models.
Evaluation.
Background jobs.
Student 2 — Frontend/AI/Integration
Responsible for:

Next.js.
UI/UX.
Dashboards.
Visualization.
AI integration.
LLM tools.
Scouting reports.
End-to-end integration.
Both students collaborate on:

Architecture.
Tactical model.
Research methodology.
Final evaluation.
Documentation.
Avoid creating completely separate projects that never integrate.

47. Development Phases
PHASE 0 — Planning
Before writing code:

Define exact research question.
Define MVP.
Define datasets.
Define architecture.
Define database schema.
Define ML objective.
Define evaluation metrics.
Deliverables:

architecture.md
research.md
data.md
database-schema.md

PHASE 1 — Repository Setup
Create:

frontend
backend
ml
scripts
docs

Set up:

Git.
Docker.
Docker Compose.
PostgreSQL.
Redis.
FastAPI.
Next.js.
CI.
Goal:

docker compose up

→ frontend works
→ backend works
→ database works
→ Redis works

PHASE 2 — Database
Implement:

SQLAlchemy models.
Alembic migrations.
PostgreSQL schema.
pgvector.
Create seed data.

Goal:

Backend
   ↓
PostgreSQL
   ↓
Players visible through API

PHASE 3 — Data Ingestion
Implement API-Football ingestion.

Then StatsBomb.

Then optional SkillCorner.

Each source should have its own adapter:

data_sources/
├── api_football.py
├── statsbomb.py
└── skillcorner.py

Do not mix provider-specific logic throughout the application.

Goal:

External data
→ normalized internal model
→ PostgreSQL

PHASE 4 — Data Processing
Implement:

Player identity resolution.
Per-90 metrics.
Percentiles.
Position groups.
League normalization.
Feature generation.
Create reproducible scripts.

Goal:

Raw data
→ clean ML-ready dataset

PHASE 5 — Player Profiles
Build:

Player profile API.
Statistics API.
Player frontend.
Charts.
Attribute profiles.
Goal:

A user can search for a player and see a complete profile.

PHASE 6 — Baseline Scout
Before ML:

Build a simple scoring engine.

Example:

Position match
+
Age
+
Budget
+
Position statistics
+
Basic tactical requirements

Return top 20 candidates.

This is your baseline.

PHASE 7 — ML Scout
Build the actual ML system.

Experiment with:

Feature selection.
Normalization.
XGBoost.
Similarity.
Clustering.
Evaluate against the baseline.

Goal:

Demonstrate that the ML system improves candidate retrieval/ranking.

PHASE 8 — Tactical Fit
Implement:

Team Profile
+
Player Profile
=
Tactical Fit

Start with interpretable rules.

Then experiment with ML if appropriate.

Goal:

A coach can specify a tactical style and receive players compatible with it.

PHASE 9 — Player Similarity
Implement pgvector.

Generate player embeddings.

Support:

Find players similar to X.

Then:

Find players similar to X
AND
under €15M
AND
under 23

PHASE 10 — AI Scout
Add LLM.

First implement:

Natural language
→ structured query

Then:

Ranked candidates
→ LLM
→ scouting explanation

Then add tool calling.

Goal:

The AI becomes a useful interface over the actual scouting engine.

PHASE 11 — Scouting Reports
Generate reports containing:

Executive summary

Tactical fit

Statistical strengths

Weaknesses

Financial fit

Risk

Similar players

Recommendation

Evidence

Reports should always be grounded in database/model results.

PHASE 12 — Advanced Dashboard
Build:

Scout search.
Player comparison.
Tactical radar.
Similar players.
AI report.
Shortlist.
Team profile.
Focus on usability.

PHASE 13 — Evaluation
Run experiments.

Compare:

Simple baseline
vs
Statistical model
vs
ML model
vs
ML + tactical model

Evaluate.

Document results.

Create charts.

PHASE 14 — Production Hardening
Add:

Authentication.
Rate limiting.
Caching.
Error handling.
Logging.
Background jobs.
API documentation.
Database indexes.
Security checks.
PHASE 15 — Final Deployment
Deploy:

Frontend
Backend
PostgreSQL
Redis
Workers

Make sure the entire system is reproducible.

48. MVP Definition
The MVP is complete when a user can:

Open the website.
Search for a player.
View the player's statistics.
Enter a natural-language scouting request.
Receive ranked players.
See the score of each player.
See why each player was selected.
Compare two players.
Ask the AI questions about the recommendations.
Find similar players.
Everything else is optional.

49. Advanced Features
Only implement these if the MVP is stable.

Possible extensions:

Transfer simulation.
Squad composition analysis.
Salary constraints.
Injury risk.
Player aging curves.
Future performance prediction.
Automated shortlist generation.
Recruitment budget optimization.
SkillCorner tactical tracking.
Multi-season player trajectories.
Explainable AI visualizations.
50. What NOT to Build
Do not add features just because they sound impressive.

Avoid:

AI agents everywhere
Blockchain
NFTs
Real-time video
Computer vision
Kubernetes
Microservices
Custom LLM training
Custom vector database
Mobile app
Social network

unless the core system is already finished.

51. Security
Never:

Commit API keys.
Expose database credentials.
Trust raw LLM output.
Allow arbitrary SQL from users.
Return internal errors.
Store unnecessary personal data.
Validate all AI-generated structured queries using Pydantic schemas.

52. Performance
Optimize in this order:

Database queries
        ↓
Indexes
        ↓
Caching
        ↓
Background jobs
        ↓
ML inference
        ↓
LLM calls

Do not prematurely optimize.

53. Important Backend Principle
Keep these layers separate:

API
 ↓
Service
 ↓
Repository
 ↓
Database

Example:

ScoutController
      ↓
ScoutService
      ↓
PlayerRepository
      ↓
PostgreSQL

ML should also be separated:

ScoutService
      ↓
RankingService
      ↓
ML Model

AI should be separated:

ScoutService
      ↓
AIService
      ↓
LLM Provider

54. Important AI Principle
The LLM is not the source of truth.

Source of truth:

PostgreSQL
+
Football datasets
+
ML models

LLM role:

Interpret
Explain
Summarize
Compare
Answer questions

If the LLM says something unsupported by the data, the system should not present it as fact.

55. Important Research Principle
Every major ML decision must be explainable.

Document:

Why this feature?
Why this normalization?
Why this model?
Why these weights?
Why this metric?
Why this evaluation split?

The goal is not merely to create an application.

The goal is to demonstrate that the proposed methodology is useful and measurable.

56. Suggested Research Question
Primary research question:

Can a data-driven machine learning system identify football players who are tactically compatible with a target team's playing style while considering performance, age, and financial constraints?

Possible subquestions:

Does league normalization improve cross-league player ranking?
Does tactical information improve player retrieval?
Does ML outperform a simple statistical baseline?
Does player embedding improve similar-player retrieval?
Can an LLM accurately explain model-generated scouting recommendations?
57. Final System
The completed system should look like:

                  USER
                   |
                   v
            NEXT.JS FRONTEND
                   |
                   v
              FASTAPI
                   |
                   v
            SCOUTING ENGINE
                   |
        +----------+----------+
        |          |          |
        v          v          v
    DATABASE       ML       VECTOR
        |        MODELS     SEARCH
        |          |          |
        +----------+----------+
                   |
                   v
              TOP PLAYERS
                   |
                   v
               AI SERVICE
                   |
                   v
            SCOUTING REPORT
                   |
                   v
             FRONTEND UI

Data:

API-Football
StatsBomb
SkillCorner
      |
      v
    ETL
      |
      v
PostgreSQL
      |
      v
Feature Engineering
      |
      v
ML / Tactical Models

58. Implementation Rules for Claude
When helping us implement this project, follow these rules.

Rule 1
Work incrementally.

Never generate the entire application at once.

Implement one phase at a time.

Rule 2
Before writing significant code, explain:

What we are building.
Why.
Which files will change.
How it connects to the architecture.
Rule 3
Prefer simple solutions.

Do not introduce new infrastructure unless necessary.

Rule 4
Do not invent football data.

If a dataset does not contain a metric, tell us.

Rule 5
Do not invent API-Football endpoints.

Verify endpoint structure against the current API documentation when necessary.

Rule 6
Do not make the LLM responsible for deterministic calculations.

Statistics and scoring belong in Python/backend code.

Rule 7
Every ML experiment must be reproducible.

Record:

Dataset.
Features.
Model.
Hyperparameters.
Metrics.
Rule 8
Every feature should have a reason.

If a feature does not contribute to the product or research question, question whether it belongs.

Rule 9
Do not overengineer.

Prefer:

FastAPI
PostgreSQL
Redis
Celery
Next.js

over a large distributed architecture.

Rule 10
When we get stuck, debug systematically.

Use:

Problem
↓
Reproduce
↓
Logs
↓
Hypothesis
↓
Small test
↓
Fix
↓
Regression test

59. Claude's Role
Claude should act as:

Senior backend engineer.
ML engineer.
Data engineer.
AI engineer.
Software architect.
Master's project supervisor.
Claude should guide us rather than blindly generating code.

For every phase:

Explain the objective.
Explain the architecture.
List the tasks.
Implement one task.
Test it.
Verify it.
Move to the next task.
Do not skip testing.

60. First Tasks
Start the project in exactly this order:

STEP 1
Create Git repository.

STEP 2
Create monorepo structure.

STEP 3
Create Docker Compose.

STEP 4
Start PostgreSQL.

STEP 5
Start Redis.

STEP 6
Create FastAPI application.

STEP 7
Create Next.js application.

STEP 8
Connect FastAPI to PostgreSQL.

STEP 9
Create Alembic migrations.

STEP 10
Create initial database schema.

STEP 11
Create health-check endpoint.

STEP 12
Create first frontend page.

STEP 13
Create API-Football ingestion adapter.

STEP 14
Import a small dataset.

STEP 15
Verify player data in PostgreSQL.

STEP 16
Create player API.

STEP 17
Create player profile frontend.

STEP 18
Add StatsBomb ingestion.

STEP 19
Build feature engineering pipeline.

STEP 20
Build baseline scout.

STEP 21
Evaluate baseline.

STEP 22
Build ML model.

STEP 23
Evaluate ML model.

STEP 24
Build tactical-fit model.

STEP 25
Add pgvector.

STEP 26
Add player similarity.

STEP 27
Build natural-language scout query.

STEP 28
Integrate LLM.

STEP 29
Generate AI scouting reports.

STEP 30
Build final dashboard.

STEP 31
Run final evaluation.

STEP 32
Dockerize and deploy.

STEP 33
Write technical documentation.

STEP 34
Write Master's thesis/report.

61. Definition of Done
The project is finished when:

[✓] Frontend works
[✓] Backend works
[✓] Database works
[✓] Data ingestion works
[✓] Data is normalized
[✓] Player profiles work
[✓] Baseline exists
[✓] ML model exists
[✓] ML model is evaluated
[✓] Tactical fit exists
[✓] Player similarity exists
[✓] AI scout exists
[✓] AI explanations are grounded
[✓] Player comparison works
[✓] Tests exist
[✓] Docker works
[✓] Documentation exists
[✓] Research evaluation exists
[✓] System is reproducible

62. Final Goal
The final user experience should be:

USER:

"I need a U23 defensive midfielder,
under €15M, good at pressing,
comfortable in possession,
and suitable for a 4-3-3."

                    ↓

              AI FOOTBALL SCOUT

                    ↓

        500 candidates filtered

                    ↓

        ML ranking + tactical fit

                    ↓

             TOP 5 PLAYERS

                    ↓

       ┌────────────────────────┐
       │ PLAYER A — 92/100      │
       │                        │
       │ Tactical fit: 94       │
       │ Performance: 89        │
       │ Potential: 95          │
       │ Financial: 91          │
       │                        │
       │ WHY?                   │
       │ Strong pressing and    │
       │ progressive passing    │
       │ profile for the        │
       │ requested system.      │
       └────────────────────────┘

                    ↓

USER:

"Who is the safest option?"

                    ↓

AI:

"Player A has the highest current-performance
score and lowest uncertainty, while Player B
has greater long-term potential."

                    ↓

USER:

"Find cheaper alternatives."

                    ↓

             AI SCOUT

                    ↓

             3 alternatives

The final product should feel like a real football recruitment intelligence platform, while the underlying system demonstrates serious work in backend engineering, data engineering, machine learning, information retrieval, tactical modeling, and AI.

END OF PROJECT GUIDE
When beginning implementation, start with STEP 1 only. Do not jump ahead. Verify each phase before moving to the next one.