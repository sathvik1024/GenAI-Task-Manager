/**
 * TaskList component for displaying and managing tasks.
 * Includes filtering, searching, and task actions.
 */

import React, { useState, useEffect, useRef } from "react";
import { taskAPI, aiAPI, handleApiError, getAuthToken } from "../utils/api";
import TaskItem from "./TaskItem";

const DEBOUNCE_MS = 350;

const TaskList = ({ refreshTrigger, onTaskUpdate }) => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({
    status: "",
    priority: "",
    category: "",
    search: "",
  });
  const [prioritizing, setPrioritizing] = useState(false);

  // refs to avoid setting state after unmount and to debounce search
  const mountedRef = useRef(true);
  const debounceTimerRef = useRef(null);

  useEffect(() => {
    mountedRef.current = true;

    const timer = setTimeout(() => {
      const token = getAuthToken();
      if (token) {
        fetchTasks();
      } else {
        if (mountedRef.current) setLoading(false);
      }
    }, 500); // allow auth to settle

    return () => {
      mountedRef.current = false;
      clearTimeout(timer);
      clearTimeout(debounceTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTrigger, filters.status, filters.priority, filters.category]);

  // Debounce search
  useEffect(() => {
    clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => {
      if (mountedRef.current) fetchTasks();
    }, DEBOUNCE_MS);

    return () => clearTimeout(debounceTimerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.search, refreshTrigger]);

  const fetchTasks = async () => {
    try {
      if (mountedRef.current) {
        setLoading(true);
        setError("");
      }

      // Filter out empty values (guard against non-string just in case)
      const activeFilters = Object.fromEntries(
        Object.entries(filters).filter(
          ([, value]) => typeof value === "string" && value.trim() !== ""
        )
      );

      const response = await taskAPI.getTasks(activeFilters);

      const list = Array.isArray(response?.tasks) ? response.tasks : [];
      if (mountedRef.current) setTasks(list);
    } catch (err) {
      if (mountedRef.current) setError(handleApiError(err));
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  };

  const handleFilterChange = (filterName, value) => {
    setFilters((prev) => ({
      ...prev,
      [filterName]: value,
    }));
  };

  const clearFilters = () => {
    setFilters({
      status: "",
      priority: "",
      category: "",
      search: "",
    });
  };

  const handleTaskAction = async (taskId, action, data = {}) => {
    try {
      let response;

      switch (action) {
        case "update":
          response = await taskAPI.updateTask(taskId, data);
          break;
        case "delete":
          await taskAPI.deleteTask(taskId);
          setTasks((prev) => prev.filter((t) => t.id !== taskId));
          if (onTaskUpdate) onTaskUpdate();
          return;
        default:
          return;
      }

      // Update task in list safely
      if (response && response.task) {
        setTasks((prev) => prev.map((t) => (t.id === taskId ? response.task : t)));
      }

      if (onTaskUpdate) onTaskUpdate();
    } catch (err) {
      setError(handleApiError(err));
    }
  };

  const handlePrioritizeTasks = async () => {
    try {
      setPrioritizing(true);
      const incompleteTasks = tasks.filter((t) => t.status !== "completed");
      const taskIds = incompleteTasks.map((t) => t.id);

      const response = await aiAPI.prioritizeTasks(taskIds);

      // Reorder tasks based on AI prioritization
      const prioritizedTasks = Array.isArray(response?.prioritized_tasks)
        ? response.prioritized_tasks
        : [];
      const completedTasks = tasks.filter((t) => t.status === "completed");

      setTasks([...prioritizedTasks, ...completedTasks]);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setPrioritizing(false);
    }
  };

  const getFilteredTasksCount = () => {
    const activeFilters = Object.values(filters).filter(
      (value) => typeof value === "string" && value.trim() !== ""
    );
    return activeFilters.length > 0 ? tasks.length : null;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="loading-spinner mr-2" />
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
                onChange={(e) => handleFilterChange("search", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                className="input"
                value={filters.status}
                onChange={(e) => handleFilterChange("status", e.target.value)}
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
                onChange={(e) => handleFilterChange("priority", e.target.value)}
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
                onChange={(e) => handleFilterChange("category", e.target.value)}
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
                type="button"
              >
                {prioritizing ? (
                  <>
                    <div className="loading-spinner mr-2" />
                    Filtering...
                  </>
                ) : (
                  <>Filter</>
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
            {Object.values(filters).some(
              (f) => typeof f === "string" && f.trim() !== ""
            )
              ? "Try adjusting your filters or search terms."
              : "Get started by creating your first task!"}
          </p>
          <a href="/tasks/new" className="btn-primary">
            Create Task
          </a>
        </div>
      ) : (
        <div className="space-y-4">
          {tasks.map((task) => (
            <TaskItem key={task.id} task={task} onAction={handleTaskAction} />
          ))}
        </div>
      )}
    </div>
  );
};

export default TaskList;
