/**
 * SummaryCard component for displaying AI-generated task summaries.
 * Shows daily/weekly summaries and task statistics.
 */

import React, { useState, useEffect } from 'react';
import { aiAPI, taskAPI, handleApiError, getAuthToken } from '../utils/api';

const SummaryCard = ({ refreshTrigger }) => {
  const [summary, setSummary] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [period, setPeriod] = useState('daily');
  const [aiAvailable, setAiAvailable] = useState(true);

  useEffect(() => {
    // Add a delay to ensure authentication is established
    const timer = setTimeout(() => {
      const token = getAuthToken();
      console.log('SummaryCard: Checking for token...', token ? 'found' : 'not found');
      if (token) {
        fetchData();
      } else {
        console.log('SummaryCard: No token available, skipping API calls');
        setLoading(false);
      }
    }, 500); // Increased delay

    return () => clearTimeout(timer);
  }, [period, refreshTrigger]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError('');

      console.log('SummaryCard: Fetching task statistics...');
      // Fetch task statistics
      const statsResponse = await taskAPI.getStats();
      setStats(statsResponse);
      console.log('SummaryCard: Stats fetched successfully');

      // Check AI availability and fetch summary
      try {
        const aiHealthResponse = await aiAPI.healthCheck();
        setAiAvailable(aiHealthResponse.openai_api_configured);

        if (aiHealthResponse.openai_api_configured) {
          const summaryResponse = await aiAPI.generateSummary(period);
          setSummary(summaryResponse);
        } else {
          setSummary(null);
        }
      } catch (aiError) {
        console.warn('AI service unavailable:', aiError);
        setAiAvailable(false);
        setSummary(null);
      }
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const getCompletionPercentage = () => {
    if (!stats || stats.total_tasks === 0) return 0;
    return Math.round((stats.completed_tasks / stats.total_tasks) * 100);
  };

  const getProgressColor = (percentage) => {
    if (percentage >= 80) return 'bg-success-500';
    if (percentage >= 60) return 'bg-primary-500';
    if (percentage >= 40) return 'bg-warning-500';
    return 'bg-danger-500';
  };

  if (loading) {
    return (
      <div className="card">
        <div className="card-content">
          <div className="flex items-center justify-center py-8">
            <div className="loading-spinner mr-2"></div>
            <span>Loading summary...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* AI Summary Card */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              {aiAvailable ? '🤖 AI Summary' : '📊 Task Summary'}
            </h3>
            <div className="flex space-x-2">
              <button
                onClick={() => setPeriod('daily')}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  period === 'daily'
                    ? 'bg-primary-100 text-primary-800'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                Daily
              </button>
              <button
                onClick={() => setPeriod('weekly')}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  period === 'weekly'
                    ? 'bg-primary-100 text-primary-800'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                Weekly
              </button>
            </div>
          </div>
        </div>

        <div className="card-content">
          {error ? (
            <div className="text-danger-600 text-sm">{error}</div>
          ) : aiAvailable && summary ? (
            <div>
              <p className="text-gray-700 mb-4">{summary.summary}</p>
              {summary.generated_at && (
                <div className="text-xs text-gray-500">
                  Generated {new Date(summary.generated_at).toLocaleString()}
                </div>
              )}
            </div>
          ) : !aiAvailable ? (
            <div className="text-center py-4">
              <div className="text-gray-400 text-2xl mb-2">🔧</div>
              <p className="text-gray-600 text-sm mb-2">
                AI summaries are not available
              </p>
              <p className="text-xs text-gray-500">
                Configure your OpenAI API key to enable AI features
              </p>
            </div>
          ) : (
            <div className="text-gray-600">No summary available</div>
          )}
        </div>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Tasks */}
          <div className="card">
            <div className="card-content">
              <div className="flex items-center">
                <div className="p-2 bg-primary-100 rounded-lg">
                  <span className="text-primary-600 text-xl">📝</span>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-600">Total Tasks</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.total_tasks}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Completed Tasks */}
          <div className="card">
            <div className="card-content">
              <div className="flex items-center">
                <div className="p-2 bg-success-100 rounded-lg">
                  <span className="text-success-600 text-xl">✅</span>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-600">Completed</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.completed_tasks}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Pending Tasks */}
          <div className="card">
            <div className="card-content">
              <div className="flex items-center">
                <div className="p-2 bg-warning-100 rounded-lg">
                  <span className="text-warning-600 text-xl">⏳</span>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-600">Pending</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.pending_tasks}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Completion Rate */}
          <div className="card">
            <div className="card-content">
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <span className="text-purple-600 text-xl">📈</span>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-600">Completion Rate</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.completion_rate}%</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Progress Bar */}
      {stats && stats.total_tasks > 0 && (
        <div className="card">
          <div className="card-content">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Overall Progress</span>
              <span className="text-sm text-gray-600">{getCompletionPercentage()}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${getProgressColor(getCompletionPercentage())}`}
                style={{ width: `${getCompletionPercentage()}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>{stats.completed_tasks} completed</span>
              <span>{stats.total_tasks - stats.completed_tasks} remaining</span>
            </div>
          </div>
        </div>
      )}

      {/* Urgent Tasks Alert */}
      {stats && (stats.urgent_tasks > 0 || stats.overdue_tasks > 0) && (
        <div className="card border-warning-200 bg-warning-50">
          <div className="card-content">
            <div className="flex items-center">
              <span className="text-warning-600 text-xl mr-3">⚠️</span>
              <div>
                <h4 className="font-medium text-warning-800">Attention Required</h4>
                <p className="text-sm text-warning-700">
                  {stats.urgent_tasks > 0 && `${stats.urgent_tasks} urgent task${stats.urgent_tasks > 1 ? 's' : ''}`}
                  {stats.urgent_tasks > 0 && stats.overdue_tasks > 0 && ' • '}
                  {stats.overdue_tasks > 0 && `${stats.overdue_tasks} overdue task${stats.overdue_tasks > 1 ? 's' : ''}`}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SummaryCard;
