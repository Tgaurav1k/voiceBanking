import { useState } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card } from '../components/ui/card';
import { Mic, Phone, Lock, UserCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';

const Home = ({ onLogin }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    pin: ''
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const endpoint = isRegister ? '/auth/register' : '/auth/login';
      const payload = isRegister ? formData : { phone: formData.phone, pin: formData.pin };
      
      const response = await axios.post(`${API}${endpoint}`, payload);
      toast.success(isRegister ? 'Account created successfully!' : 'Welcome back!');
      onLogin(response.data.token, response.data.name);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4" data-testid="home-page">
      <div className="max-w-6xl w-full grid md:grid-cols-2 gap-12 items-center">
        <motion.div 
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="space-y-6"
        >
          <div className="inline-flex items-center gap-3 bg-blue-100 px-6 py-3 rounded-full">
            <Mic className="text-blue-600" size={24} />
            <span className="text-blue-800 font-semibold text-lg">Voice Banking</span>
          </div>
          
          <h1 className="text-5xl lg:text-6xl font-bold text-gray-900 leading-tight" data-testid="hero-heading">
            Banking Made <span className="text-blue-600">Simple</span> with Voice
          </h1>
          
          <p className="text-xl text-gray-600 leading-relaxed">
            Secure voice-first banking for everyone. Check balance, transfer money, 
            pay bills - all with your voice.
          </p>
          
          <div className="flex flex-wrap gap-4 pt-4">
            <div className="flex items-center gap-3 bg-white px-6 py-4 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <Mic className="text-blue-600" size={24} />
              </div>
              <div>
                <p className="font-semibold text-gray-900">Voice Control</p>
                <p className="text-sm text-gray-500">Natural speech</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3 bg-white px-6 py-4 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                <Lock className="text-purple-600" size={24} />
              </div>
              <div>
                <p className="font-semibold text-gray-900">Secure</p>
                <p className="text-sm text-gray-500">PIN protected</p>
              </div>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <Card className="p-8 shadow-2xl border-0 bg-white/80 backdrop-blur" data-testid="auth-form">
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-3xl font-bold text-gray-900">
                  {isRegister ? 'Create Account' : 'Welcome Back'}
                </h2>
                <p className="text-gray-500 mt-2 text-lg">
                  {isRegister ? 'Start your voice banking journey' : 'Sign in to continue'}
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                {isRegister && (
                  <div className="space-y-2">
                    <label className="text-base font-medium text-gray-700 flex items-center gap-2">
                      <UserCircle size={20} />
                      Full Name
                    </label>
                    <Input
                      data-testid="name-input"
                      type="text"
                      placeholder="Enter your name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required
                      className="h-14 text-lg"
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-base font-medium text-gray-700 flex items-center gap-2">
                    <Phone size={20} />
                    Phone Number
                  </label>
                  <Input
                    data-testid="phone-input"
                    type="tel"
                    placeholder="Enter phone number"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    required
                    className="h-14 text-lg"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-base font-medium text-gray-700 flex items-center gap-2">
                    <Lock size={20} />
                    4-Digit PIN
                  </label>
                  <Input
                    data-testid="pin-input"
                    type="password"
                    placeholder="Enter 4-digit PIN"
                    value={formData.pin}
                    onChange={(e) => {
                      const val = e.target.value.replace(/\D/g, '').slice(0, 4);
                      setFormData({ ...formData, pin: val });
                    }}
                    required
                    maxLength={4}
                    className="h-14 text-lg tracking-widest"
                  />
                </div>

                <Button 
                  data-testid="submit-button"
                  type="submit" 
                  className="w-full h-14 text-lg font-semibold bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  disabled={loading}
                >
                  {loading ? 'Please wait...' : (isRegister ? 'Create Account' : 'Sign In')}
                </Button>
              </form>

              <div className="text-center pt-4">
                <button
                  data-testid="toggle-auth-button"
                  onClick={() => setIsRegister(!isRegister)}
                  className="text-blue-600 hover:text-blue-700 font-medium text-base"
                >
                  {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Register"}
                </button>
              </div>
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default Home;