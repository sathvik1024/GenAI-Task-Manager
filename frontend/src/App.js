/**
 * Main App component with routing and authentication context.
 * Handles user authentication state and route protection.
 */

import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { authAPI, getAuthToken, getUser, setUser, setAuthToken } from './utils/api';

// Import pages and components
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import TaskForm from './pages/TaskForm';

// Create Auth Context
const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Auth Provider Component
const AuthProvider = ({ children }) => {
  const [user, setUserState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const token = getAuthToken();
      const savedUser = getUser();

      if (token && savedUser) {
        // Verify token is still valid
        try {
          const response = await authAPI.verifyToken();
          if (response.valid) {
            setUserState(savedUser);
            setIsAuthenticated(true);
          } else {
            // Token invalid, clear storage
            setAuthToken(null);
            setUser(null);
            setIsAuthenticated(false);
          }
        } catch (verifyError) {
          console.error('Token verification failed:', verifyError);
          // If verification fails, clear auth state
          setAuthToken(null);
          setUser(null);
          setIsAuthenticated(false);
        }
      } else {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setAuthToken(null);
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const login = async (credentials) => {
    try {
      console.log('Attempting login...');
      const response = await authAPI.login(credentials);
      console.log('Login response:', response);

      if (response.access_token && response.user) {
        // Set token first
        setAuthToken(response.access_token);

        // Verify token was set
        const storedToken = getAuthToken();
        console.log('Token verification after login:', storedToken ? 'token stored' : 'token missing');

        // Set user data
        setUser(response.user);
        setUserState(response.user);
        setIsAuthenticated(true);

        console.log('Login successful, user authenticated');
        return { success: true };
      } else {
        console.error('Invalid login response:', response);
        return { success: false, error: 'Invalid response from server' };
      }
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Login failed'
      };
    }
  };

  const signup = async (userData) => {
    try {
      console.log('Attempting signup...');
      const response = await authAPI.signup(userData);
      console.log('Signup response:', response);

      if (response.access_token && response.user) {
        setAuthToken(response.access_token);
        setUser(response.user);
        setUserState(response.user);
        setIsAuthenticated(true);
        console.log('Signup successful, user authenticated');
        return { success: true };
      } else {
        console.error('Invalid signup response:', response);
        return { success: false, error: 'Invalid response from server' };
      }
    } catch (error) {
      console.error('Signup error:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Signup failed'
      };
    }
  };

  const logout = () => {
    setAuthToken(null);
    setUser(null);
    setUserState(null);
    setIsAuthenticated(false);
  };

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    signup,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  console.log('ProtectedRoute - isAuthenticated:', isAuthenticated, 'loading:', loading);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="loading-spinner"></div>
        <span className="ml-2">Loading...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    console.log('User not authenticated, redirecting to login');
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Public Route Component (redirect if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  console.log('PublicRoute - isAuthenticated:', isAuthenticated, 'loading:', loading);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="loading-spinner"></div>
        <span className="ml-2">Loading...</span>
      </div>
    );
  }

  if (isAuthenticated) {
    console.log('User authenticated, redirecting to dashboard');
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// Main App Component
function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App min-h-screen bg-gray-50">
          <Routes>
            {/* Public routes */}
            <Route 
              path="/login" 
              element={
                <PublicRoute>
                  <Login />
                </PublicRoute>
              } 
            />
            
            {/* Protected routes */}
            <Route 
              path="/dashboard" 
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/tasks/new" 
              element={
                <ProtectedRoute>
                  <TaskForm />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/tasks/edit/:id" 
              element={
                <ProtectedRoute>
                  <TaskForm />
                </ProtectedRoute>
              } 
            />
            
            {/* Default redirect */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            
            {/* 404 page */}
            <Route 
              path="*" 
              element={
                <div className="min-h-screen flex items-center justify-center">
                  <div className="text-center">
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">404</h1>
                    <p className="text-gray-600 mb-4">Page not found</p>
                    <a href="/dashboard" className="btn-primary">
                      Go to Dashboard
                    </a>
                  </div>
                </div>
              } 
            />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
