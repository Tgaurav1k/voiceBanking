import requests
import sys
import json
from datetime import datetime
import tempfile
import os

class VoiceBankingAPITester:
    def __init__(self, base_url="https://sql-project.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.user_name = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}: {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token and not params:
            params = {'token': self.token}
        elif self.token and params and 'token' not in params:
            params['token'] = self.token

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                if files:
                    # Remove Content-Type for file uploads
                    headers.pop('Content-Type', None)
                    response = requests.post(url, files=files, params=params)
                else:
                    response = requests.post(url, json=data, headers=headers, params=params)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if success and response.content:
                try:
                    response_data = response.json()
                    details += f", Response: {json.dumps(response_data, indent=2)[:200]}..."
                except:
                    details += f", Response: {str(response.content)[:100]}..."
            elif not success:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Error: {response.text[:100]}"

            self.log_test(name, success, details)
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_user_registration(self):
        """Test user registration"""
        timestamp = datetime.now().strftime('%H%M%S')
        test_data = {
            "name": f"Test User {timestamp}",
            "phone": f"555{timestamp}",
            "pin": "1234",
            "language_preference": "en"
        }
        
        success, response = self.run_test(
            "User Registration", 
            "POST", 
            "auth/register", 
            200, 
            data=test_data
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user_id']
            self.user_name = response['name']
            
        return success

    def test_user_login(self):
        """Test user login with existing credentials"""
        # Create a new user specifically for login test
        timestamp = datetime.now().strftime('%H%M%S')
        test_data = {
            "name": f"Login Test User {timestamp}",
            "phone": f"777{timestamp}",
            "pin": "9876",
            "language_preference": "en"
        }
        
        # Register user first
        success, response = self.run_test(
            "Register User for Login Test", 
            "POST", 
            "auth/register", 
            200, 
            data=test_data
        )
        
        if not success:
            return False
            
        # Now test login with same credentials
        login_data = {
            "phone": f"777{timestamp}",
            "pin": "9876"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        return success

    def test_get_account(self):
        """Test getting account information"""
        if not self.token:
            return False
            
        return self.run_test("Get Account", "GET", "account", 200)[0]

    def test_intent_recognition(self):
        """Test intent recognition"""
        test_cases = [
            {"text": "check my balance", "expected_intent": "check_balance"},
            {"text": "transfer money", "expected_intent": "transfer_money"},
            {"text": "pay electricity bill", "expected_intent": "pay_bill"},
            {"text": "show my transactions", "expected_intent": "mini_statement"},
            {"text": "help me", "expected_intent": "help"}
        ]
        
        all_passed = True
        for case in test_cases:
            success, response = self.run_test(
                f"Intent Recognition - {case['text'][:20]}...",
                "POST",
                "intent/recognize",
                200,
                data={"text": case["text"]}
            )
            
            if success and response.get('intent') != case['expected_intent']:
                self.log_test(
                    f"Intent Accuracy - {case['text'][:20]}...",
                    False,
                    f"Expected {case['expected_intent']}, got {response.get('intent')}"
                )
                all_passed = False
            elif success:
                self.log_test(
                    f"Intent Accuracy - {case['text'][:20]}...",
                    True,
                    f"Correctly identified as {response.get('intent')}"
                )
        
        return all_passed

    def test_transfer_money(self):
        """Test money transfer"""
        if not self.token:
            return False
            
        # First create a recipient user
        timestamp = datetime.now().strftime('%H%M%S')
        recipient_data = {
            "name": f"Recipient {timestamp}",
            "phone": f"666{timestamp}",
            "pin": "5678",
            "language_preference": "en"
        }
        
        success, _ = self.run_test(
            "Create Recipient User",
            "POST",
            "auth/register",
            200,
            data=recipient_data
        )
        
        if not success:
            return False
        
        # Now test transfer
        transfer_data = {
            "recipient_phone": f"666{timestamp}",
            "amount": 100.0,
            "description": "Test transfer"
        }
        
        return self.run_test(
            "Transfer Money",
            "POST",
            "transaction/transfer",
            200,
            data=transfer_data
        )[0]

    def test_bill_payment(self):
        """Test bill payment"""
        if not self.token:
            return False
            
        bill_data = {
            "bill_type": "Electricity",
            "amount": 50.0,
            "description": "Monthly electricity bill"
        }
        
        return self.run_test(
            "Bill Payment",
            "POST",
            "transaction/bill-pay",
            200,
            data=bill_data
        )[0]

    def test_get_transactions(self):
        """Test getting transaction history"""
        if not self.token:
            return False
            
        return self.run_test("Get Transactions", "GET", "transactions", 200)[0]

    def test_voice_transcription(self):
        """Test voice transcription endpoint"""
        # Test with invalid audio to check error handling
        try:
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_file:
                # Write minimal webm header (this won't actually work for real transcription)
                temp_file.write(b'dummy audio data for testing')
                temp_file_path = temp_file.name
            
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test.webm', f, 'audio/webm')}
                url = f"{self.base_url}/api/voice/transcribe"
                response = requests.post(url, files=files)
            
            os.unlink(temp_file_path)
            
            # We expect this to fail with 500 due to invalid audio data
            if response.status_code == 500:
                try:
                    error_data = response.json()
                    if 'Transcription failed' in error_data.get('detail', ''):
                        self.log_test(
                            "Voice Transcription Error Handling",
                            True,
                            "Correctly handled invalid audio file with proper error message"
                        )
                        return True
                except:
                    pass
            
            self.log_test(
                "Voice Transcription", 
                False, 
                f"Status: {response.status_code}, Response: {response.text[:100]}"
            )
            return False
            
        except Exception as e:
            self.log_test("Voice Transcription", False, f"Exception: {str(e)}")
            return False

    def test_speech_synthesis(self):
        """Test speech synthesis endpoint"""
        try:
            url = f"{self.base_url}/api/voice/synthesize"
            params = {"text": "Hello, this is a test", "voice": "nova"}
            
            response = requests.post(url, params=params)
            
            success = response.status_code == 200
            if success:
                # Check if we got audio data
                content_type = response.headers.get('content-type', '')
                if 'audio' in content_type:
                    details = f"Status: {response.status_code}, Content-Type: {content_type}, Size: {len(response.content)} bytes"
                else:
                    details = f"Status: {response.status_code}, Unexpected content type: {content_type}"
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:100]}"
            
            self.log_test("Speech Synthesis", success, details)
            return success
            
        except Exception as e:
            self.log_test("Speech Synthesis", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Voice Banking API Tests...")
        print("=" * 60)
        
        # Basic connectivity
        self.test_root_endpoint()
        
        # Authentication tests
        self.test_user_registration()
        self.test_user_login()
        
        # Account tests
        self.test_get_account()
        
        # Voice and AI tests
        self.test_intent_recognition()
        self.test_voice_transcription()
        self.test_speech_synthesis()
        
        # Banking operations (only if authenticated)
        if self.token:
            self.test_transfer_money()
            self.test_bill_payment()
            self.test_get_transactions()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            
        return self.tests_passed, self.tests_run, self.test_results

def main():
    tester = VoiceBankingAPITester()
    passed, total, results = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            'summary': {
                'passed': passed,
                'total': total,
                'success_rate': f"{(passed/total)*100:.1f}%"
            },
            'results': results
        }, f, indent=2)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())