import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, ShieldAlert, FileText, UserCircle } from 'lucide-react';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav style={{ padding: '1rem 2rem', background: 'rgba(0,0,0,0.3)', borderBottom: '1px solid rgba(255,255,255,0.05)', backdropFilter: 'blur(10px)' }}>
      <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-display)' }}>
          <ShieldAlert size={28} color="var(--primary)" />
          <span>Aegis<span style={{ color: 'var(--primary)' }}>Claims</span></span>
        </Link>
        
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
            <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
              <Link to="/policies" style={{ fontWeight: 500 }}>Policies</Link>
              <Link to="/claims" style={{ fontWeight: 500 }}>Claims</Link>
              {user.role === 'admin' && (
                <Link to="/admin/flagged" style={{ fontWeight: 500, color: 'var(--danger)' }}>Flagged Claims</Link>
              )}
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <UserCircle size={20} color="var(--text-muted)" />
                <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                  {user.username} <span style={{ opacity: 0.5 }}>({user.role})</span>
                </span>
              </div>
              <button onClick={handleLogout} className="btn btn-outline" style={{ padding: '0.4rem 0.75rem', fontSize: '0.875rem' }}>
                <LogOut size={16} /> Logout
              </button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: '1rem' }}>
            <Link to="/login" className="btn btn-outline">Login</Link>
            <Link to="/register" className="btn btn-primary">Register</Link>
          </div>
        )}
      </div>
    </nav>
  );
}
