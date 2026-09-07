import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../context/AuthContext';
import type { Policy, PaginatedResponse } from '../types';
import { FileText, Plus, CheckCircle, Clock } from 'lucide-react';

export default function Policies() {
  const api = useApi();
  const { user } = useAuth();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [type, setType] = useState<'auto' | 'health' | 'property'>('auto');
  const [coverage, setCoverage] = useState('');
  const [premium, setPremium] = useState('');
  const [startDate, setStartDate] = useState('');

  const fetchPolicies = async () => {
    try {
      setLoading(true);
      const res = await api.get<PaginatedResponse<Policy>>('/policies/');
      setPolicies(res.data.results);
    } catch (err) {
      console.error('Failed to fetch policies', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
  }, [api]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/policies/', {
        policy_type: type,
        coverage_amount: coverage,
        premium: premium,
        start_date: startDate
      });
      setShowForm(false);
      setCoverage('');
      setPremium('');
      setStartDate('');
      fetchPolicies();
    } catch (err) {
      console.error('Failed to create policy', err);
      alert('Failed to create policy. Check inputs.');
    }
  };

  const handleActivate = async (id: number) => {
    if (!window.confirm('Activate this policy?')) return;
    try {
      await api.patch(`/policies/${id}/activate/`, { status: 'active' });
      fetchPolicies();
    } catch (err) {
      console.error('Failed to activate policy', err);
      alert('Failed to activate policy.');
    }
  };

  return (
    <div className="container animate-fade-in-up">
      <div className="page-header">
        <div>
          <h1 className="page-title">Insurance Policies</h1>
          <p style={{ color: 'var(--text-muted)' }}>Manage and review coverage plans.</p>
        </div>
        {user?.role === 'customer' && !showForm && (
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={18} /> New Policy Request
          </button>
        )}
      </div>

      {showForm && (
        <div className="glass-card" style={{ padding: '2rem', marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1.5rem' }}>Request New Policy</h3>
          <form onSubmit={handleCreate} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            <div className="input-group">
              <label className="input-label">Policy Type</label>
              <select className="input-field" value={type} onChange={e => setType(e.target.value as any)} required>
                <option value="auto">Auto Insurance</option>
                <option value="health">Health Insurance</option>
                <option value="property">Property Insurance</option>
              </select>
            </div>
            
            <div className="input-group">
              <label className="input-label">Coverage Amount ($)</label>
              <input type="number" step="0.01" className="input-field" value={coverage} onChange={e => setCoverage(e.target.value)} required />
            </div>
            
            <div className="input-group">
              <label className="input-label">Premium ($)</label>
              <input type="number" step="0.01" className="input-field" value={premium} onChange={e => setPremium(e.target.value)} required />
            </div>
            
            <div className="input-group">
              <label className="input-label">Start Date</label>
              <input type="date" className="input-field" value={startDate} onChange={e => setStartDate(e.target.value)} required />
            </div>
            
            <div style={{ gridColumn: '1 / -1', display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary">Submit Request</button>
            </div>
          </form>
        </div>
      )}

      <div className="glass-card">
        <div className="glass-table-container">
          <table className="glass-table">
            <thead>
              <tr>
                <th>Policy Number</th>
                {user?.role === 'admin' && <th>User</th>}
                <th>Type</th>
                <th>Coverage</th>
                <th>Premium</th>
                <th>Start Date</th>
                <th>Status</th>
                {user?.role === 'admin' && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '3rem' }}>Loading policies...</td>
                </tr>
              ) : policies.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                    <FileText size={48} style={{ margin: '0 auto 1rem', opacity: 0.2 }} />
                    No policies found.
                  </td>
                </tr>
              ) : (
                policies.map(p => (
                  <tr key={p.id}>
                    <td style={{ fontWeight: 600, color: 'var(--primary)' }}>{p.policy_number || 'Pending'}</td>
                    {user?.role === 'admin' && <td>{p.user_username}</td>}
                    <td style={{ textTransform: 'capitalize' }}>{p.policy_type}</td>
                    <td>${Number(p.coverage_amount).toLocaleString()}</td>
                    <td>${Number(p.premium).toLocaleString()}</td>
                    <td>{p.start_date}</td>
                    <td>
                      <span className={`badge badge-${p.status}`}>
                        {p.status.replace('_', ' ')}
                      </span>
                    </td>
                    {user?.role === 'admin' && (
                      <td>
                        {p.status === 'pending_activation' && (
                          <button onClick={() => handleActivate(p.id)} className="btn btn-primary" style={{ padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}>
                            <CheckCircle size={14} /> Activate
                          </button>
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
