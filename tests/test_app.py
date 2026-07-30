import pytest
from datetime import datetime, timedelta, timezone
import io
from app import app, db
from models import User, Election, Candidate, VoteRecord, Vote, ChatLog

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_voter_registration_and_validation(client):
    """Test voter registration with age and duplicate checks."""
    # Underage registration should fail
    underage_dob = (datetime.now(timezone.utc) - timedelta(days=16*365)).strftime('%Y-%m-%d')
    res = client.post('/register', data={
        'full_name': 'Young Elector',
        'email': 'young@example.com',
        'voter_id': 'YNG9990001',
        'date_of_birth': underage_dob,
        'state': 'Delhi (NCT)',
        'constituency': 'New Delhi',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert b"Voter Ineligible" in res.data or b"at least 18 years old" in res.data

    # Valid registration should succeed
    adult_dob = (datetime.now(timezone.utc) - timedelta(days=25*365)).strftime('%Y-%m-%d')
    res = client.post('/register', data={
        'full_name': 'Adult Elector',
        'email': 'adult@example.com',
        'voter_id': 'ADL1112223',
        'date_of_birth': adult_dob,
        'state': 'Delhi (NCT)',
        'constituency': 'New Delhi',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert b"Registration successful" in res.data

    # Duplicate EPIC voter_id registration should fail
    res2 = client.post('/register', data={
        'full_name': 'Duplicate Elector',
        'email': 'dup@example.com',
        'voter_id': 'ADL1112223',
        'date_of_birth': adult_dob,
        'state': 'Delhi (NCT)',
        'constituency': 'New Delhi',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert b"An account with this EPIC" in res2.data

def test_login_and_role_access_control(client):
    """Test login authentication and admin decorator protection."""
    with app.app_context():
        voter = User(full_name="Standard Voter", email="voter@example.com", voter_id="VTR12345", role="voter", is_verified=True)
        voter.set_password("voterpass")
        admin = User(full_name="ECI Admin", email="admin@eci.gov.in", voter_id="ADM12345", role="admin", is_verified=True)
        admin.set_password("adminpass")
        db.session.add_all([voter, admin])
        db.session.commit()

    # Voter login
    res = client.post('/login', data={'identity': 'voter@example.com', 'password': 'voterpass'}, follow_redirects=True)
    assert b"Welcome back, Standard Voter!" in res.data

    # Voter attempting to access admin dashboard should be restricted
    res_admin = client.get('/admin/dashboard', follow_redirects=True)
    assert b"Access restricted to administrators only" in res_admin.data

    client.get('/logout')

    # Admin login
    res_adm_login = client.post('/login', data={'identity': 'admin@eci.gov.in', 'password': 'adminpass'}, follow_redirects=True)
    assert b"CEO Dashboard" in res_adm_login.data or b"Electoral Roll" in res_adm_login.data

def test_direct_registration_and_login_flow(client):
    """Test that registration automatically enables immediate login without email verification requirement."""
    adult_dob = (datetime.now(timezone.utc) - timedelta(days=22*365)).strftime('%Y-%m-%d')
    res_reg = client.post('/register', data={
        'full_name': 'New Elector',
        'email': 'newelector@example.com',
        'voter_id': 'NEW1112223',
        'date_of_birth': adult_dob,
        'state': 'Delhi (NCT)',
        'constituency': 'New Delhi',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert b"Registration successful" in res_reg.data

    # Immediate login should succeed
    res_login = client.post('/login', data={'identity': 'newelector@example.com', 'password': 'password123'}, follow_redirects=True)
    assert b"Welcome back, New Elector!" in res_login.data


def test_election_creation_and_voting_flow(client):
    """Test election creation, candidate addition, vote casting, and single-vote constraint."""
    now = datetime.now(timezone.utc)
    with app.app_context():
        admin = User(full_name="ECI Officer", email="admin@eci.gov.in", voter_id="ADM001", role="admin", is_verified=True)
        admin.set_password("admin123")
        voter = User(full_name="Rajesh Voter", email="rajesh@example.com", voter_id="DLX1001", role="voter", is_verified=True)
        voter.set_password("voter123")
        db.session.add_all([admin, voter])
        db.session.commit()

        election = Election(
            title="Assembly Election 2026",
            description="State Legislative Assembly Voting",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=24),
            status="active"
        )
        db.session.add(election)
        db.session.commit()

        c1 = Candidate(election_id=election.id, name="Candidate Alpha", party="Party A")
        c2 = Candidate(election_id=election.id, name="Candidate Beta", party="Party B")
        db.session.add_all([c1, c2])
        db.session.commit()
        
        election_id = election.id
        c1_id = c1.id

    # Log in as voter and cast vote
    client.post('/login', data={'identity': 'rajesh@example.com', 'password': 'voter123'}, follow_redirects=True)
    res_vote = client.post(f'/voter/vote/{election_id}', data={'candidate_id': c1_id}, follow_redirects=True)
    assert b"Your vote for &quot;Candidate Alpha&quot; has been recorded" in res_vote.data or b"recorded successfully" in res_vote.data

    # Second vote attempt should be blocked
    res_double_vote = client.post(f'/voter/vote/{election_id}', data={'candidate_id': c1_id}, follow_redirects=True)
    assert b"already cast your vote" in res_double_vote.data or b"not currently open" in res_double_vote.data

    with app.app_context():
        assert VoteRecord.query.filter_by(election_id=election_id).count() == 1
        assert Vote.query.filter_by(election_id=election_id).count() == 1

def test_api_chat_endpoint(client):
    """Test AI Chatbot API endpoint and intelligent response fallback."""
    res = client.post('/api/chat', json={'message': 'How do I cast my vote on this portal?'})
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['status'] == 'success'
    assert 'MatDan' in json_data['message'] or 'Vote' in json_data['message']

def test_admin_export_endpoints(client):
    """Test CSV and PDF election result exports."""
    now = datetime.now(timezone.utc)
    with app.app_context():
        admin = User(full_name="ECI Officer", email="admin@eci.gov.in", voter_id="ADM001", role="admin", is_verified=True)
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()

        election = Election(
            title="General Election 2026",
            start_time=now - timedelta(hours=2),
            end_time=now + timedelta(hours=10),
            status="active"
        )
        db.session.add(election)
        db.session.commit()

        c = Candidate(election_id=election.id, name="Test Candidate", party="Test Party")
        db.session.add(c)
        db.session.commit()
        election_id = election.id

    client.post('/login', data={'identity': 'admin@eci.gov.in', 'password': 'admin123'}, follow_redirects=True)
    
    # Test CSV Export
    res_csv = client.get(f'/admin/export/{election_id}/csv')
    assert res_csv.status_code == 200
    assert res_csv.content_type == 'text/csv; charset=utf-8' or 'text/csv' in res_csv.content_type
    assert b"General Election 2026" in res_csv.data

    # Test PDF Export
    res_pdf = client.get(f'/admin/export/{election_id}/pdf')
    assert res_pdf.status_code == 200
    assert res_pdf.content_type == 'application/pdf'
    assert res_pdf.data.startswith(b'%PDF')

