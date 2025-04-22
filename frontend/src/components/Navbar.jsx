import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, LogOut, User, Home, MessageSquare, History, BarChart2 } from 'lucide-react';
import { useAuth } from './AuthContext';

const NavBar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="border-b border-gray-700 bg-gray-900/70 backdrop-blur-sm sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo and brand */}
          <div className="flex items-center gap-2">
            <Shield className="h-8 w-8 text-blue-400" />
            <span className="font-bold text-white text-lg">SOC Analyst</span>
          </div>
          
          {/* Main navigation */}
          <nav className="hidden md:block">
            <ul className="flex space-x-8">
              <li>
                <Link to="/" className="text-gray-300 hover:text-white flex items-center gap-2">
                  <Home className="w-4 h-4" />
                  Home
                </Link>
              </li>
              <li>
                <Link to="/chat" className="text-gray-300 hover:text-white flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" />
                  Analysis
                </Link>
              </li>
              <li>
                <Link to="/dashboard" className="text-gray-300 hover:text-white flex items-center gap-2">
                  <BarChart2 className="w-4 h-4" />
                  Dashboard
                </Link>
              </li>
              <li>
                <Link to="/history" className="text-gray-300 hover:text-white flex items-center gap-2">
                  <History className="w-4 h-4" />
                  History
                </Link>
              </li>
            </ul>
          </nav>
          
          {/* User menu */}
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-300">
              <span className="hidden md:inline">Welcome, </span>
              <span className="font-medium text-white">{user?.username || 'Analyst'}</span>
            </div>
            <button 
              onClick={handleLogout}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden md:inline">Logout</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default NavBar;