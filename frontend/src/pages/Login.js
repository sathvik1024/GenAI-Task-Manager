/**
 * Login and Signup page component.
 * Handles user authentication with form validation.
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../App";

const Login = () => {
  const navigate = useNavigate();
  const { login, signup } = useAuth();

  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    whatsapp_number: "", // ✅ WhatsApp e.g., +919876543210
  });

  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  // Handle input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
    if (errors.submit) {
      setErrors((prev) => ({ ...prev, submit: "" }));
    }
  };

  // Validate input
  const validateForm = () => {
    const newErrors = {};

    // username
    if (!formData.username.trim()) {
      newErrors.username = "Username is required";
    } else if (formData.username.trim().length < 3) {
      newErrors.username = "Username must be at least 3 characters";
    }

    // email (signup only)
    if (!isLogin) {
      if (!formData.email.trim()) {
        newErrors.email = "Email is required";
      } else if (!/^\S+@\S+\.\S+$/.test(formData.email.trim())) {
        newErrors.email = "Please enter a valid email";
      }
    }

    // password
    if (!formData.password) {
      newErrors.password = "Password is required";
    } else if (!isLogin && formData.password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    // confirm password (signup only)
    if (!isLogin && formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    // WhatsApp (signup only)
    if (!isLogin) {
      if (!formData.whatsapp_number.trim()) {
        newErrors.whatsapp_number = "WhatsApp number is required";
      } else if (!/^\+\d{10,15}$/.test(formData.whatsapp_number.trim())) {
        newErrors.whatsapp_number =
          "Enter valid WhatsApp number (e.g. +919876543210)";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Submit handler
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    setLoading(true);
    setErrors((prev) => ({ ...prev, submit: "" }));

    try {
      let result;
      if (isLogin) {
        result = await login({
          username: formData.username.trim(),
          password: formData.password,
        });
      } else {
        result = await signup({
          username: formData.username.trim(),
          email: formData.email.trim().toLowerCase(),
          password: formData.password,
          whatsapp_number: formData.whatsapp_number.trim(),
        });
      }

      if (result?.success) {
        navigate("/dashboard", { replace: true });
      } else {
        setErrors((prev) => ({
          ...prev,
          submit: result?.error || "Authentication failed",
        }));
      }
    } catch (err) {
      setErrors((prev) => ({
        ...prev,
        submit: "An unexpected error occurred",
      }));
    } finally {
      setLoading(false);
    }
  };

  // Switch between modes
  const toggleMode = () => {
    setIsLogin((prev) => !prev);
    setFormData({
      username: "",
      email: "",
      password: "",
      confirmPassword: "",
      whatsapp_number: "",
    });
    setErrors({});
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <div
            className="mx-auto h-12 w-12 bg-blue-600 rounded-lg flex items-center justify-center"
            aria-hidden="true"
          >
            <svg
              className="h-8 w-8 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
              />
            </svg>
          </div>
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            GenAI Task Manager
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {isLogin ? "Sign in to your account" : "Create your account"}
          </p>
        </div>

        {/* Card */}
        <div className="card">
          <div className="card-content">
            <form className="space-y-6" onSubmit={handleSubmit} noValidate>
              {errors.submit && (
                <div
                  className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md"
                  role="alert"
                >
                  {errors.submit}
                </div>
              )}

              {/* Username */}
              <div>
                <label
                  htmlFor="username"
                  className="block text-sm font-medium text-gray-700"
                >
                  Username
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  className={`input mt-1 ${
                    errors.username ? "border-danger-300" : ""
                  }`}
                  placeholder="Enter your username"
                  value={formData.username}
                  onChange={handleInputChange}
                  aria-invalid={!!errors.username}
                  aria-describedby={errors.username ? "username-error" : undefined}
                />
                {errors.username && (
                  <p id="username-error" className="mt-1 text-sm text-danger-600">
                    {errors.username}
                  </p>
                )}
              </div>

              {/* Email (Signup only) */}
              {!isLogin && (
                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Email
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    className={`input mt-1 ${
                      errors.email ? "border-danger-300" : ""
                    }`}
                    placeholder="you@example.com"
                    value={formData.email}
                    onChange={handleInputChange}
                    aria-invalid={!!errors.email}
                    aria-describedby={errors.email ? "email-error" : undefined}
                  />
                  {errors.email && (
                    <p id="email-error" className="mt-1 text-sm text-danger-600">
                      {errors.email}
                    </p>
                  )}
                </div>
              )}

              {/* WhatsApp (Signup only) */}
              {!isLogin && (
                <div>
                  <label
                    htmlFor="whatsapp_number"
                    className="block text-sm font-medium text-gray-700"
                  >
                    WhatsApp Number
                  </label>
                  <input
                    id="whatsapp_number"
                    name="whatsapp_number"
                    type="text"
                    className={`input mt-1 ${
                      errors.whatsapp_number ? "border-danger-300" : ""
                    }`}
                    placeholder="+919876543210"
                    value={formData.whatsapp_number}
                    onChange={handleInputChange}
                    aria-invalid={!!errors.whatsapp_number}
                    aria-describedby={
                      errors.whatsapp_number ? "wa-error" : undefined
                    }
                  />
                  {errors.whatsapp_number && (
                    <p id="wa-error" className="mt-1 text-sm text-danger-600">
                      {errors.whatsapp_number}
                    </p>
                  )}
                </div>
              )}

              {/* Password */}
              <div>
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-gray-700"
                >
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  className={`input mt-1 ${
                    errors.password ? "border-danger-300" : ""
                  }`}
                  placeholder="Enter your password"
                  value={formData.password}
                  onChange={handleInputChange}
                  aria-invalid={!!errors.password}
                  aria-describedby={errors.password ? "password-error" : undefined}
                />
                {errors.password && (
                  <p id="password-error" className="mt-1 text-sm text-danger-600">
                    {errors.password}
                  </p>
                )}
              </div>

              {/* Confirm Password (Signup only) */}
              {!isLogin && (
                <div>
                  <label
                    htmlFor="confirmPassword"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Confirm Password
                  </label>
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    className={`input mt-1 ${
                      errors.confirmPassword ? "border-danger-300" : ""
                    }`}
                    placeholder="Confirm your password"
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                    aria-invalid={!!errors.confirmPassword}
                    aria-describedby={
                      errors.confirmPassword ? "confirm-error" : undefined
                    }
                  />
                  {errors.confirmPassword && (
                    <p id="confirm-error" className="mt-1 text-sm text-danger-600">
                      {errors.confirmPassword}
                    </p>
                  )}
                </div>
              )}

              {/* Submit */}
              <div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full btn-primary flex justify-center items-center disabled:opacity-60"
                >
                  {loading ? (
                    <>
                      <div className="loading-spinner mr-2" />
                      {isLogin ? "Signing in..." : "Creating account..."}
                    </>
                  ) : isLogin ? (
                    "Sign in"
                  ) : (
                    "Create account"
                  )}
                </button>
              </div>

              {/* Switch mode */}
              <div className="text-center">
                <button
                  type="button"
                  onClick={toggleMode}
                  className="text-sm text-blue-600 hover:text-blue-500"
                >
                  {isLogin
                    ? "Don't have an account? Sign up"
                    : "Already have an account? Sign in"}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Tiny helper note */}
        <p className="text-center text-xs text-gray-500">
          Tip: WhatsApp number must include country code, e.g., +91…
        </p>
      </div>
    </div>
  );
};

export default Login;
