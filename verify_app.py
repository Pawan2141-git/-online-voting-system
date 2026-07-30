import unittest
import io
from datetime import datetime, timedelta
from app import app
from models import db, User, Election, Candidate, VoteRecord, Vote, AuditLog

class MatDanEnhancementsTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()

        self.app_context = app.app_context()
        self.app_context.push()

        db.session.remove()
        db.drop_all()
        db.create_all()

        # Create admin
        admin = User(full_name='Chief Election Officer', email='admin@eci.gov.in', voter_id='ECI0001001', role='admin')
        admin.set_password('adminpass')
        
        # Create voter 1
        voter1 = User(
            full_name='Rajesh Sharma',
            email='rajesh@test.in',
            voter_id='DLX1234567',
            date_of_birth=datetime(1995, 5, 10).date(),
            state='Delhi (NCT)',
            constituency='New Delhi',
            role='voter'
        )
        voter1.set_password('voterpass')

        db.session.add_all([admin, voter1])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_dark_mode_and_headers(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('X-Frame-Options'), 'SAMEORIGIN')
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')

    def test_audit_logging(self):
        AuditLog.log('TEST_ACTION', 'Testing audit log creation')
        log = AuditLog.query.filter_by(action='TEST_ACTION').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.details, 'Testing audit log creation')

    def test_voter_eligibility_age_rules(self):
        # Underage registration (16 years old) -> Should fail
        underage_dob = (datetime.utcnow() - timedelta(days=16*365)).strftime('%Y-%m-%d')
        resp_underage = self.client.post('/register', data={
            'full_name': 'Minor Voter',
            'email': 'minor@test.in',
            'voter_id': 'MIN1234567',
            'date_of_birth': underage_dob,
            'state': 'Delhi (NCT)',
            'constituency': 'Chandni Chowk',
            'password': 'voterpassword',
            'confirm_password': 'voterpassword'
        })
        self.assertIn(b'must be at least 18 years old', resp_underage.data)

        # Valid adult registration (25 years old) -> Should succeed
        adult_dob = (datetime.utcnow() - timedelta(days=25*365)).strftime('%Y-%m-%d')
        resp_adult = self.client.post('/register', data={
            'full_name': 'Eligible Adult Voter',
            'email': 'adult@test.in',
            'voter_id': 'ADU1234567',
            'date_of_birth': adult_dob,
            'state': 'Maharashtra',
            'constituency': 'Mumbai South',
            'password': 'voterpassword',
            'confirm_password': 'voterpassword'
        }, follow_redirects=True)
        self.assertIn(b'Registration successful', resp_adult.data)

        new_voter = User.query.filter_by(voter_id='ADU1234567').first()
        self.assertIsNotNone(new_voter)
        self.assertTrue(new_voter.is_eligible_voter)
        self.assertEqual(new_voter.state, 'Maharashtra')

    def test_password_reset_flow(self):
        user = User.query.filter_by(email='rajesh@test.in').first()
        token = user.get_reset_token()
        self.assertTrue(user.verify_reset_token(token))

        # Perform password reset via route
        reset_resp = self.client.post(f'/reset-password/{token}', data={
            'password': 'newsecretpassword',
            'confirm_password': 'newsecretpassword'
        }, follow_redirects=True)
        self.assertEqual(reset_resp.status_code, 200)
        self.assertIn(b'password has been reset successfully', reset_resp.data)

        # Verify new password login
        login_resp = self.client.post('/login', data={
            'identity': 'DLX1234567',
            'password': 'newsecretpassword'
        }, follow_redirects=True)
        self.assertIn(b'Welcome back', login_resp.data)

    def test_bulk_voter_csv_import(self):
        # Log in as Admin
        self.client.post('/login', data={'identity': 'admin@eci.gov.in', 'password': 'adminpass'})

        csv_content = (
            "full_name,email,voter_id,password\n"
            "Sita Lakshmi,sita@test.in,KER4455667,voter123\n"
            "Ramesh Babu,ramesh@test.in,TNX1122334,voter123\n"
        )
        data = {
            'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'voters.csv')
        }

        import_resp = self.client.post('/admin/voters/import', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(import_resp.status_code, 200)
        self.assertIn(b'Successfully registered 2 voters', import_resp.data)

        # Verify voters were saved in database
        imported_voter = User.query.filter_by(voter_id='KER4455667').first()
        self.assertIsNotNone(imported_voter)
        self.assertEqual(imported_voter.full_name, 'Sita Lakshmi')

if __name__ == '__main__':
    unittest.main()
