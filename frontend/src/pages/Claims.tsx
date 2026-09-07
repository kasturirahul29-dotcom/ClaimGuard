import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../context/AuthContext';
import type { Claim, Policy, PaginatedResponse } from '../types';
import { FileText, Plus, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

export default function Claims() {
  const api = useApi();
  const { user } = useAuth();
  const [claims, setClaims] = useState<Claim[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState('');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');

  const fetchClaims = async () => {
    try {
      setLoading(true);
      const res = await api.get<PaginatedResponse<Claim>>('/claims/');
      setClaims(res.data.results);
    } catch (err) {
      console.error('Failed to fetch claims', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchActivePolicies = async () => {
    if (user?.role !== 'customer') return;
    try {
      const res = await api.get<PaginatedResponse<Policy>>('/policies/?status=active');
      setPolicies(res.data.results);
    } catch (err) {
      console.error('Failed to fetch policies', err);
    }
  };

  useEffect(() => {
    fetchClaims();
    fetchActivePolicies();
  }, [api, user]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/claims/', {
        policy: selectedPolicy,
        claim_amount: amount,
        description: description
      });
      setShowForm(false);
      setSelectedPolicy('');
      setAmount('');
      setDescription('');
      fetchClaims();
    } catch (err: any) {
      console.error('Failed to create claim', err);
      const msg = err.response?.data ? JSON.stringify(err.response.data) : 'Failed to file claim.';
      alert(`Error: ${msg}`);
    }
  };

  const handleReview = async (id: number, status: 'approved' | 'rejected') => {
    if (!window.confirm(`Are you sure you want to ${status} this claim?`)) return;
    try {
      await api.patch(`/claims/${id}/review/`, { status });
      fetchClaims();
    } catch (err) {
      console.error('Failed to review claim', err);
      alert('Failed to review claim.');
    }
  };

  return (
    <div className="container animate-fade-in-up">
      <div className="page-header">
        <div>
          <h1 className="page-title">Claims Processing</h1>
          <p style={{ color: 'var(--text-muted)' }}>File and track insurance claims.</p>
        </div>
        {user?.role === 'customer' && !showForm && (
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={18} /> File New Claim
          </button>
        )}
      </div>

      {showForm && (
        <div className="glass-card" style={{ padding: '2rem', marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1.5rem' }}>File a Claim</h3>
          <form onSubmit={handleCreate} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            <div className="input-group" style={{ gridColumn: '1 / -1' }}>
              <label className="input-label">Select Active Policy</label>
              <select className="input-field" value={selectedPolicy} onChange={e => setSelectedPolicy(e.target.value)} required>
                <option value="" disabled>-- Select a Policy --</option>
                {policies.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.policy_number} ({p.policy_type}) - Coverage: ${p.coverage_amount}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="input-group">
              <label className="input-label">Claim Amount ($)</label>
              <input type="number" step="0.01" className="input-field" value={amount} onChange={e => setAmount(e.target.value)} required />
            </div>
            
            <div className="input-group" style={{ gridColumn: '1 / -1' }}>
              <label className="input-label">Description of Incident</label>
              <textarea className="input-field" rows={4} value={description} onChange={e => setDescription(e.target.value)} required />
            </div>
            
            <div style={{ gridColumn: '1 / -1', display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={policies.length === 0}>
                Submit Claim
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="glass-card">
        <div className="glass-table-container">
          <table className="glass-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Policy</th>
                {user?.role === 'admin' && <th>Submitted By</th>}
                <th>Amount</th>
                <th>Date Filed</th>
                <th>Status</th>
                <th>Details</th>
                {user?.role === 'admin' && <th>Review Actions</th>}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '3rem' }}>Loading claims...</td>
                </tr>
              ) : claims.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                    <FileText size={48} style={{ margin: '0 auto 1rem', opacity: 0.2 }} />
                    No claims found.
                  </td>
                </tr>
              ) : (
                claims.map(c => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600 }}>#{c.id}</td>
                    <td style={{ color: 'var(--primary)' }}>{c.policy_number}</td>
                    {user?.role === 'admin' && <td>{c.submitted_by_username}</td>}
                    <td style={{ fontWeight: 600 }}>${Number(c.claim_amount).toLocaleString()}</td>
                    <td>{c.date_filed}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className={`badge badge-${c.status}`}>{c.status}</span>
                        {c.fraud_flag && (
                          <AlertTriangle size={16} color="var(--warning)" title="Flagged by system" />
                        )}
                      </div>
                    </td>
                    <td style={{ fontSize: '0.875rem' }}>
                      <div style={{ maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={c.description}>
                        {c.description}
                      </div>
                      {user?.role === 'admin' && c.fraud_flag && c.fraud_reason && (
                        <div style={{ color: 'var(--warning)', marginTop: '0.25rem', fontSize: '0.75rem', fontWeight: 600 }}>
                          {c.fraud_reason}
                        </div>
                      )}
                    </td>
                    {user?.role === 'admin' && (
                      <td>
                        {c.status === 'pending' ? (
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button onClick={() => handleReview(c.id, 'approved')} className="btn btn-outline" style={{ padding: '0.25rem 0.5rem', color: 'var(--success)', borderColor: 'var(--success-bg)' }} title="Approve">
                              <CheckCircle size={16} />
                            </button>
                            <button onClick={() => handleReview(c.id, 'rejected')} className="btn btn-outline" style={{ padding: '0.25rem 0.5rem', color: 'var(--danger)', borderColor: 'var(--danger-bg)' }} title="Reject">
                              <XCircle size={16} />
                            </button>
                          </div>
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            by {c.reviewed_by_username || 'System'}
                          </span>
                        )}
                      </td>
                    )}
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
