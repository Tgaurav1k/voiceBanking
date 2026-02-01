import { useState, useEffect } from 'react';
import '@/App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import { Toaster } from './components/ui/sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState(null);
  const [userName, setUserName] = useState('');

  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    const storedName = localStorage.getItem('userName');
    if (storedToken) {
      setToken(storedToken);
      setUserName(storedName || '');
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogin = (token, name) => {
    setToken(token);
    setUserName(name);
    setIsAuthenticated(true);
    localStorage.setItem('token', token);
    localStorage.setItem('userName', name);
  };

  const handleLogout = () => {
    setToken(null);
    setUserName('');
    setIsAuthenticated(false);
    localStorage.removeItem('token');
    localStorage.removeItem('userName');
  };

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route 
            path="/" 
            element={
              isAuthenticated ? 
                <Navigate to="/dashboard" replace /> : 
                <Home onLogin={handleLogin} />
            } 
          />
          <Route 
            path="/dashboard" 
            element={
              isAuthenticated ? 
                <Dashboard token={token} userName={userName} onLogout={handleLogout} /> : 
                <Navigate to="/" replace />
            } 
          />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;