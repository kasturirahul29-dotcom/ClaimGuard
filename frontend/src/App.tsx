import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

import AppLayout from './layout/AppLayout';
import Login from './pages/Login';
import Register from './pages/Register';
import Policies from './pages/Policies';
import Claims from './pages/Claims';
import AdminFlagged from './pages/AdminFlagged';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

const PublicOnlyRoute = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  if (user) {
    return <Navigate to="/policies" replace />;
  }
  return <>{children}</>;
};

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        {/* Public Routes */}
        <Route index element={<Navigate to="/login" replace />} />
        <Route path="login" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
        <Route path="register" element={<PublicOnlyRoute><Register /></PublicOnlyRoute>} />
        
        {/* Protected Routes */}
        <Route path="policies" element={<ProtectedRoute><Policies /></ProtectedRoute>} />
        <Route path="claims" element={<ProtectedRoute><Claims /></ProtectedRoute>} />
        <Route path="admin/flagged" element={<ProtectedRoute><AdminFlagged /></ProtectedRoute>} />
      </Route>
    </Routes>
  );
}
