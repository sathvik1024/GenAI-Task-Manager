# GenAI Task Manager

A full-stack AI-powered task management application built with Flask (Python) backend and React (JavaScript) frontend. Features natural language task parsing, intelligent prioritization, and automated summaries using OpenAI's GPT models.

## 🚀 Features

### Backend (Flask)
- **User Authentication**: JWT-based signup/login system
- **Task CRUD Operations**: Create, read, update, delete tasks
- **AI-Powered Task Parsing**: Convert natural language to structured task data
- **Intelligent Prioritization**: AI-driven task ordering by urgency
- **Automated Summaries**: Daily/weekly AI-generated productivity summaries
- **Task Scheduling**: Background reminders for upcoming deadlines
- **Search & Filtering**: Advanced task filtering by status, priority, category

### Frontend (React)
- **Modern UI**: Responsive design with Tailwind CSS
- **Dashboard**: Overview with statistics and AI summaries
- **Task Management**: Intuitive task creation and editing
- **AI Integration**: Natural language task input with real-time parsing
- **Real-time Updates**: Dynamic task status changes
- **Mobile Responsive**: Works seamlessly on all devices

## 🛠️ Tech Stack

### Backend
- **Flask**: Web framework
- **MongoDB**: Database 
- **Flask-JWT-Extended**: Authentication
- **OpenAI API**: AI features
- **APScheduler**: Background task scheduling
- **Flask-CORS**: Cross-origin resource sharing

### Frontend
- **React 18**: UI framework
- **React Router**: Client-side routing
- **Axios**: HTTP client
- **Tailwind CSS**: Styling framework
- **Modern JavaScript**: ES6+ features

## 📦 Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- OpenAI API key (for AI features)

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   JWT_SECRET_KEY=your_jwt_secret_key_here
   DATABASE_URL=sqlite:///tasks.db
   FLASK_ENV=development
   ```

5. **Run the backend**:
   ```bash
   python app.py
   ```
   
   Backend will be available at: `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the development server**:
   ```bash
   npm start
   ```
   
   Frontend will be available at: `http://localhost:3000`

## 🎯 Usage

### Getting Started

1. **Access the application**: Open `http://localhost:3000` in your browser
2. **Create an account**: Sign up with username, email, and password
3. **Login**: Use your credentials to access the dashboard

### Creating Tasks

#### Method 1: AI-Powered Natural Language Input
1. Click "New Task" or use the AI parser
2. Enter natural language description:
   ```
   "Finish the quarterly report by Friday 5pm, high priority, work category"
   ```
3. AI will extract:
   - Title: "Finish the quarterly report"
   - Deadline: Friday 5pm
   - Priority: High
   - Category: Work
   - Suggested subtasks

#### Method 2: Manual Form Input
1. Fill out the structured form manually
2. Add subtasks, set deadlines, choose priority
3. Categorize your task

### Managing Tasks

- **View Tasks**: Browse all tasks with filtering and search
- **Update Status**: Quick status changes (pending → in progress → completed)
- **Edit Tasks**: Modify any task details
- **Delete Tasks**: Remove completed or unwanted tasks
- **AI Prioritization**: Let AI reorder tasks by urgency

### AI Features

- **Task Parsing**: Convert "Buy groceries tomorrow evening" → structured task
- **Smart Prioritization**: AI analyzes deadlines and importance
- **Daily Summaries**: "You completed 5 tasks today! Focus on the urgent project deadline tomorrow."
- **Weekly Reports**: Comprehensive productivity insights

## 📁 Project Structure

```
genai-task-manager/
├── backend/
│   ├── app.py                 # Flask application entry point
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example          # Environment variables template
│   ├── database.py           # Database configuration
│   ├── models.py             # SQLAlchemy models (User, Task)
│   ├── routes/
│   │   ├── auth_routes.py    # Authentication endpoints
│   │   ├── task_routes.py    # Task CRUD endpoints
│   │   └── ai_routes.py      # AI-powered endpoints
│   └── services/
│       ├── ai_service.py     # OpenAI API integration
│       └── scheduler.py      # Background task scheduler
├── frontend/
│   ├── package.json          # Node.js dependencies
│   ├── tailwind.config.js    # Tailwind CSS configuration
│   ├── src/
│   │   ├── App.js            # Main React component
│   │   ├── utils/api.js      # API client utilities
│   │   ├── pages/
│   │   │   ├── Login.js      # Authentication page
│   │   │   ├── Dashboard.js  # Main dashboard
│   │   │   └── TaskForm.js   # Task creation/editing
│   │   └── components/
│   │       ├── TaskList.js   # Task list with filtering
│   │       ├── TaskItem.js   # Individual task card
│   │       └── SummaryCard.js # AI summary display
│   └── public/
│       └── index.html        # HTML template
└── README.md                 # This file
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here

# Database Configuration
DATABASE_URL=sqlite:///tasks.db

# Flask Configuration
FLASK_ENV=development
```

### Database Configuration

The application uses SQLite by default for easy setup. To use PostgreSQL:

1. Install PostgreSQL and create a database
2. Update `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://username:password@localhost/genai_tasks
   ```
3. Install PostgreSQL adapter:
   ```bash
   pip install psycopg2-binary
   ```

## 🤖 AI Features Configuration

### OpenAI API Setup

1. **Get API Key**: Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. **Create API Key**: Generate a new secret key
3. **Add to Environment**: Set `OPENAI_API_KEY` in your `.env` file
4. **Verify Setup**: The app will show AI availability status

### AI Capabilities

- **Task Parsing**: Extracts title, deadline, priority, category, and subtasks
- **Prioritization**: Considers deadlines, priority levels, and task context
- **Summaries**: Generates motivational and actionable daily/weekly reports
- **Subtask Suggestions**: Breaks down complex tasks into manageable steps

## 🚀 Deployment

### Backend Deployment (Heroku/Railway/DigitalOcean)

1. **Prepare for production**:
   ```bash
   pip freeze > requirements.txt
   ```

2. **Set environment variables** on your hosting platform

3. **Database migration** (if using PostgreSQL):
   ```bash
   flask db upgrade
   ```

### Frontend Deployment (Vercel/Netlify)

1. **Build the application**:
   ```bash
   npm run build
   ```

2. **Deploy the `build` folder** to your hosting platform

3. **Configure API URL** for production in your deployment settings

## 🧪 Testing

### Backend Testing
```bash
cd backend
python -m pytest tests/
```

### Frontend Testing
```bash
cd frontend
npm test
```

