/**
 * TaskList component for displaying and managing tasks.
 * Includes filtering, searching, and task actions.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { taskAPI, aiAPI, handleApiError, getAuthToken } from '../utils/api';
import TaskItem from './TaskItem';

const DEBOUNCE_MS = 350;

const TaskList = ({ refreshTrigger, onTaskUpdate }) => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    status: '',
    priority: '',
    category: '',
    search: ''
  });
  const [prioritizing, setPrioritizing] = useState(false);

  // Debounced search text to avoid firing request on every keystroke
  const [searchRaw, setSearchRaw] = useState('');
  useEffect(() => setSearchRaw(filters.search), [filters.search]);

  const debouncedSearch = useMemo(() => {
    // keep a stable value that updates after DEBOUNCE_MS
    let handle;
    let value = searchRaw;
    return {
      get current() {
        return value;
      },
      set(next, onDone) {
        value = next;
        clearTimeout(handle);
        handle = setTimeout(() => onDone(next), DEBOUNCE_MS);
      },
      cancel() {
        clearTimeout(handle);
      }
    };
  }, [searchRaw]);

  // Kick off fetch when mounted / refreshTrigger changes / filters change
  useEffect(() => {
    const timer = setTimeout(() => {
      const token = getAuthToken();
      console.log('TaskList: Checking for token...', token ? 'found' : 'not found');
      if (token) {
        fetchTasks();
      } else {
        console.log('TaskList: No token available, skipping API calls');
        setLoading(false);
      }
    }, 500); // allow auth to settle

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTrigger, filters.status, filters.priority, filters.category]);

  // Separate effect for search to use debounce
  useEffect(() => {
    debouncedSearch.set(filters.search, () => fetchTasks());
    return () => debouncedSearch.cancel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.search, refreshTrigger]);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      setError('');

      console.log('TaskList: Fetching tasks...');
      console.log('TaskList: Current filters:', filters);

      // Filter out empty values (guard against non-string just in case)
      const activeFilters = Object.fromEntries(
        Object.entries(filters).filter(
          ([_, value]) => typeof value === 'string' && value.trim() !== ''
        )
      );
      console.log('TaskList: Active filters:', activeFilters);

      const response = await taskAPI.getTasks(activeFilters);
      console.log('TaskList: API response:', response);
      console.log(
        'TaskList: Number of tasks received:',
        response.tasks ? response.tasks.length : 0
      );

      setTasks(Array.isArray(response.tasks) ? response.tasks : []);
      console.log('TaskList: Tasks set in state');
    } catch (err) {
      console.error('TaskList: Error fetching tasks:', err);
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (filterName, value) => {
    setFilters((prev) => ({
      ...prev,
      [filterName]: value
    }));
  };

  const clearFilters = () => {
    setFilters({
      status: '',
      priority: '',
      category: '',
      search: ''
    });
  };

  const handleTaskAction = async (taskId, action, data = {}) => {
    try {
      let response;

      switch (action) {
        case 'update':
          response = await taskAPI.updateTask(taskId, data);
          break;
        case 'delete':
          await taskAPI.deleteTask(taskId);
          setTasks((prev) => prev.filter((t) => t.id !== taskId));
          if (onTaskUpdate) onTaskUpdate();
          return;
        default:
          return;
      }

      // Update task in list safely
      if (response && response.task) {
        setTasks((prev) =>
          prev.map((t) => (t.id === taskId ? response.task : t))
        );
      }

      if (onTaskUpdate) onTaskUpdate();
    } catch (err) {
      setError(handleApiError(err));
    }
  };

  const handlePrioritizeTasks = async () => {
    try {
      setPrioritizing(true);
      const incompleteTasks = tasks.filter((t) => t.status !== 'completed');
      const taskIds = incompleteTasks.map((t) => t.id);

      const response = await aiAPI.prioritizeTasks(taskIds);

      // Reorder tasks based on AI prioritization
      const prioritizedTasks = Array.isArray(response.prioritized_tasks)
        ? response.prioritized_tasks
        : [];
      const completedTasks = tasks.filter((t) => t.status === 'completed');

      setTasks([...prioritizedTasks, ...completedTasks]);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setPrioritizing(false);
    }
  };

  const getFilteredTasksCount = () => {
    const activeFilters = Object.values(filters).filter(
      (value) => typeof value === 'string' && value.trim() !== ''
    );
    return activeFilters.length > 0 ? tasks.length : null;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="loading-spinner mr-2"></div>
        <span>Loading tasks...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters and Search */}
      <div className="card">
        <div className="card-content">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Search
              </label>
              <input
                type="text"
                className="input"
                placeholder="Search tasks..."
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                className="input"
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
              >
                <option value="">All Status</option>
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Priority
              </label>
              <select
                className="input"
                value={filters.priority}
                onChange={(e) => handleFilterChange('priority', e.target.value)}
              >
                <option value="">All Priorities</option>
                <option value="urgent">Urgent</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <input
                type="text"
                className="input"
                placeholder="Filter by category"
                value={filters.category}
                onChange={(e) => handleFilterChange('category', e.target.value)}
              />
            </div>
          </div>

          <div className="flex justify-between items-center">
            <div className="flex space-x-2">
              <button onClick={clearFilters} className="btn-secondary text-sm">
                Clear Filters
              </button>

              <button
                onClick={handlePrioritizeTasks}
                disabled={prioritizing || tasks.length === 0}
                className="btn-primary text-sm flex items-center"
              >
                {prioritizing ? (
                  <>
                    <div className="loading-spinner mr-2"></div>
                    AI Prioritizing...
                  </>
                ) : (
                  <>🤖 AI Prioritize</>
                )}
              </button>
            </div>

            <div className="text-sm text-gray-600">
              {getFilteredTasksCount() !== null
                ? `${tasks.length} filtered tasks`
                : `${tasks.length} total tasks`}
            </div>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      {/* Tasks List */}
      {tasks.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 text-6xl mb-4">📝</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No tasks found</h3>
          <p className="text-gray-600 mb-4">
            {Object.values(filters).some((f) => typeof f === 'string' && f.trim() !== '')
              ? 'Try adjusting your filters or search terms.'
              : 'Get started by creating your first task!'}
          </p>
          <a href="/tasks/new" className="btn-primary">
            Create Task
          </a>
        </div>
      ) : (
        <div className="space-y-4">
          {console.log('TaskList: Rendering tasks:', tasks)}
          {tasks.map((task, index) => {
            console.log(`TaskList: Rendering task ${index}:`, task);
            return <TaskItem key={task.id} task={task} onAction={handleTaskAction} />;
          })}
        </div>
      )}
    </div>
  );
};

export default TaskList;
