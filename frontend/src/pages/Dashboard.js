/**
 * Dashboard page component - main interface for task management.
 * Displays task summary, statistics, and task list with navigation.
 */

import React, { useState, useEffect } from "react";
import { useAuth } from "../App";
import { useLocation, Link } from "react-router-dom";
import SummaryCard from "../components/SummaryCard";
import TaskList from "../components/TaskList";

const Dashboard = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [activeTab, setActiveTab] = useState("overview");

  // Refresh when path changes (e.g., back/forward or after edits)
  useEffect(() => {
    setRefreshTrigger((prev) => prev + 1);
  }, [location.pathname]);

  const handleTaskUpdate = () => {
    // Trigger refresh of both summary and task list
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleLogout = () => {
    if (window.confirm("Are you sure you want to logout?")) {
      logout();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center mr-3" aria-hidden="true">
                <svg
                  className="h-5 w-5 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
                  />
                </svg>
              </div>
              <h1 className="text-xl font-semibold text-gray-900">
                GenAI Task Manager
              </h1>
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-sm text-gray-600 truncate max-w-[30ch]" title={user?.username || "User"}>
                Welcome, {user?.username || "User"}!
              </span>

              <button
                onClick={handleTaskUpdate}
                className="btn-secondary text-sm"
                title="Refresh tasks"
                type="button"
              >
                Refresh
              </button>

              <Link to="/tasks/new" className="btn-primary" aria-label="Create new task">
                + New Task
              </Link>

              <button onClick={handleLogout} className="btn-secondary" type="button" aria-label="Logout">
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8" aria-label="Tabs">
            <button
              onClick={() => setActiveTab("overview")}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === "overview"
                  ? "border-primary-500 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
              type="button"
              aria-current={activeTab === "overview" ? "page" : undefined}
            >
              📊 Overview
            </button>

            <button
              onClick={() => setActiveTab("tasks")}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === "tasks"
                  ? "border-primary-500 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
              type="button"
              aria-current={activeTab === "tasks" ? "page" : undefined}
            >
              📝 All Tasks
            </button>
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === "overview" && (
          <div className="space-y-8">
            {/* Welcome Section */}
            <div className="text-center">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">
                Your Task Dashboard
              </h2>
              <p className="text-gray-600 max-w-2xl mx-auto">
                Manage your tasks efficiently with AI-powered insights.
              </p>
            </div>

            {/* Summary Cards */}
            <SummaryCard refreshTrigger={refreshTrigger} />

            {/* Quick Actions */}
            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-semibold text-gray-900">
                  Quick Actions
                </h3>
              </div>
              <div className="card-content">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Link
                    to="/tasks/new"
                    className="p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors group"
                  >
                    <div className="text-center">
                      <div className="text-2xl mb-2 group-hover:scale-110 transition-transform">
                        📝
                      </div>
                      <h4 className="font-medium text-gray-900 mb-1">
                        Create Task
                      </h4>
                      <p className="text-sm text-gray-600">
                        Add a new task
                      </p>
                    </div>
                  </Link>

                  <button
                    onClick={() => setActiveTab("tasks")}
                    className="p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors group"
                    type="button"
                  >
                    <div className="text-center">
                      <div className="text-2xl mb-2 group-hover:scale-110 transition-transform">
                        📋
                      </div>
                      <h4 className="font-medium text-gray-900 mb-1">
                        View All Tasks
                      </h4>
                      <p className="text-sm text-gray-600">
                        Browse and manage your tasks
                      </p>
                    </div>
                  </button>

                  <div className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                    <div className="text-center">
                      <div className="text-2xl mb-2">🤖</div>
                      <h4 className="font-medium text-gray-900 mb-1">
                        AI Features
                      </h4>
                      <p className="text-sm text-gray-600">
                        Parsing, prioritization & summaries
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Tasks Preview */}
            <div className="card">
              <div className="card-header">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Recent Tasks
                  </h3>
                  <button
                    onClick={() => setActiveTab("tasks")}
                    className="text-sm text-primary-600 hover:text-primary-700"
                    type="button"
                  >
                    View all →
                  </button>
                </div>
              </div>
              <div className="card-content">
                <TaskList
                  refreshTrigger={refreshTrigger}
                  onTaskUpdate={handleTaskUpdate}
                />
              </div>
            </div>
          </div>
        )}

        {activeTab === "tasks" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-900">All Tasks</h2>
              <Link to="/tasks/new" className="btn-primary" aria-label="Create new task">
                + Create New Task
              </Link>
            </div>

            <TaskList
              refreshTrigger={refreshTrigger}
              onTaskUpdate={handleTaskUpdate}
            />
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
