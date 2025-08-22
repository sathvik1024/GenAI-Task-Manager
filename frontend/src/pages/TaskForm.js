/**
 * TaskForm component for creating and editing tasks.
 * Includes AI-powered task parsing and manual form input.
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { taskAPI, aiAPI, handleApiError } from '../utils/api';

const TaskForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = Boolean(id);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    deadline: '',
    priority: 'medium',
    category: '',
    subtasks: []
  });

  const [aiInput, setAiInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showAiForm, setShowAiForm] = useState(!isEditing);
  const [subtaskInput, setSubtaskInput] = useState('');

  useEffect(() => {
    if (isEditing) {
      fetchTask();
    }
  }, [id, isEditing]);

  const fetchTask = async () => {
    try {
      setLoading(true);
      const response = await taskAPI.getTask(id);
      const task = response.task;
      
      setFormData({
        title: task.title,
        description: task.description || '',
        deadline: task.deadline ? task.deadline.slice(0, 16) : '', // Format for datetime-local input
        priority: task.priority,
        category: task.category || '',
        subtasks: task.subtasks || []
      });
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleAiParse = async () => {
    if (!aiInput.trim()) {
      setError('Please enter a task description');
      return;
    }

    try {
      setAiLoading(true);
      setError('');

      const response = await aiAPI.parseTask(aiInput);
      const parsed = response.parsed_task;
      
      setFormData({
        title: parsed.title,
        description: parsed.description || '',
        deadline: parsed.deadline ? parsed.deadline.slice(0, 16) : '',
        priority: parsed.priority,
        category: parsed.category || '',
        subtasks: parsed.subtasks || []
      });
      
      setShowAiForm(false);
      setSuccess('Task parsed successfully! Review and submit below.');
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setAiLoading(false);
    }
  };

  const handleCreateFromAi = async () => {
    if (!aiInput.trim()) {
      setError('Please enter a task description');
      return;
    }

    try {
      setAiLoading(true);
      setError('');

      const response = await aiAPI.createFromText(aiInput);
      setSuccess('Task created successfully!');
      
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setAiLoading(false);
    }
  };

  const addSubtask = () => {
    if (subtaskInput.trim()) {
      setFormData(prev => ({
        ...prev,
        subtasks: [...prev.subtasks, subtaskInput.trim()]
      }));
      setSubtaskInput('');
    }
  };

  const removeSubtask = (index) => {
    setFormData(prev => ({
      ...prev,
      subtasks: prev.subtasks.filter((_, i) => i !== index)
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.title.trim()) {
      setError('Title is required');
      return;
    }

    try {
      setLoading(true);
      setError('');
      
      const taskData = {
        ...formData,
        deadline: formData.deadline || null
      };

      if (isEditing) {
        await taskAPI.updateTask(id, taskData);
        setSuccess('Task updated successfully!');
      } else {
        await taskAPI.createTask(taskData);
        setSuccess('Task created successfully!');
      }
      
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
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
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-primary-600 hover:text-primary-700 mb-4 flex items-center"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-3xl font-bold text-gray-900">
            {isEditing ? 'Edit Task' : 'Create New Task'}
          </h1>
          <p className="text-gray-600 mt-2">
            {isEditing 
              ? 'Update your task details below'
              : 'Create a task manually or let AI parse it from natural language'
            }
          </p>
        </div>

        {/* Error/Success Messages */}
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

        {/* AI Input Form */}
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
                    placeholder="e.g., 'Finish the quarterly report by Friday 5pm, high priority, work category'"
                    value={aiInput}
                    onChange={(e) => setAiInput(e.target.value)}
                  />
                </div>
                
                <div className="flex space-x-3">
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
                      '🔍 Parse & Review'
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
                      '⚡ Create Directly'
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

        {/* Manual Task Form */}
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
                {/* Title */}
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

                {/* Description */}
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

                {/* Deadline and Priority */}
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

                {/* Category */}
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

                {/* Subtasks */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Subtasks
                  </label>
                  
                  {/* Add Subtask */}
                  <div className="flex space-x-2 mb-3">
                    <input
                      type="text"
                      className="input flex-1"
                      placeholder="Add a subtask"
                      value={subtaskInput}
                      onChange={(e) => setSubtaskInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addSubtask())}
                    />
                    <button
                      type="button"
                      onClick={addSubtask}
                      className="btn-secondary"
                    >
                      Add
                    </button>
                  </div>
                  
                  {/* Subtask List */}
                  {formData.subtasks.length > 0 && (
                    <div className="space-y-2">
                      {formData.subtasks.map((subtask, index) => (
                        <div key={index} className="flex items-center space-x-2 p-2 bg-gray-50 rounded-md">
                          <span className="flex-1 text-sm">{subtask}</span>
                          <button
                            type="button"
                            onClick={() => removeSubtask(index)}
                            className="text-danger-600 hover:text-danger-700"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Submit Buttons */}
                <div className="flex space-x-3 pt-4">
                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary flex items-center"
                  >
                    {loading ? (
                      <>
                        <div className="loading-spinner mr-2"></div>
                        {isEditing ? 'Updating...' : 'Creating...'}
                      </>
                    ) : (
                      isEditing ? 'Update Task' : 'Create Task'
                    )}
                  </button>
                  
                  <button
                    type="button"
                    onClick={() => navigate('/dashboard')}
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
