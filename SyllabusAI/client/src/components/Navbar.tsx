import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useState } from 'react';

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center gap-2 no-underline">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">S</span>
            </div>
            <span className="text-xl font-bold text-text">
              Syllabus<span className="text-primary">AI</span>
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-6">
            <Link to="/browse" className="text-text-secondary hover:text-primary transition-colors no-underline text-sm font-medium">
              Browse
            </Link>

            {isAuthenticated ? (
              <>
                <Link to="/dashboard" className="text-text-secondary hover:text-primary transition-colors no-underline text-sm font-medium">
                  Dashboard
                </Link>
                {user?.role === 'admin' && (
                  <Link to="/admin" className="text-text-secondary hover:text-primary transition-colors no-underline text-sm font-medium">
                    Admin
                  </Link>
                )}
                <div className="flex items-center gap-3 ml-2">
                  <div className="w-8 h-8 bg-primary-light rounded-full flex items-center justify-center">
                    <span className="text-white text-xs font-bold">
                      {user?.firstName?.[0]}{user?.lastName?.[0]}
                    </span>
                  </div>
                  <span className="text-sm font-medium text-text">{user?.firstName}</span>
                  <button
                    onClick={handleLogout}
                    className="text-sm text-text-secondary hover:text-red-500 transition-colors bg-transparent border-none cursor-pointer"
                  >
                    Logout
                  </button>
                </div>
              </>
            ) : (
              <div className="flex items-center gap-3">
                <Link to="/login" className="text-sm font-medium text-text-secondary hover:text-primary transition-colors no-underline">
                  Sign in
                </Link>
                <Link to="/register" className="text-sm font-medium bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark transition-colors no-underline">
                  Get Started
                </Link>
              </div>
            )}
          </div>

          <button
            className="md:hidden bg-transparent border-none cursor-pointer p-2"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            <div className="w-5 h-0.5 bg-text mb-1"></div>
            <div className="w-5 h-0.5 bg-text mb-1"></div>
            <div className="w-5 h-0.5 bg-text"></div>
          </button>
        </div>

        {menuOpen && (
          <div className="md:hidden pb-4 border-t border-border pt-4 flex flex-col gap-3">
            <Link to="/browse" className="text-text-secondary no-underline text-sm" onClick={() => setMenuOpen(false)}>Browse</Link>
            {isAuthenticated ? (
              <>
                <Link to="/dashboard" className="text-text-secondary no-underline text-sm" onClick={() => setMenuOpen(false)}>Dashboard</Link>
                {user?.role === 'admin' && (
                  <Link to="/admin" className="text-text-secondary no-underline text-sm" onClick={() => setMenuOpen(false)}>Admin</Link>
                )}
                <button onClick={() => { handleLogout(); setMenuOpen(false); }} className="text-left text-sm text-red-500 bg-transparent border-none cursor-pointer p-0">Logout</button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-text-secondary no-underline text-sm" onClick={() => setMenuOpen(false)}>Sign in</Link>
                <Link to="/register" className="text-primary font-medium no-underline text-sm" onClick={() => setMenuOpen(false)}>Get Started</Link>
              </>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}
