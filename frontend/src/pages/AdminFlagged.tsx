import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../context/AuthContext';
import type { Claim, PaginatedResponse } from '../types';
import { ShieldAlert, CheckCircle, XCircle } from 'lucide-react';
import { Navigate } from 'react-router-dom';

export default function AdminFlagged() {
  const api = useApi();
  const { user } = useAuth();
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);

  if (user?.role !== 'admin') {
    return <Navigate to="/claims" replace />;
  }

  const fetchFlagged = async () => {
    try {
      setLoading(true);
      const res = await api.get<PaginatedResponse<Claim>>('/claims/flagged/');
      setClaims(res.data.results);
    } catch (err) {
      console.error('Failed to fetch flagged claims', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFlagged();
  }, [api]);

  const handleReview = async (id: number, status: 'approved' | 'rejected') => {
    if (!window.confirm(`Are you sure you want to ${status} this flagged claim?`)) return;
    try {
      await api.patch(`/claims/${id}/review/`, { status });
      fetchFlagged();
    } catch (err) {
      console.error('Failed to review claim', err);
      alert('Failed to review claim.');
    }
  };

  return (
    <div className="container animate-fade-in-up">
      <div className="page-header">
        <div>
          <h1 className="page-title" style={{ color: 'var(--danger)' }}>Flagged Claims Queue</h1>
          <p style={{ color: 'var(--text-muted)' }}>High priority review needed for potential fraud.</p>
        </div>
      </div>

      <div className="glass-card" style={{ borderColor: 'rgba(239, 68, 68, 0.3)' }}>
        <div className="glass-table-container">
          <table className="glass-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Policy</th>
                <th>Submitted By</th>
                <th>Amount</th>
                <th>Details</th>
                <th>Fraud Reason</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '3rem' }}>Loading flagged queue...</td>
                </tr>
              ) : claims.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                    <ShieldAlert size={48} style={{ margin: '0 auto 1rem', opacity: 0.2 }} />
                    No flagged claims require review!
                  </td>
                </tr>
              ) : (
                claims.map(c => (
                  <tr key={c.id} style={{ background: 'rgba(239, 68, 68, 0.05)' }}>
                    <td style={{ fontWeight: 600 }}>#{c.id}</td>
                    <td style={{ color: 'var(--primary)' }}>{c.policy_number}</td>
                    <td>{c.submitted_by_username}</td>
                    <td style={{ fontWeight: 600 }}>${Number(c.claim_amount).toLocaleString()}</td>
                    <td style={{ fontSize: '0.875rem' }}>{c.description}</td>
                    <td style={{ color: 'var(--danger)', fontWeight: 600, fontSize: '0.875rem' }}>
                      {c.fraud_reason}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button onClick={() => handleReview(c.id, 'approved')} className="btn btn-outline" style={{ padding: '0.25rem 0.5rem', color: 'var(--success)', borderColor: 'var(--success-bg)' }} title="Approve">
                          <CheckCircle size={16} />
                        </button>
                        <button onClick={() => handleReview(c.id, 'rejected')} className="btn btn-outline" style={{ padding: '0.25rem 0.5rem', color: 'var(--danger)', borderColor: 'var(--danger-bg)' }} title="Reject">
                          <XCircle size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
