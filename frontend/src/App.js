/**
 * Main App component with routing and authentication context.
 * Handles user authentication state and route protection.
 */

import React, { useState, useEffect, useMemo, createContext, useContext } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import {
  authAPI,
  getAuthToken,
  getUser,
  setUser as persistUser,
  setAuthToken,
} from "./utils/api";

// Pages
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import TaskForm from "./pages/TaskForm";

// -----------------------------
// Auth Context
// -----------------------------
const AuthContext = createContext(null);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
};

// -----------------------------
// Auth Provider
// -----------------------------
const AuthProvider = ({ children }) => {
  const [user, setUserState] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const token = getAuthToken();
        const savedUser = getUser();

        if (token && savedUser) {
          try {
            const res = await authAPI.verifyToken();
            if (res?.valid) {
              setUserState(savedUser);
              setIsAuthenticated(true);
            } else {
              setAuthToken(null);
              persistUser(null);
              setIsAuthenticated(false);
            }
          } catch {
            setAuthToken(null);
            persistUser(null);
            setIsAuthenticated(false);
          }
        } else {
          setIsAuthenticated(false);
        }
      } finally {
        setLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  const login = async (credentials) => {
    try {
      const res = await authAPI.login(credentials);
      if (res?.access_token && res?.user) {
        setUserState(res.user);
        setIsAuthenticated(true);
        return { success: true };
      }
      return { success: false, error: "Invalid response from server" };
    } catch (error) {
      return { success: false, error: error?.response?.data?.error || "Login failed" };
    }
  };

  const signup = async (userData) => {
    try {
      const res = await authAPI.signup(userData);
      if (res?.access_token && res?.user) {
        setUserState(res.user);
        setIsAuthenticated(true);
        return { success: true };
      }
      return { success: false, error: "Invalid response from server" };
    } catch (error) {
      return { success: false, error: error?.response?.data?.error || "Signup failed" };
    }
  };

  const logout = () => {
    setAuthToken(null);
    persistUser(null);
    setUserState(null);
    setIsAuthenticated(false);
  };

  const value = useMemo(
    () => ({ user, isAuthenticated, loading, login, signup, logout }),
    [user, isAuthenticated, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// -----------------------------
// Route Guards
// -----------------------------
const LoadingScreen = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="loading-spinner" />
    <span className="ml-2">Loading...</span>
  </div>
);

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
};

const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return children;
};

// -----------------------------
// App
// -----------------------------
function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            {/* Public */}
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <Login />
                </PublicRoute>
              }
            />

            {/* Protected */}
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

            {/* Default & 404 */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route
              path="*"
              element={
                <div className="min-h-screen flex items-center justify-center">
                  <div className="text-center">
                    <h1 className="text-4xl font-bold text-gray-900 mb-2">404</h1>
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
