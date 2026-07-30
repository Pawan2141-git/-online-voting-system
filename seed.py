from app import app
from models import db, User, Election, Candidate, VoteRecord, Vote
from datetime import datetime, timedelta, timezone

def seed_database():
    with app.app_context():
        # Create tables
        db.create_all()

        # Check if Admin already exists
        admin = User.query.filter_by(email='admin@eci.gov.in').first()
        if not admin:
            admin = User(
                full_name='Chief Election Officer (ECI)',
                email='admin@eci.gov.in',
                voter_id='ECI0001001',
                role='admin',
                is_verified=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print("--> Seeded Admin: admin@eci.gov.in / admin123 (EPIC No: ECI0001001)")
        else:
            print("--> Admin user already exists.")

        # Seed Sample Indian Voters
        sample_voters = [
            ("Rajesh Kumar Sharma", "rajesh.sharma@example.in", "DLX1234567", "voter123", datetime(1992, 5, 15).date(), "Delhi (NCT)", "New Delhi"),
            ("Priya Patel", "priya.patel@example.in", "GUJ9876543", "voter123", datetime(1995, 8, 22).date(), "Gujarat", "Ahmedabad West"),
            ("Amitabh Banerjee", "amit.banerjee@example.in", "WBK5544332", "voter123", datetime(1988, 11, 10).date(), "West Bengal", "Kolkata South"),
            ("Sunita Reddy", "sunita.reddy@example.in", "TSH8877665", "voter123", datetime(1999, 2, 4).date(), "Telangana", "Hyderabad"),
            ("Vikram Singh", "vikram.singh@example.in", "UPM4433221", "voter123", datetime(2001, 12, 19).date(), "Uttar Pradesh", "Varanasi")
        ]

        voter_objs = []
        for name, email, voter_id, pwd, dob, st, const in sample_voters:
            u = User.query.filter_by(email=email).first()
            if not u:
                u = User(full_name=name, email=email, voter_id=voter_id, date_of_birth=dob, state=st, constituency=const, role='voter', is_verified=True)
                u.set_password(pwd)
                db.session.add(u)
                voter_objs.append(u)

        
        db.session.commit()
        print(f"--> Seeded {len(voter_objs)} sample Indian voters.")


        # Check if sample Indian election exists
        sample_election = Election.query.filter_by(title="2026 Lok Sabha General Election - New Delhi Parliamentary Constituency").first()
        now = datetime.now(timezone.utc)

        if not sample_election:
            sample_election = Election(
                title="2026 Lok Sabha General Election - New Delhi Parliamentary Constituency",
                description="Official Digital Voting Portal for New Delhi Constituency. Vote for your Member of Parliament (MP) to represent your voice in Lok Sabha.",
                start_time=now - timedelta(hours=3),
                end_time=now + timedelta(days=7),
                status='active'
            )
            db.session.add(sample_election)
            db.session.flush()

            # Add candidates with Indian party symbols
            c1 = Candidate(
                election_id=sample_election.id,
                name="Dr. Ananya Verma",
                party="Bharatiya People's Party (Symbol: 🪷 Lotus)",
                photo_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=300&auto=format&fit=crop&q=80",
                bio="Former IAS Officer & Social Reformer. Focus on digital infrastructure, urban green transport, youth employment, and AI education initiatives."
            )
            c2 = Candidate(
                election_id=sample_election.id,
                name="Rajeshwar Rao",
                party="National Progressive Congress (Symbol: ✋ Hand)",
                photo_url="https://images.unsplash.com/photo-1560250097-0b93528c311a?w=300&auto=format&fit=crop&q=80",
                bio="Experienced 2-term MLA & Economist. Advocating healthcare subsidization, public education reform, and small business tax relief."
            )
            c3 = Candidate(
                election_id=sample_election.id,
                name="Gurpreet Singh Ahluwalia",
                party="Aam Jan Parishad (Symbol: 🧹 Broom)",
                photo_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&auto=format&fit=crop&q=80",
                bio="RTI Activist & Anti-Corruption Campaigner. Pledged transparent governance, free clean drinking water, and mohalla clinics expansion."
            )
            c4 = Candidate(
                election_id=sample_election.id,
                name="NOTA (None Of The Above)",
                party="Electoral Right Option",
                photo_url="https://images.unsplash.com/photo-1584438784894-089d6a62b8fa?w=300&auto=format&fit=crop&q=80",
                bio="Select NOTA if you do not wish to vote for any of the contesting candidates in this election."
            )

            db.session.add_all([c1, c2, c3, c4])
            db.session.flush()

            print("--> Seeded Indian election with 4 candidates (including NOTA).")

            # Seed a couple of initial votes from sample voters
            all_voters = User.query.filter_by(role='voter').all()
            if len(all_voters) >= 3:
                vr1 = VoteRecord(user_id=all_voters[0].id, election_id=sample_election.id)
                v1 = Vote(election_id=sample_election.id, candidate_id=c1.id, voter_hash=Vote.generate_hash(all_voters[0].id, sample_election.id))
                
                vr2 = VoteRecord(user_id=all_voters[1].id, election_id=sample_election.id)
                v2 = Vote(election_id=sample_election.id, candidate_id=c2.id, voter_hash=Vote.generate_hash(all_voters[1].id, sample_election.id))

                db.session.add_all([vr1, v1, vr2, v2])

            db.session.commit()
            print("--> Seeded initial sample votes.")

        else:
            print("--> Sample election already exists.")

        print("=== MatDan India Seeding Complete ===")

if __name__ == '__main__':
    seed_database()
