import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Mic, MicOff, LogOut, User, DollarSign, ArrowUpRight, ArrowDownLeft, Receipt } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import VoiceRecorder from '../components/VoiceRecorder';

const Dashboard = ({ token, userName, onLogout }) => {
  const [account, setAccount] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [avatarState, setAvatarState] = useState('idle');
  const [currentOperation, setCurrentOperation] = useState(null);
  const [operationData, setOperationData] = useState({});
  const audioRef = useRef(null);

  useEffect(() => {
    fetchAccount();
    fetchTransactions();
  }, []);

  const fetchAccount = async () => {
    try {
      const response = await axios.get(`${API}/account`, { params: { token } });
      setAccount(response.data);
    } catch (error) {
      toast.error('Failed to fetch account');
    }
  };

  const fetchTransactions = async () => {
    try {
      const response = await axios.get(`${API}/transactions`, { params: { token, limit: 5 } });
      setTransactions(response.data);
    } catch (error) {
      toast.error('Failed to fetch transactions');
    }
  };

  const handleAudioRecording = async (blob) => {
    try {
      setIsListening(false);
      setAvatarState('listening');
      
      const formData = new FormData();
      formData.append('file', blob, 'audio.webm');
      
      const response = await axios.post(`${API}/voice/transcribe`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const text = response.data.text;
      setTranscript(text);
      
      await processVoiceCommand(text);
    } catch (error) {
      toast.error('Failed to process voice command');
      setAvatarState('idle');
    }
  };

  const processVoiceCommand = async (text) => {
    try {
      const intentResponse = await axios.post(`${API}/intent/recognize`, { text });
      const intent = intentResponse.data.intent;
      
      let responseText = '';
      
      switch (intent) {
        case 'check_balance':
          responseText = `Your current balance is ${account.balance.toFixed(2)} dollars`;
          break;
          
        case 'mini_statement':
          await fetchTransactions();
          const recentCount = Math.min(transactions.length, 3);
          responseText = `You have ${recentCount} recent transactions. ${transactions.slice(0, 3).map(t => 
            `${t.type === 'debit' ? 'Paid' : 'Received'} ${t.amount.toFixed(2)} dollars`
          ).join('. ')}`;
          break;
          
        case 'transfer_money':
          setCurrentOperation('transfer');
          responseText = 'Please enter the recipient phone number and amount';
          break;
          
        case 'pay_bill':
          setCurrentOperation('bill');
          responseText = 'Please enter the bill type and amount';
          break;
          
        case 'help':
          responseText = 'You can check balance, transfer money, pay bills, or view recent transactions. Just speak naturally!';
          break;
          
        default:
          responseText = 'I did not understand that. Try saying check balance, transfer money, or pay bill';
      }
      
      await speakResponse(responseText);
    } catch (error) {
      toast.error('Failed to process command');
      setAvatarState('idle');
    }
  };

  const speakResponse = async (text) => {
    try {
      setAvatarState('speaking');
      
      const response = await axios.post(
        `${API}/voice/synthesize`, 
        null,
        { 
          params: { text, voice: 'nova' },
          responseType: 'blob'
        }
      );
      
      const audioUrl = URL.createObjectURL(response.data);
      const audio = new Audio(audioUrl);
      
      audio.onended = () => {
        setAvatarState('idle');
        URL.revokeObjectURL(audioUrl);
      };
      
      await audio.play();
    } catch (error) {
      console.error('Speech synthesis failed:', error);
      setAvatarState('idle');
    }
  };

  const handleTransfer = async () => {
    if (!operationData.phone || !operationData.amount) {
      toast.error('Please enter phone number and amount');
      return;
    }
    
    try {
      await axios.post(`${API}/transaction/transfer`, {
        recipient_phone: operationData.phone,
        amount: parseFloat(operationData.amount),
        description: 'Voice transfer'
      }, { params: { token } });
      
      toast.success('Transfer successful!');
      fetchAccount();
      fetchTransactions();
      setCurrentOperation(null);
      setOperationData({});
      
      await speakResponse('Transfer completed successfully');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Transfer failed');
    }
  };

  const handleBillPay = async () => {
    if (!operationData.billType || !operationData.amount) {
      toast.error('Please enter bill type and amount');
      return;
    }
    
    try {
      await axios.post(`${API}/transaction/bill-pay`, {
        bill_type: operationData.billType,
        amount: parseFloat(operationData.amount),
        description: `${operationData.billType} bill payment`
      }, { params: { token } });
      
      toast.success('Bill paid successfully!');
      fetchAccount();
      fetchTransactions();
      setCurrentOperation(null);
      setOperationData({});
      
      await speakResponse('Bill payment completed successfully');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Bill payment failed');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50" data-testid="dashboard-page">
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center">
              <Mic className="text-white" size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Voice Banking</h1>
              <p className="text-sm text-gray-500">Welcome, {userName}</p>
            </div>
          </div>
          
          <Button 
            data-testid="logout-button"
            onClick={onLogout} 
            variant="outline" 
            className="flex items-center gap-2 h-11 px-6"
          >
            <LogOut size={18} />
            Logout
          </Button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <Card className="p-6 bg-gradient-to-br from-blue-600 to-purple-600 text-white border-0 shadow-xl" data-testid="balance-card">
              <div className="flex items-center gap-3 mb-4">
                <DollarSign size={24} />
                <p className="text-lg opacity-90">Account Balance</p>
              </div>
              <h2 className="text-5xl font-bold mb-2" data-testid="balance-amount">
                ${account?.balance?.toFixed(2) || '0.00'}
              </h2>
              <p className="text-sm opacity-75">Account: {account?.account_number || 'Loading...'}</p>
            </Card>

            <Card className="p-8 text-center shadow-lg" data-testid="avatar-card">
              <motion.div
                animate={{
                  scale: avatarState === 'speaking' ? [1, 1.05, 1] : 1,
                }}
                transition={{ repeat: avatarState === 'speaking' ? Infinity : 0, duration: 0.8 }}
                className="mx-auto w-48 h-48 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center mb-6 shadow-2xl"
              >
                {avatarState === 'listening' && <Mic className="text-white" size={64} />}
                {avatarState === 'speaking' && <Mic className="text-white animate-pulse" size={64} />}
                {avatarState === 'idle' && <User className="text-white" size={64} />}
              </motion.div>
              
              <div className="space-y-3">
                <p className="text-xl font-semibold text-gray-900">
                  {avatarState === 'listening' && 'Listening...'}
                  {avatarState === 'speaking' && 'Speaking...'}
                  {avatarState === 'idle' && 'Ready to help'}
                </p>
                
                <div className="flex justify-center">
                  <VoiceRecorder onRecordingComplete={handleAudioRecording} />
                </div>
                
                {transcript && (
                  <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-4 p-4 bg-blue-50 rounded-lg"
                  >
                    <p className="text-sm text-gray-600 mb-1">You said:</p>
                    <p className="text-base font-medium text-gray-900" data-testid="transcript-text">{transcript}</p>
                  </motion.div>
                )}
              </div>
            </Card>
          </div>

          <div className="lg:col-span-2 space-y-6">
            <Card className="p-6 shadow-lg">
              <h3 className="text-2xl font-bold text-gray-900 mb-4">Quick Actions</h3>
              <div className="grid sm:grid-cols-2 gap-4">
                <Button 
                  data-testid="check-balance-btn"
                  onClick={() => processVoiceCommand('check balance')}
                  className="h-24 flex flex-col items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-lg"
                >
                  <DollarSign size={28} />
                  Check Balance
                </Button>
                
                <Button 
                  data-testid="transfer-money-btn"
                  onClick={() => setCurrentOperation('transfer')}
                  className="h-24 flex flex-col items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-lg"
                >
                  <ArrowUpRight size={28} />
                  Transfer Money
                </Button>
                
                <Button 
                  data-testid="pay-bill-btn"
                  onClick={() => setCurrentOperation('bill')}
                  className="h-24 flex flex-col items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-lg"
                >
                  <Receipt size={28} />
                  Pay Bill
                </Button>
                
                <Button 
                  data-testid="view-statement-btn"
                  onClick={() => processVoiceCommand('show transactions')}
                  className="h-24 flex flex-col items-center justify-center gap-2 bg-orange-600 hover:bg-orange-700 text-lg"
                >
                  <Receipt size={28} />
                  Mini Statement
                </Button>
              </div>
            </Card>

            <AnimatePresence>
              {currentOperation === 'transfer' && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <Card className="p-6 shadow-lg" data-testid="transfer-form">
                    <h3 className="text-2xl font-bold text-gray-900 mb-4">Transfer Money</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-base font-medium text-gray-700 mb-2">Recipient Phone</label>
                        <Input
                          data-testid="recipient-phone-input"
                          type="tel"
                          placeholder="Enter phone number"
                          value={operationData.phone || ''}
                          onChange={(e) => setOperationData({ ...operationData, phone: e.target.value })}
                          className="h-12 text-lg"
                        />
                      </div>
                      <div>
                        <label className="block text-base font-medium text-gray-700 mb-2">Amount ($)</label>
                        <Input
                          data-testid="transfer-amount-input"
                          type="number"
                          placeholder="Enter amount"
                          value={operationData.amount || ''}
                          onChange={(e) => setOperationData({ ...operationData, amount: e.target.value })}
                          className="h-12 text-lg"
                        />
                      </div>
                      <div className="flex gap-3">
                        <Button 
                          data-testid="confirm-transfer-btn"
                          onClick={handleTransfer} 
                          className="flex-1 h-12 text-lg bg-blue-600 hover:bg-blue-700"
                        >
                          Confirm Transfer
                        </Button>
                        <Button 
                          data-testid="cancel-transfer-btn"
                          onClick={() => { setCurrentOperation(null); setOperationData({}); }}
                          variant="outline"
                          className="flex-1 h-12 text-lg"
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              )}

              {currentOperation === 'bill' && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <Card className="p-6 shadow-lg" data-testid="bill-pay-form">
                    <h3 className="text-2xl font-bold text-gray-900 mb-4">Pay Bill</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-base font-medium text-gray-700 mb-2">Bill Type</label>
                        <Input
                          data-testid="bill-type-input"
                          type="text"
                          placeholder="e.g., Electricity, Water, Internet"
                          value={operationData.billType || ''}
                          onChange={(e) => setOperationData({ ...operationData, billType: e.target.value })}
                          className="h-12 text-lg"
                        />
                      </div>
                      <div>
                        <label className="block text-base font-medium text-gray-700 mb-2">Amount ($)</label>
                        <Input
                          data-testid="bill-amount-input"
                          type="number"
                          placeholder="Enter amount"
                          value={operationData.amount || ''}
                          onChange={(e) => setOperationData({ ...operationData, amount: e.target.value })}
                          className="h-12 text-lg"
                        />
                      </div>
                      <div className="flex gap-3">
                        <Button 
                          data-testid="confirm-bill-pay-btn"
                          onClick={handleBillPay} 
                          className="flex-1 h-12 text-lg bg-green-600 hover:bg-green-700"
                        >
                          Pay Bill
                        </Button>
                        <Button 
                          data-testid="cancel-bill-pay-btn"
                          onClick={() => { setCurrentOperation(null); setOperationData({}); }}
                          variant="outline"
                          className="flex-1 h-12 text-lg"
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              )}
            </AnimatePresence>

            <Card className="p-6 shadow-lg" data-testid="transactions-card">
              <h3 className="text-2xl font-bold text-gray-900 mb-4">Recent Transactions</h3>
              <div className="space-y-3">
                {transactions.length === 0 ? (
                  <p className="text-gray-500 text-center py-8 text-lg">No transactions yet</p>
                ) : (
                  transactions.map((t) => (
                    <div 
                      key={t.transaction_id} 
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
                      data-testid="transaction-item"
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                          t.type === 'debit' ? 'bg-red-100' : 'bg-green-100'
                        }`}>
                          {t.type === 'debit' ? 
                            <ArrowUpRight className="text-red-600" size={24} /> : 
                            <ArrowDownLeft className="text-green-600" size={24} />
                          }
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900 text-lg">{t.description}</p>
                          <p className="text-sm text-gray-500">
                            {new Date(t.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <p className={`text-xl font-bold ${
                        t.type === 'debit' ? 'text-red-600' : 'text-green-600'
                      }`}>
                        {t.type === 'debit' ? '-' : '+'}${t.amount.toFixed(2)}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
