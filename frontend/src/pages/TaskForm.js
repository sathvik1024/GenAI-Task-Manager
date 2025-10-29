/**
 * TaskForm component for creating and editing tasks.
 * Includes AI-powered task parsing and manual form input.
 */

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { taskAPI, aiAPI, handleApiError } from "../utils/api";

/* ------------------------------------------------------------------
   Date helpers for <input type="datetime-local">
------------------------------------------------------------------- */
const pad2 = (n) => String(n).padStart(2, "0");

const toInputValueFromDate = (d) => {
  const y = d.getFullYear();
  const m = pad2(d.getMonth() + 1);
  const day = pad2(d.getDate());
  const h = pad2(d.getHours());
  const min = pad2(d.getMinutes());
  return `${y}-${m}-${day}T${h}:${min}`;
};

const tryParseAsISO = (s) => {
  const normalized = /\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}/.test(s)
    ? s.replace(/\s+/, "T")
    : s;
  const d = new Date(normalized);
  return isNaN(d.getTime()) ? null : d;
};

const tryParseAsDMY = (s) => {
  const m = s
    .trim()
    .match(
      /^(\d{1,2})[-/](\d{1,2})[-/](\d{4})(?:\s+(\d{1,2})(?::(\d{2}))?)?$/i
    );
  if (!m) return null;
  const dd = parseInt(m[1], 10);
  const mm = parseInt(m[2], 10);
  const yyyy = parseInt(m[3], 10);
  let hh = m[4] ? parseInt(m[4], 10) : 23;
  let min = m[5] ? parseInt(m[5], 10) : 59;
  if (mm < 1 || mm > 12 || dd < 1 || dd > 31 || hh < 0 || hh > 23 || min < 0 || min > 59)
    return null;
  return new Date(yyyy, mm - 1, dd, hh, min, 0, 0);
};

const formatDateForInput = (value) => {
  if (!value) return "";
  try {
    if (value instanceof Date) return toInputValueFromDate(value);
    const s = String(value).trim();
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(s)) return s;
    const iso = tryParseAsISO(s);
    if (iso) return toInputValueFromDate(iso);
    const dmy = tryParseAsDMY(s);
    if (dmy) return toInputValueFromDate(dmy);
    const onlyDate = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (onlyDate) {
      const d = new Date(+onlyDate[1], +onlyDate[2] - 1, +onlyDate[3], 23, 59, 0, 0);
      return toInputValueFromDate(d);
    }
    return "";
  } catch {
    return "";
  }
};

/* Understands DMY with am/pm (e.g., "22-08-2025 9 PM") and ISO */
const parseServerDeadline = (value) => {
  if (!value) return "";
  try {
    if (value instanceof Date) return toInputValueFromDate(value);
    const s = String(value).trim();

    const dmyAmPm = s.match(
      /^(\d{1,2})[-/](\d{1,2})[-/](\d{4})\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)$/i
    );
    if (dmyAmPm) {
      const dd = +dmyAmPm[1];
      const mm = +dmyAmPm[2];
      const yyyy = +dmyAmPm[3];
      let hh = +dmyAmPm[4];
      const min = dmyAmPm[5] ? +dmyAmPm[5] : 0;
      const ampm = dmyAmPm[6].toLowerCase();
      if (ampm === "pm" && hh !== 12) hh += 12;
      if (ampm === "am" && hh === 12) hh = 0;
      if (mm < 1 || mm > 12 || dd < 1 || dd > 31 || hh < 0 || hh > 23 || min < 0 || min > 59)
        return "";
      return toInputValueFromDate(new Date(yyyy, mm - 1, dd, hh, min, 0, 0));
    }

    const iso = tryParseAsISO(s);
    if (iso) return toInputValueFromDate(iso);
    const dmy = tryParseAsDMY(s);
    if (dmy) return toInputValueFromDate(dmy);
    return formatDateForInput(s);
  } catch {
    return "";
  }
};

const TaskForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = Boolean(id);

  const [formData, setFormData] = useState({
    title: "",
    description: "",
    deadline: "",
    priority: "medium",
    category: "",
    subtasks: [],
  });

  const [aiInput, setAiInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showAiForm, setShowAiForm] = useState(!isEditing);
  const [subtaskInput, setSubtaskInput] = useState("");
  const [suggesting, setSuggesting] = useState(false);

  // Fetch task when editing
  const fetchTask = useCallback(async () => {
    try {
      setLoading(true);
      const { task } = await taskAPI.getTask(id);
      setFormData({
        title: task.title,
        description: task.description || "",
        deadline: parseServerDeadline(task.deadline),
        priority: task.priority || "medium",
        category: task.category || "",
        subtasks: task.subtasks || [],
      });
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (isEditing) fetchTask();
  }, [isEditing, fetchTask]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((p) => ({ ...p, [name]: value }));
  };

  const handleAiParse = async () => {
    if (!aiInput.trim()) {
      setError("Please enter a task description");
      return;
    }
    try {
      setAiLoading(true);
      setError("");
      setSuccess("");

      const { parsed_task: parsed } = await aiAPI.parseTask(aiInput);
      console.log("AI parsed ->", parsed); // helpful log

      setFormData({
        title: parsed?.title || "",
        description: parsed?.description || "",
        deadline: parseServerDeadline(parsed?.deadline),
        priority: parsed?.priority || "medium",
        category: parsed?.category || "",
        subtasks: parsed?.subtasks || [],
      });

      setShowAiForm(false);
      setSuccess("Task parsed successfully! Review and submit below.");
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setAiLoading(false);
    }
  };

  const handleCreateFromAi = async () => {
    if (!aiInput.trim()) {
      setError("Please enter a task description");
      return;
    }
    try {
      setAiLoading(true);
      setError("");
      setSuccess("");
      await aiAPI.createFromText(aiInput);
      setSuccess("Task created successfully!");
      setTimeout(() => navigate("/dashboard"), 900);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setAiLoading(false);
    }
  };

  const addSubtask = () => {
    const t = subtaskInput.trim();
    if (!t) return;
    setFormData((p) => ({ ...p, subtasks: [...p.subtasks, t] }));
    setSubtaskInput("");
  };

  const removeSubtask = (index) => {
    setFormData((p) => ({
      ...p,
      subtasks: p.subtasks.filter((_, i) => i !== index),
    }));
  };

  const handleSuggestSubtasks = async () => {
    if (!formData.title.trim()) {
      setError("Enter a title before asking AI to suggest subtasks");
      return;
    }
    try {
      setSuggesting(true);
      setError("");
      const res = await aiAPI.suggestSubtasks(
        formData.title.trim(),
        formData.description.trim()
      );
      const suggested = res?.suggested_subtasks || [];
      if (suggested.length) {
        setFormData((p) => ({
          ...p,
          subtasks: [...p.subtasks, ...suggested.filter(Boolean)],
          category: p.category || res?.suggested_category || "general",
          priority: p.priority || res?.suggested_priority || "medium",
        }));
        setSuccess("Subtasks suggested and added!");
      } else {
        setSuccess("No subtasks suggested for this title.");
      }
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setSuggesting(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!formData.title.trim()) {
      setError("Title is required");
      return;
    }

    try {
      setLoading(true);
      const payload = {
        ...formData,
        title: formData.title.trim(),
        description: formData.description.trim(),
        category: formData.category.trim(),
        deadline: formData.deadline || null,
        subtasks: (formData.subtasks || []).filter((s) => s && s.trim()),
      };

      if (isEditing) {
        await taskAPI.updateTask(id, payload);
        setSuccess("Task updated successfully!");
      } else {
        await taskAPI.createTask(payload);
        setSuccess("Task created successfully!");
      }

      setTimeout(() => navigate("/dashboard"), 900);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (loading && isEditing) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="loading-spinner mr-2"></div>
        <span>Loading task...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <button
            onClick={() => navigate("/dashboard")}
            className="text-primary-600 hover:text-primary-700 mb-4 flex items-center"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-3xl font-bold text-gray-900">
            {isEditing ? "Edit Task" : "Create New Task"}
          </h1>
          <p className="text-gray-600 mt-2">
            {isEditing
              ? "Update your task details below"
              : "Create a task manually or let AI parse it from natural language"}
          </p>
        </div>

        {error && (
          <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md mb-6">
            {success}
          </div>
        )}

        {!isEditing && showAiForm && (
          <div className="card mb-6">
            <div className="card-header">
              <h3 className="text-lg font-semibold text-gray-900">
                🤖 AI Task Parser
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                Describe your task in natural language and let AI extract the details
              </p>
            </div>
            <div className="card-content">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Describe your task
                  </label>
                  <textarea
                    className="textarea"
                    rows={4}
                    placeholder={`e.g., "Finish the quarterly report by Friday 5pm, high priority, work category"`}
                    value={aiInput}
                    onChange={(e) => setAiInput(e.target.value)}
                  />
                </div>

                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={handleAiParse}
                    disabled={aiLoading}
                    className="btn-primary flex items-center"
                  >
                    {aiLoading ? (
                      <>
                        <div className="loading-spinner mr-2"></div>
                        Parsing...
                      </>
                    ) : (
                      "🔍 Parse & Review"
                    )}
                  </button>

                  <button
                    onClick={handleCreateFromAi}
                    disabled={aiLoading}
                    className="btn-success flex items-center"
                  >
                    {aiLoading ? (
                      <>
                        <div className="loading-spinner mr-2"></div>
                        Creating...
                      </>
                    ) : (
                      "⚡ Create Directly"
                    )}
                  </button>

                  <button
                    onClick={() => setShowAiForm(false)}
                    className="btn-secondary"
                  >
                    Manual Form
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {(!showAiForm || isEditing) && (
          <div className="card">
            <div className="card-header">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">
                  Task Details
                </h3>
                {!isEditing && (
                  <button
                    onClick={() => setShowAiForm(true)}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    🤖 Use AI Parser
                  </button>
                )}
              </div>
            </div>

            <div className="card-content">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Title *
                  </label>
                  <input
                    type="text"
                    name="title"
                    required
                    className="input"
                    placeholder="Enter task title"
                    value={formData.title}
                    onChange={handleInputChange}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description
                  </label>
                  <textarea
                    name="description"
                    className="textarea"
                    rows={3}
                    placeholder="Enter task description"
                    value={formData.description}
                    onChange={handleInputChange}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Deadline
                    </label>
                    <input
                      type="datetime-local"
                      name="deadline"
                      className="input"
                      value={formData.deadline}
                      onChange={handleInputChange}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Priority
                    </label>
                    <select
                      name="priority"
                      className="input"
                      value={formData.priority}
                      onChange={handleInputChange}
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="urgent">Urgent</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Category
                  </label>
                  <input
                    type="text"
                    name="category"
                    className="input"
                    placeholder="e.g., work, personal, health"
                    value={formData.category}
                    onChange={handleInputChange}
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Subtasks
                    </label>
                    <button
                      type="button"
                      onClick={handleSuggestSubtasks}
                      disabled={suggesting}
                      className="text-sm text-primary-600 hover:text-primary-700"
                    >
                      {suggesting ? "Suggesting…" : "🤖 Suggest subtasks"}
                    </button>
                  </div>

                  <div className="flex space-x-2 mb-3">
                    <input
                      type="text"
                      className="input flex-1"
                      placeholder="Add a subtask"
                      value={subtaskInput}
                      onChange={(e) => setSubtaskInput(e.target.value)}
                      onKeyDown={(e) =>
                        e.key === "Enter" && (e.preventDefault(), addSubtask())
                      }
                    />
                    <button
                      type="button"
                      onClick={addSubtask}
                      className="btn-secondary"
                    >
                      Add
                    </button>
                  </div>

                  {formData.subtasks.length > 0 && (
                    <div className="space-y-2">
                      {formData.subtasks.map((subtask, index) => (
                        <div
                          key={`${subtask}-${index}`}
                          className="flex items-center space-x-2 p-2 bg-gray-50 rounded-md"
                        >
                          <span className="flex-1 text-sm">{subtask}</span>
                          <button
                            type="button"
                            onClick={() => removeSubtask(index)}
                            className="text-danger-600 hover:text-danger-700"
                            aria-label={`Remove subtask ${index + 1}`}
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex space-x-3 pt-4">
                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary flex items-center"
                  >
                    {loading ? (
                      <>
                        <div className="loading-spinner mr-2"></div>
                        {isEditing ? "Updating..." : "Creating..."}
                      </>
                    ) : isEditing ? (
                      "Update Task"
                    ) : (
                      "Create Task"
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={() => navigate("/dashboard")}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskForm;
