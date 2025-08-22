# 🚀 Quick Start Guide

Get your GenAI Task Manager up and running in 5 minutes!

## Prerequisites

- Python 3.8+ installed
- Node.js 16+ installed
- OpenAI API key (optional, for AI features)

## Option 1: Automated Setup (Recommended)

Run the setup script to automatically configure everything:

```bash
python setup.py
```

This will:
- Check system requirements
- Set up Python virtual environment
- Install all dependencies
- Create start scripts
- Generate .env file template

## Option 2: Manual Setup

### Backend Setup

1. **Navigate to backend and create virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   
   # Activate virtual environment
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-openai-api-key-here
   JWT_SECRET_KEY=your-secret-key-here
   ```

### Frontend Setup

1. **Navigate to frontend and install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

## Running the Application

### Start Backend (Terminal 1)
```bash
cd backend
# Activate virtual environment first
python app.py
```

### Start Frontend (Terminal 2)
```bash
cd frontend
npm start
```

## Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000

## First Steps

1. **Create Account**: Sign up with username, email, and password
2. **Try AI Features**: Create a task using natural language:
   ```
   "Finish project report by Friday 5pm, high priority, work category"
   ```
3. **Explore Dashboard**: View your tasks, statistics, and AI summaries

## Getting Your OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign up or log in
3. Create a new API key
4. Copy and paste into your `.env` file

**Note**: AI features will be disabled without an API key, but basic task management still works!

## Troubleshooting

### Common Issues

**Backend won't start:**
- Make sure virtual environment is activated
- Check if all dependencies are installed: `pip install -r requirements.txt`

**Frontend won't start:**
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check Node.js version: `node --version`

**CORS errors:**
- Make sure backend is running on port 5000
- Check that Flask-CORS is installed

**AI features not working:**
- Verify OpenAI API key in `.env` file
- Check API key has sufficient credits
- Ensure internet connection

### Need Help?

- Check the full [README.md](README.md) for detailed documentation
- Open an issue on GitHub
- Review error messages in browser console and terminal

## What's Next?

- Explore AI task parsing with natural language
- Try the intelligent task prioritization
- Set up daily/weekly AI summaries
- Customize task categories and priorities
- Use the search and filtering features

Happy task managing! 🎉
